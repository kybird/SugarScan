# GM 화면 쿼드의 단일 출처 — 사람 라벨 우선, 없으면 검출기 출력.
#
# 2026-09-13 까지 모든 측정이 gmscreen_quads_oriented.jsonl 을 '실측'이라 부르며
# 썼다. 그 파일은 detect_datumo_gm.py 의 **모델 예측**이다(행마다 score 가 붙어
# 있다). 사람이 그린 화면 상자는 screen_boxes.jsonl 에 411행 따로 있었고,
# 측정 경로 어디도 그걸 보지 않았다.
#
# 차이가 작지 않다. 「이름모를 가로형모델」의 화면 종횡비가
#   검출기 n=15 median 0.80  (세로로 보인다)
#   사람  n=16 median 2.15  (가로형이다)
# 로 갈렸고, 그 0.80 이 합성 프로파일에 들어가 가로형 기기를 세로로 그리게
# 했다. OneTouch UltraMini 도 2.12 vs 2.65 로 다르다.
#
# 두 파일은 같은 좌표계다 — 표시(EXIF 적용) 좌표. screen_boxes 의 ow/oh 는
# 표시 크기이고, gmscreen_quads 도 표시 좌표다(convert_quads_oriented.py 머리말,
# G20 로더 통일). screen_boxes 의 upright 는 워프 크롭의 회전 수이지 쿼드의
# 좌표계 표시가 아니다.
#
# 사용:
#   from gm_quads import load_gm_quads
#   quads, stats = load_gm_quads()     # id -> np.ndarray(4,2)
import json
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
HUMAN = HERE / "screen_boxes.jsonl"                  # 사람 라벨(읽기 전용)
DETECTOR = HERE / "gmscreen_quads_oriented.jsonl"    # 검출기 출력(읽기 전용)


def _load_jsonl(p):
    rows = []
    if not p.exists():
        return rows
    with open(p, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def load_gm_quads(prefer_human=True, with_source=False):
    """id -> quad(4x2 float32). 사람 라벨을 먼저 쓰고 없는 장만 검출기로.

    prefer_human=False 면 옛 동작(검출기만) — 기준선 재현용이다.
    with_source=True 면 (quads, source) 를 돌려준다: source[id] in
    {"human", "detector"}.
    반환 두 번째 값은 집계 dict — 보고서에 그대로 적을 수 있게.
    """
    src = {}
    quads = {}
    if prefer_human:
        for r in _load_jsonl(HUMAN):
            if r.get("source") != "human" or "quad" not in r:
                continue          # skipped 행은 라벨이 아니다
            quads[r["id"]] = np.asarray(r["quad"], np.float32)
            src[r["id"]] = "human"
    n_human = len(quads)
    for r in _load_jsonl(DETECTOR):
        if r["id"] in quads:
            continue
        quads[r["id"]] = np.asarray(r["quad"], np.float32)
        src[r["id"]] = "detector"
    stats = dict(total=len(quads), human=n_human,
                 detector=len(quads) - n_human)
    if with_source:
        return quads, src, stats
    return quads, stats


def quad_rows(prefer_human=True):
    """{"id":..., "quad":[[x,y]x4], "source":...} 목록 — 옛 코드가 jsonl 행
    모양을 기대하는 자리에 그대로 끼운다."""
    quads, src, _ = load_gm_quads(prefer_human, with_source=True)
    return [{"id": i, "quad": q.tolist(), "source": src[i]}
            for i, q in quads.items()]


if __name__ == "__main__":
    _, st = load_gm_quads()
    print(f"GM 쿼드 {st['total']}장 — 사람 {st['human']} · 검출기 {st['detector']}")
