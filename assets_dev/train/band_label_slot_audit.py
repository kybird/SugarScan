# 밴드 라벨이 '빈 앞자리를 포함했는가'를 감사한다.
#
# 배경(2026-09-14): 사람이 비교 시트를 보고 「사람 라벨링이 숫자를 두자리만
# 감싸고있네」라고 지적했다. 확인해 보니 규약이 장마다 갈려 있었다.
#
# 규약은 '빈자리를 넣는다'다(사람 지침). 합성기도 그렇게 그린다 — 2자리 값과
# 3자리 값의 밴드 폭이 같다(w/h 1.591 vs 1.601, n=40000). 그러므로 두 자리를
# 딱 감싼 사람 라벨은 규약 위반이고, 검출기는 맞게 내고도 IoU 를 잃는다.
#
# 자릿수는 상위 값 라벨(upstream/datumo/labels.jsonl 의 reading)에서 온다.
# 화면 쿼드는 gm_quads 로더(사람 라벨 우선).
#
# 한계(2026-09-14, 수정 작업 뒤 확인): 문턱이 '3자리 중앙 w/h 의 80%' 라는
# **상대 기준**이라 0 이 나올 수 없다. 라벨을 전부 고쳐도 분포가 통째로 올라가면
# 문턱도 따라 올라 하위 몇 장이 계속 걸린다. 기기마다 숫자 간격이 달라 w/h 하나로
# 슬롯 수를 판정할 수 없는 것이 근본 이유다.
#
# 그러므로 **걸린 장 수를 합격 기준으로 쓰지 마라.** 판정 신호는 아래 한 줄이다:
# 걸린 무리의 게이트 IoU 가 나머지보다 눌려 있으면 진짜 결함이고, 같거나 높으면
# 문턱의 오탐이다. 이 자는 결함을 **찾는** 데 쓰고 **합격을 선언하는** 데 쓰지 않는다.
#
# 사용: python band_label_slot_audit.py [--thresh 0.80] [--list]
import argparse
import json
from pathlib import Path

import numpy as np

from band_exclusions import load_excluded
from gm_quads import load_gm_quads

HERE = Path(__file__).resolve().parent
UP = HERE.parent / "upstream" / "datumo"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--thresh", type=float, default=0.80,
                    help="3자리 중앙 w/h 대비 이 비율 미만이면 '슬롯 부족'")
    ap.add_argument("--list", action="store_true", help="해당 장 id 를 인쇄")
    args = ap.parse_args()

    vals = {json.loads(l)["id"]: json.loads(l)["reading"]
            for l in open(UP / "labels.jsonl", encoding="utf-8")}
    gm, st = load_gm_quads()
    ex = load_excluded()
    rows = []
    for line in open(HERE / "band_boxes.jsonl", encoding="utf-8"):
        b = json.loads(line)
        v, G = vals.get(b["id"]), gm.get(b["id"])
        if v is None or G is None or b["id"] in ex:
            continue
        q = np.asarray(b["quad"], float)
        bw = q[:, 0].max() - q[:, 0].min()
        bh = q[:, 1].max() - q[:, 1].min()
        gw = G[:, 0].max() - G[:, 0].min()
        rows.append(dict(id=b["id"], nd=len(str(abs(int(v)))),
                         wh=bw / max(bh, 1e-6), share=bw / max(gw, 1e-6)))

    print(f"GM 쿼드 출처 — 사람 {st['human']} · 검출기 {st['detector']}")
    print(f"사람 선언 제외 {len(ex)}장 — 분모가 제외 전과 다르다")
    print(f"{'자리':>3} {'n':>4} {'w/h p5':>8} {'p25':>8} {'median':>8} {'p95':>8}")
    by = {}
    for nd in sorted({r["nd"] for r in rows}):
        a = np.asarray([r["wh"] for r in rows if r["nd"] == nd])
        by[nd] = a
        print(f"{nd:>3} {len(a):>4} " +
              " ".join(f"{np.percentile(a, p):8.3f}" for p in (5, 25, 50, 95)))

    if 3 not in by:
        raise SystemExit("3자리 표본이 없다 — 기준을 못 세운다")
    cut = float(np.median(by[3])) * args.thresh
    bad = [r for r in rows if r["nd"] == 2 and r["wh"] < cut]
    n2 = sum(1 for r in rows if r["nd"] == 2)
    print(f"\n3자리 중앙 w/h={np.median(by[3]):.3f}  문턱={cut:.3f}"
          f"  (2슬롯 예상 {np.median(by[3]) * 2 / 3:.3f})")
    print(f"빈자리를 안 넣은 2자리 라벨: {len(bad)}/{n2} "
          f"(게이트 전체의 {100 * len(bad) / len(rows):.1f}%)")
    if args.list:
        for r in sorted(bad, key=lambda r: r["wh"]):
            print(f"   {r['id']:<22} w/h={r['wh']:.3f}  폭/화면={r['share']:.3f}")

    # 게이트 성적에 얼마나 먹히는지 — 이미 있는 게이트 결과를 읽는다
    bad_ids = {r["id"] for r in bad}
    for d in sorted((HERE / "_diag").glob("band_det_*/gate_results.jsonl")):
        g = [json.loads(l) for l in open(d, encoding="utf-8")]
        t = [r["iou_det"] for r in g if r["id"] in bad_ids]
        o = [r["iou_det"] for r in g if r["id"] not in bad_ids]
        if not t:
            continue
        mt, mo = float(np.median(t)), float(np.median(o))
        verdict = "진짜 결함" if mt < mo - 0.05 else "문턱 오탐(결함 아님)"
        print(f"  {d.parent.name:<22} 전체 {np.median(t + o):.3f}  "
              f"슬롯부족 {mt:.3f}(n={len(t)})  "
              f"나머지 {mo:.3f}(n={len(o)})   → {verdict}")


if __name__ == "__main__":
    raise SystemExit(main())
