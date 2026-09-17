"""합성 밴드 검출기 — gmscreen(화면 검출) 체크포인트에서 클래스를 옮긴다.

마일스톤 「합성만으로 사진에서 값까지 한 번 통과시킨다」의 검출 단계다.
대상이 LCD 화면 전체가 아니라 **혈당 숫자 영역(밴드)** 하나로 바뀐다.
출력은 축정렬 상자다 — YOLOX 가 원래 내는 형식이고, 사람 밴드 라벨 277장도
같은 형식이라 나중에 실촬로 재평가할 수 있다.

학습 데이터는 전부 합성이다(세트 A, synth_panel 시드 20260916). 실촬 0장.
검증 분할도 같은 생성기의 같은 시드에서 잘랐으므로 여기서 나오는 mAP 는
**기록이지 일반화의 증거가 아니다.** 일반화는 이 마일스톤의 목적이 아니다.

기존 exp 들(D:\\tmp\\YOLOX\\gmscreen_ft*.py)과 달리 이 파일은 저장소 안에 둔다 —
런을 재현하려면 exp 가 코드와 함께 남아 있어야 한다. 부르는 법:

    python D:/tmp/YOLOX/tools/train.py \\
        -f D:/Project/sugarScan/assets_dev/train/yolox_synthband_exp.py \\
        -d 1 -b 16 --fp16 \\
        -c D:/Project/sugarScan/assets_dev/train/yolox_out/gmscreen/best_ckpt.pth

해상도 640 은 gmscreen_ft4(G25)가 확정한 값을 그대로 쓴다 — 여기서 다시
스윕하지 않는다. 합성 캔버스는 600~900px 대라 640 이 거의 등배다.
"""
from yolox.exp import Exp as BaseExp


class Exp(BaseExp):
    def __init__(self):
        super().__init__()
        self.num_classes = 1          # glucose_band. gmscreen 도 1 이라 헤드가 맞는다
        self.depth = 0.33             # yolox-nano 계열 — gmscreen 체크포인트와 동형
        self.width = 0.25
        self.data_dir = r"D:\Project\sugarScan\assets_dev\train\synth_coco\A_yolox"
        self.train_ann = "instances_train2017.json"
        self.val_ann = "instances_val2017.json"
        self.input_size = (640, 640)
        self.test_size = (640, 640)
        self.max_epoch = 25
        self.batch_size = 16
        self.data_num_workers = 4
        self.eval_interval = 5
        self.output_dir = r"D:\Project\sugarScan\assets_dev\train\yolox_out"
        self.print_interval = 20
        self.warmup_epochs = 2
        self.basic_lr_per_img = 0.000015625
        self.exp_name = "synthband_v0"
