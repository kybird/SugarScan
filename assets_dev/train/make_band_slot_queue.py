# 밴드 라벨의 '빈 앞자리 누락' 을 고칠 큐와, 전수 검토 큐를 만든다.
#
# 배경(2026-09-14): 사람이 비교 시트를 보고 「사람 라벨링이 숫자를 두자리만
# 감싸고있네」라고 지적했다. band_label_slot_audit.py 로 재니 2자리 값 44장 중
# 15장이 빈 앞자리를 안 넣었고, 그 15장은 어느 모델에서도 IoU 0.53~0.62 에
# 갇혀 있었다(나머지 261장은 0.71~0.84).
#
# 규약은 '빈자리를 넣는다'다. 합성기도 그렇게 그린다(2자리 밴드 w/h 1.591 vs
# 3자리 1.601, n=40000). 그러므로 검출기는 맞게 내고도 점수를 잃는다.
#
# 두 개를 낸다:
#   band_slot_fix_queue.json    빈자리 누락 15장 — 고칠 것
#   band_review_queue.json      밴드 라벨 전량 — 자릿수별 중앙에서 벗어난 순
#
# 전수 큐를 '의심 순'으로 정렬하는 이유: 277장을 끝까지 볼 필요가 없게 하려는
# 것이다. 중간에 멈춰도 이상한 것은 이미 다 본 상태가 된다.
#
# 자를 새로 만들지 않는다 — band_label_slot_audit.py 와 같은 계산을 쓴다.
#
# 사용: python make_band_slot_queue.py
import json
from pathlib import Path

import numpy as np

from gm_quads import load_gm_quads

HERE = Path(__file__).resolve().parent
UP = HERE.parent / "upstream" / "datumo"
THRESH = 0.80          # 3자리 중앙 w/h 대비 — band_label_slot_audit 와 같은 값


def rows():
    vals = {json.loads(l)["id"]: json.loads(l)["reading"]
            for l in open(UP / "labels.jsonl", encoding="utf-8")}
    gm, _ = load_gm_quads()
    out = []
    for line in open(HERE / "band_boxes.jsonl", encoding="utf-8"):
        b = json.loads(line)
        v, G = vals.get(b["id"]), gm.get(b["id"])
        if v is None or G is None or "quad" not in b:
            continue
        q = np.asarray(b["quad"], float)
        bw = q[:, 0].max() - q[:, 0].min()
        bh = q[:, 1].max() - q[:, 1].min()
        out.append(dict(id=b["id"], val=int(v), nd=len(str(abs(int(v)))),
                        wh=bw / max(bh, 1e-6)))
    return out


def main():
    rs = rows()
    med = {nd: float(np.median([r["wh"] for r in rs if r["nd"] == nd]))
           for nd in {r["nd"] for r in rs}}
    cut = med[3] * THRESH

    fix = [r for r in rs if r["nd"] == 2 and r["wh"] < cut]
    fix.sort(key=lambda r: r["wh"])
    (HERE / "band_slot_fix_queue.json").write_text(json.dumps(
        [dict(id=r["id"], stratum="빈자리 누락",
              note=f"값 {r['val']}({r['nd']}자리) · 상자 w/h {r['wh']:.2f} "
                   f"(3자리 중앙 {med[3]:.2f}) · 빈 앞자리까지 감싼다")
         for r in fix], ensure_ascii=False, indent=1), encoding="utf-8")

    # 전수 — 자릿수별 중앙에서 벗어난 정도가 큰 순
    for r in rs:
        r["dev"] = abs(r["wh"] - med[r["nd"]]) / med[r["nd"]]
    rs.sort(key=lambda r: -r["dev"])
    (HERE / "band_review_queue.json").write_text(json.dumps(
        [dict(id=r["id"], stratum=f"{r['nd']}자리",
              note=f"값 {r['val']} · 상자 w/h {r['wh']:.2f} "
                   f"(같은 자릿수 중앙 {med[r['nd']]:.2f}, 편차 {r['dev'] * 100:+.0f}%)")
         for r in rs], ensure_ascii=False, indent=1), encoding="utf-8")

    print(f"band_slot_fix_queue.json   {len(fix)}장  (고칠 것)")
    print(f"band_review_queue.json     {len(rs)}장  (전수 검토, 의심 순)")
    print(f"자릿수별 중앙 w/h: " +
          "  ".join(f"{k}자리 {v:.3f}" for k, v in sorted(med.items())))
    print("\n전수 큐 앞 10장 — 여기부터 보면 된다")
    for r in rs[:10]:
        print(f"   {r['id']:<22} 값 {r['val']:>4}  w/h {r['wh']:.2f}  "
              f"편차 {r['dev'] * 100:+.0f}%")


if __name__ == "__main__":
    raise SystemExit(main())
