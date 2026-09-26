"""검출기 개선 재학습 — bandft_v1 시작 + 새 세대 합성(B2) 혼합.

사람 진단 2026-09-26: 기울어진 장면에서 박스가 앞·뒤 자리 한 자리를
잘라버린다 — 새 세대 합성의 정확 GT(B2 1,000장·기울기 포함)를 실사진
107장과 섞어 박스 회귀를 바로잡는다. 저 lr 유지(파인튜닝 연속).

    python D:/tmp/YOLOX/tools/train.py \
        -f D:/Project/sugarScan/assets_dev/train/yolox_bandft2_exp.py \
        -d 1 -b 8 --fp16 -expn bandft_v2 \
        -c D:/Project/sugarScan/assets_dev/train/yolox_out/bandft_v1/best_ckpt.pth
"""
from yolox_synthband_exp import Exp as BaseSynthbandExp


class Exp(BaseSynthbandExp):
    def __init__(self):
        super().__init__()
        self.data_dir = (r"D:\Project\sugarScan\assets_dev\train"
                         r"\bandft2_mixed")
        self.exp_name = "bandft_v2"
        self.max_epoch = 20
        self.batch_size = 8
        self.warmup_epochs = 1
        self.basic_lr_per_img = 0.000015625 * 0.1
        self.eval_interval = 5
        self.mosaic_prob = 0.0
        self.enable_mixup = False
