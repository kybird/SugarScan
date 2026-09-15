# 가로형 밴드 라벨 전수 검토 큐 — 기기 안에서 벗어난 순.
#
# 배경(2026-09-15): 밤샘 스윕에서 세로형은 0.780 -> 0.859 로 올랐는데 가로형만
# 0.69 근처에서 안 움직였다. 데이터를 늘려도 안 오르니 다른 원인이다.
#
# 라벨을 보니 같은 기기·같은 자릿수인데 밴드 폭이 갈렸다:
#   이름모를 가로형모델  1091(129) 0.336 · 1046(142) 0.341 · 606(121) 0.349
#                        1815(145) 0.612 · 1622(110) 0.606 · 1822(149) 0.622
#   1.7배 차이다. 좁은 쪽은 숫자를 자른 라벨로 보인다.
#
# 정렬 기준은 **그 기기 자신의 중앙값에서 벗어난 정도**다. 기기마다 밴드 폭이
# 다른 것은 정상이므로(칼럼형 0.54 vs 전폭형 0.86) 전체 분포로 재면 정상
# 기기가 통째로 걸린다. 기기 안에서 튀는 장만 잡는다.
#
# n<3 인 기기는 중앙값이 못 미더우므로 뒤로 보낸다 — 순서만 밀고 빼지는 않는다.
#
# 사용: python make_wide_review_queue.py
import json
from collections import defaultdict
from pathlib import Path

import numpy as np

from band_exclusions import load_excluded
from gm_quads import load_gm_quads

HERE = Path(__file__).resolve().parent
UP = HERE.parent / "upstream" / "datumo"
OUT = HERE / "band_wide_queue.json"


def main():
    gm, _ = load_gm_quads()
    ex = load_excluded()
    vals = {json.loads(l)["id"]: json.loads(l)["reading"]
            for l in open(UP / "labels.jsonl", encoding="utf-8")}
    devs = {json.loads(l)["id"]: json.loads(l)
            for l in open(HERE / "device_labels.jsonl", encoding="utf-8")}

    rows = []
    for line in open(HERE / "band_boxes.jsonl", encoding="utf-8"):
        b = json.loads(line)
        G = gm.get(b["id"])
        if G is None or "quad" not in b or b["id"] in ex:
            continue
        gw = G[:, 0].max() - G[:, 0].min()
        gh = G[:, 1].max() - G[:, 1].min()
        if gw / max(gh, 1e-6) <= 1.0:
            continue                      # 가로형만
        q = np.asarray(b["quad"], float)
        d = devs.get(b["id"], {})
        name = f"{d.get('brand', '')} {d.get('model', '')}".strip() or "(미식별)"
        v = vals.get(b["id"])
        rows.append(dict(id=b["id"], dev=name, val=v,
                         nd=len(str(abs(int(v)))) if v is not None else 0,
                         bw=(q[:, 0].max() - q[:, 0].min()) / gw,
                         bh=(q[:, 1].max() - q[:, 1].min()) / max(gh, 1e-6)))

    by = defaultdict(list)
    for r in rows:
        by[r["dev"]].append(r["bw"])
    med = {k: float(np.median(v)) for k, v in by.items()}

    for r in rows:
        m = med[r["dev"]]
        r["dev_n"] = len(by[r["dev"]])
        r["dev_med"] = m
        r["dev"] = r["dev"]
        # 그 기기 중앙값 대비 몇 % 벗어났나
        r["dev_off"] = (r["bw"] - m) / max(m, 1e-6)
        # n<3 기기는 중앙값이 못 미더우므로 뒤로
        r["_key"] = abs(r["dev_off"]) * (1.0 if r["dev_n"] >= 3 else 0.35)

    rows.sort(key=lambda r: -r["_key"])
    OUT.write_text(json.dumps([
        dict(id=r["id"], stratum=f"가로형 · {r['dev']}",
             note=(f"값 {r['val']}({r['nd']}자리) · 밴드폭/화면폭 {r['bw']:.3f} "
                   f"(같은 기기 중앙 {r['dev_med']:.3f}, n={r['dev_n']}, "
                   f"편차 {r['dev_off'] * 100:+.0f}%) · 숫자칸 전체를 감쌌는지 본다"))
        for r in rows], ensure_ascii=False, indent=1), encoding="utf-8")

    print(f"{OUT.name}  {len(rows)}장")
    print(f"{'id':<22} {'기기':<24} {'값':>5} {'bw':>6} {'편차':>7}")
    for r in rows[:15]:
        print(f"{r['id']:<22} {r['dev'][:22]:<24} {str(r['val']):>5} "
              f"{r['bw']:>6.3f} {r['dev_off'] * 100:>+6.0f}%")


if __name__ == "__main__":
    raise SystemExit(main())
