#!/bin/sh
# 4번 — 남은 두 실패를 각각 노린다. 설계 근거는 BAND_EXP_PLAN §18.5~§18.8.
#
# 3번 뒤 남은 것(개발 586): 일부만 3.69% · 딴 데 1.90% · 미검출 0.13%.
# 부풀림은 소진됐다(면적비 중앙 1.68, τ=2.0) — --grow 도 --under-w 상향도
# 틀린 방향이라 이번에는 걸지 않는다.
#
# 팔 A  ascene    전체 기기 장면(TD). 노리는 것은 **딴 데**.
#                 기전: 기기 전체를 보여 주면 버튼·로고가 밴드가 아님을 배운다.
# 팔 B  asize512  입력 416 -> 512(TC). 노리는 것은 **일부만의 꼬리**.
#                 기전: /16 단일 특징맵이라 격자가 26x26 -> 32x32 가 된다.
#                 **구조는 안 건드린다**(SPEC §5.3). 입력 크기만 바꾼다.
#                 평가 해상도는 체크포인트 meta["size"] 에서 저절로 따라온다.
#
# 대조군은 둘 다 atone (TC · 416 · --aug --under-w 3.0). 다시 굽지 않는다.
#
# 사전 등록한 판정 (§18.7):
#   주 지표  **Datumo 272**, 배포 상자가 숫자 칸을 담는 비율. Roboflow 는
#            좌우 규약이 우리와 달라(쏠림 +0.247) 부 지표로 내렸다. n=272 로
#            작다는 것을 함께 적는다.
#   부 지표  실패 구성. A 는 딴 데, B 는 일부만. 노린 칸이 아닌 칸이 움직이면
#            기전 설명이 틀린 것이므로 그렇게 적는다.
#   면적     게이트(담음 ∧ 면적<=2)를 함께 낸다. 담음이 올라도 게이트가
#            내려가면 이득이 아니다.
#   퇴행     각 조건의 자기 도메인 — A 는 VD, B 는 VC.
#   주의     0.8~1.9% 구간이다. 유의하지 않게 나올 가능성이 높고, 그 경우
#            "움직이지 않았다"가 아니라 **"이 표본으로는 가를 수 없다"**로 적는다.
set -e
PY=C:/Users/admin/miniconda3/envs/sugartrain/python.exe
H=D:/Project/sugarScan/assets_dev/train
O=$H/band_out/fix4
D=$H/_diag/fix4
ANN=instances_curve_07998.json
mkdir -p "$O" "$D"

echo "=== 1. 장 목록 이식 $(date +%H:%M:%S)"
# TD 는 --axis scene 으로 받는다. 장면 축은 **상자가 움직이는 것이 개입**이라
# 상자 동일성을 불변량으로 쓸 수 없다(§18.8). 대신 파일명 1:1 과 밴드
# 종횡비 보존을 본다. TC 는 3번에서 이미 이식했다.
"$PY" "$H/build_bg_subset.py" --dst "$H/synth_coco/TD" --axis scene 2>&1 | tail -5

echo "=== 2. 학습 $(date +%H:%M:%S)"
for ARM in scene size512; do
  case $ARM in
    scene)   DATA=$H/synth_coco/TD; VAL=$H/synth_coco/VD; SZ=416 ;;
    size512) DATA=$H/synth_coco/TC; VAL=$H/synth_coco/VC; SZ=512 ;;
  esac
  for S in 0 1 2 3 4 5 6 7; do
    N="a${ARM}_s${S}"
    [ -f "$O/$N.pt" ] && { echo "  $N 이미 있음"; continue; }
    echo "=== $N 시작 $(date +%H:%M:%S)"
    "$PY" -u "$H/train_band.py" --data "$DATA" --train-ann "$ANN" \
      --out "$O/$N.pt" --steps 8000 --batch 32 --width 1.0 --size "$SZ" \
      --score-target bce --seed "$S" --aug --under-w 3.0 \
      --save-every 2000 --mid-eval --mid-data "$VAL" > "$O/$N.log" 2>&1
  done
done

echo "=== 3. 평가 $(date +%H:%M:%S)"
# 해상도는 넘기지 않는다 — 세 평가자 모두 체크포인트 meta["size"] 를 기본으로
# 읽는다(eval_band_real.py:340 · eval_band_roboflow.py:71 · eval_band.py:55).
# 여기서 따로 주면 학습과 어긋날 여지만 생긴다.
for ARM in scene size512; do
  case $ARM in
    scene)   VAL=$H/synth_coco/VD ;;
    size512) VAL=$H/synth_coco/VC ;;
  esac
  CK=""
  for S in 0 1 2 3 4 5 6 7; do CK="$CK $O/a${ARM}_s${S}.pt"; done
  echo "--- $ARM Datumo (주 지표) $(date +%H:%M:%S)"
  for C in $CK; do "$PY" "$H/eval_band_real.py" --ckpt "$C" --no-overlay \
      --out-dir "$D" > /dev/null 2>&1; done
  echo "--- $ARM Roboflow (부 지표) $(date +%H:%M:%S)"
  "$PY" "$H/eval_band_roboflow.py" --ckpt $CK --out-dir "$D" 2>&1 | grep -c jsonl
  echo "--- $ARM 자기 도메인 (퇴행) $(date +%H:%M:%S)"
  for S in 0 1 2 3 4 5 6 7; do
    "$PY" "$H/eval_band.py" --ckpt "$O/a${ARM}_s${S}.pt" --data "$VAL" \
      --ann instances_train2017.json --manifest "$VAL/manifest.jsonl" \
      --out "$D/synth_a${ARM}_s${S}.jsonl" > /dev/null 2>&1
  done
done
echo "4번 완료 $(date +%H:%M:%S)"
