# 리더 합성 팔 빌더 — 합성 화면을 리더 캐시(320x160)로 굽는다.
#
# 2026-09-13 개편: 렌더러를 synth_profiles.render_any 에서 **synth_panel** 로
# 옮겼다. 그 전에는 리더와 검출기가 서로 다른 합성기를 봤다 — 검출기는
# synth_panel(기기 12종·극성 사람 선언·단위 아래·기기 형질 고정), 리더는
# render_profiled(극성을 rng<0.5 동전던지기, 기기 개념 없음, 단위가 숫자 옆).
# 한 저장소에서 두 모델이 다른 세계를 배우고 있었다.
#
# 프레이밍도 맞췄다. 실사진 팔은 GM 쿼드를 BOX_MARGIN 10% 로 사방 확장해
# 워프하는데(reader_onnx_spec.md '프레임 조립'), 옛 합성 팔은 화면만 320x160
# 으로 그렸다. 이제 synth_panel.reader_view 가 실사진 팔과 같은 함수
# (build_cache_v2.framed_src_rect)를 통과한다.
#
#  - 실사진 배열·id 는 바이트 그대로(분할·홀드아웃 불변 — md5 로 증명).
#  - 합성 장수·val 분할 절차는 build_cache_v2 와 동일: 23,000장, 5% val,
#    RandomState(42) 순열.
#  - 값 분포는 코퍼스 실측(synth_panel.sample_value) — 구판의 균등
#    randint(30,511) 은 200 이상을 8.0% 가 아니라 3자리의 76% 로 만들었다.
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
import synth_panel  # noqa: E402
from build_cache_v2 import encode_label, BLANK, MAX_LABEL, IN_H, IN_W  # noqa: E402

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
    X = np.zeros((N_SYNTH, IN_H, IN_W), np.uint8)
    y = np.full((N_SYNTH, MAX_LABEL), BLANK, np.int32)
    ln = np.zeros(N_SYNTH, np.int32)
    for i in range(N_SYNTH):
        val = synth_panel.sample_value(rng)
        s = synth_panel.render_panel(val, rng)
        img, _ = synth_panel.reader_view(s)
        label = s["label"]
        assert label == str(val) and label.isdigit(), f"라벨 오염: {label!r}"
        assert img.shape == (IN_H, IN_W), img.shape
        X[i] = img
        if (i + 1) % 2000 == 0:
            print(f"  {i + 1}/{N_SYNTH}", flush=True)
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
          f"(seed {SEED}, 렌더러 synth_panel, 프로파일 "
          f"{len(synth_panel.PROFILES)}종)")
    print(f"real arrays byte-identical: {len(real_keys)}/{len(real_keys)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
