# 이 기기(kybir) 훈련 환경 — melotts conda env (2026-11-14 지정)

사람 지시(2026-11-14 밤): "이 기기는 conda 환경이 있다. 참고하자" — 신규 env 생성
대신 기존 env 를 읽기 전용으로 쓴다. torch+cv2+numpy 조합을 갖춘 유일한 env 가
melotts 였다(나머지: base/moss-tts/shorts_generator/supertonic-studio 는 cv2 없음).
**어떤 env 에도 pip/conda 설치를 하지 않는다** — 고정 환경 오염 금지
(`doc/wiki/antipatterns/unpinned-pip-in-frozen-training-env.md`).

## 사양

| 항목 | 값 |
|---|---|
| conda env | `melotts` (`C:\Users\kybir\.conda\envs\melotts`) |
| python | 3.11.15 |
| torch | 2.3.1+cu121 |
| opencv(cv2) | 4.13.0 |
| numpy | 1.26.4 |
| GPU | NVIDIA GeForce RTX 4070 Ti SUPER (드라이버 CUDA 13.3) |
| `torch.cuda.is_available()` | True |

## 호출 규약

- 파이썬을 **직접 부른다**: `C:/Users/kybir/.conda/envs/melotts/python.exe …`
- `conda run -n melotts` 는 여러 줄 `-c` 스크립트를 못 받는다
  (`NotImplementedError: … newlines not implemented` — docs/BAND_HANDOFF.md §1
  와 같은 함정, 재확인 2026-11-14).
- 모든 스크립트는 `assets_dev/train/` 에서 돈다.

## 검증 (2026-11-14)

- `validate_synth_panel.py` 완주(500장). 스키마 결함 1건 수정 — rec 에서 `quad`
  가 빠져 178·209·248행이 죽어 있었다(1a8a405, 2026-09-17 부터). 정답 라벨은
  `box`(축정렬)인 §9.5 규칙 그대로, quad 는 진단 메타데이터로 glass_quad 와 같은
  취급으로 복구.
- `train_band.py --steps 10 --batch 8` GPU 스모크 통과(9초, cuda 자동 선택).

## 알려진 별개 문제 (환경 불가침)

`validate_synth_panel.py` 하드 검사가 현재 main 에서 실패한다 — `sizes` 39/500,
기기고정 요소 드롭(icon:battery 등) 45건. 커밋 스왑 실험(52f2593 의 synth_panel 로
재실행)에서도 sizes 41·드롭 80건으로 **d5518ee(값 분포 전환) 이전부터 실패** —
GEN3(52f2593) 통합 후 검증기를 안 돌린 드리프트다. 원인은 생성기·검증기 불일치이지
환경이 아니므로 합성기 작업(마일스톤 「모자이크 오확정 거절 학습」 카드 2)에서
다룬다.

대조: 옛 훈련 기계(admin)의 `sugartrain` env 는 py3.10 이었다. 이 기기 계보의
학습은 torch 2.3.1+cu121 에서 시작하는 **새 학습 경로**(설계 §2 자체 초기화)이므로
버전 차이는 짝비교 arm 들이 모두 이 env 에서 돈다는 조건으로 중립화된다.
