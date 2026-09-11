# 기기 단절 분할 캐시 — train 1,356 / holdout 1,138(45.6%), 홀드아웃 24종

2026-09-11 · 칸반 카드 「기기 단절 분할 캐시를 만든다」.
전제: [`grouped-split-rebaseline-2026-09-10.md`](grouped-split-rebaseline-2026-09-10.md) —
세션 무절 재분할과 같은 절차를 **기기 단위**로 반복한다. 현재 기준선은 그
보고서의 96.67% / 위험 1.51% 다.

## 방법

1. **입력**: `assets_dev/train/device_labels.jsonl` — 사람이 사진 2,494장에 한 장씩
   붙인 기기 라벨(54종, 전부 status=identified). 읽기 전용.
   - 기기 정체성 = **brand+model+variant** 세 필드 결합. `print`(인쇄 언어)·
     `rotation`(숫자 방향)은 정체성에서 제외(카드 Notes).
   - 풀 대응: 캐시 실사진 2,494장 = 라벨 2,494장. 라벨 없는 캐시 사진 0장,
     캐시 밖 라벨 0장 — 완전 일치.
2. **재배열(재계산 아님)**: `build_device_split.py` — 워프된 실사진 배열과
   합성(synth_*) 배열은 기존 `data_cache_v2.npz` 에서 그대로 복사하고,
   real_train/real_holdout 소속만 기기 단위로 다시 정한다. 이미지 재디코딩·
   재워프 없음(`antipatterns/duplicated-geometry-implementation` 회피).
3. **결정적 선택**: 기기명 정렬 + 고정 시드 `RandomState(20260911)` 순열로
   기기를 하나씩 홀드아웃에 통째로 담아 목표 45%까지 충족. 담을 때 55% 상한을
   깨는 기기는 건너뛴다(대형 기기 독점 방지).
4. **저장 전 검증(assert)**: ① 교차 기기 0 ② 홀드아웃 비율 35~55% ③ 단일 기기
   홀드아웃 비중 ≤25%. 실패 시 캐시를 남기지 않고 종료.

## 결과

- **재분할**: train 1,356 / holdout 1,138(**45.6%**, 실사진 2,494장 기준).
- **교차 기기 0 검증 통과** — 54종 중 홀드아웃 24종 / train 30종.
- **단일 기기 최대 비중 21.1%**(CareSens N 240장) — 가드 25% 이내.
- **값 균형**(build_grouped_split 과 같은 항목):
  - train: 값 30~508, 평균 133, 2자리 283장
  - holdout: 값 52~511, 평균 134, 2자리 229장
- **결정성 검증**: 시드·정렬이 고정이라 두 번 실행해 id 목록·전 배열 완전
  일치 확인(임시 출력 비교 후 삭제).

홀드아웃에 들어간 기기 24종(전체 목록·장수는
`assets_dev/train/_diag/device_split/holdout_devices.json`):
CareSens N(240) · 오토-첵(156) · Gmate(89) · HANDOK BAROZEN(80) ·
ACCU-CHEK Performa 은색 각진버튼(79) · SD CodeFree(60) · CareSens Dual(59) ·
ACCU-CHEK Performa Nano 파랑 케이스(59) · GC 녹십자 MS Green Doctor(55) ·
GC 녹십자 MS ONE(52) · ACURA PLUS(40) · ACCU-CHEK Instant(34) · MaeilzeN(30) ·
OneTouch Ultra(30) · CareSens N Premier(29) · gDoctor(14) · Dr.Diary+(10) ·
FORA(6) · ACURA VIEW(4) · Boryung CareTouch 일반LCD(3) · ACCU-CHEK Active
원형베젤(3) · 도루코S Premium(3) · Contour TS(2) · VERI-Q(1).

## 산출물

- `assets_dev/train_device/data_cache_v2.npz` — 기존 캐시와 같은 키 구성
  (gitignored, 스크립트로 재생성 가능).
- `assets_dev/train/_diag/device_split/holdout_devices.json` — 홀드아웃·train
  기기 목록과 장수, 시드, 비율(AC2 — 이 파일만 보면 54종 중 무엇을 뺐는지 안다).
- `assets_dev/train/build_device_split.py` — 빌더.

## 재현

```bash
cd assets_dev/train
C:/Users/admin/miniconda3/envs/sugartrain/python.exe build_device_split.py
# 결정성 확인(임시 출력과 id·배열 비교):
#   build_device_split.py --out <다른경로>.npz --meta-out <다른경로>.json
```

## 한계

- 기기 단위 분할이라 장면(세션)과 직교하지 않는다 — 같은 기기의 사진은
  장면 성분과 강하게 겹친다. 즉 이 분할은 세션 무결 분할보다 **엄격한 상위집합**
  조건이다(기기가 갈리면 그 기기의 장면도 함께 갈린다).
- 홀드아웃 24종이 코퍼스 기기 다양성의 절반도 안 되는 값 분포를 대표한다는
  보장은 없다 — 카드 2의 측정은 "이 24종의 미학습 성적"이지 "임의 미학습
  기기의 기대치"가 아니다.
