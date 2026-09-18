"""합성 밴드 검출기 — COCO 시작 + 합성 5배(A2 5,000장).

`yolox_synthband_exp.py` 와 **데이터 양만** 다르다. 시작점 규칙(COCO 사전학습,
gmscreen 금지)과 에폭·배치·해상도·증강은 전부 같다 — 두 가지를 동시에 바꾸면
무엇이 움직였는지 못 가른다.

왜 필요한가(2026-09-17): 시작점을 gmscreen(실촬 1,276장 학습)에서 COCO 로
바꾸자 성적이 내려갔다 — 세트 B 검출 실패 1 -> 10, C 0 -> 5. 라이선스를
깨끗하게 한 대가다. 합성은 굽는 비용밖에 안 드니 **데이터로 그 격차를 메울 수
있는지** 본다. 못 메우면 그 사실이 답이다.

    python D:/tmp/YOLOX/tools/train.py \
        -f D:/Project/sugarScan/assets_dev/train/yolox_synthband_a2_exp.py \
        -d 1 -b 16 --fp16 -expn synthband_P00 \
        -c D:/Project/sugarScan/assets_dev/train/weights/yolox_nano.pth
"""
from yolox_synthband_exp import Exp as BaseSynthbandExp


class Exp(BaseSynthbandExp):
    def __init__(self):
        super().__init__()
        self.data_dir = (r"D:\Project\sugarScan\assets_dev\train"
                         r"\synth_coco\P00_yolox")
        self.exp_name = "synthband_P00"
