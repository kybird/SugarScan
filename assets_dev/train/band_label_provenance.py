# 밴드 라벨의 출처를 가린다 — A키(웹툴 acceptPred)가 저장한 장과 사람이
# 직접 그린 장을 분리한다.
#
# 배경(2026-09-27): A키는 파란 예측(band_quads_pred.jsonl, atone_s0)을 그대로
# 수락해 저장했다 — 이때 source 가 "human"으로 찍혀 둘이 구분되지 않았다.
# 이 라벨들로 atone_s0 를 평가하면 89장이 자기 예측을 자기가 채점해
# IoU 중앙이 0.8532 → 0.9199 로 부풀었다(실측).
#
# 판정: 라벨 quad 와 예측 quad 의 최대 좌표차가 **정확히 0.0** 이면 수락장.
# 무수정 수락은 직렬화를 그대로 지나므로 차가 0이고, 사람이 그리거나 조정한
# 상자는 픽셀 단위로 같아질 수 없다. 2026-09-27 실측 101/351장이 0.0,
# 0.001~3px 구간은 비어 있어 이분형이 흔들리지 않는다.
#
# 사용:
#   python band_label_provenance.py            # 요약 인쇄
#   python band_label_provenance.py --retag    # 수락장 source 를
#                                              # "pred-accepted" 로 소급 태그
#                                              # (원자 교체 — 서버가 읽는 중에도 안전)
import argparse
import json
import os
from pathlib import Path

HERE = Path(__file__).resolve().parent
PRED = HERE / "band_quads_pred.jsonl"
LABELS = HERE / "band_boxes.jsonl"


def _quads(p):
    out = {}
    for line in Path(p).read_text(encoding="utf-8").splitlines():
        if line.strip():
            j = json.loads(line)
            if j.get("quad"):
                out[j["id"]] = j["quad"]
    return out


def accepted_ids(pred_path=PRED, label_path=LABELS):
    """A키 무수정 수락장 id 집합."""
    pred, lab = _quads(pred_path), _quads(label_path)
    out = set()
    for cid, q in lab.items():
        p = pred.get(cid)
        if p and max(abs(a - b) for pa, pb in zip(q, p)
                     for a, b in zip(pa, pb)) == 0.0:
            out.add(cid)
    return out


def retag():
    acc = accepted_ids()
    rows = [json.loads(l) for l in
            LABELS.read_text(encoding="utf-8").splitlines() if l.strip()]
    n = 0
    for r in rows:
        if r["id"] in acc and r.get("source") != "pred-accepted":
            r["source"] = "pred-accepted"
            n += 1
    tmp = LABELS.with_suffix(".jsonl.tmp")
    with tmp.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    os.replace(tmp, LABELS)  # 원자 교체 — 서버가 요청마다 다시 읽는다
    print(f"소급 태그 {n}장 -> pred-accepted (전체 {len(rows)}행)")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--retag", action="store_true",
                    help="수락장 source 를 pred-accepted 로 바꿔 원자 교체")
    a = ap.parse_args()
    if a.retag:
        retag()
    else:
        acc = accepted_ids()
        rows = [json.loads(l) for l in
                LABELS.read_text(encoding="utf-8").splitlines() if l.strip()]
        n_human = sum(1 for r in rows if r.get("source") != "pred-accepted")
        print(f"라벨 {len(rows)}행 = 사람 {n_human} + A키 수락 {len(acc)}")
        for i in sorted(acc)[:10]:
            print("  ", i)
        if len(acc) > 10:
            print(f"   ... 외 {len(acc) - 10}장")
