# 미학습 기기 성적 집계 — 「미학습 기기 성적을 잰다」 카드.
#
# eval_reader.py 가 남긴 reader_preds_tta.json {id: [pred, gt, agree]} 를
# 네 층(완전일치·위험·안전 실패·무출력)으로 갈라 전체와 기기별로 낸다.
# 층 정의는 split-leakage-audit-2026-09-09.md · grouped-split-rebaseline 와
# 동일: 위험 = 오답 중 자릿수 보존 오독. 득표율 거절(agree < 0.778, G24)은
# 별도 행으로 함께 센다(층과 겹친다 — 거절은 정답여부와 독립 신호).
#
# 층을 합치지 않는다: 완전일치 하나로 요약하면 위험군이 묻힌다
# (antipatterns/aggregate-hides-stratified-failure).
import argparse
import json
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
AGREE_REJECT = 0.778  # G24 스윕의 득표율 거절 임계


def layers_of(pred, gt):
    if pred == gt:
        return "exact"
    if pred == "":
        return "blank"
    return "risky" if len(pred) == len(gt) else "safe"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--preds", default=str(HERE.parent / "train_device"
                                           / "reader_preds_tta.json"))
    ap.add_argument("--labels", default="device_labels.jsonl")
    ap.add_argument("--out", default=str(HERE / "_diag" / "device_split"
                                         / "eval_by_device.json"))
    args = ap.parse_args()

    preds = json.loads(Path(args.preds).read_text(encoding="utf-8"))
    labels = {}
    with open(HERE / args.labels, encoding="utf-8") as f:
        for line in f:
            if line.strip():
                r = json.loads(line)
                labels[r["id"]] = (r["brand"].strip(), r["model"].strip(),
                                   r["variant"].strip())

    tally = defaultdict(lambda: defaultdict(int))   # device -> layer -> n
    reject = defaultdict(int)
    overall = defaultdict(int)
    for cid, (pred, gt, agree) in preds.items():
        layer = layers_of(pred, gt)
        overall[layer] += 1
        dev = labels.get(cid)
        assert dev is not None, f"라벨 없는 홀드아웃 사진: {cid}"
        tally[dev][layer] += 1
        if agree < AGREE_REJECT:
            reject[dev] += 1
            overall["rejected"] += 1

    total = sum(overall[k] for k in ("exact", "risky", "safe", "blank"))
    print(f"홀드아웃 {total}장 — {Path(args.preds)}")
    for k in ("exact", "risky", "safe", "blank"):
        print(f"  {k:6s} {overall[k]:5d} ({100 * overall[k] / total:.2f}%)")
    print(f"  거절(agree<{AGREE_REJECT}) {overall['rejected']} "
          f"({100 * overall['rejected'] / total:.2f}%) — 층과 겹침")

    rows = []
    print(f"\n{'사진':>4} {'일치':>4} {'일치%':>6} {'위험':>4} {'안전':>4} "
          f"{'무출력':>4} {'거절':>4}  기기")
    for dev, t in sorted(tally.items(),
                         key=lambda kv: -sum(kv[1].values())):
        n = sum(t.values())
        row = {
            "brand": dev[0], "model": dev[1], "variant": dev[2],
            "n": n, "exact": t["exact"], "risky": t["risky"],
            "safe": t["safe"], "blank": t["blank"], "rejected": reject[dev],
            "exact_pct": round(100 * t["exact"] / n, 1),
        }
        rows.append(row)
        name = " / ".join(p for p in dev if p) or "(무명)"
        print(f"{n:4d} {t['exact']:4d} {row['exact_pct']:6.1f} "
              f"{t['risky']:4d} {t['safe']:4d} {t['blank']:4d} "
              f"{reject[dev]:4d}  {name}")

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(
        {"overall": {k: overall[k] for k in
                     ("exact", "risky", "safe", "blank", "rejected")},
         "total": total, "agree_reject": AGREE_REJECT, "devices": rows},
        ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n저장: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
