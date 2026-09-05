# G25 — GM 검출기 입력 해상도 416 → 640

- 브랜치: `glm/G25-gm-input-640`
- 커밋: `<이 보고서와 함께 커밋>`
- 상태: 완료 — **결론은 부정. 640 은 세 지표 전부에서 416 보다 나쁘다.**

## 요약

ft4(640 입력)는 ft2·ft3(416) 에 비해 **전량 검출 2,494/2,497 → 2,472, 평가
holdout 판독 42/49·43/49 → 31/49, 가로 LCD GM 실패 16 → 18**. 세 지표가 전부
같은 방향을 가리킨다. **입력 해상도 가설은 이 값으로 기각이다** — "구조 한계로
닫고 이 방향을 더는 파지 않는다"가 이 작업의 결론.

## 핵심 수치

| 지표 | ft2 (416, 운영) | ft3 (416) | **ft4 (640)** |
|---|---|---|---|
| 평가 holdout 49장 판독 완전일치 | 42/49 (85.7%) | 43/49 (87.8%) | **31/49 (63.3%)** |
| └ 검출 실패(박스 없음) | 1 | 1 | **6** |
| └ 계층별 | wide 8/10 · lowconf 34/38 | wide 8/10 · lowconf 34/38 | wide **5/10** · lowconf **26/38** |
| 전량 검출 수 (/2,512) | 2,494 | 2,497 | **2,472** |
| 가로 LCD GM 실패 (회전 2장 제외 49장) | 16 | 16 | **18** (미검출 7 + 접힘 11) |
| val AP (IoU .50:.95, 각자 test_size) | — | best 70.87 | best 69.71 |

ft4 의 holdout 실패 18건 중 6건이 **검출 자체를 못 한 것**(97·1494·103·111 외
2)이다. 박스는 내지만 판독이 틀린 것도 12건 — 416 대비 박스 품질이 나빠졌다는
방향의 증거가 양쪽(누락+왜곡)에서 나왔다.

## 무엇을 했나

- `D:\tmp\YOLOX\gmscreen_ft4_exp.py` 신규 — `gmscreen_ft3_exp.py` 복사 후
  **세 줄만** 변경: `input_size/test_size (640,640)` · `exp_name "gmscreen_ft4"`.
  (저장소 밖 파일 — ft2·ft3 exp 파일과 같은 관례. 전문은 이 보고서 말미)
- `assets_dev/train/detect_datumo_gm.py` — `--imgsz` 인자 추가(기본 416).
  **74행 resize 와 82행 스케일 역산 두 곳이 같은 `imgsz` 변수를 쓴다.**
- `assets_dev/train/diag_wide_gm.py` 신규 — 가로 LCD GM 성적 집계 보조.
- 학습: `tools/train.py -f gmscreen_ft4_exp.py -d 1 -b 8 --fp16 -c
  yolox_out/gmscreen/best_ckpt.pth -o` (ft3 과 같은 베이스 체크포인트).
  **배치 16 → 8** — 지시서 명시대로. 640² 은 416² 의 2.37배 픽셀이라 8GB GPU
  에서 같은 배치를 유지할 수 없다. 에폭(25)·lr·warmup 은 ft3 과 동일.
  학습 소요 약 39분 (00:39~01:18).
- 추론: `detect_datumo_gm.py --ckpt yolox_out/gmscreen_ft4/best_ckpt.pth
  --imgsz 640 --out gmscreen_quads_ft4.jsonl` (운영 파일 아닌 새 파일).

## 왜 그렇게 했나

- **배치 8 은 지시서 명시 값**이다. 검출 비교의 공정성 우려는 남지만(배치가
  절반으로 줄면 업데이트 노이즈가 커진다) 지시서가 이 조합을 지정했고, 임의로
  다른 값을 시도하지 않았다.
- 가로 평가 기준: 미검출 + 검출 w/h<1.1 (회전 2장 1564·1565 제외, 분모 49).
  이 기준으로 ft3 실패 **16건**이 문서(2026-09-04 Case 9, DONE.md)와 정확히
  일치한다. 문서의 "45장" 명단은 어디에도 기록돼 있지 않아 재현 불가능하고,
  분자(16)를 맞추는 재현 가능한 기준을 잠가 세 채본(ft2·ft3·ft4)에 동일
  적용했다. ft2 도 같은 16이므로 ft2↔ft3 비교는 문서와 일치한다.
- ft4 접힘 박스 11개의 score 는 0.62~0.89 로 제법 높다 — 낮은 conf 문제가
  아니라 **640 에서 오히려 화면을 세로로 접는 학습**을 했다는 뜻으로 읽힌다.

## 검증

- **416 기본값 회귀 검사**: 수정된 `detect_datumo_gm.py` 를 ft2 체크포인트·
  기본 인자로 재실행 → `_diag/gm416_recheck.jsonl` 가 운영
  `gmscreen_quads.jsonl` 과 **바이트 단위로 동일** (`diff` 0행).
  인자 추가가 기존 동작을 바꾸지 않는다는 직접 증거다.
- `eval_lcd_fix.py` 세 채본 재실행 — ft2 42/49 · ft3 43/49 로 지시서 기준값
  재현 후 ft4 평가.
- `diag_wide_gm.py --fold 1.1` 세 채본 동일 기준.
- `flutter analyze`·`flutter test` — 대상 아님. `lib/` 변경 0줄.

## 건드리지 않고 남긴 것

- 운영 파일 전부 무변경: `gmscreen_quads.jsonl` · `gmscreen_quads_oriented.jsonl`
  · `gmscreen_quads_ft3.jsonl` · `reader_model` · `data_cache_v2.npz` ·
  `checkpoints_v2`. 리더(CTC)·캐시는 건드리지 않았다.
- `gmscreen_quads_ft4.jsonl`(신규)·`yolox_out/gmscreen_ft4/`(신규)·
  `ft4_train.log{,.err}`·`_diag/gm416_recheck.jsonl` — 산출물로 남김(비추적).
- ft4 val AP 가 ft3 보다 낮은 원인 분석(배치 절반의 영향 vs 해상도 자체)은
  범위 밖으로 남긴다 — 어느 쪽이든 "이 설정으로는 안 된다"는 결론이 같다.

## 막힌 것

없음.

## 부록 — gmscreen_ft4_exp.py 전문

```python
from yolox.exp import Exp as BaseExp


class Exp(BaseExp):
    """gmscreen 파인튜닝 4차 — 입력 해상도 416 → 640 (G25)."""

    def __init__(self):
        super().__init__()
        self.num_classes = 1
        self.depth = 0.33
        self.width = 0.25
        self.data_dir = r"D:\Project\sugarScan\assets_dev\train\gmscreen_ft"
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
        self.exp_name = "gmscreen_ft4"
```
