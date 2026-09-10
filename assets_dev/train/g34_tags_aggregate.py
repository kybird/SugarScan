# G34 4단계 — 1차 태깅(device_tags.jsonl) 생성 + 집계.
#
# 태깅 원칙(카드 Plan 4): 브랜드 각인이 원본 해상도 교차 검증으로 확인된
# 성분만 브랜드를 채운다. 시트(400px) 판독의 브랜드 문구는 모델이 조건마다
# 다르게 읽는 것이 실측됐다(같은 검정-타원형이 OneTouch Ultra / GlucoNeX
# plus / CUEDIO PAW / GLUCOCARD 로 갈림) — 구조(외형군)는 믿고 글자는
# 안 믿는다. 검증 안 된 성분은 brand 빈 값 + low + 사람 검토 대상.
#
# 검증 근거(2026-09-10, _diag/device_tags/verify_*.png 전해상도 스트립):
#   c001 565장 — 사분위 4표본 전부 "CareSens II"(i-SENS, 흰색 소형·파란
#          백라이트·타원 버튼 2개·나무 책상). batch2/2624 포함.
#   c003 723장 — 사분위 4표본 전부 "CareSens N". batch2/2636 포함.
#   c009·c122·c161·c201 — 대표 원본 각 1장씩 "OneTouch Ultra"(검정 타원·
#          흰 각인·베이지 천 배경 4/4 일치).
#
# AC #5 보강: 검증 성분 대표와 dhash 해밍 ≤14 인 미검증 성분 대표를
# '같은 기기 후보'로 계산해 저확신 목록 우선순위로 쓴다. 8 이면 이미 같은
# 성분이라 9~14 만 의미가 있다(dhash 는 회전에 약하다는 감사 보고서 §4
# 한계 ② 를 숫자로 다루는 장치).
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from audit_split_leakage import dhash  # noqa: E402

DATUMO = HERE.parent / "upstream" / "datumo"
NEAR = 14  # 같은 기기 후보 컷오프(성분 임계 8 보다 넉넉히)

VERIFIED = {
    "c001": {"brand": "CareSens", "model": "II",
             "confidence": "high",
             "note": "사분위 4/4 표본 'CareSens II' — verify_giant_c001.png"},
    "c003": {"brand": "CareSens", "model": "N",
             "confidence": "high",
             "note": "사분위 4/4 표본 'CareSens N' — verify_giant_c003.png"},
    "c009": {"brand": "OneTouch", "model": "Ultra",
             "confidence": "medium",
             "note": "원본 판독 'OneTouch Ultra' — verify_grp_blackoval.png"},
    "c122": {"brand": "OneTouch", "model": "Ultra",
             "confidence": "medium",
             "note": "원본 판독 'OneTouch Ultra' — verify_grp_blackoval.png"},
    "c161": {"brand": "OneTouch", "model": "Ultra",
             "confidence": "medium",
             "note": "원본 판독 'OneTouch Ultra' — verify_grp_blackoval.png"},
    "c201": {"brand": "OneTouch", "model": "Ultra",
             "confidence": "medium",
             "note": "원본 판독 'OneTouch Ultra' — verify_grp_blackoval.png"},
}


def main() -> int:
    comps = json.loads((HERE / "_diag" / "scene_components.json").read_text(
        encoding="utf-8"))
    n = len(comps)
    assert n == 710, n

    # 1) device_tags.jsonl — 성분 1행. 검증 성분만 브랜드.
    rows = []
    for cid in sorted(comps):
        members = comps[cid]
        rep = members[0]
        sheet = int(cid[1:]) // 40 + 1
        cell = int(cid[1:]) % 40
        v = VERIFIED.get(cid)
        rows.append({
            "component": cid,
            "rep": rep,
            "size": len(members),
            "sheet": sheet,
            "cell": cell,
            "brand": v["brand"] if v else "",
            "model": v["model"] if v else "",
            "confidence": v["confidence"] if v else "low",
            "by": "agent",
            "checked": False,
            "note": v["note"] if v else
            "1차 시트 스캔만으로 브랜드 확신 불가 — 사람 확인 필요",
        })
    dest = HERE / "device_tags.jsonl"
    with dest.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"device_tags.jsonl: {len(rows)}행 → {dest}", flush=True)

    # 2) AC #5 — 대표 간 dhash 거리로 '같은 기기 후보' 탐색.
    reps = [r["rep"] for r in rows]
    hashes = {}
    for rid in reps:
        p = DATUMO / "extracted" / "TILDE" / f"{rid}.jpg"
        h = dhash(p)
        if h is None:
            print(f"불러오기 실패: {rid}")
            return 2
        hashes[rid] = h
    bits = np.stack([hashes[r] for r in reps])
    tri = np.bitwise_xor(bits[:, None, :], bits[None, :, :]).sum(-1)
    iu = np.triu_indices(n, k=1)
    dists = tri[iu]

    near_pairs = []
    for (i, j), d in zip(zip(*iu), dists):
        if 8 < d <= NEAR:  # 8 이하는 이미 같은 성분
            near_pairs.append((int(d), rows[i]["component"], rows[j]["component"]))
    near_pairs.sort()
    print(f"\n대표 간 거리 9~{NEAR}: {len(near_pairs)}쌍 (같은 기기 후보)",
          flush=True)
    for d, a, b in near_pairs[:20]:
        print(f"  {a}–{b} (해밍 {d})", flush=True)

    # 검증 성분 대표와 가까운 미검증 성분 → 검토 우선순위.
    verified_idx = [k for k, r in enumerate(rows) if r["component"] in VERIFIED]
    prio = {}
    for vi in verified_idx:
        for k in range(n):
            if k in verified_idx:
                continue
            d = int(tri[vi, k])
            if 8 < d <= NEAR:
                prio.setdefault(rows[k]["component"], []).append(
                    (VERIFIED[rows[vi]["component"]]["brand"], d))
    print(f"\n검증 기기와 해밍 9~{NEAR}인 미검증 성분: {len(prio)}개", flush=True)

    # 3) 집계 — 성분 수와 장수 양쪽(AC #4).
    total_imgs = sum(r["size"] for r in rows)
    print(f"\n== 집계 (성분 {n}개 · 장수 {total_imgs}) ==", flush=True)
    from collections import defaultdict
    by_dev = defaultdict(lambda: [0, 0])
    for r in rows:
        key = f"{r['brand']} {r['model']}".strip() or "(미확인)"
        by_dev[key][0] += 1
        by_dev[key][1] += r["size"]
    for key, (c_cnt, i_cnt) in sorted(by_dev.items(), key=lambda kv: -kv[1][1]):
        print(f"  {key:28s} 성분 {c_cnt:3d}개 · {i_cnt:4d}장 "
              f"({100 * i_cnt / total_imgs:.1f}%)", flush=True)

    low = [r for r in rows if r["confidence"] == "low"]
    print(f"\n저확신(사람 검토 대상): {len(low)}개 성분", flush=True)

    # 4) 요약 JSON — 웹툴 검토 화면이 읽는다.
    summary = {
        "near_pairs": [{"a": a, "b": b, "dist": d} for d, a, b in near_pairs],
        "review_priority": {k: v for k, v in prio.items()},
    }
    (HERE / "_diag" / "device_tags" / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=1), encoding="utf-8")
    print("summary.json 저장", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
