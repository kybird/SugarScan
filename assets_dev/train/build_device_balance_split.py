# 기기 편중 완화 학습셋 — 「기기 편중을 줄이면 미학습 기기 성적이 오르는지 잰다」.
#
# 입력: train_device/data_cache_v2.npz(카드 1 의 기기 단절 분할 — 대조군)과
# device_labels.jsonl. real_holdout 은 한 글자도 건드리지 않고 복사한다(모든
# 팔이 같은 시험지를 받는다 — 짝비교의 전제). 합성 배열도 그대로 복사.
# real_train 의 기기 분포만 다시 만든다(재배열, 재계산 아님).
#
# 두 팔:
#   cap       기기당 중앙값(28장) 상한 절단 — 카드 AC1 의 예시 규칙 그대로.
#             총 장수가 줄어드는 교란이 있다(보고서에 명시).
#   equalize  총 장수를 대조군과 같은 1,356장으로 유지하며 기기별 쿼터를
#             균등화(작은 기기 오버샘플링) — 스텝수까지 같아 편중 효과만
#             분리된다(카드 Notes 의 권고 팔).
#
# 결정성: 어떤 사진을 남기고 복제할지는 기기명·사진 id 정렬 + 고정 시드로
# 재현 가능하다. 실행마다 다른 학습셋이 나오면 A/B 전체가 무효다.
import argparse
import json
import statistics
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
SEED = 20260911  # build_device_split 과 같은 고정 시드


def device_key(row):
    return (row["brand"].strip(), row["model"].strip(), row["variant"].strip())


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default=str(HERE.parent / "train_device"
                                          / "data_cache_v2.npz"),
                    help="대조군(기기 단절) 캐시")
    ap.add_argument("--labels", default="device_labels.jsonl")
    ap.add_argument("--mode", choices=("cap", "equalize"), required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    base = np.load(args.base, allow_pickle=True)
    tr_ids = [str(x) for x in base["real_train_ids"]]
    ho_ids = [str(x) for x in base["real_holdout_ids"]]
    labels = {}
    with open(HERE / args.labels, encoding="utf-8") as f:
        for line in f:
            if line.strip():
                r = json.loads(line)
                labels[r["id"]] = r

    groups = {}
    for cid in tr_ids:
        groups.setdefault(device_key(labels[cid]), []).append(cid)
    counts = sorted((len(v) for v in groups.values()), reverse=True)
    median = statistics.median(counts)
    print(f"train 기기 {len(groups)}종 {len(tr_ids)}장 — 최대 {counts[0]} "
          f"중앙값 {median}", flush=True)

    quota = {}
    if args.mode == "cap":
        # 절단: 기기당 min(n, median). 남길 사진은 id 정렬 앞에서부터(결정적).
        cap = int(median)
        for k, ids in groups.items():
            quota[k] = sorted(ids)[:cap]
        desc = f"기기당 상한 {cap}(중앙값)"
    else:
        # 균등화: 총 장수를 대조군과 같게. 기기수 Q, 총 N → 기기별 기본
        # N//Q 장, 나머지 N%Q 는 기기명 정렬 앞의 기기에 하나씩(결정적).
        # 기기 고유 사진이 쿼터보다 적으면 정렬 순서로 순환 복제해 채운다.
        Q, N = len(groups), len(tr_ids)
        base_q, extra = divmod(N, Q)
        for i, k in enumerate(sorted(groups)):
            q = base_q + (1 if i < extra else 0)
            ids = sorted(groups[k])
            if len(ids) >= q:
                quota[k] = ids[:q]
            else:
                reps = [ids[j % len(ids)] for j in range(q)]
                quota[k] = reps
        desc = f"기기별 쿼터 {base_q}~{base_q + 1}(총 {N} 유지, 복제 포함)"

    new_ids = [i for k in sorted(quota) for i in quota[k]]
    n_unique = len(set(new_ids))
    print(f"mode={args.mode}: {desc} → {len(new_ids)}행 "
          f"(고유 {n_unique}장, 복제 {len(new_ids) - n_unique}행)", flush=True)
    # 검증: 홀드아웃과 교차 없음 + 새 train 은 기존 train 의 부분집합(복제 포함).
    assert not (set(new_ids) & set(ho_ids)), "train/holdout 교차 발생"
    assert set(new_ids) <= set(tr_ids), "대조군 train 밖의 사진 사용"

    pos = {c: k for k, c in enumerate(tr_ids)}
    X_all = base["real_train_images"]
    y_all = base["real_train_label_ids"]
    l_all = base["real_train_label_lens"]
    ix = np.array([pos[i] for i in new_ids])

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        out,
        synth_train_images=base["synth_train_images"],
        synth_train_label_ids=base["synth_train_label_ids"],
        synth_train_label_lens=base["synth_train_label_lens"],
        synth_val_images=base["synth_val_images"],
        synth_val_label_ids=base["synth_val_label_ids"],
        synth_val_label_lens=base["synth_val_label_lens"],
        real_train_images=X_all[ix],
        real_train_label_ids=y_all[ix],
        real_train_label_lens=l_all[ix],
        real_train_ids=np.array(new_ids),
        real_holdout_images=base["real_holdout_images"],
        real_holdout_label_ids=base["real_holdout_label_ids"],
        real_holdout_label_lens=base["real_holdout_label_lens"],
        real_holdout_ids=np.array(ho_ids),
    )
    print(f"저장: {out}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
