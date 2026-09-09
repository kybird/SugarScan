# G28 — CTC 리더 tflite 내보내기·파리티 대조

- 브랜치: `glm/G28-tflite-parity`
- 커밋: `<이 보고서와 함께 커밋>`
- 상태: **중단 — 지시서가 예고한 유효한 결론.** 변환에 `SELECT_TF_OPS`(Flex)가
  필요하다고 변환기 스스로 통보했다. 지시서 *"고쳐서 통과시키지 말 것"* 에 따라
  그 지점에서 멈췄다. 파리티 측정은 tflite 가 없어 불가능했다.

## 요약

`reader_model`(BiLSTM 포함) 은 `TFLITE_BUILTINS` 만으로는 tflite 로 변환되지
않는다. BiLSTM 이 while-loop + `tf.TensorListReserve` 로 내려가는데, 이 연산의
legalize 가 실패하고 변환기의 권고 해법이 `SELECT_TF_OPS` 다. Flex 를 켜면
안드로이드 바이너리에 TF 런타임이 통째로 실려 앱이 수십 MB 늘어난다 — 지시서가
명시한 대로 **그 결정은 사람 몫**이다.

## 무엇을 했나

| 파일 | 상태 |
|---|---|
| `assets_dev/train/export_reader_tflite.py` | 작성·실행 — 변환 실패를 재현, 원문 에러 출력 |
| `assets_dev/train/diag_tflite_parity.py` | 작성 — tflite 부재로 본 실행 불가, 케라스 절반만 검증(아래) |
| `assets_dev/train/reader_fp16.tflite` | **생성 못 함** |
| `assets_dev/train/_diag/G28-parity.json` | **생성 못 함** — 파리티를 잴 대상이 없다 |

- 변환 설정: `optimizations=[DEFAULT]`, `supported_types=[float16]`,
  `supported_ops=[TFLITE_BUILTINS]` **만**. `SELECT_TF_OPS` 는 넣지 않았다.
- 파리티 스크립트는 hold-out 정의(캐시 `real_train_ids` 1,372장 제외 → 파일
  존재 1,122장), TTA off, 전처리 1회·양 경로 공유, `_decode`·`BOX_MARGIN`·
  EXIF(`exif_transpose`) 전부 `eval_reader.py` 재사용으로 구성했다. tflite 가
  생기면 수정 없이 바로 돌린다.

## 왜 그렇게 했나

- 변환 실패 시 **원문을 한 글자도 손대지 않고** 보고서에 남겼다(아래). 판정의
  정본이 에러 문구 자체라서다.
- 멈춘 뒤에도 파리티 스크립트를 커밋한 이유: 산출물 목록에 있고, 어느 결정
  (Flex 수용 또는 아키텍처 교체)이 나든 즉시 재사용돼야 하는 측정 도구라서.
  실행되지 않은 코드를 검증된 척 두지 않기 위해 아래 "검증" 에 무엇을 확인했고
  무엇을 못 했는지 적는다.

## 막힌 것 — 변환기 원문

TensorFlow 2.10.1, `TFLITE_BUILTINS` 만 허용한 변환 결과(exit 1). 전체 로그는
`assets_dev/train/_diag/g28_export.log`(비커밋, gitignore).

```
ConverterError('C:\\Users\\admin\\miniconda3\\envs\\sugartrain\\lib\\site-packages\\tensorflow\\python\\saved_model\\save.py:1268:0: error: \'tf.TensorListReserve\' op requires element_shape to be static during TF Lite transformation pass\n<unknown>:0: note: loc(fused["StatefulPartitionedCall:", "StatefulPartitionedCall"]): called from\nC:\\Users\\admin\\miniconda3\\envs\\sugartrain\\lib\\site-packages\\tensorflow\\python\\saved_model\\save.py:1268:0: error: failed to legalize operation \'tf.TensorListReserve\' that was explicitly marked illegal\n<unknown>:0: note: loc(fused["StatefulPartitionedCall:", "StatefulPartitionedCall"]): called from\n<unknown>:0: error: Lowering tensor list ops is failed. Please consider using Select TF ops and disabling `_experimental_lower_tensor_list_ops` flag in the TFLite converter object. For example, converter.target_spec.supported_ops = [tf.lite.OpsSet.TFLITE_BUILTINS, tf.lite.OpsSet.SELECT_TF_OPS]\\n converter._experimental_lower_tensor_list_ops = False\\n')
```

막힌 연산은 `tf.TensorListReserve` — 모델의 `Bidirectional(LSTM)` 이 while-loop
+ TensorList 로 그래프화된 것(`export_reader_tflite.py` 실행 시 출력한 모델
요약: Conv2D×3 → Permute → Reshape → Dense → **bidirectional** → logits).
변환기의 권고 해법이 `SELECT_TF_OPS` 추가인데, 그건 지시서가 금지한 방향이라
적용하지 않았다.

**시도하지 않은 우회로** (전부 "통과시키려고 고치는" 것이라 금지 범위):
- `supported_ops` 에 `SELECT_TF_OPS` 추가, `_experimental_lower_tensor_list_ops = False`
- 배치를 고정한 concrete function 진입으로 TensorList element_shape 를 정적으로 만들기
- BiLSTM 을 unidirectional 두 개로 분해해 그래프를 고쳐 변환하기

## 판정

지시서의 셋(완전일치 100% 통과 / 99.0% 이상 조건부 / 99.0% 미만 실패) 중
**어디에도 해당하지 않는다** — 측정 자체가 변환 단계에서 막혀 도달하지 못했다.
지시서의 넷째 분기 *"SELECT_TF_OPS 가 필요하다고 나오면 거기서 멈추고 보고"* 가
이 작업의 결론이다.

다음 결정(사람 몫):
1. **Flex 수용** — 변환은 되겠으나 안드로이드 앱 크기 수십 MB 증가.
2. **아키텍처 교체 후 재학습** — TensorList 로 내려가지 않는 구조로 바꾼다.
   재학습은 G28 범위 밖.

## 검증

```
conda run -n sugartrain python assets_dev/train/export_reader_tflite.py
  → exit 1, 위 원문 (tflite 미생성)

conda run -n sugartrain python assets_dev/train/diag_tflite_parity.py
  → "[불가] reader_fp16.tflite 이 없다 — 변환이 SELECT_TF_OPS 를 요구해 막혔다…"
    (임포트 사슬 eval_reader→build_cache_v2 포함 정상 기동 확인)

케라스 절반 표본 검증 (diag_tflite_parity 의 _crop_rect·_load_gray·_decode 재사용):
  glucose_batch1/1:    pred='87' gt=87  logits_shape=(40, 11)
  glucose_batch1/1002: pred='92' gt=92  logits_shape=(40, 11)
  glucose_batch1/1004: pred='93' gt=93  logits_shape=(40, 11)
  → hold-out 3장 전부 정상 판독. 크롭 기하·EXIF·디코딩 재사용이 옳게 붙었다.

flutter analyze  → No issues found!
flutter test     → All tests passed! (387 tests)
```

tflite 경로(반쪽)는 한 번도 실행되지 않았다 — 위 검증은 케라스 경로와
스크립트 기동만 확인한 것이다.

## 건드리지 않고 남긴 것

- `lib/` 아래 0줄 (`flutter analyze`·`flutter test` 로 무변경 확인).
- `reader_model/`, `data_cache_v2.npz`, `gmscreen_quads.jsonl`,
  `band_boxes.jsonl`, `screen_boxes.jsonl` — 읽기만 했다.
- `eval_reader.py`·기존 `diag_*.py` — 한 줄도 고치지 않았다.
- `build_cache_v2.BOX_MARGIN`(0.10×4) — import 로만 가져다 썼다.
- 모델 재학습 없음.
- 기존에 워킹트리에 있던 `AGENTS.md` 변경분(내 작업 아님) — 커밋에서 제외했다.
