# 평가 jsonl(eval_synthband_real 산출)의 IoU 를 기기별로 분해한다.
# 카드 「실사진 밴드 라벨로 검출기 파인튜닝」 AC#4(기기별 분해)의 자.
#
# 사용:
#   python device_iou_breakdown.py post.jsonl [--pre pre.jsonl]
#   --pre 를 주면 각 기기의 전 중앙을 나란히 찍는다.
import argparse
import json

import numpy as np

HERE = __import__("pathlib").Path(__file__).resolve().parent


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("rows", help="eval_synthband_real 산출 jsonl")
    ap.add_argument("--pre", default=None, help="비교 대상(파인튜닝 전) jsonl")
    args = ap.parse_args()

    dev = {}
    for l in (HERE / "device_labels.jsonl").read_text(encoding="utf-8").splitlines():
        if l.strip():
            j = json.loads(l)
            dev[j["id"]] = (j["brand"] + " " + j["model"] + " "
                            + j.get("variant", "")).strip()
    pre = {}
    if args.pre:
        for l in open(args.pre, encoding="utf-8"):
            if l.strip():
                j = json.loads(l)
                pre[j["id"]] = j.get("iou")

    groups = {}
    for l in open(args.rows, encoding="utf-8"):
        if not l.strip():
            continue
        j = json.loads(l)
        if j.get("iou") is None:
            continue
        groups.setdefault(dev.get(j["id"], "?"), []).append(
            (j["iou"], pre.get(j["id"])))

    print(f"기기별 IoU 중앙(n={sum(len(v) for v in groups.values())}장,"
          f" {len(groups)}기기)" + (" — post (pre)" if args.pre else ""))
    for g in sorted(groups, key=lambda g: np.median([a for a, _ in groups[g]])):
        a = [x for x, _ in groups[g]]
        line = f"  {g:<36} n={len(a):2d}  {np.median(a):.3f}"
        if args.pre:
            b = [x for _, x in groups[g] if x is not None]
            line += f"  ({np.median(b):.3f})" if b else "  (—)"
        print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
