# 합성으로만 학습한 밴드 검출기를 **실촬**에서 잰다 — 도메인 격차의 크기.
#
# 왜 필요한가: 합성 세트 B·C 성적(1300/1300, IoU 중앙 0.956)은 **같은 생성기의
# 다른 시드**일 뿐이다. 마일스톤 문구가 이미 못박았다 — "검증도 같은 생성기라
# 일반화는 증명하지 못한다". 실촬 숫자가 없으면 아키텍처 결정을 할 수 없다.
#
# **프레이밍을 맞추는 것이 이 자의 핵심이다.** 합성 패널은 실촬 "전체 사진"이
# 아니라 기기 크롭에 가깝다(2026-09-17 실측: 밴드/프레임 넓이비가 합성 0.315 대
# 실촬 전체사진 0.108 로 2.9배 차이, 실촬 LCD 박스 기준으로는 0.391 로 근접).
# 전체 사진을 그냥 먹이면 분포 밖에서 재는 것이라 격차가 부풀려진다.
# 그래서 GM 쿼드에 **학습 캐시와 같은 여백**을 붙여 자른다 —
# build_cache_v2.framed_src_rect 를 그대로 부른다(BOX_MARGIN 이 정본).
#
# 정답은 사람 밴드 라벨(band_boxes.jsonl, 읽기 전용)이다.
# 기본 모집단은 기기 단절 분할의 **홀드아웃**이다 — train 쪽은 다른 작업이
# 학습에 쓸 수 있으므로 평가에 섞지 않는다.
#
# 한계(출력에 함께 찍는다): 이 홀드아웃에 가로형이 0장이다. 구조적이라
# 시드로 안 풀린다 — 가로형 밴드 라벨이 기기 두 종뿐이고 둘 다 train 으로 갔다.
#
# 사용:
#   python eval_synthband_real.py --ckpt yolox_out/synthband_v2_a2/best_ckpt.pth
import argparse
import json
import sys
from pathlib import Path

import cv2
import numpy as np
import torch

sys.path.insert(0, "D:/tmp/YOLOX")
from yolox.data.data_augment import ValTransform  # noqa: E402
from yolox.exp import get_exp  # noqa: E402
from yolox.utils import postprocess  # noqa: E402

from build_cache_v2 import framed_src_rect  # 프레이밍 정본  # noqa: E402
from gm_quads import quad_rows, load_gm_quads  # GM 쿼드 단일 출처  # noqa: E402
from band_exclusions import load_excluded  # 사람이 못 그린다고 선언한 장  # noqa: E402

HERE = Path(__file__).resolve().parent
DATUMO = HERE.parent / "upstream" / "datumo"
BANDS = HERE / "band_boxes.jsonl"
SPLIT = HERE / "_diag" / "band_device_split" / "band_device_split.json"
EXP = str(HERE / "yolox_synthband_exp.py")
WIDE = HERE / "_diag" / "wide_all" / "wide_ids.json"


def wide_ids():
    """가로형 id 집합 — 사람이 전량을 훑어 만든 목록이 정본이다
    (make_wide_survey.py, 2,512장 중 51장). 여기서 다시 판정하지 않는다."""
    return set(json.loads(WIDE.read_text(encoding="utf-8")))


def orient_block(rows, wide, indent="  "):
    """방향별로 갈라 인쇄한다. **세로형 성적과 가로형 성적을 한 줄로 뭉개면
    안 된다** — 가로형이 46장/258장이라 전체 중앙값은 세로형 중앙값과 거의
    같아지고, 가로형이 무너져도 숫자가 안 움직인다."""
    for name, sel in (("세로형", [r for r in rows if r["id"] not in wide]),
                      ("가로형", [r for r in rows if r["id"] in wide])):
        if not sel:
            print(f"{indent}{name} n=0 — 이 모집단은 {name} 성적을 재지 못한다")
            continue
        v = np.array([r["iou"] for r in sel])
        miss = sum(1 for r in sel if r["pred"] is None)
        print(f"{indent}{name} n={len(sel)} 실패 {miss} · IoU 중앙 "
              f"{np.median(v):.4f} p10 {np.percentile(v, 10):.4f} · "
              f">=0.5 {int((v >= .5).sum())} · >=0.75 {int((v >= .75).sum())}")


def analyze(path):
    """낸 결과를 깨 본다 — **IoU 한 축으로는 실패의 종류가 구분되지 않는다.**

    리더에게 해로운 것은 IoU 가 낮은 것이 아니라 **숫자가 잘리는 것**이다.
    상자가 정답보다 커서 IoU 가 0.6 인 장과, 상자가 정답을 반만 덮어 IoU 가
    0.6 인 장은 정반대 사건이다. 앞은 리더가 멀쩡히 읽고 뒤는 못 읽는다.
    그래서 세 축으로 가른다:

      포함률  area(정답 ∩ 예측) / area(정답).  1.0 = 정답을 전부 덮는다.
              **리더에게는 이게 가장 중한 축이다.**
      넓이비  area(예측) / area(정답).  1 보다 크면 여유, 작으면 좁다.
      IoU     게이트가 쓰는 축. 위 둘의 혼합이라 단독으로는 해석이 안 된다.

    부호 규약은 synthband_box_error.py 머리말과 같다 — 두 자가 다른 말을
    쓰면 수치를 나란히 못 놓는다.
    """
    rows = [json.loads(l) for l in
            Path(path).read_text(encoding="utf-8").splitlines() if l.strip()]
    wide = wide_ids()
    dev = {}
    dp = HERE / "device_labels.jsonl"
    if dp.exists():
        for l in dp.read_text(encoding="utf-8").splitlines():
            if l.strip():
                j = json.loads(l)
                dev[j["id"]] = j.get("model") or j.get("device") or "?"

    def inter(a, b):
        x0, y0 = max(a[0], b[0]), max(a[1], b[1])
        x1, y1 = min(a[2], b[2]), min(a[3], b[3])
        return max(0.0, x1 - x0) * max(0.0, y1 - y0)

    for r in rows:
        g = r["gt"]
        ga = (g[2] - g[0]) * (g[3] - g[1])
        if r["pred"] and ga > 0:
            p_ = r["pred"]
            r["contain"] = inter(g, p_) / ga
            r["area_ratio"] = ((p_[2] - p_[0]) * (p_[3] - p_[1])) / ga
        else:
            r["contain"] = r["area_ratio"] = None

    print(f"모집단 {path}  n={len(rows)}")
    for name, sel in (("전체", rows),
                      ("세로형", [r for r in rows if r["id"] not in wide]),
                      ("가로형", [r for r in rows if r["id"] in wide])):
        if not sel:
            continue
        hit = [r for r in sel if r["pred"]]
        miss = len(sel) - len(hit)
        c = np.array([r["contain"] for r in hit])
        a = np.array([r["area_ratio"] for r in hit])
        v = np.array([r["iou"] for r in hit])
        print()
        print(f"[{name}] n={len(sel)} · 검출 실패 {miss}")
        print(f"  검출된 {len(hit)}장 안에서:")
        print(f"    포함률  p1={np.percentile(c,1):.3f} p10={np.percentile(c,10):.3f} "
              f"중앙={np.median(c):.3f}  |  1.0 {int((c>=.999).sum())}장 "
              f">=0.99 {int((c>=.99).sum())}장 <0.95 {int((c<.95).sum())}장")
        print(f"    넓이비  p10={np.percentile(a,10):.3f} 중앙={np.median(a):.3f} "
              f"p90={np.percentile(a,90):.3f}")
        # 변별 치우침 — 부호 규약은 synthband_box_error.py 머리말과 같다.
        # 양수 = 예측이 정답 밖으로 나갔다(여유), 음수 = 안으로 파고들었다(잘림).
        # 넓이비가 1 보다 큰데도 포함률이 낮으면 **크기가 아니라 위치** 문제다.
        # 어느 변이 파고드는지 알아야 처방이 갈린다.
        bias = {}
        for e in ("left", "right", "top", "bottom"):
            vals = []
            for r in hit:
                g, q = r["gt"], r["pred"]
                gw, gh = g[2] - g[0], g[3] - g[1]
                vals.append({"left": (g[0]-q[0])/gw, "right": (q[2]-g[2])/gw,
                             "top": (g[1]-q[1])/gh, "bottom": (q[3]-g[3])/gh}[e])
            bias[e] = np.asarray(vals)
        print("    치우침(+여유 / -파고듦, 정답 크기 대비)")
        for e in ("left", "right", "top", "bottom"):
            b = bias[e]
            print(f"      {e:<7} p10={np.percentile(b,10):+.3f} "
                  f"중앙={np.median(b):+.3f} p90={np.percentile(b,90):+.3f}"
                  f"  | 파고든 장 {int((b<0).sum())}")
        print(f"    IoU     p10={np.percentile(v,10):.3f} 중앙={np.median(v):.3f}")
        # IoU 가 낮은 장의 **종류**를 가른다. 분모는 반드시 그 부분집합이어야
        # 한다 — 전체에서 세어 놓고 "IoU<0.75 중"이라 적으면 80 > 41 처럼
        # 성립 불가능한 문장이 나온다(2026-09-17 실제로 냈다).
        low = [r for r in hit if r["iou"] < 0.75]
        loose = sum(1 for r in low if r["contain"] >= 0.99)
        tight = sum(1 for r in low if r["contain"] < 0.95)
        print(f"  IoU<0.75 {len(low)}장의 종류 — "
              f"정답을 다 덮었는데 상자가 큰 장(포함률>=0.99) {loose} · "
              f"정답을 파고든 장(포함률<0.95) {tight} · "
              f"나머지 {len(low)-loose-tight}")
        # IoU 가 높아도 파고들 수 있다 — 리더에게는 이쪽이 더 중하다.
        cut_ok = sum(1 for r in hit if r["contain"] < 0.95 and r["iou"] >= 0.75)
        print(f"  IoU>=0.75 인데 포함률<0.95 인 장 {cut_ok} "
              f"— **게이트가 통과시키는데 숫자가 잘릴 수 있는 장이다**")

    # ── 검출기가 '무엇을 밴드라 부르는가' ────────────────────────────────
    # 예측 상자와 정답 상자를 **같은 분모(GM 화면 쿼드)** 로 재서 나란히 놓는다.
    # measure_panel_stats.py 의 band / synth-band --vs glass 와 같은 정의라
    # 세 수치(사람 라벨 · 합성 라벨 · 검출기 출력)를 한 표에 놓을 수 있다.
    #
    # 왜 필요한가: IoU 가 낮을 때 '모델이 못 한다'와 '모델이 다른 규약을
    # 정확히 배웠다'는 처방이 정반대다. 뒤쪽이면 데이터를 늘려도 천장이다.
    gmq = {r["id"]: r for r in quad_rows()}
    for name, sel in (("세로형", [r for r in rows if r["id"] not in wide]),
                      ("가로형", [r for r in rows if r["id"] in wide])):
        gw_, gh_, pw_, ph_ = [], [], [], []
        for r in sel:
            g = gmq.get(r["id"])
            if g is None or not r["pred"]:
                continue
            q = np.asarray(g["quad"], float)
            W = q[:, 0].max() - q[:, 0].min()
            H = q[:, 1].max() - q[:, 1].min()
            if W <= 0 or H <= 0:
                continue
            gt, pr = r["gt"], r["pred"]
            gw_.append((gt[2]-gt[0])/W); gh_.append((gt[3]-gt[1])/H)
            pw_.append((pr[2]-pr[0])/W); ph_.append((pr[3]-pr[1])/H)
        if not gw_:
            continue
        print()
        print(f"[{name}] 밴드 규약 — 분모는 GM 화면 쿼드 (n={len(gw_)})")
        for lab, a_, b_ in (("폭 band_w/화면_w", gw_, pw_),
                            ("높이 band_h/화면_h", gh_, ph_)):
            a_, b_ = np.asarray(a_), np.asarray(b_)
            print(f"  {lab}")
            print(f"    사람 라벨 중앙={np.median(a_):.3f} "
                  f"[p10={np.percentile(a_,10):.3f} p90={np.percentile(a_,90):.3f}]")
            print(f"    검출기   중앙={np.median(b_):.3f} "
                  f"[p10={np.percentile(b_,10):.3f} p90={np.percentile(b_,90):.3f}]")

    if dev:
        from collections import defaultdict
        agg = defaultdict(list)
        for r in rows:
            agg[dev.get(r["id"], "라벨없음")].append(r)
        print()
        print("기기별 (검출 실패 / n · 포함률<0.95 장수) — 실패가 몰린 기기가 있나")
        for k, sel in sorted(agg.items(), key=lambda kv: -len(kv[1])):
            if len(sel) < 4:
                continue
            miss = sum(1 for r in sel if not r["pred"])
            cut = sum(1 for r in sel if r["contain"] is not None and r["contain"] < 0.95)
            mark = "  <-" if (miss + cut) * 3 > len(sel) else ""
            print(f"  {k:<28} {miss:>3}/{len(sel):<4} · 자름 {cut:>3}{mark}")
    return 0


def rect(quad):
    q = np.asarray(quad, float)
    return [q[:, 0].min(), q[:, 1].min(), q[:, 0].max(), q[:, 1].max()]


def iou(a, b):
    x0, y0 = max(a[0], b[0]), max(a[1], b[1])
    x1, y1 = min(a[2], b[2]), min(a[3], b[3])
    i = max(0.0, x1 - x0) * max(0.0, y1 - y0)
    u = (a[2]-a[0])*(a[3]-a[1]) + (b[2]-b[0])*(b[3]-b[1]) - i
    return i / u if u > 0 else 0.0


def compare(specs):
    """같은 모집단·같은 정답이어야 부른다. 층 중앙값만 보면 이상치 한 장이
    평균을 끌고 가는 것을 축의 효과로 읽는다([[same-seed-is-not-paired]] 의
    짝비교 절)."""
    data = {}
    for spec in specs:
        name, _, path = spec.partition("=")
        data[name] = {r["id"]: r for r in
                      (json.loads(l) for l in
                       Path(path).read_text(encoding="utf-8").splitlines()
                       if l.strip())}
    names = list(data)
    common = set.intersection(*(set(d) for d in data.values()))
    print(f"짝지은 장 {len(common)} (각 팔 " +
          " · ".join(f"{n} {len(data[n])}" for n in names) + ")")
    base = names[0]
    wide = wide_ids()
    groups = (("전체", sorted(common)),
              ("세로형", [i for i in sorted(common) if i not in wide]),
              ("가로형", [i for i in sorted(common) if i in wide]))
    for n in names[1:]:
        print(f"  {n} vs {base}")
        for gname, ids in groups:
            if not ids:
                print(f"    {gname:<4} n=0")
                continue
            d = np.array([data[n][i]["iou"] - data[base][i]["iou"] for i in ids])
            win = int((d > 0.01).sum())
            lose = int((d < -0.01).sum())
            print(f"    {gname:<4} 승 {win} · 패 {lose} · 무 {len(d)-win-lose}"
                  f"  | 짝차이 중앙 {np.median(d):+.4f} 평균 {d.mean():+.4f}")
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ckpt", required=True)
    ap.add_argument("--exp", default=EXP)
    ap.add_argument("--conf", type=float, default=0.25)
    ap.add_argument("--gmsrc", default="human", choices=("human", "detector"),
                    help="lcdcrop 일 때 무엇으로 자를까. human = 사람이 그린 LCD"
                         " 쿼드(배포에는 없는 오라클). detector = gmscreen 검출기"
                         " 출력 — **배포가 실제로 쓰는 것**")
    ap.add_argument("--frame", default="lcdcrop", choices=("lcdcrop", "photo"),
                    help="검출기에 무엇을 먹일까. lcdcrop = LCD 쿼드 + 여백으로"
                         " 자른 것(합성 분포에 맞춘 것). photo = 전체 혈당기"
                         " 사진 그대로(배포가 실제로 받는 것)")
    ap.add_argument("--side", default="scorable",
                    choices=("scorable", "holdout", "train", "all"),
                    help="scorable = 채점 가능한 전량(기본). 합성만으로 학습한"
                         " 모델은 실사진을 한 장도 안 보므로 기기 단절 분할이"
                         " 의미가 없다 — 정답이 있는 장은 전부 쓴다")
    ap.add_argument("--out", default=str(HERE / "_diag" / "synthband_real"))
    ap.add_argument("--analyze", metavar="jsonl",
                    help="낸 결과를 포함률·넓이비로 깨 본다 — IoU 한 축으로는"
                         " '상자가 크다'와 '숫자를 잘랐다'가 구분되지 않는다")
    ap.add_argument("--compare", nargs="+", metavar="이름=jsonl",
                    help="같은 모집단의 결과들을 짝지어 승·패·무로 센다")
    args = ap.parse_args()

    if args.analyze:
        return analyze(args.analyze)
    if args.compare:
        return compare(args.compare)

    bands = {}
    for l in BANDS.read_text(encoding="utf-8").splitlines():
        if l.strip():
            j = json.loads(l)
            if j.get("quad"):
                bands[j["id"]] = rect(j["quad"])
    # 자르는 쿼드의 출처. 사람 라벨로 자르면 배포에 없는 오라클을 쓰는 것이라
    # 성적이 부풀린다 — 2026-09-17 까지 모든 실촬 수치가 그랬다.
    if args.gmsrc == "detector":
        _q, _st = load_gm_quads(prefer_human=False)
        gm = {k: {"quad": v} for k, v in _q.items()}
    else:
        gm = {r["id"]: r for r in quad_rows()}
    labels = {}
    for l in (DATUMO / "labels.jsonl").read_text(encoding="utf-8").splitlines():
        if l.strip():
            j = json.loads(l)
            labels[j["id"]] = j["image"]

    # ── 모집단 ────────────────────────────────────────────────────────
    # 기본은 **채점 가능한 전량**이다. 구판은 기기 단절 분할의 홀드아웃을
    # 기본으로 삼았는데, 그 분할은 실사진 파인튜닝용이다 — 합성만으로 학습한
    # 모델에는 누수가 성립하지 않으므로 정답이 있는 장을 버릴 이유가 없다
    # (사람 지적 2026-09-17: "실촬은 훈련에사용하지 않으니 평가로 사용할수
    # 있는거아니야?"). 실측: 분할 id 258 vs 채점 가능 276.
    #
    # **사람 제외 선언은 어느 모집단에서도 뺀다.** 구판은 이걸 부르지 않아
    # band_label_excluded.jsonl 의 5장(전부 가로형 — 프레임이 숫자칸을 자름 3,
    # 정립 정규화 없음 2)이 가로형 46장 안에 섞여 있었다. 사람이 "규약대로
    # 라벨할 수 없다"고 선언한 장을 정답으로 쓰면 검출기가 맞게 내고도 점수를
    # 잃는다(band_exclusions.py 머리말).
    excluded = set(load_excluded())
    if args.side == "scorable":
        ids = sorted(bands)
    else:
        split = json.loads(SPLIT.read_text(encoding="utf-8"))
        ids = (split["holdout_ids"] if args.side == "holdout"
               else split["train_ids"] if args.side == "train"
               else split["train_ids"] + split["holdout_ids"])
    n_before = len(ids)
    ids = [i for i in ids if i not in excluded]
    n_dropped = n_before - len(ids)

    exp = get_exp(args.exp, None)
    model = exp.get_model().cuda().eval()
    model.load_state_dict(torch.load(args.ckpt, map_location="cpu")["model"])
    pre = ValTransform(legacy=False)

    rows, skipped = [], []
    for cid in ids:
        if cid not in bands or cid not in gm or cid not in labels:
            skipped.append(cid)
            continue
        img = cv2.imread(str(DATUMO / labels[cid]))
        if img is None:
            skipped.append(cid)
            continue
        # ── 프레이밍 ──────────────────────────────────────────────────
        # lcdcrop: LCD 쿼드 + BOX_MARGIN. **합성 분포에 맞춘 크롭이다.**
        #   합성기는 LCD + 얇은 베젤만 그리고(실측 유리/캔버스 넓이 중앙 0.482)
        #   실촬은 전체 혈당기 사진이다(LCD/사진 넓이 중앙 0.056). 넓이로 8.6배,
        #   선형 2.9배 차이다. 자르면 그 격차가 사라지므로 합성 모델에 유리하다.
        # photo: 전체 사진 그대로. **배포가 실제로 받는 것**이고, 2단 구조
        #   (화면 검출 -> 크롭 -> 밴드 검출)를 안 쓸 때의 입력이다.
        #   자르지 않으므로 좌표 변환도 없다.
        if args.frame == "photo":
            x0, y0 = 0, 0
            crop = img
        else:
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            fr = framed_src_rect(gray, gm[cid]["quad"])  # 학습 캐시와 같은 여백
            x0, y0 = int(fr[0][0]), int(fr[0][1])
            x1, y1 = int(fr[2][0]), int(fr[2][1])
            crop = img[y0:y1, x0:x1]
        if crop.size == 0 or min(crop.shape[:2]) < 16:
            skipped.append(cid)
            continue
        r = min(exp.test_size[0] / crop.shape[0], exp.test_size[1] / crop.shape[1])
        t, _ = pre(crop, None, exp.test_size)
        with torch.no_grad():
            det = postprocess(model(torch.from_numpy(t).unsqueeze(0).float().cuda()),
                              exp.num_classes, args.conf, 0.45, class_agnostic=True)[0]
        rec = {"id": cid, "gt": bands[cid], "frame": args.frame,
               "crop": [x0, y0, x0 + crop.shape[1], y0 + crop.shape[0]]}
        if det is None or len(det) == 0:
            rec.update(pred=None, score=None, iou=0.0)
        else:
            o = det.cpu().numpy()
            k = int(np.argmax(o[:, 4] * o[:, 5]))
            # 크롭 좌표 -> 원본 사진 좌표
            b = [float(o[k][0]) / r + x0, float(o[k][1]) / r + y0,
                 float(o[k][2]) / r + x0, float(o[k][3]) / r + y0]
            rec.update(pred=[round(v, 1) for v in b],
                       score=round(float(o[k][4] * o[k][5]), 4),
                       iou=round(iou(b, bands[cid]), 4))
        rows.append(rec)

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    p = out / f"{args.side}_{args.frame}_{args.gmsrc}.jsonl"
    with p.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    v = np.array([r["iou"] for r in rows])
    miss = sum(1 for r in rows if r["pred"] is None)
    wide = wide_ids()
    n_wide = sum(1 for r in rows if r["id"] in wide)
    print(f"체크포인트 {Path(args.ckpt).parent.name} · 모집단 {args.side} "
          f"n={len(rows)} (건너뜀 {len(skipped)})")
    print(f"  사람 제외 선언으로 뺀 장 {n_dropped} (band_label_excluded.jsonl)")
    print("  프레이밍: " + ("전체 혈당기 사진 그대로 — **배포가 받는 입력**"
                             if args.frame == "photo" else
                             f"LCD 쿼드({args.gmsrc}) + BOX_MARGIN"
                             + ("  ← 배포에 없는 오라클" if args.gmsrc == "human"
                                else "  ← 배포가 실제로 쓰는 경로")))
    print(f"  검출 실패 {miss}장")
    print(f"  IoU 중앙 {np.median(v):.4f} · 평균 {v.mean():.4f} · "
          f"p10 {np.percentile(v, 10):.4f} · 최소 {v.min():.4f}")
    print(f"  >=0.5 {int((v >= .5).sum())}장 · >=0.75 {int((v >= .75).sum())}장")
    print(f"  가로형 {n_wide}장 — 0이면 위 수치는 **세로형 성적일 뿐이다**")
    orient_block(rows, wide)
    print(f"-> {p}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
