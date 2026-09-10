# 분할 누수 감사 — 재학습 없이 기존 예측(reader_preds.json, G29 crc32 기준선)을
# 촬영 세션 층으로 다시 집계해 누수를 정량화한다.
#
# 근거: build_cache_v2.py:169-176 은 GM 쿼드 풀을 np.random.RandomState(123) 으로
# **이미지 단위로** 셔플해 train/holdout 을 가른다. 강화 프롬프트 §26/§38 가 경고하는
# "같은 촬영 버스트가 양쪽에 섞이는" 누수를 이 스크립트가 계측한다.
#
# 세션 프록시: 같은 batch 내에서 (보정된) reading 이 같은 연속 번호 런.
# 가정 검증: 런 안 인접쌍의 dhash 해밍이 전체 평균보다 눈에 띄게 낮아야 한다
# (낮지 않으면 세션 프록시가 틀렸다는 뜻 — 그대로 보고하고 해석을 바꾼다).
#
# 산출:
#   - 콘솔 리포트(아래 출력 형식)
#   - _diag/split_leakage_report.json (전체 수치)
#   - _diag/split_leakage_pairs/ (교차 근접쌍 몽타주, 눈검증용)
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
from PIL import Image, ImageOps

HERE = Path(__file__).resolve().parent
DATUMO = HERE.parent / "upstream" / "datumo"
REJECT_AT = 0.778  # webtool.py api_failures 와 같은 값(정본: webtool)
DHASH_NEAR = 8     # 64비트 dhash 에서 이 해밍 이하면 근접쌍으로 본다


def dhash(path: Path) -> np.ndarray | None:
    """9x8 그레이 dhash — 64비트. JPEG draft 디코드로 원본 크기와 무관하게 빠르다.

    EXIF 회전을 적용한다(G20 통일: 비교는 표시 좌표계에서).
    """
    try:
        with Image.open(path) as im:
            im.draft("L", (32, 32))
            g = ImageOps.exif_transpose(im).convert("L").resize((9, 8))
            a = np.asarray(g, dtype=np.int16)
    except Exception:
        return None
    return (a[:, 1:] > a[:, :-1]).ravel().astype(np.uint8)


def bucket_of(pred: str, gt: str) -> str:
    if pred == gt:
        return "exact"
    if not pred:
        return "blank"
    return "risky" if len(pred) == len(gt) else "safe"


def main() -> int:
    cache = np.load(HERE / "data_cache_v2.npz", allow_pickle=True)
    train_ids = {str(x) for x in cache["real_train_ids"]}
    hold_ids = {str(x) for x in cache["real_holdout_ids"]}
    preds = json.loads((HERE / "reader_preds.json").read_text(encoding="utf-8"))

    readings = {}
    for l in (DATUMO / "labels.jsonl").read_text(encoding="utf-8").splitlines():
        if l.strip():
            j = json.loads(l)
            readings[j["id"]] = str(j["reading"])
    corr = HERE / "gt_corrections.jsonl"
    if corr.exists():
        for l in corr.read_text(encoding="utf-8").splitlines():
            if l.strip():
                j = json.loads(l)
                readings[j["id"]] = str(j["corrected"])

    pool = sorted(train_ids | hold_ids,
                  key=lambda i: (i.split("/")[0], int(i.split("/")[1])))

    # --- 1) dhash 계산 ---
    hashes, missing = {}, 0
    for cid in pool:
        p = DATUMO / "extracted" / "TILDE" / f"{cid}.jpg"
        h = dhash(p) if p.exists() else None
        if h is None:
            missing += 1
        else:
            hashes[cid] = h
    print(f"dhash: {len(hashes)}장 계산 (불러오기 실패 {missing})")

    # --- 2) 세션 프록시: 같은 batch 내 같은 reading 의 연속 번호 런 ---
    runs, cur = [], []
    for cid in pool:
        batch, n = cid.split("/")
        n = int(n)
        if cur:
            pb, pn = cur[-1].split("/")
            if pb == batch and n == int(pn) + 1 \
                    and readings.get(cid) == readings.get(cur[-1]):
                cur.append(cid)
                continue
            runs.append(cur)
        cur = [cid]
    if cur:
        runs.append(cur)
    sizes = Counter(len(r) for r in runs)
    print(f"세션 런(연속+같은reading): {len(runs)}개, 크기 분포 "
          f"(1장:{sizes[1]} 2장:{sizes[2]} 3장이상:{sum(v for k, v in sizes.items() if k >= 3)})")

    # 가정 검증: 런 안 인접쌍 해밍 vs 전체 무작위쌍 해밍
    def ham(a, b):
        return int(np.bitwise_xor(a, b).sum())

    intra = [ham(hashes[a], hashes[b])
             for r in runs if len(r) >= 2
             for a, b in zip(r, r[1:]) if a in hashes and b in hashes]
    rng = np.random.RandomState(0)
    all_ids = sorted(hashes)
    inter = []
    for _ in range(len(intra) * 3):
        a, b = rng.choice(len(all_ids), 2, replace=False)
        inter.append(ham(hashes[all_ids[a]], hashes[all_ids[b]]))
    print(f"가정 검증 — 런 내 인접쌍 해밍: 평균 {np.mean(intra):.1f} / p90 "
          f"{np.percentile(intra, 90):.0f} vs 무작위쌍 평균 {np.mean(inter):.1f}")

    # --- 3) 교차 분할 누수 ---
    run_of = {cid: i for i, r in enumerate(runs) for cid in r}
    leaky_hold, leaky_train = set(), set()
    for r in runs:
        t = [c for c in r if c in train_ids]
        h = [c for c in r if c in hold_ids]
        if t and h:
            leaky_hold.update(h)
            leaky_train.update(t)
    print(f"세션 기준 누수: holdout {len(leaky_hold)}/{len(hold_ids)}장"
          f"({100 * len(leaky_hold) / len(hold_ids):.1f}%) 이 train 과 같은 런"
          f" / 연루 train {len(leaky_train)}장")

    # 직접 근접쌍(픽셀 근거): dhash 해밍 ≤ DHASH_NEAR 인 교차쌍
    ids_h = sorted(hashes)
    bits = np.stack([hashes[i] for i in ids_h])
    idx = {c: k for k, c in enumerate(ids_h)}
    tri = np.bitwise_xor(bits[:, None, :], bits[None, :, :]).sum(-1)
    near = np.argwhere(np.triu(tri <= DHASH_NEAR, k=1))
    cross = [(ids_h[a], ids_h[b], int(tri[a, b]))
             for a, b in near
             if (ids_h[a] in train_ids) != (ids_h[b] in train_ids)]
    same_split_near = len(near) - len(cross)
    print(f"픽셀 근접쌍(해밍≤{DHASH_NEAR}): 교차 분할 {len(cross)}쌍 / "
          f"같은 분할 {same_split_near}쌍")

    # --- 4) 근접쌍 연결요소 = 장면 세션 ---
    # 연속번호+같은reading 프록시는 실재하지 않았다(런 12개). 실제 세션 구조는
    # "같은 배치의 가까운 번호, 같은 구도, 값은 바뀜"(몽타주 눈검증) 이므로
    # 픽셀 근접쌍의 연결요소를 세션으로 쓴다.
    parent = list(range(len(ids_h)))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for a, b in near:
        ra, rb = find(int(a)), find(int(b))
        if ra != rb:
            parent[ra] = rb
    comp_of = {}
    for k in range(len(ids_h)):
        comp_of.setdefault(find(k), []).append(ids_h[k])
    comps = list(comp_of.values())
    multi = [c for c in comps if len(c) >= 2]
    comp_sizes = Counter(len(c) for c in comps)
    print(f"연결요소: 총 {len(comps)}개 중 2장 이상 {len(multi)}개 "
          f"(최대 {max(len(c) for c in comps)}장, 크기분포 "
          f"2:{comp_sizes[2]} 3~5:{sum(v for k, v in comp_sizes.items() if 3 <= k <= 5)} "
          f"6장 이상:{sum(v for k, v in comp_sizes.items() if k >= 6)})")

    scene_leaky_hold = set()
    label_leaky_hold = set()
    cross_comps = 0
    for c in comps:
        t = [x for x in c if x in train_ids]
        h = [x for x in c if x in hold_ids]
        if not (t and h):
            continue
        cross_comps += 1
        t_readings = {readings.get(x) for x in t}
        for x in h:
            scene_leaky_hold.add(x)
            if readings.get(x) in t_readings:
                label_leaky_hold.add(x)
    print(f"교차 성분 {cross_comps}개 — 장면 누수 holdout {len(scene_leaky_hold)}장"
          f"({100 * len(scene_leaky_hold) / len(hold_ids):.1f}%), "
          f"이 중 같은 값까지 train 에 있는 holdout {len(label_leaky_hold)}장"
          f"({100 * len(label_leaky_hold) / len(hold_ids):.1f}%)")

    # --- 5) 기존 예측 재집계: 층별 ---
    def agg(sub):
        rows = []
        for cid in sub:
            v = preds.get(cid)
            if v is None:
                continue
            pred, gt, agree = str(v[0]), str(v[1]), v[2]
            rows.append((cid, pred, gt, agree, bucket_of(pred, gt)))
        n = len(rows)
        if n == 0:
            return None
        c = Counter(r[4] for r in rows)
        rej = sum(1 for r in rows if r[3] is not None and r[3] < REJECT_AT)
        return {
            "n": n,
            "exact": c["exact"], "exact_pct": 100 * c["exact"] / n,
            "risky": c["risky"], "risky_pct": 100 * c["risky"] / n,
            "safe": c["safe"], "blank": c["blank"],
            "rejected_by_agree": rej,
            "wrong_examples": [
                {"id": r[0], "gt": r[2], "pred": r[1], "agree": r[3]}
                for r in rows if r[4] in ("risky", "safe", "blank")][:30],
        }

    clean = agg([c for c in preds
                 if c not in scene_leaky_hold])
    scene_only = agg([c for c in preds
                      if c in scene_leaky_hold and c not in label_leaky_hold])
    label_leak = agg([c for c in preds if c in label_leaky_hold])
    overall = agg(list(preds))

    print("\n== 기존 모델 재집계(재학습 없음, reader_preds.json) ==")
    for name, a in (("전체 홀드아웃", overall),
                    ("완전 clean (교차 성분 없음)", clean),
                    ("장면 누수만 (같은 값 없음)", scene_only),
                    ("값 누수 (train 에 같은 장면+같은 값)", label_leak)):
        if a is None:
            print(f"{name}: 표본 0")
            continue
        print(f"{name}: n={a['n']} exact={a['exact']} ({a['exact_pct']:.2f}%) "
              f"risky={a['risky']} ({a['risky_pct']:.2f}%) safe={a['safe']} "
              f"blank={a['blank']} 득표율거절={a['rejected_by_agree']}")

    # 몽타주: 교차 근접쌍 상위 6쌍을 눈검증용으로 저장
    out_dir = HERE / "_diag" / "split_leakage_pairs"
    out_dir.mkdir(parents=True, exist_ok=True)
    cross.sort(key=lambda t: t[2])
    for k, (a, b, h) in enumerate(cross[:6]):
        pair = []
        for cid in (a, b):
            p = DATUMO / "extracted" / "TILDE" / f"{cid}.jpg"
            with Image.open(p) as im:
                im.draft("RGB", (360, 360))
                g = ImageOps.exif_transpose(im).convert("L")
                g.thumbnail((360, 360))
                pair.append(g)
        w = sum(p.width for p in pair) + 8
        canvas = Image.new("L", (w, max(p.height for p in pair)), 255)
        x = 0
        for p in pair:
            canvas.paste(p, (x, 0))
            x += p.width + 8
        ta = "train" if a in train_ids else "hold"
        tb = "train" if b in train_ids else "hold"
        canvas.save(out_dir / f"pair{k}_{a.replace('/', '_')}({ta})_"
                    f"{b.replace('/', '_')}({tb})_h{h}.png")
    print(f"몽타주 {min(6, len(cross))}쌍 → {out_dir}")

    report = {
        "split": {"train": len(train_ids), "holdout": len(hold_ids),
                  "mechanism": "RandomState(123) image-level shuffle "
                               "(build_cache_v2.py:169-176)"},
        "session_runs_naive_proxy": {
            "count": len(runs),
            "size_dist": {str(k): v for k, v in sorted(sizes.items())},
            "note": "연속번호+같은reading 프록시 — 실제 세션 구조와 불일치(아래)"},
        "assumption_check": {
            "intra_adjacent_hamming_mean": round(float(np.mean(intra)), 2),
            "intra_adjacent_hamming_p90": round(float(np.percentile(intra, 90)), 1),
            "random_pair_hamming_mean": round(float(np.mean(inter)), 2),
        },
        "components": {"total": len(comps),
                       "multi": len(multi),
                       "max_size": max(len(c) for c in comps),
                       "cross_split": cross_comps},
        "leakage": {
            "cross_split_near_pairs": len(cross),
            "near_pair_threshold": DHASH_NEAR,
            "scene_leaky_holdout": len(scene_leaky_hold),
            "scene_leaky_holdout_pct":
                round(100 * len(scene_leaky_hold) / len(hold_ids), 1),
            "label_leaky_holdout": len(label_leaky_hold),
            "label_leaky_holdout_pct":
                round(100 * len(label_leaky_hold) / len(hold_ids), 1)},
        "reagg": {"overall": overall, "clean": clean,
                  "scene_only": scene_only, "label_leak": label_leak},
        "near_pairs_sample": [
            {"a": a, "b": b, "hamming": h,
             "reading_a": readings.get(a), "reading_b": readings.get(b)}
            for a, b, h in cross[:40]],
    }
    (HERE / "_diag" / "split_leakage_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print("리포트 → _diag/split_leakage_report.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
