# CTC 리더 logits 모델을 ONNX 로 내보내고 TF 추론과의 파리티를 검증한다.
#
# 배경(G28·86d3dbe): tflite 변환은 BiLSTM 의 TensorListReserve 로 불가라 온디바이스
# 경로는 ONNX 로 확정됐다. 이 스크립트는 그 첫 단계 — PC 에서 모델 측 준비를
# 끝낸다(런타임 패키지 선택은 사람 판정 대기 중).
#
# 단계:
#   1. reader_model(SavedModel) 로드 → logits 모델(입력만, CTC 손실 레이어 제외)
#   2. tf2onnx 변환(opset 13) → reader_model.onnx
#   3. 파리티: 학습 캐시의 real holdout 이미지(전량)에 대해 TF logits 와
#      ONNX Runtime logits 를 비교 — 최대 절대차 + greedy 디코드 완전일치.
#      캐시 배열을 그대로 쓰므로 전처리는 구조적으로 동일하다(§36).
#
# 입력 규격(§36, 정본은 이 파일 헤더와 reader_onnx_spec.md):
#   - 입력: float32 NHWC [N,160,320,1], 값 0~255(정규화는 모델 첫 층 Rescaling
#     이 담당: x/127.5 - 1)
#   - 출력: float32 [N,40,11] logits(시간축 40, 클래스 0~9 + blank=10)
#   - 디코드: greedy CTC(반복·blank 제거)
import argparse
import json
import sys
from pathlib import Path

import numpy as np
import tensorflow as tf
import tf2onnx

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from ctc_reader_v2 import CTCLayer, NUM_CLASSES, SEQ_LEN  # noqa: E402


def greedy_decode(logits):
    """eval_reader._decode 와 동일한 greedy CTC."""
    ids = logits.argmax(-1)
    out, prev = [], -1
    for v in ids:
        if v != prev and v != NUM_CLASSES - 1:
            out.append(str(v))
        prev = v
    return "".join(out)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="reader_model")
    ap.add_argument("--cache", default="data_cache_v2.npz")
    ap.add_argument("--out", default="reader_model.onnx")
    ap.add_argument("--batch", type=int, default=64)
    ap.add_argument("--max-images", type=int, default=0,
                    help="0 이면 홀드아웃 전량")
    args = ap.parse_args()

    model_dir = HERE / args.model
    model = tf.keras.models.load_model(
        model_dir, custom_objects={"CTCLayer": CTCLayer})
    logits_model = tf.keras.Model(
        model.get_layer("img").input, model.get_layer("logits").output)
    print(f"로드: {model_dir.name} → logits {logits_model.output_shape}")

    spec = (tf.TensorSpec((None, 160, 320, 1), tf.float32, name="img"),)
    proto, _ = tf2onnx.convert.from_keras(
        logits_model, input_signature=spec, opset=13)
    onnx_path = HERE / args.out
    onnx_path.write_bytes(proto.SerializeToString())
    print(f"변환: {onnx_path.name} {onnx_path.stat().st_size / 1e6:.2f} MB")

    import onnxruntime as ort
    sess = ort.InferenceSession(str(onnx_path),
                                providers=["CPUExecutionProvider"])
    onnx_in = sess.get_inputs()[0].name

    cache = np.load(HERE / args.cache, allow_pickle=True)
    X = cache["real_holdout_images"]
    ids = [str(x) for x in cache["real_holdout_ids"]]
    if args.max_images:
        X, ids = X[: args.max_images], ids[: args.max_images]
    print(f"파리티 대상: {len(ids)}장 (캐시 홀드아웃)")

    max_diff = 0.0
    agree = 0
    diffs = []
    for s in range(0, len(X), args.batch):
        batch = X[s: s + args.batch][..., np.newaxis].astype(np.float32)
        tf_out = logits_model.predict(batch, verbose=0)
        ort_out = sess.run(None, {onnx_in: batch})[0]
        d = float(np.abs(tf_out - ort_out).max())
        max_diff = max(max_diff, d)
        diffs.append(d)
        for k in range(len(batch)):
            if greedy_decode(tf_out[k]) == greedy_decode(ort_out[k]):
                agree += 1
    report = {
        "model": args.model,
        "cache": args.cache,
        "onnx": args.out,
        "onnx_bytes": onnx_path.stat().st_size,
        "images": len(ids),
        "decode_match": agree,
        "decode_match_pct": round(100 * agree / len(ids), 2),
        "logit_max_abs_diff": max_diff,
        "logit_mean_batchdiff": round(float(np.mean(diffs)), 6),
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    (HERE / "_diag").mkdir(exist_ok=True)
    (HERE / "_diag" / "reader_onnx_parity.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
