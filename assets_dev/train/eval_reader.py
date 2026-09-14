# reader_model을 hold-out(파인튜닝에 안 쓴 Datumo 장)에서 평가한다.
# 산출: reader_preds.json {id: [pred, gt, agree]} — 라벨러 모니터 표시용.
#
# **판독은 TTA 다수결이다**(2026-09-04). 같은 크롭을 줌·이동·대비로 N회 흔들어
# 읽고 최다 득표를 답으로 쓴다. 기본 greedy 대비 완전일치 94.83 → 96.88%,
# 위험군 1.60 → 1.07%. `agree` 는 그 답의 득표율로, **거절 신호**로도 쓴다 —
# 정답의 득표율 중앙은 1.000, 위험군은 0.556 이라 잘 갈린다.
#
# 세 번째 원소 `agree` 는 뒤에 덧붙은 것이라 옛 소비자(`v[0]`·`v[1]`)와 호환된다.
#
# TTA 시드는 cid 를 crc32 로 해시한다(2026-09-08, G29-A). 예전의 파이썬 hash() 는
# 프로세스마다 솔트가 달라 같은 이미지가 실행마다 다른 변형을 받아 수치가 재현
# 되지 않았다(failure-atlas §7.1). 위의 96.88/1.07 은 불안정한 시드로 잰 옛 값 —
# crc32 기준선은 docs/reports/G29-letterbox-warp.md 에 있다.
import argparse
import json
import zlib
from collections import Counter
from pathlib import Path

import cv2
import numpy as np
import tensorflow as tf
from PIL import Image, ImageOps

HERE = Path(__file__).resolve().parent
MODEL_NAME = "reader_model"
CACHE_NAME = "data_cache_v2.npz"   # 학습셋 정본 — hold-out 은 여기서 정의된다
PREDS_NAME = "reader_preds.json"
IN_H, IN_W = 160, 320
NUM_CLASSES = 11
TTA_N = 8            # 추론 N+1 회. 0 이면 TTA 없이 기본 판독만
TTA_SEED = 7
# 학습 캐시와 같은 값이어야 한다. 정본은 build_cache_v2.BOX_MARGIN.
# band_crop_box 도 마찬가지 — G30 세로형 크롭의 유일한 구현은 build_cache_v2 에
# 있고 학습·추론이 같은 함수를 써야 프레이밍이 갈라지지 않는다.
from build_cache_v2 import BOX_MARGIN, band_crop_box, load_rotated_ids  # noqa: E402


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


def load_gray(img_path):
    """원본 jpg → 표시(EXIF 적용) 좌표계 회색조. 실패 시 None.

    좌표 정본은 표시 이미지다. gmscreen_quads.jsonl 은 cv2.imread(EXIF 적용)로
    만들어진 표시 좌표계인데 PIL 은 EXIF 를 무시한다 — 여기서 굽지 않으면 원본의
    83.5%(orientation=6)에 옆으로 누운 이미지에 올바른 좌표를 물려 평가가 통째로
    망가진다. 실측: 이 한 줄 유무로 완전일치 14.7% ↔ 90.7% (표본 300).
    """
    try:
        with Image.open(img_path) as pil:
            pil.load()
            pil = ImageOps.exif_transpose(pil)
            return cv2.cvtColor(
                np.asarray(pil.convert("RGB")), cv2.COLOR_RGB2GRAY)
    except Exception:
        return None


# framed_src_rect / frame_crop 의 정본은 build_cache_v2 로 옮겼다(2026-09-13).
# 프레이밍 규약(BOX_MARGIN)이 거기 있는데 함수가 여기 있으면, 합성 쪽에서
# 같은 프레이밍을 쓰려고 eval_reader 를 import 하는 순간 tensorflow 가 딸려
# 온다. 이름은 그대로 재수출한다 — 기존 호출자(make_failure_atlas·
# g30_check_cache)가 eval_reader 에서 가져간다.
from build_cache_v2 import framed_src_rect, frame_crop  # noqa: E402,F401



def parse_args():
    """평가 대상을 갈아 끼울 수 있는 CLI. 인자 없이 돌리면 종래 동작 그대로다.

    워크트리에서 실행할 때는 --data-root 로 메인 트리의 assets_dev/train 을
    지정한다 — npz·모델·원본 이미지는 전부 gitignored 라 워크트리에 없다.
    """
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--data-root", type=Path, default=None,
                    help="데이터 루트(기본: 스크립트 폴더)")
    ap.add_argument("--model", default=MODEL_NAME,
                    help="data_root 기준 모델 디렉터리명")
    ap.add_argument("--cache", default=CACHE_NAME,
                    help="hold-out 정의의 정본 캐시")
    ap.add_argument("--out", default=None,
                    help="판독 결과 json(data_root 기준 경로). 기본: "
                         "reader_preds.json (--bandcrop 면 reader_preds_bandcrop"
                         ".json)")
    ap.add_argument("--bandcrop", action="store_true",
                    help="G30 세로형 크롭(세로 [0.00, 0.72])을 추론 프레이밍에도 "
                         "적용한다 — 학습 캐시와 같은 band_crop_box 를 쓴다")
    args = ap.parse_args()
    if args.out is None:
        args.out = ("reader_preds_bandcrop.json" if args.bandcrop
                    else PREDS_NAME)
    return args


def main() -> int:
    args = parse_args()
    data = args.data_root if args.data_root else HERE
    model_dir = data / args.model
    datumo = data.parent / "upstream" / "datumo"
    gm_quads = data / "gmscreen_quads.jsonl"
    cache_path = data / args.cache
    preds_path = data / args.out
    model = tf.keras.models.load_model(model_dir)
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
    if cache_path.exists():
        trained = {str(v) for v in np.load(str(cache_path))["real_train_ids"]}
        print(f"학습셋 {len(trained)}장을 평가에서 제외한다 (캐시 기준)")
    else:
        print(f"경고: {cache_path.name} 이 없어 학습셋을 제외하지 못한다 — "
              "이 수치는 학습한 장을 포함한다")

    quads = {}
    for l in gm_quads.read_text(encoding="utf-8").splitlines():
        if l.strip():
            j = json.loads(l)
            quads[j["id"]] = j["quad"]
    rotated_ids = load_rotated_ids(data) if args.bandcrop else frozenset()
    if args.bandcrop:
        print(f"bandcrop 켜짐 — 세로형만 세로 [0.00, 0.72] 크롭 "
              f"(rotated 제외 {len(rotated_ids)}장)")

    readings = {}
    for l in (datumo / "labels.jsonl").read_text(encoding="utf-8").splitlines():
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

    exact = wrong = skipped = 0
    misses = []
    preds_out = {}
    for cid, quad in quads.items():
        if cid in trained:
            continue
        gt = corrections.get(cid) or str(readings.get(cid))
        p = datumo / "extracted" / "TILDE" / f"{cid}.jpg"
        if not p.exists():
            skipped += 1
            continue
        img = load_gray(p)
        if img is None:
            skipped += 1
            continue
        rect = frame_crop(img, quad, cid, args.bandcrop, rotated_ids)
        # 기본 판독 + TTA 흔들기 N회 → 다수결. 득표율을 함께 남긴다.
        # 시드의 cid 해시는 crc32 — 파이썬 hash() 는 프로세스마다 솔트가 달라
        # 같은 장이 실행마다 다른 변형을 받아 결과가 재현되지 않았다(G29-A).
        variants = [rect]
        rng = np.random.RandomState(
            TTA_SEED + (zlib.crc32(cid.encode("utf-8")) & 0xFFFF))
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

    preds_path.write_text(json.dumps(preds_out, ensure_ascii=False), encoding="utf-8")
    total = exact + wrong
    print(f"hold-out total={total} (skipped {skipped})")
    print(f"exact={exact} ({100 * exact / max(total, 1):.1f}%) wrong={wrong}")
    for m in misses[:15]:
        print("  MISS", m)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
