# 밴드 시범 라벨링 작업 목록을 만든다 — 사람이 "어느 장을 라벨링할지" 고르지
# 않아도 되게. 산출: band_pilot.json (라벨러 큐가 읽는다)
#
# 층은 셋이고 이유가 다르다:
#   wide    가로 화면 — 판독 51.6% 로 가장 약한 클래스(세로는 94.4%)
#   misread 자릿수 보존 오독 — 위험군. 값이 그럴듯해 안전망을 통과한다
#   control 정답 장 — **대조군.** 실패만 보면 공통 성질이 전부 원인처럼 보인다
#           (2026-09-04 에 이 실수를 세 번 했다)
import json
from pathlib import Path

import numpy as np
import tensorflow as tf

HERE = Path(__file__).resolve().parent
DATUMO = HERE.parent / "upstream" / "datumo"
OUT = HERE / "band_pilot.json"
BLANK = 10
N_MISREAD = 30
N_CONTROL = 20


def load(p, key="quad"):
    d = {}
    for l in Path(p).read_text(encoding="utf-8").splitlines():
        if l.strip():
            j = json.loads(l)
            d[j["id"]] = j.get(key)
    return d


def ar(q):
    a = np.array(q, float)
    h = a[:, 1].ptp()
    return a[:, 0].ptp() / h if h > 0 else 0


def greedy(seq):
    s, prev = [], -1
    for v in seq:
        v = int(v)
        if v != prev and v != BLANK:
            s.append(str(v))
        prev = v
    return "".join(s)


def main() -> int:
    scr = load(HERE / "screen_boxes.jsonl")
    gm = load(HERE / "gmscreen_quads.jsonl")

    cache = np.load(str(HERE / "data_cache_v2.npz"))
    X, y = cache["real_holdout_images"], cache["real_holdout_label_ids"]
    ids = [str(v) for v in cache["real_holdout_ids"]]
    gts = ["".join(str(int(v)) for v in row if int(v) != BLANK) for row in y]

    model = tf.keras.models.load_model(str(HERE / "reader_model"))
    am = np.argmax(model.predict(X[..., None].astype(np.float32),
                                 batch_size=128, verbose=0), axis=-1)
    preds = [greedy(r) for r in am]

    rows, seen = [], set()

    def add(cid, stratum, note):
        if cid in seen or cid not in gm:
            return
        if not (DATUMO / "extracted" / "TILDE" / f"{cid}.jpg").exists():
            return
        seen.add(cid)
        rows.append({"id": cid, "stratum": stratum, "note": note})

    # 1) 가로 화면 — 사람 라벨 기준 w/h > 1.2
    for cid, q in sorted(scr.items()):
        if q and ar(q) > 1.2:
            add(cid, "wide", f"가로 화면 w/h={ar(q):.2f}")

    # 2) 위험군 오독 — 자릿수 보존, blank 아님
    mis = []
    for i, (p, g) in enumerate(zip(preds, gts)):
        if p == g or len(p) != len(g):
            continue
        if int(np.sum(am[i] != BLANK)) <= 2:
            continue
        mis.append((ids[i], g, p))
    step = max(1, len(mis) // N_MISREAD)      # 간격 표본 — 앞부분만 집지 않는다
    for cid, g, p in mis[::step][:N_MISREAD]:
        add(cid, "misread", f"오독 {g}->{p}")

    # 3) 대조군 — 정답 장을 간격 표본으로
    ok = [ids[i] for i, (p, g) in enumerate(zip(preds, gts)) if p == g]
    step = max(1, len(ok) // N_CONTROL)
    for cid in ok[::step][:N_CONTROL]:
        add(cid, "control", "정답 장(대조군)")

    OUT.write_text(json.dumps(rows, ensure_ascii=False, indent=1),
                   encoding="utf-8")
    from collections import Counter
    c = Counter(r["stratum"] for r in rows)
    print(f"작업 목록 {len(rows)}장 → {OUT.name}")
    for k in ("wide", "misread", "control"):
        print(f"  {k:8s} {c[k]}장")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
