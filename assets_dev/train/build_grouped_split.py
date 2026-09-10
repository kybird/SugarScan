# 장면 성분 단위 재분할 캐시 — 「장면 성분 분할 재학습」 의 1단계.
#
# 근거(docs/reports/split-leakage-audit-2026-09-09.md): 기존 분할은 이미지 단위
# 시드 셔플이라 홀드아웃 73.7% 가 train 과 같은 촬영 장면을 공유했다. 이 스크립트는
# dhash 근접쌍(해밍 ≤8)의 연결요소 = 장면 세션을 분할 단위로 삼아 real_train/
# real_holdout 을 다시 자른다. 합성(synth_*) 배열과 워프된 실사진 배열은 기존
# 캐시에서 그대로 복사한다 — 재계산이 아니라 **재배열** 이다.
#
# 산출: --out 캐시 npz. 검증: 교차 성분 0 을 출력에서 확인 못 하면 실패로 종료.
# 임계 민감도: 해밍 ≤6 도 함께 계수해 기록한다(재분할 자체는 ≤8 기준).
import argparse
import json
import sys
from collections import Counter
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from audit_split_leakage import dhash  # noqa: E402

DATUMO = HERE.parent / "upstream" / "datumo"
HOLD_TARGET = 0.45  # 기존 분할과 같은 홀드아웃 비율(이미지 수 기준)


def components_of(ids, hashes, threshold):
    """근접쌍 연결요소 — audit_split_leakage 와 같은 union-find."""
    idx = {c: k for k, c in enumerate(ids)}
    bits = np.stack([hashes[c] for c in ids])
    tri = np.bitwise_xor(bits[:, None, :], bits[None, :, :]).sum(-1)
    near = np.argwhere(np.triu(tri <= threshold, k=1))
    parent = list(range(len(ids)))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for a, b in near:
        ra, rb = find(int(a)), find(int(b))
        if ra != rb:
            parent[ra] = rb
    groups = {}
    for k in range(len(ids)):
        groups.setdefault(find(k), []).append(ids[k])
    return list(groups.values())


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", default="data_cache_v2.npz")
    ap.add_argument("--out", default=str(HERE.parent / "train_grouped"
                                         / "data_cache_v2.npz"))
    ap.add_argument("--threshold", type=int, default=8)
    args = ap.parse_args()

    cache = np.load(HERE / args.cache, allow_pickle=True)
    tr_ids = [str(x) for x in cache["real_train_ids"]]
    ho_ids = [str(x) for x in cache["real_holdout_ids"]]
    all_ids = tr_ids + ho_ids
    # 마스터 배열: 기존 train 행 뒤에 기존 holdout 행을 이어 붙인 것.
    X_all = np.concatenate([cache["real_train_images"],
                            cache["real_holdout_images"]], axis=0)
    y_all = np.concatenate([cache["real_train_label_ids"],
                            cache["real_holdout_label_ids"]], axis=0)
    l_all = np.concatenate([cache["real_train_label_lens"],
                            cache["real_holdout_label_lens"]], axis=0)
    assert len(all_ids) == len(X_all)

    print(f"dhash 계산 {len(all_ids)}장…", flush=True)
    hashes = {}
    for cid in all_ids:
        p = DATUMO / "extracted" / "TILDE" / f"{cid}.jpg"
        h = dhash(p) if p.exists() else None
        if h is None:
            print(f"불러오기 실패: {cid}", flush=True)
            return 2
        hashes[cid] = h

    # 임계 민감도(AC1): ≤6 와 ≤8 의 성분 수 비교.
    for t in (6, args.threshold):
        comps = components_of(all_ids, hashes, t)
        multi = sum(1 for c in comps if len(c) >= 2)
        print(f"해밍 ≤{t}: 성분 {len(comps)}개(2장 이상 {multi}), "
              f"최대 {max(len(c) for c in comps)}장", flush=True)

    comps = components_of(all_ids, hashes, args.threshold)
    old_train = set(tr_ids)

    def sort_key(comp):
        head = min(comp, key=lambda i: (i.split("/")[0], int(i.split("/")[1])))
        return (head.split("/")[0], int(head.split("/")[1]))

    # 결정적 배정: 성분을 (batch, 최소번호) 순으로 돌며 홀드아웃 목표 치수만큼
    # 통째로 쌓는다. 나머지는 train. 한 성분이 양쪽에 걸칠 방법이 구조적으로 없다.
    hold_ids_new = []
    for comp in sorted(comps, key=sort_key):
        if len(hold_ids_new) < HOLD_TARGET * len(all_ids):
            hold_ids_new.extend(comp)
        # 목표를 채우면 남은 성분은 전부 train 으로 떨어진다(아래 세트 차감).
    hold_set = set(hold_ids_new)
    # 목표 초과 방지: 마지막 성분까지만 담았으므로 초과 폭은 한 성분 크기 이하.
    train_ids_new = [i for i in all_ids if i not in hold_set]
    print(f"재분할: train {len(train_ids_new)} / holdout {len(hold_ids_new)} "
          f"({100 * len(hold_ids_new) / len(all_ids):.1f}%)", flush=True)

    # 무결성: 교차 성분 0 검증(AC2).
    hold_final = set(train_ids_new) & hold_set
    assert not hold_final
    cross = [c for c in comps
             if set(c) & hold_set and set(c) - hold_set]
    print(f"교차 성분: {len(cross)}개 (0이어야 한다)", flush=True)
    if cross:
        print("교차 성분이 남았다 — 분할 로직 오류. 중단.", flush=True)
        return 3

    # 새 분할의 균형 sanity: 값 분포가 한쪽으로 몰리지 않았는지.
    def dist(name, ids):
        vals = [int("".join(str(int(v)) for v in y_all[all_ids.index(i)]
                            if int(v) != 10)) for i in ids]
        print(f"{name}: 값 {min(vals)}~{max(vals)} 평균 {np.mean(vals):.0f} "
              f"· 2자리 {sum(1 for v in vals if v < 100)}장", flush=True)

    dist("train", train_ids_new)
    dist("holdout", hold_ids_new)

    def rows_for(ids):
        pos = {c: k for k, c in enumerate(all_ids)}
        ix = np.array([pos[i] for i in ids])
        return X_all[ix], y_all[ix], l_all[ix]

    X_t, y_t, l_t = rows_for(train_ids_new)
    X_h, y_h, l_h = rows_for(hold_ids_new)

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        out,
        synth_train_images=cache["synth_train_images"],
        synth_train_label_ids=cache["synth_train_label_ids"],
        synth_train_label_lens=cache["synth_train_label_lens"],
        synth_val_images=cache["synth_val_images"],
        synth_val_label_ids=cache["synth_val_label_ids"],
        synth_val_label_lens=cache["synth_val_label_lens"],
        real_train_images=X_t,
        real_train_label_ids=y_t,
        real_train_label_lens=l_t,
        real_train_ids=np.array(train_ids_new),
        real_holdout_images=X_h,
        real_holdout_label_ids=y_h,
        real_holdout_label_lens=l_h,
        real_holdout_ids=np.array(hold_ids_new),
    )
    print(f"저장: {out}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
