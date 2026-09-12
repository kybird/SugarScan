# 생성기 품질 기준선 — 「생성기 품질 지표 — 합성만 학습해 실사진에서 잰다」 카드.
#
# 무엇을 재나: **pre 단계(합성만) 체크포인트**를 기기 단절 홀드아웃 1,138장에서
# eval_reader.py 와 완전히 같은 프로토콜(TTA 8+기본, crc32 시드, 득표율 거절
# 0.778)로 재독, device_eval_report.py 로 네 층(완전일치/위험/안전실패/무출력)
# 으로 집계한다. 파인튜닝(ft)이 실사진만 쓰므로, 이 수치가 생성기 품질이 성적에
# 직접 드러나는 유일한 자리다 — 이후 생성기 카드(DSEG 교체 등)는 이 기준선과
# 같은 명령으로 짝비교한다.
#
# ft 팔: 이 스크립트는 ft 를 다시 돌리지 않는다. 기존 _diag/device_split/
# eval_by_device.json(같은 pre 체크포인트에서 ft 60에폭을 태운 reader_model 의
# 평가)가 짝이 되므로 재현 명령에 포함하지 않는다.
#
# 재현(워크트리·메인 동일, GPU 는 conda run 통해서만 잡힌다):
#   conda run -n sugartrain python eval_generator_baseline.py \
#       --weights ../train_device/checkpoints_v2/pre_best.weights.h5 --name pre_v1
#
# 프레이밍 주의: eval_reader.py 는 원본 jpg(upstream/datumo/extracted/TILDE)를
# 다시 워프한다 — 카드가 금지한 '재워프'가 아니다. 금지는 **아틀라스류 조사에서
# 캐시를 안 두고 제각각 새로 워프하는 것**이고, 평가 프로토콜의 정본은 학습과
# 같은 build_cache_v2 프레이밍으로 원본에서 워프하는 eval_reader 다(BOX_MARGIN·
# band_crop_box 공유). hold-out 정의는 --cache 로 지정한 학습 캐시의
# real_train_ids(기기 단절 분할의 train 1,356장)뿐이다.
import argparse
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import ctc_reader_v2  # noqa: E402  아키텍처 정본 — import 만 쓴다(학습은 안 돈다)

# 기기 단절 분할 캐시. hold-out 정의(평가에서 뺄 train 장)의 정본.
DEVICE_CACHE = "../train_device/data_cache_v2.npz"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--weights", default=str(HERE.parent / "train_device"
                                             / "checkpoints_v2"
                                             / "pre_best.weights.h5"),
                    help="pre(합성만) 체크포인트 .weights.h5")
    ap.add_argument("--name", default="pre_v1",
                    help="모델·결과 파일 접두어 (reader_model_<name>, "
                         "reader_preds_<name>.json)")
    args = ap.parse_args()

    weights = Path(args.weights)
    assert weights.exists(), f"체크포인트 없음: {weights}"
    model_dir = HERE / f"reader_model_{args.name}"
    preds_path = HERE / f"reader_preds_{args.name}.json"
    bydev_path = HERE / "_diag" / "device_split" / f"eval_{args.name}_by_device.json"

    # 1) 아키텍처는 저장소 코드로 다시 세우고 pre 가중치만 얹는다.
    #    ft 산출물(reader_model)을 불러 덮어쓰지 않는다 — ft 관련 파일과의 결합을
    #    만들지 않기 위해서다.
    if not model_dir.exists():
        import tensorflow as tf  # noqa: F401  (ctc_reader_v2 가 이미 import 함)
        train_model, _ = ctc_reader_v2.build_model()
        train_model.load_weights(str(weights))
        train_model.save(str(model_dir))
        print(f"model dir: {model_dir}", flush=True)
    else:
        print(f"model dir 재사용: {model_dir}", flush=True)

    # 2) 판독 — eval_reader 프로토콜 그대로(TTA·crc32·거절 임계 불변).
    cmd_eval = [sys.executable, str(HERE / "eval_reader.py"),
                "--data-root", str(HERE),
                "--model", model_dir.name,
                "--cache", DEVICE_CACHE,
                "--out", preds_path.name]
    print("+", " ".join(cmd_eval), flush=True)
    subprocess.run(cmd_eval, check=True, cwd=str(HERE))

    # 3) 네 층 집계 — device_eval_report 프로토콜 그대로.
    cmd_rep = [sys.executable, str(HERE / "device_eval_report.py"),
               "--preds", str(preds_path), "--out", str(bydev_path)]
    print("+", " ".join(cmd_rep), flush=True)
    subprocess.run(cmd_rep, check=True, cwd=str(HERE))

    d = json.loads(bydev_path.read_text(encoding="utf-8"))
    print(json.dumps(d.get("overall", {}), ensure_ascii=False), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
