# 기기 단절(device-disjoint) 재분할 캐시 — 「기기 단절 분할 캐시를 만든다」 카드.
#
# 근거: docs/reports/grouped-split-rebaseline-2026-09-10.md — 세션 무결 재분할과
# 같은 절차를 기기 단위로 반복한다. device_labels.jsonl(사람이 2,494장에 붙인
# 기기 라벨)의 brand+model+variant 를 기기 정체성으로 삼아 real_train/
# real_holdout 소속을 다시 정한다. 합성(synth_*) 배열과 워프된 실사진 배열은
# 기존 캐시에서 그대로 복사한다 — 재계산이 아니라 **재배열** 이다.
#
# 기기 정체성에 print(인쇄 언어)·rotation(숫자 방향)은 쓰지 않는다(카드 Notes).
# 결정성: 기기명 정렬 + 고정 시드 순열. 실행할 때마다 같은 분할이 나와야 한다.
# 검증: 교차 기기 0·홀드아웃 비율 35~55%·단일 기기 독점 가드를 저장 **전에**
# assert 로 건다 — 실패하면 캐시를 남기지 않고 종료한다.
import argparse
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
HOLD_TARGET = 0.45   # 기존 분할·세션 재분할과 같은 목표 비율
HOLD_MIN = 0.35      # 카드 AC4 의 허용 하한(기기 단위라 범위로 판정)
HOLD_MAX = 0.55
SHARE_CAP = 0.25     # 홀드아웃에서 단일 기기 최대 비중(대형 기기 독점 가드)
SEED = 20260911      # 고정 시드 — 바꾸면 다음 비교 전체가 무효가 된다


def device_key(row):
    """기기 정체성 = brand+model+variant. print/rotation 은 정체성이 아니다."""
    return (row["brand"].strip(), row["model"].strip(), row["variant"].strip())


def display(key):
    return " / ".join(p for p in key if p) or "(무명)"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", default="data_cache_v2.npz")
    ap.add_argument("--labels", default="device_labels.jsonl")
    ap.add_argument("--out", default=str(HERE.parent / "train_device"
                                         / "data_cache_v2.npz"))
    ap.add_argument("--meta-out", default=str(HERE / "_diag" / "device_split"
                                              / "holdout_devices.json"))
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

    labels = {}
    with open(HERE / args.labels, encoding="utf-8") as f:
        for line in f:
            if line.strip():
                r = json.loads(line)
                labels[r["id"]] = r

    # 캐시 풀 ↔ 라벨 대응: device_labels 는 이 작업의 입력이므로 풀을 완전히
    # 덮지 못하면 분할 자체가 불가능하다(카드 Notes — 차이를 출력에 찍는다).
    missing = sorted(set(all_ids) - set(labels))
    unused = sorted(set(labels) - set(all_ids))
    print(f"캐시 실사진 {len(all_ids)}장 / 라벨 {len(labels)}장 — "
          f"라벨 없는 캐시 사진 {len(missing)}장, 캐시 밖 라벨 {len(unused)}장",
          flush=True)
    if missing:
        print("라벨이 풀을 덮지 않는다 — device_labels.jsonl 은 읽기 전용 자산이므로 "
              "여기서 멈춘다(사람 판정).", flush=True)
        return 2

    # 기기 단위 그룹.
    groups = {}
    for cid in all_ids:
        groups.setdefault(device_key(labels[cid]), []).append(cid)
    order = sorted(groups)  # 기기명 정렬 — 결정성의 첫 축
    print(f"기기 {len(order)}종, 최대 {max(len(groups[k]) for k in order)}장",
          flush=True)

    # 결정적 담기: 고정 시드 순열을 돌며 목표 치수까지 기기 통째로 홀드아웃에
    # 쌓는다. 단일 기기가 55% 상한을 깨뜨릴 것 같으면 건너뛰고 다음 기기(대형
    # 기기가 홀드아웃을 삼키지 않게 하는 장치). 나머지는 전부 train.
    total = len(all_ids)
    perm = np.random.RandomState(SEED).permutation(len(order))
    hold_keys, n_hold = [], 0
    for k in perm:
        key = order[int(k)]
        if n_hold >= HOLD_TARGET * total:
            break
        if n_hold + len(groups[key]) > HOLD_MAX * total:
            continue
        hold_keys.append(key)
        n_hold += len(groups[key])
    hold_set = {i for k in hold_keys for i in groups[k]}
    train_ids_new = [i for i in all_ids if i not in hold_set]
    hold_ids_new = [i for k in hold_keys for i in groups[k]]
    ratio = len(hold_ids_new) / total
    print(f"재분할: train {len(train_ids_new)} / holdout {len(hold_ids_new)} "
          f"({100 * ratio:.1f}%) — 시드 {SEED}", flush=True)

    # 검증 1: 교차 기기 0. 구조적으로 보장되지만 저장 전에 다시 확인한다(카드).
    hold_devs = {device_key(labels[i]) for i in hold_ids_new}
    train_devs = {device_key(labels[i]) for i in train_ids_new}
    cross = hold_devs & train_devs
    print(f"교차 기기: {len(cross)}종 (0이어야 한다)", flush=True)
    assert not cross, f"교차 기기 발생: {cross}"

    # 검증 2: 홀드아웃 비율 범위(AC4) + 단일 기기 독점 가드.
    assert HOLD_MIN <= ratio <= HOLD_MAX, f"비율 {ratio:.3f} 범위 밖"
    top_share = max(len(groups[k]) for k in hold_keys) / len(hold_ids_new)
    print(f"홀드아웃 기기 {len(hold_keys)}종, 단일 기기 최대 비중 "
          f"{100 * top_share:.1f}%", flush=True)
    assert top_share <= SHARE_CAP, f"단일 기기 비중 {top_share:.3f}"

    # 균형(AC3): build_grouped_split.py 와 같은 항목.
    pos = {c: k for k, c in enumerate(all_ids)}

    def dist(name, ids):
        vals = [int("".join(str(int(v)) for v in y_all[pos[i]]
                            if int(v) != 10)) for i in ids]
        print(f"{name}: 값 {min(vals)}~{max(vals)} 평균 {np.mean(vals):.0f} "
              f"· 2자리 {sum(1 for v in vals if v < 100)}장", flush=True)

    dist("train", train_ids_new)
    dist("holdout", hold_ids_new)

    def rows_for(ids):
        ix = np.array([pos[i] for i in ids])
        return X_all[ix], y_all[ix], l_all[ix]

    X_t, y_t, l_t = rows_for(train_ids_new)
    X_h, y_h, l_h = rows_for(hold_ids_new)

    # 저장은 모든 assert 를 통과한 뒤에만.
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

    meta = {
        "seed": SEED,
        "hold_target": HOLD_TARGET,
        "hold_ratio": round(ratio, 4),
        "n_real_total": total,
        "n_train": len(train_ids_new),
        "n_holdout": len(hold_ids_new),
        "n_device_kinds": len(order),
        "holdout_devices": [
            {"brand": b, "model": m, "variant": v, "photos": len(groups[(b, m, v)])}
            for (b, m, v) in sorted(hold_keys,
                                    key=lambda k: -len(groups[k]))
        ],
        "train_devices": [
            {"brand": b, "model": m, "variant": v, "photos": len(groups[(b, m, v)])}
            for (b, m, v) in sorted(train_devs,
                                    key=lambda k: -len(groups[k]))
        ],
        "identity_rule": "brand+model+variant (print/rotation excluded)",
        "cache_source": str((HERE / args.cache).relative_to(HERE.parent)),
    }
    meta_out = Path(args.meta_out)
    meta_out.parent.mkdir(parents=True, exist_ok=True)
    meta_out.write_text(json.dumps(meta, ensure_ascii=False, indent=2),
                        encoding="utf-8")
    print(f"기기 목록: {meta_out}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
