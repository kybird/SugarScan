# 사전 병합 — 같은 기기 후보 쌍(dhash 해밍 9~14)으로 미확인 성분을 미리 묶는다.
#
# dhash 는 회전에 약해 같은 혈당계를 각도만 달리 찍은 사진을 별개 성분으로
# 갈라 놓는다(실측: OneTouch Ultra 가 c009·c122·c161·c201 네 조각). 그래서
# 미확인 704성분은 미확인 704종이 아니다. 웹툴에서 사람이 같은 기기를 수백 번
# 다시 판별하지 않도록, 검토 전에 그룹으로 묶어 둔다.
#
# 이 스크립트의 본체는 "많이 묶기"가 아니라 "잘못 묶었는지 잡기"다.
# 쌍을 전이적으로 이으면 A-B 가 가깝고 B-C 가 가깝다는 이유로 A 와 C 가 전혀
# 다른 기기여도 한 그룹이 된다(연쇄). 두 가지로 막는다.
#
#   1. 자동 반증 — 브랜드가 확인된 성분 6개는 서로 다른 기종 3종이다.
#      한 그룹에 다른 기종이 둘 들어오면 그 임계값은 즉시 기각한다.
#      사람 눈을 기다릴 필요가 없는 판정이다.
#   2. 눈 확인 — 2개 이상 묶인 그룹마다 대표 이미지를 나란히 붙인 스트립을
#      원본 해상도로 낸다. 브랜드 문구는 근거로 쓰지 않는다(400px 시트에서
#      같은 기기가 판독마다 다른 브랜드로 읽혔다 — G34 실측).
#
# device_tags.jsonl 을 덮어쓰지 않는다. 사람이 checked 로 바꾼 행이 섞이는
# 파일이라 자동 산출로 건드리면 사람 판정이 조용히 사라진다.
#
# 산출: _diag/device_tags/premerge.json (+ --strips 로 premerge_gNN.png)
import argparse
import json
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
DIAG = HERE / "_diag" / "device_tags"
TAGS = HERE / "device_tags.jsonl"
SUMMARY = DIAG / "summary.json"


def load():
    rows = [json.loads(l) for l in TAGS.read_text(encoding="utf-8").splitlines() if l.strip()]
    pairs = json.loads(SUMMARY.read_text(encoding="utf-8"))["near_pairs"]
    return rows, pairs


def union(components, pairs, thr):
    """임계값 이하 쌍을 전이적으로 잇는다. → {대표: [성분…]}"""
    par = {c: c for c in components}

    def find(x):
        while par[x] != x:
            par[x] = par[par[x]]
            x = par[x]
        return x

    for p in pairs:
        if p["dist"] > thr or p["a"] not in par or p["b"] not in par:
            continue
        a, b = find(p["a"]), find(p["b"])
        if a != b:
            par[a] = b
    groups = defaultdict(list)
    for c in components:
        groups[find(c)].append(c)
    return groups


def measure(rows, pairs, thr):
    size = {r["component"]: r["size"] for r in rows}
    device = {r["component"]: f'{r["brand"]} {r["model"]}'.strip()
              for r in rows if r["brand"]}
    groups = union(list(size), pairs, thr)

    conflicts, anchored, unknown_absorbed = [], 0, 0
    for rep, members in groups.items():
        known = {device[c] for c in members if c in device}
        if len(known) > 1:
            conflicts.append((rep, sorted(known), members))
        if known:
            unknown_absorbed += sum(1 for c in members if c not in device)
            anchored += 1
    biggest = max(groups.values(), key=lambda g: sum(size[c] for c in g))
    return {
        "threshold": thr,
        "groups": len(groups),
        "multi_component_groups": sum(1 for g in groups.values() if len(g) > 1),
        "unknown_absorbed_by_verified": unknown_absorbed,
        "verified_anchored_groups": anchored,
        "biggest_group_components": len(biggest),
        "biggest_group_images": sum(size[c] for c in biggest),
        "conflicts": [{"members": m, "devices": d} for _, d, m in conflicts],
    }, groups


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--threshold", type=int, default=None,
                    help="확정 임계값. 주면 premerge.json 을 쓴다")
    ap.add_argument("--strips", action="store_true",
                    help="2개 이상 묶인 그룹의 검증 스트립을 낸다")
    args = ap.parse_args()

    rows, pairs = load()
    size = {r["component"]: r["size"] for r in rows}
    total_imgs = sum(size.values())
    print(f"성분 {len(rows)} · 장수 {total_imgs} · 후보쌍 {len(pairs)}")
    print(f"{'thr':>4} {'그룹':>6} {'다성분':>6} {'검증에붙은미확인':>16} "
          f"{'최대그룹(성분/장)':>18}  기종충돌")
    for thr in range(9, 15):
        m, _ = measure(rows, pairs, thr)
        flag = "기각" if m["conflicts"] else "ok"
        why = "; ".join("+".join(c["devices"]) + " (%d성분)" % len(c["members"])
                        for c in m["conflicts"])
        print(f"{thr:>4} {m['groups']:>6} {m['multi_component_groups']:>6} "
              f"{m['unknown_absorbed_by_verified']:>16} "
              f"{m['biggest_group_components']:>8}/{m['biggest_group_images']:<9} "
              f"{flag} {why}")

    if args.threshold is None:
        return 0

    m, groups = measure(rows, pairs, args.threshold)
    if m["conflicts"]:
        print(f"\n임계 {args.threshold} 는 서로 다른 기종을 한 그룹에 넣는다. 기각.")
        return 1

    DIAG.mkdir(parents=True, exist_ok=True)
    rep_img = {r["component"]: r["rep"] for r in rows}
    device = {r["component"]: f'{r["brand"]} {r["model"]}'.strip()
              for r in rows if r["brand"]}
    out = []
    for gi, (rep, members) in enumerate(sorted(groups.items(),
                                               key=lambda kv: -sum(size[c] for c in kv[1]))):
        members = sorted(members)
        known = sorted({device[c] for c in members if c in device})
        out.append({
            "group": f"g{gi:04d}",
            "components": members,
            "images": sum(size[c] for c in members),
            "reps": [rep_img[c] for c in members],
            "device": known[0] if known else "",
            "source": "verified" if known else "",
        })
    payload = {"threshold": args.threshold, "measured": m, "groups": out}
    (DIAG / "premerge.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\npremerge.json — 그룹 {len(out)} (임계 {args.threshold})")

    if args.strips:
        THR[0] = args.threshold
        strips(out, rep_img)
    return 0


THR = [0]


def strips(groups, rep_img):
    """2개 이상 묶인 그룹을 한 줄에 하나씩 — 한 장에 여러 그룹을 담아 눈으로 훑는다.

    브랜드 각인을 읽는 용도가 아니다(그 글자는 신뢰하지 않는다). 몸체 색·형태·
    버튼 배치·화면 비율이 같은 기기인지만 본다. 그래서 셀은 380px 로 충분하고,
    대신 한 화면에서 그룹끼리 비교되도록 여러 그룹을 한 장에 담는다.
    """
    import cv2
    import numpy as np
    from PIL import Image, ImageOps

    src = HERE.parent / "upstream" / "datumo" / "extracted" / "TILDE"
    CELL, COLS, PER = 380, 6, 6
    multi = [g for g in groups if len(g["components"]) > 1]
    multi.sort(key=lambda g: -len(g["components"]))
    print(f"검증 스트립 — 다성분 그룹 {len(multi)}")

    def cell(cid):
        with Image.open(src / f"{cid}.jpg") as pil:
            pil.load()
            pil = ImageOps.exif_transpose(pil)
            pil.thumbnail((CELL - 6, CELL - 6))
            return cv2.cvtColor(np.asarray(pil.convert("RGB")), cv2.COLOR_RGB2BGR)

    for si in range(0, len(multi), PER):
        chunk = multi[si:si + PER]
        h = len(chunk) * (CELL + 30)
        canvas = np.full((h, COLS * (CELL + 6), 3), 25, np.uint8)
        for r, g in enumerate(chunk):
            y0 = r * (CELL + 30)
            # cv2 putText 는 한글을 물음표로 그린다. 라벨은 ASCII 로 쓴다.
            head = "%s  %dcomp %dimg  %s" % (g["group"], len(g["components"]),
                                             g["images"], g["device"] or "unverified")
            cv2.putText(canvas, head, (6, y0 + 20), cv2.FONT_HERSHEY_SIMPLEX,
                        0.62, (80, 220, 255), 2, cv2.LINE_AA)
            for c, cid in enumerate(g["reps"][:COLS]):
                im = cell(cid)
                yy, xx = y0 + 26, c * (CELL + 6)
                canvas[yy:yy + im.shape[0], xx:xx + im.shape[1]] = im
        cv2.imwrite(str(DIAG / ("premerge_t%d_sheet_%02d.png" % (THR[0], si // PER))), canvas)
    print("  시트 %d장" % ((len(multi) + PER - 1) // PER))


if __name__ == "__main__":
    raise SystemExit(main())
