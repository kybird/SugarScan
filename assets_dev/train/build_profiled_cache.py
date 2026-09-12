# 프로파일 합성 캐시 빌더 — 「합성에 기기 프로파일 도입」 카드 (2026-09-11).
#
# 기기 단절 캐시(train_device/data_cache_v2.npz)를 복사해 **합성 배열만**
# synth_profiles.render_any 산출로 교체한 A/B 팔 캐시를 만든다.
#  - 실사진 배열·id 는 바이트 그대로(분할·홀드아웃 불변 — md5 로 증명).
#  - 합성 장수·val 분할 절차는 build_cache_v2 와 동일: 23,000장, 5% val,
#    RandomState(42) 순열. 다른 것은 렌더러뿐이다(변인 1개).
#  - 라벨은 값 자릿수뿐(encode_label 과 동일 규약, BLANK=10 패딩).
#
# 재현:
#   conda run -n sugartrain python build_profiled_cache.py \
#       --out ../train_profiled/data_cache_v2.npz
import argparse
import random
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import synth_profiles  # noqa: E402
from build_cache_v2 import encode_label, BLANK, MAX_LABEL  # noqa: E402

SRC = HERE.parent / "train_device" / "data_cache_v2.npz"
N_SYNTH = 23000        # 기존 캐시와 동일(21,850 train + 1,150 val = 5%)
SEED = 19000           # 카드 ordinal — 기준선 팔과 다른 값으로 문서화됨


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(HERE.parent / "train_profiled"
                                         / "data_cache_v2.npz"))
    args = ap.parse_args()
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)

    src = np.load(SRC, allow_pickle=True)
    import hashlib
    md5 = lambda a: hashlib.md5(a.tobytes()).hexdigest()
    real_keys = [k for k in src.files if k.startswith("real_")]
    real_md5 = {k: md5(src[k]) for k in real_keys}

    rng = random.Random(SEED)
    X = np.zeros((N_SYNTH, 160, 320), np.uint8)
    y = np.full((N_SYNTH, MAX_LABEL), BLANK, np.int32)
    ln = np.zeros(N_SYNTH, np.int32)
    for i in range(N_SYNTH):
        val = rng.randint(30, 511)
        img, label = synth_profiles.render_any(val, rng, (320, 160))
        assert label == str(val) and label.isdigit(), f"라벨 오염: {label!r}"
        X[i] = img
        y[i], ln[i] = encode_label(label)
    assert ln.min() >= 1 and X.min() >= 0 and X.max() <= 255

    # val 분할 — build_cache_v2 와 같은 절차(5%, RandomState(42) 순열).
    perm = np.random.RandomState(42).permutation(N_SYNTH)
    n_val = max(1, int(N_SYNTH * 0.05))
    val_idx, train_idx = perm[:n_val], perm[n_val:]

    arrays = dict(
        synth_train_images=X[train_idx],
        synth_train_label_ids=y[train_idx],
        synth_train_label_lens=ln[train_idx],
        synth_val_images=X[val_idx],
        synth_val_label_ids=y[val_idx],
        synth_val_label_lens=ln[val_idx],
    )
    for k in src.files:                       # 실사진 전부 원본 그대로
        if not k.startswith("synth_"):
            arrays[k] = src[k]
    np.savez(str(out), **arrays)

    # 검증 — 모양·실사진 바이트 동일.
    chk = np.load(str(out), allow_pickle=True)
    assert set(chk.files) == set(src.files), "키 집합 불일치"
    for k in src.files:
        assert chk[k].shape == src[k].shape and chk[k].dtype == src[k].dtype, k
    bad = [k for k in real_keys if md5(chk[k]) != real_md5[k]]
    assert not bad, f"실사진 배열이 변했다: {bad}"
    print(f"saved {out}")
    print(f"synth train={len(train_idx)} val={len(val_idx)} "
          f"(seed {SEED}, 프로파일 {len(synth_profiles.PROFILES)}종 균등)")
    print(f"real arrays byte-identical: {len(real_keys)}/{len(real_keys)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
