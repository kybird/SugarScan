# gmscreen_quads(표시 좌표계)를 라벨러 힌트용으로 그대로 복사한다.
#
# [2026-09-02 정정] 이 스크립트는 원래 raw→표시 회전 변환을 했으나, 원본
# gmscreen_quads.jsonl 은 detect_datumo_gm.py 의 1차 경로 cv2.imread(EXIF 자동
# 적용) 가 만든 것이라 **처음부터 표시(EXIF 적용) 좌표계**였다(워프+육안 실측,
# docs/reports/G20-exif-loader-unification.md). 표시 좌표를 한 번 더 회전하는
# 순간 ori=6(전체의 83.5%) 힌트가 이중 회전으로 어긋났다. 이제는 변환 없이
# 복사만 한다. 원본이 raw 좌표계로 바뀌는 일이 생기면 이 복사도 틀어지므로
# 그런 일은 없어야 한다(loaders 전부 표시 좌표계로 통일됨, G20).
import os
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = HERE / "gmscreen_quads.jsonl"
DST = HERE / "gmscreen_quads_oriented.jsonl"

data = SRC.read_text(encoding="utf-8")
tmp = DST.with_name(DST.name + ".tmp")
tmp.write_text(data, encoding="utf-8")
os.replace(tmp, DST)  # 라벨링 서버가 요청마다 읽는다 — 부분 읽기 방지 원자 교체
print(f"복사 완료: {len(data.splitlines())}행 → {DST.name}")
