# READING 밴드 검출 모델 로컬 학습 — MediaPipe Model Maker (EfficientDet-Lite0)
#
# 데이터: assets_dev/train/reading/{train,valid}/  (COCO, 단일 클래스 reading_band)
# 산출:   assets_dev/train/reading/reading_band.tflite
#
# GPU: TF 2.10 이 Windows 네이티브 GPU 를 지원하는 마지막 버전이라 이 버전에
# 고정한다. CUDA/cuDNN 은 conda 로 공급(cudatoolkit=11.2, cudnn=8.1).
# GPU 가 잡히지 않으면 경고만 내고 CPU 로 계속 — 밤새 돌리면 된다.
import json
import sys
from pathlib import Path

import tensorflow as tf

ROOT = Path(__file__).resolve().parent
BATCH = 32
EPOCHS = 40


def main() -> int:
    gpus = tf.config.list_physical_devices("GPU")
    print(f"TF {tf.__version__} | GPU: {gpus}")
    if not gpus:
        print("경고: GPU 미탐지 — CPU 학습으로 계속한다(수 시간).")

    from mediapipe_model_maker import object_detector

    loader_methods = [
        m for m in dir(object_detector.DataLoader) if not m.startswith("_")
    ]
    print("DataLoader methods:", loader_methods)

    train_data = object_detector.DataLoader.from_coco_folder(
        str(ROOT / "train"), ann_file=str(ROOT / "train" / "_annotations.coco.json")
    )
    valid_data = object_detector.DataLoader.from_coco_folder(
        str(ROOT / "valid"), ann_file=str(ROOT / "valid" / "_annotations.coco.json")
    )
    print(f"train={len(train_data)} valid={len(valid_data)}")

    spec = object_detector.SupportedModels.EFFICIENTDET_LITE0
    # 작은 밴드 검출 — 입력 512(기본 320 보다 크게). VRAM 남는 만큼 정확도에 쓴다.
    try:
        spec.config.image_size = 512
        print("image_size=512 설정")
    except AttributeError:
        print("image_size 설정 불가 — 기본 해상도로 진행")

    model = object_detector.ObjectDetector.create(
        train_data,
        spec,
        validation_data=valid_data,
        hparams={
            "batch_size": BATCH,
            "epochs": EPOCHS,
        },
    )
    out = ROOT / "reading_band.tflite"
    model.export_model(str(out))
    print("EXPORTED", out, out.stat().st_size if out.exists() else -1)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:  # API 형태가 다르면 여기서 전체 서명을 덤프한다
        print("FATAL", type(e).__name__, e)
        try:
            import inspect

            print("DataLoader:", inspect.signature(object_detector.DataLoader.from_coco_folder))
        except Exception:
            print("help:", [m for m in dir(object_detector.DataLoader)])
        raise
