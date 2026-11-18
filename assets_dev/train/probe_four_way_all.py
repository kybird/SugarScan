# 2026-11-18 밤 자율주행 ② — 4방향 전방향 판독 기록(자).
#
# 마진 규칙까지 100/11(오답 제약 1건 초과) — 4방향 계열의 마지막 후보는
# '합의': 여러 방향에서 같은 판독이 나올 때만 확정. 판단에 필요한 원데이터
# (4방향 각각의 점수·판독·확신도)를 전부 기록한다. 합의 규칙 자체는 이
# 파일의 출력으로 오프라인에서 잰다.
import argparse
import json
from pathlib import Path

import numpy as np

from eval_reject_stages import CONF_GATE, MIN_FRAC, VLO, VHI, load_detector
from probe_conf_rules import LABELS, load_oriented, load_reader_logits
from probe_four_way_fallback import read_at


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--detector", required=True)
    ap.add_argument("--reader", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    det_run, _ = load_detector(args.detector)
    read = load_reader_logits(args.reader)

    rows = {}
    for l in LABELS.read_text(encoding="utf-8").splitlines():
        if l.strip():
            j = json.loads(l)
            rows[j["id"].split("/", 1)[1]] = j

    out_rows = []
    for stem, gt in sorted(rows.items()):
        img = load_oriented(stem)
        per = []
        for k in range(4):
            im = np.ascontiguousarray(np.rot90(img, k))
            per.append(read_at(read, im, det_run))
        out_rows.append({
            "id": stem, "per": per,
            "gt": gt.get("value") if gt.get("source") == "human" else None})
    with open(args.out, "w", encoding="utf-8") as f:
        for r in out_rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"-> {args.out} ({len(out_rows)}행)")


if __name__ == "__main__":
    main()
