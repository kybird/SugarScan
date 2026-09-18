"""합성 밴드 검출기 — 규모 곡선 N=400 (방향별 400장, 학습 800장).

build_scaling_sets.py 가 생성했다. **손으로 고치지 마라** — 여섯 개의 스케줄이
서로 맞물려 있어서 하나만 고치면 곡선이 깨진다.

시작점 규칙은 yolox_synthband_exp.py 머리말이 정본이다(COCO 사전학습,
gmscreen 금지). 여섯 세트가 다른 것은 **학습 장수 하나뿐**이다 —
스텝 예산 7350 은 여섯이 모두 같고 v2 와도 같다.

    서로 다른 이미지 800장 x 반복 8 = 에포크당 6400개 항목
    **여섯 exp 의 아래 값은 전부 같다.** 다른 것은 위 줄의 '서로 다른 이미지'뿐.
    스텝/에폭 400  ·  max_epoch 18  ·  warmup 1  ·  no_aug 11
    -> 실제 스텝 7200 (목표 7350)

eval_interval 3 = max_epoch/5 이고 save_history_ckpt 가 기본 True 라
epoch_N_ckpt.pth 가 **스텝 비율 0.2·0.4·0.6·0.8·1.0 지점**에 떨어진다.
여섯 런의 스냅샷이 같은 스텝 비율에 있으므로 '데이터 고정·스텝 변화' 축을
규모 곡선 안에서 같이 읽을 수 있다 — 가장 큰 세트가 예산 끝에서 아직
오르고 있으면 곡선의 꼭대기가 과소평가된 것이고, 예산을 다시 잡아야 한다.

    python D:/tmp/YOLOX/tools/train.py         -f D:/Project/sugarScan/assets_dev/train/yolox_scale_0400_exp.py         -d 1 -b 16 --fp16 -expn scale_0400         -c D:/Project/sugarScan/assets_dev/train/weights/yolox_nano.pth
"""
from yolox_synthband_exp import Exp as BaseSynthbandExp


class Exp(BaseSynthbandExp):
    def __init__(self):
        super().__init__()
        self.data_dir = r"D:\Project\sugarScan\assets_dev\train\synth_coco\S_scale"
        self.train_ann = "instances_train_0400.json"
        self.val_ann = "instances_val2017.json"
        self.exp_name = "scale_0400"
        # 스텝 고정 — 아래 넷은 build_scaling_sets.py 가 계산한 값이다.
        self.max_epoch = 18
        self.warmup_epochs = 1
        self.no_aug_epochs = 11
        self.eval_interval = 3
