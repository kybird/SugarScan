"""실사진 밴드 파인튜닝 — synthband_v2_a2 시작(사람 결정 (가), 2026-09-24).

기저 선정 근거(홀드아웃 n=119 사전 평가, eval_synthband_real --side holdout):
    synthband_v2_a2  IoU 중앙 0.8229 · p10 0.7010 · 검출 실패 5
    synthband_v3_wide 0.7709 · p10 0.0000 · 실패 29   ← 실촌에서 퇴보

소표본(≈110장)에 맞춘 유일한 변경들 — 합성 레시피와 여러 축을 동시에
바꾸면 무엇이 움직였는지 못 가른다(a3 실험의 교훈 구조는 유지):
  · lr ×0.1(파인튜닝)  · mosaic 끔(모자이크는 파편화만 만든다)
  · mixup 끔  · 에폭 30  · 배치 8(8GB GPU 공유 환경)

    python D:/tmp/YOLOX/tools/train.py \
        -f D:/Project/sugarScan/assets_dev/train/yolox_bandft_exp.py \
        -d 1 -b 8 --fp16 -expn bandft_v1 \
        -c D:/Project/sugarScan/assets_dev/train/yolox_out/synthband_v2_a2/best_ckpt.pth
"""
from yolox_synthband_exp import Exp as BaseSynthbandExp


class Exp(BaseSynthbandExp):
    def __init__(self):
        super().__init__()
        self.data_dir = (r"D:\Project\sugarScan\assets_dev\train"
                         r"\bandft_coco")
        self.exp_name = "bandft_v1"
        self.max_epoch = 30
        self.batch_size = 8
        self.warmup_epochs = 1
        self.basic_lr_per_img = 0.000015625 * 0.1
        self.eval_interval = 5
        self.mosaic_prob = 0.0
        self.enable_mixup = False
