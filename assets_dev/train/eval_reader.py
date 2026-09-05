# reader_model을 hold-out(파인튜닝에 안 쓴 Datumo 장)에서 평가한다.
# 산출: reader_preds.json {id: [pred, gt, agree]} — 라벨러 모니터 표시용.
#
# **판독은 TTA 다수결이다**(2026-09-04). 같은 크롭을 줌·이동·대비로 N회 흔들어
# 읽고 최다 득표를 답으로 쓴다. 기본 greedy 대비 완전일치 94.83 → 96.88%,
# 위험군 1.60 → 1.07%. `agree` 는 그 답의 득표율로, **거절 신호**로도 쓴다 —
# 정답의 득표율 중앙은 1.000, 위험군은 0.556 이라 잘 갈린다.
#
# 세 번째 원소 `agree` 는 뒤에 덧붙인 것이라 옛 소비자(`v[0]`·`v[1]`)와 호환된다.
import json
from collections import Counter
from pathlib import Path

import cv2
import numpy as np
import tensorflow as tf
from PIL import Image, ImageOps

HERE = Path(__file__).resolve().parent
MODEL = HERE / "reader_model"
DATUMO = HERE.parent / "upstream" / "datumo"
GM_QUADS = HERE / "gmscreen_quads.jsonl"
CACHE = HERE / "data_cache_v2.npz"   # 학습셋 정본 — hold-out 은 여기서 정의된다
PREDS = HERE / "reader_preds.json"
IN_H, IN_W = 160, 320
NUM_CLASSES = 11
TTA_N = 8            # 추론 N+1 회. 0 이면 TTA 없이 기본 판독만
TTA_SEED = 7
# 학습 캐시와 같은 값이어야 한다. 정본은 build_cache_v2.BOX_MARGIN.
from build_cache_v2 import BOX_MARGIN  # noqa: E402


def _decode(logits):
    seq = np.argmax(logits, axis=-1)
    s, prev = [], -1
    for v in seq:
        v = int(v)
        if v != prev and v != NUM_CLASSES - 1:
            s.append(str(v))
        prev = v
    return "".join(s)


def _jitter(img, s, tx, ty, c):
    """학습 증강과 같은 종류로 흔든다 — 줌·이동·대비."""
    h, w = img.shape
    M = np.float32([[s, 0, tx * w + (1 - s) * w / 2],
                    [0, s, ty * h + (1 - s) * h / 2]])
    out = cv2.warpAffine(img, M, (w, h), borderMode=cv2.BORDER_REPLICATE)
    med = float(np.median(out))
    return np.clip((out.astype(np.float32) - med) * c + med, 0, 255).astype(np.uint8)


def main() -> int:
    model = tf.keras.models.load_model(MODEL)
    logits_model = tf.keras.Model(
        model.get_layer("img").input,
        model.get_layer("logits").output)

    # hold-out 의 정의는 **리더가 학습한 장을 뺀 것**이다. 그 정본은 학습 캐시의
    # real_train_ids 하나뿐이다.
    #
    # 2026-09-04 까지 여기서 labeled.jsonl 을 뺐는데 그건 틀린 집합이었다 —
    # 그 파일은 옛 밴드 라벨(좌표 검증 이전, band_boxes.jsonl 로 대체돼 이제
    # 아무도 안 읽는다)이고 리더 학습셋과는 358장 중 203장만 우연히 겹쳤다.
    # 결과가 양방향으로 틀렸다: 멀쩡한 356장이 평가에서 빠져 라벨러의 '판독'
    # 칸이 비어 보였고, **진짜 학습셋 1,372장 중 1,169장이 평가에 섞여** 있어
    # 표시된 성적이 실제보다 좋았다.
    trained = set()
    if CACHE.exists():
        import numpy as np
        trained = {str(v) for v in np.load(str(CACHE))["real_train_ids"]}
        print(f"학습셋 {len(trained)}장을 평가에서 제외한다 (캐시 기준)")
    else:
        print(f"경고: {CACHE.name} 이 없어 학습셋을 제외하지 못한다 — "
              "이 수치는 학습한 장을 포함한다")

    quads = {}
    for l in GM_QUADS.read_text(encoding="utf-8").splitlines():
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

    exact = wrong = skipped = 0
    misses = []
    preds_out = {}
    for cid, quad in quads.items():
        if cid in trained:
            continue
        gt = corrections.get(cid) or str(readings.get(cid))
        p = DATUMO / "extracted" / "TILDE" / f"{cid}.jpg"
        if not p.exists():
            skipped += 1
            continue
        try:
            with Image.open(p) as pil:
                pil.load()
                # 좌표 정본은 표시(EXIF 적용) 이미지다. gmscreen_quads.jsonl 은
                # cv2.imread(EXIF 적용)로 만들어진 표시 좌표계인데 PIL 은 EXIF 를
                # 무시한다 — 여기서 굽지 않으면 원본의 83.5%(orientation=6)에
                # 옆으로 누운 이미지에 올바른 좌표를 물려 평가가 통째로 망가진다.
                # 실측: 이 한 줄 유무로 완전일치 14.7% ↔ 90.7% (표본 300).
                pil = ImageOps.exif_transpose(pil)
                img = cv2.cvtColor(
                    np.asarray(pil.convert("RGB")), cv2.COLOR_RGB2GRAY)
        except Exception:
            skipped += 1
            continue
        # 프레이밍 규약은 학습 캐시와 **같아야 한다** — build_cache_v2.BOX_MARGIN.
        # 갈리면 그 불일치 자체가 성능 저하로 나타나 원인을 오독하게 된다.
        # (왼, 오른, 위, 아래) — 변마다 여유가 다르다.
        q = np.array(quad, dtype=np.float32)
        xs, ys = q[:, 0], q[:, 1]
        bx0, by0 = float(xs.min()), float(ys.min())
        bx1, by1 = float(xs.max()), float(ys.max())
        w0, h0 = bx1 - bx0, by1 - by0
        ml, mr, mt, mb = BOX_MARGIN
        bx0, by0 = max(0.0, bx0 - w0 * ml), max(0.0, by0 - h0 * mt)
        bx1 = min(float(img.shape[1] - 1), bx1 + w0 * mr)
        by1 = min(float(img.shape[0] - 1), by1 + h0 * mb)
        src = np.array(
            [[bx0, by0], [bx1, by0], [bx1, by1], [bx0, by1]], dtype=np.float32)
        dst = np.array(
            [[0, 0], [IN_W - 1, 0], [IN_W - 1, IN_H - 1], [0, IN_H - 1]],
            dtype=np.float32)
        rect = cv2.warpPerspective(
            img, cv2.getPerspectiveTransform(src, dst), (IN_W, IN_H))
        # 기본 판독 + TTA 흔들기 N회 → 다수결. 득표율을 함께 남긴다.
        variants = [rect]
        rng = np.random.RandomState(TTA_SEED + (hash(cid) & 0xFFFF))
        for _ in range(TTA_N):
            variants.append(_jitter(
                rect, rng.uniform(0.92, 1.08), rng.uniform(-0.03, 0.03),
                rng.uniform(-0.03, 0.03), rng.uniform(0.85, 1.15)))
        batch = np.asarray(variants, dtype=np.float32)[..., np.newaxis]
        outs = [_decode(l) for l in logits_model.predict(batch, verbose=0)]
        tally = Counter(outs)
        reading, k = tally.most_common(1)[0]
        preds_out[cid] = [reading, gt, round(k / len(outs), 3)]
        if reading == gt:
            exact += 1
        else:
            wrong += 1
            misses.append((cid, gt, reading))

    PREDS.write_text(json.dumps(preds_out, ensure_ascii=False), encoding="utf-8")
    total = exact + wrong
    print(f"hold-out total={total} (skipped {skipped})")
    print(f"exact={exact} ({100 * exact / max(total, 1):.1f}%) wrong={wrong}")
    for m in misses[:15]:
        print("  MISS", m)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
