# 검출 상자의 오차 분포 — infer_synthband.py 가 낸 jsonl 을 읽어 잰다.
#
# 리더가 받을 크롭이 정답 크롭에서 얼마나, 어느 쪽으로 어긋나는지를 낸다.
# 이 분포가 리더 학습의 흔들기 폭이 된다 — 지어낸 폭을 쓰지 않으려고 잰다.
#
# 세 축의 정의(부호 규약을 여기 한 번만 적는다):
#   포함률  area(정답 ∩ 예측) / area(정답).  1.0 = 정답을 전부 덮는다.
#            리더에게는 이게 가장 중한 축이다 — 덮이지 않은 부분은 숫자가 잘린다.
#   넓이비  area(예측) / area(정답).  1 보다 크면 여유, 작으면 좁다.
#   변별 치우침  변마다 정답 대비 **바깥으로** 얼마나 나갔는가를 정답 크기로 나눈 값.
#            left = (정답.x0 - 예측.x0) / 정답폭,  right = (예측.x1 - 정답.x1) / 정답폭,
#            top  = (정답.y0 - 예측.y0) / 정답높이, bottom = (예측.y1 - 정답.y1) / 정답높이.
#            양수 = 예측이 정답 밖으로 나갔다(여유), 음수 = 안으로 파고들었다(잘림).
#
# 검출 실패(pred=null)는 분포에서 **빼고 따로 센다.** 0 으로 채워 넣으면 실패가
# 분포의 꼬리로 위장돼 분위수가 조용히 나빠진다.
import argparse
import json
from pathlib import Path

import cv2
import numpy as np

QS = [1, 5, 25, 50, 75, 95, 99]


def inter_area(a, b):
    x0, y0 = max(a[0], b[0]), max(a[1], b[1])
    x1, y1 = min(a[2], b[2]), min(a[3], b[3])
    return max(0.0, x1 - x0) * max(0.0, y1 - y0)


def digit_field_containment(manifest_path):
    """숫자 필드가 예측 상자 안에 얼마나 들어오는가 — 밴드 포함률과 다른 축이다.

    정답 밴드는 **가장 넓은 값**을 담으려고 여백을 미리 뗀다
    (patterns/reserve-by-the-widest-value). 그래서 밴드 포함률이 0.73 이어도
    숫자는 멀쩡할 수 있고, 반대로 여백만 덮고 숫자 획을 자를 수도 있다.
    리더에게 해로운 것은 뒤쪽이라 따로 잰다.

    매니페스트의 rects['band'] 는 워프 **전** 패널 좌표의 숫자 필드다.
    quad_panel -> quad 가 같은 워프의 네 점 대응이므로 호모그래피를 되찾아
    필드 네 귀를 워프 후 좌표로 옮긴다. 기하를 새로 짜지 않는다.
    """
    out = {}
    for line in Path(manifest_path).read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        m = json.loads(line)
        band = next((r for r in m["rects"] if r[4] == "band"), None)
        if band is None:
            continue
        # 생성기가 워프 행렬을 직접 준다(2026-09-17). 구판은 quad_panel -> quad
        # 네 점 대응에서 호모그래피를 되찾았는데, 정답이 축정렬 사각형으로
        # 바뀌면서 그 대응이 사라졌다. 행렬을 받는 쪽이 애초에 정확하다.
        M = np.asarray(m["warp"], np.float32)
        corners = np.float32([[[band[0], band[1]], [band[2], band[1]],
                               [band[2], band[3]], [band[0], band[3]]]])
        out[f"{m['id']}.png"] = cv2.perspectiveTransform(corners, M)[0]
    return out


def poly_in_box_ratio(poly, box):
    """다각형 넓이 중 축정렬 상자 안에 드는 비율. 상자로 자른 뒤 넓이를 잰다."""
    clip = np.float32([[box[0], box[1]], [box[2], box[1]],
                       [box[2], box[3]], [box[0], box[3]]])
    inter, _ = cv2.intersectConvexConvex(np.float32(poly), clip)
    whole = cv2.contourArea(np.float32(poly))
    return float(inter) / whole if whole > 0 else 0.0


def compare(specs, manifest=None):
    """같은 세트·같은 정답에 여러 체크포인트를 나란히 놓는다.

    **같은 세트에서만 부른다.** 서로 다른 세트의 수치를 한 표에 놓으면
    분모가 달라 비교가 성립하지 않는다([[comparison-across-different-denominators]]).
    검출 실패는 분포에서 빼고 따로 센다 — 0 으로 채우면 꼬리로 위장된다.
    """
    fields = digit_field_containment(manifest) if manifest else None
    # **게이트 숫자는 필드 합격률이다** (2026-09-17 사람: "합성으로 99% 정도
    # (이런류의 모델을 만들때 최소한의 조건) 을 넘어선다면 실촬이미지로 검증").
    # IoU 로는 잴 수 없다 — IoU 가 낮은 장의 절반은 상자가 커서 낮은 것이라
    # 리더에게 무해하고, 반대로 IoU 가 높은데 숫자를 자르는 장이 있다
    # ([[proxy-metric-moves-against-the-goal]], 실촬 271장에서 19장 대 62장).
    # 합성에는 진짜 정답이 있다 — 매니페스트의 숫자 필드다.
    # 합격 = 검출됐고 **숫자 필드가 예측 상자에 100% 든다**. 검출 실패는 불합격.
    print(f"{'체크포인트':<18}{'n':>6}{'실패':>6}{'IoU중앙':>9}{'IoU최소':>9}"
          f"{'>=0.75':>8}" + (f"{'필드p1':>9}{'합격률':>9}" if fields else ""))
    for spec in specs:
        name, _, path = spec.partition("=")
        rows = [json.loads(l) for l in
                Path(path).read_text(encoding="utf-8").splitlines() if l.strip()]
        hit = [r for r in rows if r["pred"]]
        v = np.array([r["iou"] for r in hit])
        line = (f"{name:<18}{len(rows):>6}{len(rows)-len(hit):>6}"
                f"{np.median(v):>9.4f}{v.min():>9.4f}"
                f"{100*(v >= .75).mean():>7.1f}%")
        if fields:
            fv = np.array([poly_in_box_ratio(fields[r["file_name"]], r["pred"])
                           for r in hit])
            # 분모는 **전체 장**이다. 검출 실패를 빼고 세면 게이트가 무의미해진다.
            passed = int((fv >= 0.999).sum())
            line += f"{np.percentile(fv, 1):>9.4f}{100*passed/len(rows):>8.2f}%"
        print(line)
    print("  실패는 IoU 분포에서 뺐다. IoU최소는 **검출된 장 중** 최악이다.")
    if fields:
        print("  합격률 = 숫자 필드가 예측 상자에 100% 드는 장 / **전체 장**"
              " (검출 실패는 불합격). 이것이 게이트 숫자다.")
    return 0


def qline(name, v):
    qs = np.percentile(v, QS)
    return (f"  {name:<10} " + " ".join(f"p{q}={x:+.4f}" for q, x in zip(QS, qs))
            + f"  평균={v.mean():+.4f}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pred", required=True, help="infer_synthband.py 의 jsonl")
    ap.add_argument("--set", required=True, help="이미지가 있는 COCO 세트 디렉터리")
    ap.add_argument("--split", default="train2017")
    ap.add_argument("--worst-sheet", default=None)
    ap.add_argument("--worst-n", type=int, default=10)
    ap.add_argument("--manifest", default=None,
                    help="세트의 manifest.jsonl — 주면 숫자 필드 포함률까지 잰다")
    ap.add_argument("--compare", nargs="+", metavar="이름=jsonl",
                    help="여러 체크포인트를 같은 세트에서 나란히 놓는다")
    args = ap.parse_args()

    if args.compare:
        return compare(args.compare, args.manifest)

    rows = [json.loads(l) for l in
            Path(args.pred).read_text(encoding="utf-8").splitlines() if l.strip()]
    miss = [r for r in rows if r["pred"] is None]
    hit = [r for r in rows if r["pred"] is not None]

    for r in hit:
        g, p = r["gt"], r["pred"]
        gw, gh = g[2] - g[0], g[3] - g[1]
        ga = gw * gh
        r["contain"] = inter_area(g, p) / ga
        r["area_ratio"] = ((p[2] - p[0]) * (p[3] - p[1])) / ga
        r["bias"] = {"left": (g[0] - p[0]) / gw, "right": (p[2] - g[2]) / gw,
                     "top": (g[1] - p[1]) / gh, "bottom": (p[3] - g[3]) / gh}

    print(f"모집단: {args.pred}  n={len(rows)}  "
          f"검출 성공 {len(hit)} · 실패 {len(miss)}")
    if miss:
        print("  실패 장: " + ", ".join(r["file_name"] for r in miss[:10]))
    print("  (실패는 아래 분포에서 제외했다 — 0 으로 채우면 꼬리로 위장된다)")
    print(f"분위수 (n={len(hit)})")
    print(qline("IoU", np.array([r["iou"] for r in hit])))
    print(qline("포함률", np.array([r["contain"] for r in hit])))
    print(qline("넓이비", np.array([r["area_ratio"] for r in hit])))
    for e in ("left", "right", "top", "bottom"):
        print(qline(f"치우침.{e}", np.array([r["bias"][e] for r in hit])))
    full = sum(1 for r in hit if r["contain"] >= 0.999)
    print(f"  포함률 1.0(정답을 전부 덮음) {full}장 / {len(hit)} "
          f"· >=0.99 {sum(1 for r in hit if r['contain'] >= .99)}장 "
          f"· >=0.95 {sum(1 for r in hit if r['contain'] >= .95)}장")

    if args.manifest:
        fields = digit_field_containment(args.manifest)
        for r in hit:
            r["field"] = poly_in_box_ratio(fields[r["file_name"]], r["pred"])
        fv = np.array([r["field"] for r in hit])
        print(f"숫자 필드 포함률 (매니페스트 {args.manifest}, n={len(hit)})")
        print(qline("필드", fv))
        print(f"  1.0(필드를 통째로 덮음) {int((fv >= .999).sum())}장 "
              f"· >=0.99 {int((fv >= .99).sum())}장 "
              f"· <0.95 {int((fv < .95).sum())}장 "
              f"· <0.90 {int((fv < .90).sum())}장")

    if args.worst_sheet:
        key = "field" if args.manifest else "contain"
        worst = sorted(hit, key=lambda r: r[key])[:args.worst_n]
        worst = miss + worst          # 실패가 있으면 맨 앞에 둔다
        worst = worst[:args.worst_n]
        sheet(Path(args.set), args.split, worst, Path(args.worst_sheet))
    return 0


def sheet(root, split, rows, out_png, cols=5):
    cell_w, cell_h = 420, 520
    tiles = []
    for r in rows:
        img = cv2.imread(str(root / split / r["file_name"]))
        g = [int(v) for v in r["gt"]]
        cv2.rectangle(img, (g[0], g[1]), (g[2], g[3]), (0, 0, 230), 2)
        if r["pred"]:
            p = [int(v) for v in r["pred"]]
            cv2.rectangle(img, (p[0], p[1]), (p[2], p[3]), (0, 230, 0), 2)
            txt = (f"fld {r['field']:.3f}" if "field" in r
                   else f"cont {r['contain']:.3f}")
        else:
            txt = "MISS"
        cv2.putText(img, txt, (6, 26), cv2.FONT_HERSHEY_SIMPLEX, 0.8,
                    (0, 230, 0), 2)
        s = min(cell_w / img.shape[1], cell_h / img.shape[0])
        img = cv2.resize(img, (int(img.shape[1] * s), int(img.shape[0] * s)))
        pad = np.zeros((cell_h, cell_w, 3), np.uint8)
        pad[:img.shape[0], :img.shape[1]] = img
        tiles.append(pad)
    grid = [np.hstack(tiles[i:i + cols]) for i in range(0, len(tiles), cols)]
    w = max(g.shape[1] for g in grid)
    grid = [np.pad(g, ((0, 0), (0, w - g.shape[1]), (0, 0))) for g in grid]
    out_png.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(out_png), np.vstack(grid))
    print(f"최악 {len(rows)}장 시트 -> {out_png}")


if __name__ == "__main__":
    raise SystemExit(main())
