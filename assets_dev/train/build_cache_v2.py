# 데이터 캐시 구축 v2 — 라벨 정렬 수정 + val 분할 + 정수 라벨 배열.
# 산출: assets_dev/train/data_cache_v2.npz
#       python build_cache_v2.py --bandcrop → data_cache_v2_bandcrop.npz (G30)
import argparse
import json
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageOps

HERE = Path(__file__).resolve().parent
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
#
# **변마다 따로** 준다 (G26). 검출 오차는 좌우가 다르다(사람 라벨 396장 실측):
# 오른쪽이 들어온 정도의 중앙 +0.060 (10% 넘게 잘린 장 104) vs 왼쪽 +0.019 (32) ·
# 위 −0.002 (6) · 아래 −0.014 (10). 오른쪽이 3배 심한데 같은 여유를 주면
# 왼쪽은 배경만 들어와 숫자가 작아지고 오른쪽은 여전히 모자라다.
# 순서: (왼, 오른, 위, 아래).
BOX_MARGIN = (0.10, 0.10, 0.10, 0.10)

# G30 세로형 밴드 크롭 — 세로 [0.00, 0.72] 를 남기고 아래(날짜·아이콘)를 자른다.
# 근거(2026-09-08, 밴드 라벨 86장 실측 — 사람 LCD 라벨 안의 상대 위치):
# 세로형은 숫자줄이 위쪽 절반에 있고 아랫변 p95 = 0.658, 윗변 p5 = 0.077 이다.
# 0.72 는 p95 에 여유를 준 값이고, 위를 0.00 에서 움직이지 않는 것은 p5 가
# 0.077 이라 5% 의 장에서 숫자 윗획이 잘리기 때문이다. **두 값 다 바꾸지 않는다.**
BAND_CROP_BOTTOM = 0.72
# 원본 GM 박스(마진 적용 전)의 w/h > 이 값이면 가로형. 가로형은 크롭하지
# 않는다 — GM 박스가 밴드를 담고 있지 않다(46장 중 14장에서 밴드가 박스 왼쪽
# 바깥, 2026-09-08 실측). 가로형은 크롭 문제가 아니라 검출 문제다(별도 작업).
WIDE_RATIO = 1.2


def load_rotated_ids(data):
    """band_rotation.jsonl 의 id 집합 — 가로형 기기를 눕혀 찍은 장들.

    이 장들은 밴드가 세로로 길어 보여 형태 판정에 넣으면 숫자를 자른다.
    크롭에서 제외하고 원본 박스를 그대로 쓴다.
    """
    ids = set()
    f = Path(data) / "band_rotation.jsonl"
    if f.exists():
        for l in f.read_text(encoding="utf-8").splitlines():
            if l.strip():
                ids.add(json.loads(l)["id"])
    return ids


def band_crop_box(x0, y0, x1, y1, cid, rotated_ids):
    """원본 GM 박스(마진 전)에서 세로형만 아래쪽 숫자 없는 구간을 잘라낸다.

    G30 실험의 **유일한** 크롭 구현이다. 학습 캐시(이 파일)와 추론
    (eval_reader.framed_src_rect)이 이 함수를 공유한다 — 두 곳에 따로
    구현하면 크롭이 어긋나고 그 차이가 성능 차이로 위장된다
    (antipatterns/duplicated-geometry-implementation).

    - 비율의 기준은 BOX_MARGIN 적용 **전**의 원본 박스다. 순서는
      ①이 함수로 구간을 잘라 새 박스를 만들고 ②마진을 적용하는 것.
      뒤집으면 크롭이 밀리고 그 밀림이 "효과 없다"로 보인다.
    - 가로형(w/h > WIDE_RATIO)과 rotated_ids 의 장은 입력 그대로 돌려준다.
    """
    w0, h0 = x1 - x0, y1 - y0
    if cid in rotated_ids:
        return x0, y0, x1, y1
    if w0 > WIDE_RATIO * h0:
        return x0, y0, x1, y1
    return x0, y0, x1, y0 + BAND_CROP_BOTTOM * h0


def encode_label(s: str):
    ids = [int(ch) for ch in s]
    padded = ids + [BLANK] * (MAX_LABEL - len(ids))
    return padded[:MAX_LABEL], min(len(ids), MAX_LABEL)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--bandcrop", action="store_true",
                    help="세로형(GM 박스 w/h<=1.2)만 세로 [0.00, 0.72] 를 남겨 "
                         "크롭한 data_cache_v2_bandcrop.npz 를 만든다(G30). "
                         "가로형·회전 장·합성은 프레이밍 불변")
    ap.add_argument("--data-root", type=Path, default=None,
                    help="데이터 루트(기본: 스크립트 폴더). 워크트리 실행 시 메인 "
                         "트리의 assets_dev/train — 원본·합성 화면은 gitignored 다")
    args = ap.parse_args()

    data = args.data_root if args.data_root else HERE
    # 분할 시드(123/42)·풀 필터·BOX_MARGIN 은 bandcrop 과 무관하게 동일해야
    # 한다 — bandcrop 캐시의 train/holdout 이 기존 캐시와 같은 장들을 담아야
    # A/B 가 짝지은 비교가 된다(빌드 후 g30_check_cache.py 로 검증한다).
    OUT = data / ("data_cache_v2_bandcrop.npz" if args.bandcrop
                  else "data_cache_v2.npz")
    DATUMO = data.parent / "upstream" / "datumo"
    SYNTH_DIR = data / "synth_screens" / "images"
    rotated_ids = load_rotated_ids(data)

    # ===== 합성 =====
    synth_labels = {}
    for seed in (1, 2, 3):
        f = data / "synth_screens" / f"labels_{seed}.json"
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
    for l in (data / "gmscreen_quads.jsonl").read_text(encoding="utf-8").splitlines():
        if l.strip():
            j = json.loads(l)
            quads[j["id"]] = j["quad"]
    readings = {}
    for l in (DATUMO / "labels.jsonl").read_text(encoding="utf-8").splitlines():
        if l.strip():
            j = json.loads(l)
            readings[j["id"]] = j["reading"]
    corrections = {}
    corr = data / "gt_corrections.jsonl"
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

    crop_tally = {"tall_cropped": 0, "wide_kept": 0, "rotated_kept": 0}

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
            # G30 세로형 크롭 — ①원본 박스에서 구간을 잘라 새 박스을 만들고
            # ②(아래에서) 그 새 박스에 BOX_MARGIN 을 적용한다. 이 순서가
            # 지시서의 규격이다. 뒤집으면 크롭이 마진만큼 밀린다.
            if args.bandcrop:
                w_pre, h_pre = x1 - x0, y1 - y0
                if cid in rotated_ids:
                    crop_tally["rotated_kept"] += 1
                elif w_pre > WIDE_RATIO * h_pre:
                    crop_tally["wide_kept"] += 1
                else:
                    crop_tally["tall_cropped"] += 1
                x0, y0, x1, y1 = band_crop_box(
                    x0, y0, x1, y1, cid, rotated_ids)
            # 여유는 변마다 따로. 기준 폭·높이는 **마진 적용 전의 박스**(크롭이
            # 켜졌다면 크롭된 새 박스) 것을 쓴다 — 좌측 여유로 x0 이 움직인 뒤의
            # 폭을 쓰면 오른쪽 여유가 좌측 값에 영향을 받는다(순서 의존).
            w0, h0 = x1 - x0, y1 - y0
            ml, mr, mt, mb = BOX_MARGIN
            x0, y0 = max(0.0, x0 - w0 * ml), max(0.0, y0 - h0 * mt)
            x1 = min(float(g.shape[1] - 1), x1 + w0 * mr)
            y1 = min(float(g.shape[0] - 1), y1 + h0 * mb)
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
    if args.bandcrop:
        print(f"G30 크롭 집계(실사진 train+holdout): {crop_tally}")

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
