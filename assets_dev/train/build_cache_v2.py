# 데이터 캐시 구축 v2 — 라벨 정렬 수정 + val 분할 + 정수 라벨 배열.
# 산출: assets_dev/train/data_cache_v2.npz
import json
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageOps

HERE = Path(__file__).resolve().parent
DATUMO = HERE.parent / "upstream" / "datumo"
SYNTH_DIR = HERE / "synth_screens" / "images"
IN_H, IN_W = 160, 320
BLANK = 10
MAX_LABEL = 3

# 검출 박스를 사방으로 넓혀서 자른다.
#
# 근거(2026-09-04, 사람 라벨 396장 대조): GM 박스는 **오른쪽을 계통적으로 덜
# 덮는다** — 사람 박스 폭 대비 중앙 +6%, p90 +19%, p95 +28%. 79%의 장이 덜
# 덮이고 11%는 오히려 더 덮는다(p5 −6%). 혈당계 표시는 우측 정렬이라 잘리는
# 것은 마지막 자리이고, 실제로 한 글자 오독 41건 중 24건이 마지막 자리다.
#
# **일률적으로 오른쪽만 늘리지 않는다.** 편차(σ=0.096)가 평균(0.072)보다 커서
# 하나의 값으로는 못 맞춘다 — 이미 맞거나 넓게 잡은 25% 의 장에는 배경만
# 들어온다(추론 시 +8% 패딩 실험이 순손실이었다). 대신 사방으로 여유를 주고
# **학습 증강이 그 여유 안에서 프레이밍을 흔들게** 해서, 리더가 빡빡한 크롭과
# 헐거운 크롭 양쪽에 둔감해지도록 만든다.
#
# 이 값을 바꾸면 추론 경로(eval_reader.py)도 같이 바꿔야 한다 — 학습과 추론의
# 프레이밍 규약이 갈리면 그 자체가 성능 저하다.
BOX_MARGIN = 0.10


def encode_label(s: str):
    ids = [int(ch) for ch in s]
    padded = ids + [BLANK] * (MAX_LABEL - len(ids))
    return padded[:MAX_LABEL], min(len(ids), MAX_LABEL)


def main() -> int:
    OUT = HERE / "data_cache_v2.npz"

    # ===== 합성 =====
    synth_labels = {}
    for seed in (1, 2, 3):
        f = HERE / "synth_screens" / f"labels_{seed}.json"
        if f.exists():
            synth_labels.update(json.loads(f.read_text(encoding="utf-8")))
    keys = sorted(synth_labels.keys())

    X_synth = np.zeros((len(keys), IN_H, IN_W), dtype=np.uint8)
    y_synth = np.full((len(keys), MAX_LABEL), BLANK, dtype=np.int32)
    len_synth = np.zeros(len(keys), dtype=np.int32)
    kept = 0
    for k in keys:
        img = cv2.imread(str(SYNTH_DIR / f"{k}.png"), cv2.IMREAD_GRAYSCALE)
        if img is None:
            continue
        X_synth[kept] = cv2.resize(img, (IN_W, IN_H),
                                   interpolation=cv2.INTER_AREA)
        ids, ln = encode_label(synth_labels[k])
        y_synth[kept] = ids
        len_synth[kept] = ln
        kept += 1
    X_synth = X_synth[:kept]
    y_synth = y_synth[:kept]
    len_synth = len_synth[:kept]
    print(f"합성: {kept}/{len(keys)}")

    # ===== 실사진 rect =====
    # GM 쿼드 있는 전체 풀(2,007) × GT 값 → 시드 분할 train/holdout.
    # 밴드 라벨 304장에 한정하면 실데이터가 너무 적어 암기만 한다(실측).
    quads = {}
    for l in (HERE / "gmscreen_quads.jsonl").read_text(encoding="utf-8").splitlines():
        if l.strip():
            j = json.loads(l)
            quads[j["id"]] = j["quad"]
    readings = {}
    for l in (DATUMO / "labels.jsonl").read_text(encoding="utf-8").splitlines():
        if l.strip():
            j = json.loads(l)
            readings[j["id"]] = j["reading"]
    corrections = {}
    corr = HERE / "gt_corrections.jsonl"
    if corr.exists():
        for l in corr.read_text(encoding="utf-8").splitlines():
            if l.strip():
                j = json.loads(l)
                corrections[j["id"]] = j["corrected"]

    pool = []
    for cid, quad in sorted(quads.items()):
        val = corrections.get(cid, readings.get(cid))
        val = str(val or "")
        if not val.isdigit():
            continue
        if not (DATUMO / "extracted" / "TILDE" / f"{cid}.jpg").exists():
            continue
        pool.append((cid, quad, val))
    rng = np.random.RandomState(123)
    rng.shuffle(pool)
    n_hold = max(1, int(len(pool) * 0.45))
    hold_pool = pool[:n_hold]
    train_pool = pool[n_hold:]
    print(f"실사진 풀: {len(pool)} → train {len(train_pool)} / holdout {len(hold_pool)}")

    def build_real(rows):
        Xs, ys, ls, ids = [], [], [], []
        for cid, quad, val in rows:
            p = DATUMO / "extracted" / "TILDE" / f"{cid}.jpg"
            try:
                with Image.open(p) as pil:
                    pil.load()
                    # 좌표 정본은 표시(EXIF 적용) 이미지 — gmscreen_quads.jsonl 은
                    # cv2.imread(EXIF 적용) 로 만들어져 표시 좌표계다. PIL 은 EXIF 를
                    # 무시하므로 여기서 굽지 않으면 표시 좌표를 raw 이미지에 물린다.
                    pil = ImageOps.exif_transpose(pil)
                    g = cv2.cvtColor(
                        np.asarray(pil.convert("RGB")), cv2.COLOR_RGB2GRAY)
            except Exception:
                continue
            q = np.array(quad, dtype=np.float32)
            xs, ys_ = q[:, 0], q[:, 1]
            x0, y0 = float(xs.min()), float(ys_.min())
            x1, y1 = float(xs.max()), float(ys_.max())
            mw, mh = (x1 - x0) * BOX_MARGIN, (y1 - y0) * BOX_MARGIN
            x0, y0 = max(0.0, x0 - mw), max(0.0, y0 - mh)
            x1 = min(float(g.shape[1] - 1), x1 + mw)
            y1 = min(float(g.shape[0] - 1), y1 + mh)
            src = np.array(
                [[x0, y0], [x1, y0], [x1, y1], [x0, y1]], dtype=np.float32)
            dst = np.array(
                [[0, 0], [IN_W - 1, 0], [IN_W - 1, IN_H - 1], [0, IN_H - 1]],
                dtype=np.float32)
            rect = cv2.warpPerspective(
                g, cv2.getPerspectiveTransform(src, dst), (IN_W, IN_H))
            ids_, ln = encode_label(val)
            Xs.append(rect)
            ys.append(ids_)
            ls.append(ln)
            ids.append(cid)
        return (np.asarray(Xs, dtype=np.uint8), np.asarray(ys, dtype=np.int32),
                np.asarray(ls, dtype=np.int32), np.array(ids))

    X_rt, y_rt, l_rt, id_rt = build_real(train_pool)
    X_rh, y_rh, l_rh, id_rh = build_real(hold_pool)
    print(f"실사진 rect: train {len(X_rt)} / holdout {len(X_rh)}")

    # ===== 무결성 =====
    assert X_synth.shape[0] == kept
    assert np.all(len_synth >= 1)
    assert X_synth.min() >= 0 and X_synth.max() <= 255
    assert len(X_rt) > 0 and np.all(l_rt >= 1)
    assert len(X_rh) > 0 and np.all(l_rh >= 1)
    assert not (set(id_rt.tolist()) & set(id_rh.tolist()))

    # ===== val 분할 (합성 5%) =====
    rng2 = np.random.RandomState(42)
    perm = rng2.permutation(kept)
    n_val = max(1, int(kept * 0.05))
    val_idx = perm[:n_val]
    train_idx = perm[n_val:]

    # ===== 저장 =====
    np.savez(
        str(OUT),
        synth_train_images=X_synth[train_idx],
        synth_train_label_ids=y_synth[train_idx],
        synth_train_label_lens=len_synth[train_idx],
        synth_val_images=X_synth[val_idx],
        synth_val_label_ids=y_synth[val_idx],
        synth_val_label_lens=len_synth[val_idx],
        real_train_images=X_rt,
        real_train_label_ids=y_rt,
        real_train_label_lens=l_rt,
        real_train_ids=id_rt,
        real_holdout_images=X_rh,
        real_holdout_label_ids=y_rh,
        real_holdout_label_lens=l_rh,
        real_holdout_ids=id_rh,
    )
    print(f"캐시: {OUT}")
    print(f"  train synth: {len(train_idx)} | val synth: {n_val}"
          f" | real train: {len(X_rt)} | real holdout: {len(X_rh)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
