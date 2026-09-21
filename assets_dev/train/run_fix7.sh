#!/bin/sh
# 7번 — 입력 416 -> 832. 사람 지시(2026-09-20). 근거는 §21.5.
#
# 바꾸는 것은 **입력 크기 하나뿐**이다. 코퍼스도 레시피도 대조군과 같다:
#   TC · --aug --under-w 3.0 · score-target bce · 8000 step · batch 32
# 대조군은 atone(TC, 416). 구조는 안 건드린다 — SPEC §5.3 의 단일 /16 그대로고
# 입력 크기는 구조가 아니다.
#
# 왜 832 인가: 밴드가 /16 특징맵에서 차지하는 세로 칸 수가 문제였다.
#   실촬 Roboflow 개발  416 에서 중앙 3.0칸 · p10 1.9칸
#   416 에서 2.5칸 밑   n=187  통과 90.9%  딴 데 5.3%   <- 절벽
#   416 에서 2.5~3.5칸  n=211  통과 95.6%  딴 데 0.9%
# 832 면 중앙 6.1칸 · p10 3.8칸이 되어 하위 10% 도 절벽을 벗어난다.
# 512 는 이미 재 봤고 못 갈랐다(§19.2) — 3.0 -> 3.7칸이라 절벽 안이다.
#
# 사전 등록한 판정:
#   주 지표  **416 기준 세로 칸 수로 나눈 층별 성적.** 층은 사진의 속성이라
#            팔이 달라도 같은 층이다. 노리는 층은 **2.5칸 미만 187장**이다.
#            그 층이 안 움직였는데 전체가 올랐으면 기전 설명이 틀린 것이고
#            그렇게 적는다.
#   함께     **게이트(담음 ∧ 면적<=2)를 반드시 같이 낸다.** '담음' 단독은
#            상수 상자가 54.3% 를 받는 물렁한 자다(§21.1, Case 5).
#   부 지표  실패 구성(통과/일부만/딴 데/미검출), 붓스트랩 4000회.
#   퇴행     자기 도메인 VC. 같은 코퍼스를 더 큰 입력으로 보는 것이라
#            합성에서 내려가면 그것부터 이상한 일이다.
#   시드     4개. 사진 잡음이 지배적이라 더 안 태운다(§19.1).
#   주의     **나는 오늘 다섯 번 '이러면 될 것 같다'고 하고 다섯 번 틀렸다.**
#            안 갈리면 "효과 없음"이 아니라 "이 표본으로는 못 가른다"로 적는다.
#
# 대가(판정과 별개로 적는다): 832 는 연산이 416 의 4배다. 단말 추론 비용이라
# 성적이 올라도 **채택은 제품 결정**이다. 내가 정하지 않는다.
set -e
PY=C:/Users/admin/miniconda3/envs/sugartrain/python.exe
H=D:/Project/sugarScan/assets_dev/train
O=$H/band_out/fix7
D=$H/_diag/fix7
ANN=instances_curve_07998.json
mkdir -p "$O" "$D"

echo "=== 학습 $(date +%H:%M:%S)"
for S in 0 1 2 3; do
  N="abig_s${S}"
  [ -f "$O/$N.pt" ] && { echo "  $N 이미 있음"; continue; }
  echo "=== $N 시작 $(date +%H:%M:%S)"
  "$PY" -u "$H/train_band.py" --data "$H/synth_coco/TC" --train-ann "$ANN" \
    --out "$O/$N.pt" --steps 8000 --batch 32 --width 1.0 --size 832 \
    --score-target bce --seed "$S" --aug --under-w 3.0 \
    --save-every 2000 --mid-eval --mid-data "$H/synth_coco/VC" \
    > "$O/$N.log" 2>&1
done

echo "=== 평가 $(date +%H:%M:%S)"
# 해상도는 안 넘긴다 — 세 평가자 모두 체크포인트 meta["size"] 를 기본으로 읽는다.
CK=""
for S in 0 1 2 3; do CK="$CK $O/abig_s${S}.pt"; done
"$PY" "$H/eval_band_roboflow.py" --ckpt $CK --out-dir "$D" 2>&1 | grep -c jsonl
for C in $CK; do "$PY" "$H/eval_band_real.py" --ckpt "$C" --no-overlay \
    --out-dir "$D" > /dev/null 2>&1; done
for S in 0 1 2 3; do
  "$PY" "$H/eval_band.py" --ckpt "$O/abig_s${S}.pt" --data "$H/synth_coco/VC" \
    --ann instances_train2017.json --manifest "$H/synth_coco/VC/manifest.jsonl" \
    --out "$D/synth_abig_s${S}.jsonl" > /dev/null 2>&1
done
echo "7번 완료 $(date +%H:%M:%S)"
