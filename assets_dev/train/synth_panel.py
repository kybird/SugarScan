# 물리 패널 합성 렌더러 2판 — 「합성을 물리 패널 기준으로 재구성」 (2026-09-12).
#
# 1판(synth_panel.py, 참고본 _diag/panel_rebuild/attempt1_synth_panel.py)은 구조는
# 맞았지만 렌더가 못 쓰는 수준이었다. 결함 아홉의 원인과 이 판의 대응:
#   (1)(2) 글리프가 개별적으로 뒤틀려 첫 자리가 덩어리가 됨
#        -> 글리프는 패널 평면 위에 '균일 x-압축' 하나로만 세우고, 키스톤·회전은
#           조판이 끝난 이미지 전체에 한 번만 걸게 재설계했다(일관 변형).
#           워프 전 글리프 마스크에 같은 변환을 적용해 워프 후 잉크와 대조하는
#           자가검사(glyph_plane_check)를 렌더마다 돌리고 manifest 에 남긴다.
#   (3) 배터리 아이콘이 시간줄에 붙음 -> Placer 가 아이콘·도트줄 사각형까지 검사
#   (4) AVG 7 DAY 가 속 빈 글자 -> 인쇄 글자는 굵기 h/9 이상의 채움 획
#   (5) mg/dL 이 패널 안에서 잘림 -> 실제 폭을 재서 패널 안에 완전히 들어오는
#           자리 후보만 쓰고, 다 빠지면 요소를 뺀다(잘라서라도 그리지 않는다)
#   (6) 패널이 정사각형 -> 종횡비를 실측 히스토그램(2,497장)에서 뽑는다
#   (7) 글레어가 대각선 흰 줄 하나 -> 가장자리에 붙은 연한 타원 반사패치로 바꾸고
#           전폭 강선은 폐지
#   (8) 극성 반전 58%(실물 21~27%) -> 극성은 프로파일 속성이다. 2026-09-13
#           재개정: 재는 것이 아니라 사람이 선언한다(synth_profiles.
#           PROFILE_INVERTED). 자로 되찾으려던 시도는 사람 정답 30장 채점에서
#           최선이 26/30 이었고 오차가 하필 프로파일 기기에 몰렸다
#   (9) 브랜드명을 액정 안에 그림 -> 베젤 인쇄는 패널 바깥 링에만 그린다.
#           액정 문자열은 화이트리스트 토큰으로 assert 고정한다
#
# 렌더 규약(AC#7) — 한 렌더에서 출력 3종:
#   1. 패널 이미지 — 긴 변 896px, 최종 캔버스 w/h 는 GM 박스 실측 분포
#   2. 밴드 쿼드 — 최종 캔버스 픽셀 좌표계 4점(TL,TR,BR,BL). 정의: 사람 라벨과
#      같게 슬롯 필드 전체(slots 칸, 빈 앞칸 포함). n=264 재측정에서 2자리
#      밴드 폭은 3자리와 사실상 같다(세로형 0.866 vs 0.891, 2자리의 84% 가
#      0.75 이상, n=32/185, 2026-09-12) — 구판의 '보이는 숫자줄만(2자리
#      0.571)' 은 84장 편향 표본 값이라 폐기.
#      쿼드는 이미지와 같은 행렬·같은 순서를 통과한 뒤의 좌표다.
#   3. 값 라벨 — 숫자만. isdigit() assert.
#
# 실측 근거의 정본은 real_baseline.json 이다 — make_real_baseline.py 가 라벨
# 파일(band_boxes 277행·54종, 2026-09-12 재측정)에서 생성한다. 이 파일 머리말에
# 수치를 베끼지 않는다: 세 소비처(이 파일·validate_synth_panel·GLM_TASKS 3.8)가
# 각자 값을 들면 기준선이 다시 갈라진다(2026-09-12 밀도 사고, 카드 「밴드 라벨
# 확장 뒤 합성 밀도·기하 기준선을 재고정한다」). BAND_GEOM 과
# GENERIC_INVERTED_P 는 정본에서 읽는다. PANEL_ATTRS 는 더 이상 정본에서
# 파생하지 않는다 — 사람 선언이다(2026-09-13, PROFILE_INVERTED).
# 칸 폭(피치) 근거는 밴드 라벨이 아니라 육안+DSEG 측정이라 그대로 둔다:
#   칸 폭    실사진 밴드 크롭 육안 + DSEG 측정: 칸 피치 ≈ 0.50~0.60·높이,
#            글리프 폭 ≈ 피치의 0.78~0.84, DSEG7 '8' 자연 폭 0.615·높이,
#            '1' 0.065~0.18·높이(균일 압축으로 상대 폭 보존)
import argparse
import json
import random
import sys
from pathlib import Path

import cv2
import zlib
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from synth_profiles import (  # noqa: E402
    PROFILES, DOT_FMTS, dot_text, _icon, _pick_variant, _glyph_mask,
    device_identity, STATEFUL_ELEMENTS, PROFILE_INVERTED, lay_val,
)
from synth_lcd import (add_local_shadow,  # noqa: E402
                       seg_text, seg_text_width, seg_weight_from_variant,
                       SEG_WEIGHTS, SEG_SLANT)
from measure_panel_stats import edge_density_outside  # 같은 자(AC#4)  # noqa: E402
# 리더 프레이밍의 정본 — 실사진 팔과 같은 자를 쓴다(tensorflow 를 끌고 오는
# eval_reader 가 아니라 build_cache_v2 에서 가져온다, 2026-09-13).
from build_cache_v2 import framed_src_rect, IN_H, IN_W  # noqa: E402

LONG_SIDE = 896

# 실사진 기준선 정본 — make_real_baseline.py 가 라벨 파일에서 생성한다
# (band_boxes 277행·join 264, 2026-09-12 재측정). 이 파일이 갖가지 분포의
# 단일 출처다: 밀도 목표(REAL_DENSITY), 밴드 기하(BAND_GEOM), 극성(PANEL_ATTRS).
# 값은 정본에서 읽지 않고 이 파일에 베끼면 라벨이 늘 때마다 서로 어긋난다.
with open(HERE / "real_baseline.json", encoding="utf-8") as _f:
    REAL_BASELINE = json.load(_f)

# GM 박스 w/h 실측 히스토그램(2,497장, measure_panel_stats.py aspect 원문).
# 가로형(w/h>=1.3) 구간만 x2 부스트 — 실측 1.44% -> 합성 2.8%, 매우 가로 1.5%
# (실측 0.8%). AC#6 "조금 높게, 소수로". 별도 모델로 나누지 않는다(카드 Notes).
ASPECT_BINS = [
    ((0.5, 0.6), 2), ((0.6, 0.7), 221), ((0.7, 0.8), 1124), ((0.8, 0.9), 645),
    ((0.9, 1.0), 298), ((1.0, 1.1), 109), ((1.1, 1.2), 52), ((1.2, 1.3), 10),
    ((1.3, 1.4), 4 * 2), ((1.4, 1.5), 2 * 2), ((1.5, 1.6), 2 * 2),
    ((1.6, 1.7), 1 * 2), ((1.7, 1.8), 2 * 2), ((1.8, 1.9), 1 * 2),
    ((1.9, 2.0), 5 * 2), ((2.0, 2.1), 2 * 2), ((2.1, 2.2), 8 * 2),
    ((2.3, 2.4), 3 * 2), ((2.4, 2.5), 4 * 2), ((2.6, 2.7), 1 * 2),
    ((2.8, 2.9), 1 * 2),
]
# 가로형은 학습에서 제외한다(사람 지시 2026-09-13). 회전 보정 경로가 없고
# (band_rotation.jsonl 의 사람 노트와 같은 사유), 가로형 프로파일을 넣어도
# 검출기 성적이 안 움직였다(v2: UltraMini 0.554 — 구판 0.548·0.591 과 동급).
# 익명 풀의 종횡비 히스토그램도 세로 구간만 남긴다.
# 2026-09-13: 가로형을 다시 넣는다. 뺐던 이유는 '가로형 프로파일을 넣어도
# 검출기가 안 움직였다'였는데, 그때 프로파일의 종횡비가 검출기 예측 쿼드에서
# 나온 값이라 가로형 기기를 세로로 그리고 있었다(ar 0.797). 사람 라벨로
# 바로잡아 2.103 이 됐으니 이제서야 제대로 된 가로형을 만들 수 있다.
EXCLUDE_WIDE = False

_AB = [(b, n) for b, n in ASPECT_BINS if not (EXCLUDE_WIDE and b[1] > 1.0)]
_BINS = [b for b, _ in _AB]
_WEIGHTS = np.asarray([n for _, n in _AB], np.float64)

# 밴드 기하 — 정본 real_baseline.json 의 p10~p90(n=264 재측정: 세로 217·가로 47,
# make_real_baseline.py). 값은 정본에서 읽는다 — 여기 베끼면 기준선이 다시 갈라진다.
# 가로형 h p10 0.430(구판 0.690)·cx p10 0.082(구판 0.15): 84장 편향 표본엔
# 정보칼럼이 왼쪽 붙은 가로형이 없었다.
_RB_BAND = REAL_BASELINE["band"]
BAND_GEOM = {
    key: dict(h=(v["h_p10"], v["h_p90"]), cx=(v["cx_p10"], v["cx_p90"]),
              cy=(v["cy_p10"], v["cy_p90"]))
    for key, v in _RB_BAND.items() if key in ("portrait", "wide")
}
# 칸 피치 / 글리프 높이 — 실사진 밴드 크롭 육안 0.50~0.60. 1차가 band_h 를
# 맞추려 상한을 0.56 으로 좁혔으나(2026-09-12 리뷰 지적 6) 실측 근거는 0.60 이고
# band_h 자체는 이 상한과 무관하게 맞았다(합성 0.445~0.446 vs 실사진 0.447,
# synth-band n=300). 원래 근거 범위로 복원한다. 폭 제약(max_w)이 걸리는 패널의
# 높이 깎임은 클램프가 이미 흡수한다.
PITCH_RATIO = (0.50, 0.60)
GLYPH_IN_CELL = (0.78, 0.84)  # 글리프 폭 / 피치 — 같은 육안 근거

# 밀도 목표 — 정본 density.values(n=264, frame_exc 0). 렌더마다 여기서
# 재표본한다. 자는 measure_panel_stats.edge_density_outside 와 동일하다(AC#4).
REAL_DENSITY = REAL_BASELINE["density"]["values"]

# 글리프 평면 자가검사의 잉크 문턱 — 밴드 대비(p95-p5)에 비례한다(카드
# 「글리프 평면 자가검사의 잉크 문턱을 대비에 비례시킨다」, 2026-09-13).
# 구판의 고정 30 은 저대비 패널(대비 열화 카드가 의도적으로 분포를 아래로
# 넓혔다)에서 잉크를 못 넘겨 gpc 가 대비와 단조로 얽혔다 — 검사가 '평면이
# 어긋났다'와 '패널이 흐리다'를 구별하지 못했다(리뷰 2026-09-13 지적 A).
# 계수·바닥의 근거와 스윕은 diag_gpc_threshold.py 와 docs/reports/
# glyph-check-threshold.md.
GPC_INK_K = 0.25       # 문턱 = 밴드 대비 × K
GPC_INK_FLOOR = 12     # 바닥 — 광학 노이즈 σ≤9(렌더 광학 단) 위로

# ── 액정 화이트리스트(AC#14·#15) ─────────────────────────────────────────────
# 액정 안에 그릴 수 있는 알파벳 토큰 전부다. 각 근거는 실사진 id(아틀라스 요소
# 재고표 2026-09-11 + 프로파일 evidence). 이 토큰 밖의 알파벳을 액정에 그리면
# _lcd_text 가 assert 로 죽는다 — GLUCOSEDATE 같은 지어낸 문자열 차단.
LCD_TOKENS = {
    "GLU",                    # 1781, 2498 (green_doctor glulabel)
    "M", "mem", "memory",     # 727, 2498, 1186
    "AC", "PC",               # 식전후 마커 — 관찰 0건, AC#14 목록 요구로 소수 렌더
    "DAY", "AVG",             # 231, 2443, 1911 (+요일수 7·14)
    "OK", "CHECK", "STRIP",   # 120, 694, 695 (도루코 도트줄)
    "am", "pm", "AM", "PM",   # 497
}

# 같은 라벨 부류의 표기 변형. 기기는 이 중 하나만 쓴다.
_MEM_VARIANTS = {"M", "mem", "memory"}
LCD_UNITS = ["mg/dL", "mg /dL", "mg/dl"]   # 843(gmate), 1991, 1058, 1903, #33 99
LCD_ICONS = ["battery", "bluetooth", "curved-right", "curved-left",
             "tri-right", "tri-down", "triangle", "blood-drop", "mem-flag",
             "smile"]
# 베젤 인쇄(액정 밖 링 전용). 문자열의 정본은 프로파일의 bezel.texts 다 —
# 여기서 따로 들고 있다가 2026-09-13 에 실제로 갈라졌다(performa_silver 에서
# Performa Nano 를 떼어 별도 프로파일로 세웠는데 이 표에는 그대로 남아, 은색
# Performa 몸체에 'Performa Nano' 가 찍혔다). 파생으로 바꾼다.
BEZEL_TEXTS = {p["id"]: list(p["bezel"]["texts"])
               for p in PROFILES if p.get("bezel")}
_BEZEL_FONTS = [cv2.FONT_HERSHEY_SIMPLEX, cv2.FONT_HERSHEY_TRIPLEX,
                cv2.FONT_HERSHEY_COMPLEX]

# 프로파일별 극성 — synth_profiles.PROFILE_INVERTED(사람 선언)를 그대로 쓴다.
# 2026-09-13 이전에는 real_baseline.polarity.by_device 에서 파생했는데, 그
# 값을 내는 자가 프로파일 기기 셋을 틀리게 찍었다(Green Doctor·ACURA PLUS·
# Gmate — 사진은 전부 정상). 극성은 기기의 성질이라 재는 대상이 아니라
# 라벨이다. 근거 사진 id 는 PROFILE_INVERTED 옆에 있다.
PANEL_ATTRS = {pid: dict(inverted=inv)
               for pid, inv in PROFILE_INVERTED.items()}

# 학습 코퍼스가 쓰는 프로파일 — 가로형(칼럼/행 가족)은 뺀다. 프로파일 정의는
# 지우지 않는다: 기기 지식이고, 가로형을 다시 넣을 때 근거가 거기 있다.
TRAIN_PROFILES = [p for p in PROFILES
                  if not (EXCLUDE_WIDE and p.get("family") in ("column", "row"))]
# 프로파일 추첨 가중치 — 기본은 균등(None). set_wide_share() 로 가로형 비중을
# 올린다. 가로형 판정은 선언(family)이지 측정한 종횡비가 아니다: gluneo_plus 는
# 유리 종횡비가 1.18 로 1 을 넘지만 사람이 세로형이라고 선언했다(2026-09-13).
_PROFILE_WEIGHTS = None
WIDE_FAMILIES = ("column", "row")


def set_wide_share(share):
    """가로형(family=column/row) 프로파일의 합계 추첨 비중을 share 로 맞춘다.

    share=None 이면 균등(=선언된 가로형 2종 / 전체 15종 = 13.3%). 가로형 안에서,
    세로형 안에서는 각각 균등하게 나눈다 — 기기 하나를 편애하지 않는다.
    """
    global _PROFILE_WEIGHTS
    if share is None:
        _PROFILE_WEIGHTS = None
        return
    wide = [p.get("family") in WIDE_FAMILIES for p in TRAIN_PROFILES]
    nw, nn = sum(wide), len(wide) - sum(wide)
    if nw == 0 or nn == 0:
        raise SystemExit("가로형 또는 세로형 프로파일이 없다 — 비중을 못 맞춘다")
    _PROFILE_WEIGHTS = [(share / nw) if w else ((1.0 - share) / nn)
                        for w in wide]


# generic_v1(기기 미상 잔여 품)은 기기 속성이 없어 기기 일관성 제약도 없다 —
# 렌더마다 실측 코퍼스 반전률로 뽑는다.
GENERIC_INVERTED_P = REAL_BASELINE["polarity"]["inverted_pct"] / 100.0


def sample_wh(rng):
    i = rng.choices(range(len(_BINS)), weights=_WEIGHTS, k=1)[0]
    lo, hi = _BINS[i]
    return rng.uniform(lo, hi)


# 코퍼스 값 분포 실측(labels.jsonl 2,512행, 2026-09-12). 자릿수 비율만 맞추고
# 구간 안을 균등으로 뽑으면 큰 값이 과대표집된다 — randint(100,511) 균등은
# 200 이상을 3자리의 76%로 만드는데 실측은 8.0%다. 구간까지 실측을 따른다.
_VALUE_BINS = [
    ((30, 70), 0.023), ((70, 100), 0.181), ((100, 130), 0.385),
    ((130, 160), 0.211), ((160, 200), 0.119), ((200, 300), 0.062),
    ((300, 512), 0.018),
]


def sample_value(rng):
    """코퍼스 값 분포(2,512행 실측): 중앙 121 · 100 미만 20.5% · 200 이상 8.0%."""
    r = rng.random()
    acc = 0.0
    for (lo, hi), w in _VALUE_BINS:
        acc += w
        if r <= acc:
            return rng.randint(lo, hi - 1)
    return rng.randint(100, 129)


class Placer:
    """배치 충돌 검사 — 텍스트·아이콘·도트줄 전부 사각형으로 검사한다(AC#16).
    경계: 패널 안쪽 사각형. 요소가 패널 안에서 잘리는 일은 배치로 막는다(AC#12).
    프레임(캔버스) 가장자리 클리핑은 이 판에서 만들지 않는다 — 허용이 아니라
    미사용으로 보고한다."""

    def __init__(self, x0, y0, x1, y1):
        self.px0, self.py0, self.px1, self.py1 = x0, y0, x1, y1
        self.rects = []

    def reserve(self, x0, y0, x1, y1, name):
        self.rects.append((x0, y0, x1, y1, name))

    def _fits(self, x0, y0, x1, y1):
        if x0 < self.px0 or y0 < self.py0 or x1 > self.px1 or y1 > self.py1:
            return False
        for a, b, c, d, _ in self.rects:
            if x0 < c and a < x1 and y0 < d and b < y1:
                return False
        return True

    def try_place(self, x0, y0, w, h, name, alternates=()):
        for px, py in ((x0, y0),) + tuple(alternates):
            px, py = int(px), int(py)
            if self._fits(px, py, px + w, py + h):
                self.reserve(px, py, px + w, py + h, name)
                return True
        return False

    # 밴드(숫자 필드) 안에 앉아도 되는 요소 — 실물에서 숫자 옆이 원래 자리다.
    # 아이콘은 여기 없다: green_doctor 의 blood-drop 이 밴드 오른쪽 끝을 7px
    # 파고들어 마지막 자릿수 위에 얹혔다(2026-09-13, n=2600 중 2장).
    BAND_OK = frozenset(("unit", "meal", "arrow"))

    def place_fixed(self, x0, y0, w, h, name, tol=0):
        """기기 고정 레이아웃용. BAND_OK 요소만 밴드 예약을 무시한다.
        tol 은 0 이다 — 하드 검사(_count_overlaps)가 엄밀 겹침을 세므로
        여기서 여유를 두면 배치는 통과하고 검사는 실패한다(같은 세션에서
        glulabel x icon:triangle 3px 겹침이 그렇게 났다)."""
        x0, y0, w, h = int(x0), int(y0), int(w), int(h)
        if x0 < self.px0 or y0 < self.py0 or _x1(x0, w) > self.px1                 or _y1(y0, h) > self.py1:
            return False
        for a, b, c, d, nm in self.rects:
            if nm == "band" and name in self.BAND_OK:
                continue
            if x0 < c - tol and a + tol < x0 + w and y0 < d - tol                     and b + tol < y0 + h:
                return False
        self.reserve(x0, y0, x0 + w, y0 + h, name)
        return True


def _x1(x0, w):
    return x0 + w


def _y1(y0, h):
    return y0 + h


def _lcd_text(img, x, y, text, h, ink, name="", heights=None,
              thick=None, slant=0.0, digit_mask=None, digit_w=None):
    """액정 보조 글자 — 세그먼트 스트로크 폰트(카드 「합성 글리프 네 결함」
    AC#1, 2026-09-13). Hershey 벡터 폰트의 곡선은 세그먼트 LCD 가 낼 수
    없다 — 실사진 722(Gmate)는 값·시간·단위·days 줄이 전부 각진 세그먼트다.
    숫자는 7-세그, 콜론은 사각 점 두 개(synth_lcd.seg_text, 근거 722 '1:27').
    thick·slant 는 큰 숫자의 DSEG 변형(_pick_variant)과 같은 계열 — 한 패널
    안에서 굵기·기울기가 일치한다(사람 리뷰 2026-09-13: 세그먼트도 여러
    종류를 써라). 알파벳 토큰 화이트리스트 assert(AC#14)는 여기서 지킨다.
    heights 를 넘기면 그은 글자 높이를 기록한다(AC#3 크기 종수 검사).
    반환값: 그은 폭 px(배치 예약은 이 값으로)."""
    alpha_ok = LCD_TOKENS | {w for u in LCD_UNITS for w in u.split(" ")
                             if w.isalpha()}
    for w in text.split(" "):
        if w.isalpha() and len(w) >= 2:
            assert w in alpha_ok, f"액정 토큰 위반: {w!r} ({name})"
    if heights is not None:
        heights.add(h)
    return seg_text(img, x, y, text, h, ink, thick=thick, slant=slant,
                    digit_mask=digit_mask, digit_w=digit_w)


def _draw_ghost(img, x, y, dh, w_target, ink, variant, ghost, cache):
    """빈 슬롯 잔상 — '8' 전체 획만 옅게. 진한 글리프는 그리지 않는다."""
    if ghost <= 0:
        return
    gkey = (variant, dh, "ghost")
    g8 = cache.get(gkey)
    if g8 is None:
        m8 = _glyph_mask("8", variant, dh)
        if m8 is None:
            return
        w8 = m8.shape[1]
        sx = w_target / max(1, w8)
        gw = max(2, int(round(w8 * sx)))
        if gw != w8:
            m8 = cv2.resize(m8.astype(np.uint8) * 255, (gw, dh),
                            interpolation=cv2.INTER_AREA) > 96
        cache[gkey] = g8 = m8
    gx = x + (w_target - g8.shape[1]) // 2
    region = img[max(0, y):y + dh, max(0, gx):gx + g8.shape[1]]
    blend = region.astype(np.float32) * (1 - ghost) + ink * ghost
    hh = min(region.shape[0], dh)
    ww = min(region.shape[1], g8.shape[1])
    region[:hh, :ww][g8[:hh, :ww]] = blend[:hh, :ww][g8[:hh, :ww]]


def _draw_digit_uniform(img, x, y, dh, ch, w_target, ink, variant, glyph_cache,
                        plane=None):
    """숫자 한 자 — DSEG 마스크를 '균일 x-압축' 하나로 세운다(결함 (1)(2) 대응).
    w_target 은 '8' 기준 목록 폭. 같은 패널의 모든 글리프가 같은 sx 를 쓰므로
    상대 폭('1' 이 좁고 '8' 이 넓음)이 보존되고, 글리프는 모두 같은 평면 위에
    있다. plane 을 넘기면 같은 마스크를 자가검사용 평면에도 남긴다(AC#8)."""
    key = (variant, dh)
    if key not in glyph_cache:
        glyph_cache[key] = {}
    cache = glyph_cache[key]
    if ch not in cache:
        cache[ch] = _glyph_mask(ch, variant, dh)
    m = cache[ch]
    if m is None:
        return
    if "8" not in cache:
        cache["8"] = _glyph_mask("8", variant, dh)
    m8 = cache["8"]
    sx = w_target / max(1, m8.shape[1])
    w_ch = max(2, int(round(m.shape[1] * sx)))
    if w_ch != m.shape[1]:
        interp = cv2.INTER_AREA if w_ch < m.shape[1] else cv2.INTER_NEAREST
        m = cv2.resize(m.astype(np.uint8) * 255, (w_ch, dh),
                       interpolation=interp) > 96
    gx = x + (w_target - w_ch) // 2
    region = img[y:y + dh, gx:gx + w_ch]
    hh = min(region.shape[0], dh)
    ww = min(region.shape[1], w_ch)
    region[:hh, :ww][m[:hh, :ww]] = ink
    if plane is not None:
        preg = plane[y:y + dh, gx:gx + w_ch]
        preg[:hh, :ww][m[:hh, :ww]] = 255


def _dot_time_text(rng, fmt_i=None, fmts=None):
    """시간·날짜 줄. 표기 포맷(구분자·12/24시·am 표기)은 기기의 것이라
    fmt_i 로 고정하고, 숫자 내용만 렌더마다 뽑는다(사람 지침 2026-09-13)."""
    pool = fmts or DOT_FMTS
    fmt = pool[rng.randrange(len(pool)) if fmt_i is None else fmt_i % len(pool)]
    return fmt.format(h02=f"{rng.randint(0, 12):02d}",
                      m02=f"{rng.randint(0, 59):02d}",
                      M=f"{rng.randint(1, 12)}", M02=f"{rng.randint(1, 12):02d}",
                      d=f"{rng.randint(1, 31)}", d02=f"{rng.randint(1, 31):02d}",
                      # 전역 random 이 아니라 넘겨받은 rng 여야 한다 —
                      # 구판은 여기서만 모듈 전역 난수를 써서 같은 시드로도
                      # 프로세스마다 am/pm 이 달라졌다(재현성 구멍, 2026-09-13
                      # 전수 검토). 렌더러 비결정성 카드의 한 갈래다.
                      am=rng.choice(["am", "pm"]),
                      AM=rng.choice(["AM", "PM"]))


def render_panel(value, rng, profile=None):
    """물리 패널 한 장. 반환 dict:
      panel   최종 캔버스(uint8, 긴 변 896)
      quad    밴드 쿼드 4x2(float32, 캔버스 픽셀, TL-TR-BR-BL) — 이미지와 같은
              변환을 통과한 좌표
      label   값 라벨(숫자만)
      glyph_plane_check  글리프 평면 자가검사 점수(1에 가까울수록 일관 변환)
      density 최종(광학 뒤) 밴드 밖 엣지 밀도 — 같은 자로 잰 값
      rects   배치 사각형(겹침 0 검증용), dropped  뺀 요소
    밀도는 광학 뒤에 재서 목표에 못 미치면 부족분을 올려 최대 3회 재렌더한다 —
    계수 추측으로 맞추지 않는다(1판의 교훈)."""
    if profile is None:
        # 가중치가 없으면 구판 경로 그대로 — rng.choices 는 randrange 와 난수
        # 소비가 달라서, 갈아끼우면 같은 시드가 다른 코퍼스를 낸다.
        profile = (TRAIN_PROFILES[rng.randrange(len(TRAIN_PROFILES))]
                   if _PROFILE_WEIGHTS is None else
                   rng.choices(TRAIN_PROFILES, weights=_PROFILE_WEIGHTS, k=1)[0])
    pid = profile.get("id", "generic_v1")
    if profile.get("legacy"):
        profile = dict(id="generic_v1", slots=(2, 3), align="right",
                       italic=False)
        pid = "generic_v1"
    # mixed 상태는 없앴다(2026-09-13). '같은 이름 아래 두 기기'였던
    # performa_silver 는 performa_silver / performa_nano 로 쪼갰다 — 평균
    # 극성의 유령 기기를 만드는 대신 물건을 둘로 센다.
    if pid == "generic_v1":
        # 기기 미상 익명 풀만 코퍼스 비율에서 뽑는다. 여기서는 특정 기기가
        # 아니라 분포가 맞으면 된다.
        inverted = rng.random() < GENERIC_INVERTED_P
    else:
        inverted = bool(PANEL_ATTRS.get(pid, {}).get("inverted", False))
    # 밀도를 합성의 '목표'로 쓰지 않는다(사람 지시 2026-09-13).
    # 실사진의 엣지 밀도는 화면 내용이 아니라 조도·광원·그림자에 크게 좌우된다
    # — 그 값을 합성에 대입하면 렌더러가 조명 때문에 생긴 숫자를 '내용'으로
    # 맞추려 들고, 근거 없는 요소를 채워 넣게 된다. 실제로 그랬다: 밀도가
    # 목표에 못 미치면 최대 3회 다시 그려 가장 밀도 높은 장을 골랐고(여백
    # 분포가 두꺼운 몸체 쪽으로 기울었다), 모자라면 도트줄·mem·아이콘을 48회
    # 시도로 채워 넣었다.
    #
    # 렌더는 이제 1회다. 화면에 무엇이 있는지는 기기가 정하고, 밀도는 그
    # 결과를 재서 보고만 한다(manifest.density).
    return _render_once(value, rng, profile, pid, inverted)


def _gpc_bg_contrast(img, quad, glass_rect):
    """글리프 평면 검사용 배경·대비. bg 는 유리 영역에서 밴드 쿼드 bbox 를 뺀
    부분의 중앙값이고, 대비는 쿼드 bbox 안 p95-p5 — 실측 자
    measure_polarity.polarity_of 와 같은 정의다."""
    H, W = img.shape[:2]
    px0, py0, px1, py1 = glass_rect
    qx0, qx1 = int(quad[:, 0].min()), int(np.ceil(quad[:, 0].max()))
    qy0, qy1 = int(quad[:, 1].min()), int(np.ceil(quad[:, 1].max()))
    glass = img[max(0, py0):min(H, py1),
                max(0, px0):min(W, px1)].astype(np.float32)
    glass[max(0, qy0 - py0):min(glass.shape[0], qy1 - py0),
          max(0, qx0 - px0):min(glass.shape[1], qx1 - px0)] = np.nan
    med = np.nanmedian(glass)
    bg = float(med) if np.isfinite(med) else float(np.median(img))
    band = img[max(0, qy0):min(H, qy1),
               max(0, qx0):min(W, qx1)].astype(np.float32)
    contrast = float(abs(np.percentile(band, 95) - np.percentile(band, 5)))
    return bg, contrast


def gpc_ink_threshold(contrast):
    """잉크 문턱: 밴드 대비(p95-p5)의 비례 계수에 노이즈 위 바닥."""
    return max(GPC_INK_FLOOR, GPC_INK_K * contrast)


def glyph_plane_score(img, quad, glyph_warped, glass_rect, ink_thr=None):
    """글리프 평면 자가검사(AC#8 계승): 같은 변환을 통과한 글리프 마스크
    자리가 최종 이미지에서 실제 잉크(배경과 유의미하게 다른 픽셀)인지 비율로.
    ink_thr=None 이면 대비 비례 문턱(gpc_ink_threshold)을 쓴다 — 구판 고정
    문턱(30)은 진단(diag_gpc_threshold.py)이 재현용으로 넘긴다.
    주의: 워프가 마스크 밖을 borderValue(베젤색) 로 채우므로 0 이 아니라 127 로
    문턱을 낸다 — 0 비교는 캔버스 전체가 sel 이 된다."""
    bg, contrast = _gpc_bg_contrast(img, quad, glass_rect)
    if ink_thr is None:
        ink_thr = gpc_ink_threshold(contrast)
    sel = glyph_warped > 127
    ink = np.abs(img.astype(np.float32) - bg) > ink_thr
    return float((ink & sel).sum()) / max(1, sel.sum())


def _render_once(value, rng, profile, pid, inverted):
    label = str(value)
    assert label.isdigit(), f"라벨 오염: {label!r}"

    # ── 캔버스 — 실측 종횡비, 긴 변 896(AC#1·#6) ──────────────────────────
    lay = profile.get("layout")   # 기기 고정 레이아웃(2026-09-13 재구조)
    # 기기 형질 — 실측이 없는 축까지 기기로 고정한다(사람 지침 2026-09-13).
    # lay 가 없는 generic_v1 은 '여러 기기를 뭉뚱그린 익명 풀'이라 형질이 없다
    # (그게 이 풀의 존재 이유다 — 프로파일 밖 배치의 다양성 하한).
    ident = device_identity(pid) if lay is not None else None
    # 레이아웃 축은 렌더당 한 번만 뽑는다 — 기기가 중심(중앙값), 촬영이 그
    # 주위(p10~p90)를 흔든다. 같은 축을 두 번 뽑으면 밴드 폭과 위치가 서로
    # 다른 장의 것이 섞인다.
    if lay is not None:
        _L = {k: lay_val(lay, k, rng) for k in ("ar", "bw", "bh", "cx", "cy")}
    else:
        _L = None

    def _fix(key, lo, hi):
        """기기 형질 분수를 실제 범위로. 형질이 없으면(익명 풀) 렌더 rng."""
        if ident is None:
            return rng.uniform(lo, hi)
        return lo + (hi - lo) * ident[key]

    _shown_memo = {}

    def _shown(name, p):
        """요소를 이 장에 그리는가. 기기 고정 기기에서 '기기가 가진 요소'는
        항상 그린다 — 있다 없다 하면 같은 기기로 안 보인다. 상태성 요소만
        장마다 켜고 끈다(STATEFUL_ELEMENTS).

        이름별로 답을 기억한다(2026-09-15). 밴드 안 요소의 자리(_allow)를
        떼려면 '그릴지'를 배치 **전에** 알아야 하는데, 결정은 300줄 뒤
        그리는 자리에서 났다. 그래서 안 그리는 장에서도 자리는 떼어 놓았고,
        숫자가 그만큼 왼쪽으로 밀려 오른쪽에 빈 자리가 남았다.
        메모이즈하면 먼저 물어봐도 나중 호출이 같은 답을 받는다 — 난수는
        한 번만 소비된다(호출 순서가 바뀌므로 옛 코퍼스는 재현되지 않는다)."""
        if name in _shown_memo:
            return _shown_memo[name]
        if ident is None:
            v = rng.random() < p
        elif name in STATEFUL_ELEMENTS:
            v = rng.random() < p
        else:
            v = True
        _shown_memo[name] = v
        return v
    # 캔버스(=GM 크롭) 종횡비. 기기 고정 기기는 코퍼스 히스토그램에서 뽑지
    # 않는다 — 그 히스토그램은 54종이 섞인 분포라 한 기기에 씌우면 같은 기기의
    # 크롭이 0.70~0.98 로 흔들리고, 유리 종횡비는 고정인데 캔버스가 흔들리니
    # 남는 몸체 스트립 두께가 장마다 달라진다(사람 지적 2026-09-13: 같은
    # acura_plus 인데 LCD 비율과 브랜드 글자 크기가 다르다). 캔버스는 유리에
    # 마진을 더한 것이므로 그 순서로 만든다: 유리 종횡비(기기) + 마진 비율
    # (기기) -> 캔버스 종횡비. 촬영이 흔드는 것은 아래 '크롭 여유' 하나다.
    if lay is not None:
        _gwr = _L["ar"]                           # 유리 w/h(이 장의 값)
        _z = rng.uniform(0.55, 1.0)               # 크롭 여유(타이트~여유)
        _fl, _fr = ident["mg_l"] * _z, ident["mg_r"] * _z
        _ft, _fb = ident["mg_t"] * _z, ident["mg_b"] * _z
        wh = (_gwr * (1 + _fl + _fr)) / (1 + _ft + _fb)
    else:
        wh = sample_wh(rng)
    if wh >= 1.0:
        W, H = LONG_SIDE, max(64, int(round(LONG_SIDE / wh)))
    else:
        W, H = max(64, int(round(LONG_SIDE * wh))), LONG_SIDE

    # 가로형 empirical 튜플(정본 band.wide_raw, n=39)을 스트립 폭보다 먼저
    # 뽑는다 — tall 밴드 장면의 상하 몸체 얇힘(아래)과 기하 재표본이 이 값을
    # 공유한다. 균등 p10~p90 로는 치우친 가로형 분포(h median 0.747 vs 구간
    # 중앙 0.644)를 놓친다. 두 가족: 칼럼형(w<0.75)·하단행형(w>=0.75, 사람
    # 라벨이 단위·시간까지 밴드에 포함 — 971·497·66·821).
    _wide_t = None
    _wide_row = False
    # 배치 가족은 기기의 성질이지 종횡비의 함수가 아니다(2026-09-13 정정).
    # 구판은 화면 w/h >= 1.0 을 문턱으로 삼았는데, 정사각에 가까운 기기가
    # 장마다 가족을 오갔다 — GluNEO plus 는 세로형 기기에 거의 정사각 화면
    # (쿼드에 따라 0.89~1.23)이고 배치는 '큰 숫자 + 아래 한 줄'인데, 타이트
    # 쿼드에서 ar>1 이 나오면 가로형 정보 칼럼 가족으로 넘어갔다.
    # 기기 고정 프로파일은 family 를 선언한다. 익명 풀만 종횡비로 가른다.
    _fam = profile.get("family")
    if lay is not None:
        if _fam in ("column", "row"):
            _wide_t = (_L["bw"], _L["bh"], _L["cx"], _L["cy"])
            _wide_row = (_fam == "row")
    elif wh >= 1.0:
        _wr = REAL_BASELINE["band"]["wide_raw"]
        _wide_t = _wr[rng.randrange(len(_wr))]
        _wide_row = _wide_t[0] >= 0.75

    # ── 몸체 + 액정 — GM 크롭과 같은 물건(카드 2026-09-12) ──────────────────
    # 실사진 GM 크롭의 바깥 링(15%) 밀도 2.84% 는 기기 몸체에서 온다 — 몸체 인쇄
    # 브랜드·모델명(Gmate 713·722, CareTouch·MM1000 92·97·100, Boryung 97),
    # 몸체 윤곽 곡선(713·722·92·97·100), 움푹한 베젤과 그림자(233·235).
    # 구판은 균일 베젤 링만 그려 링이 1.73% 에 그쳤다(before, n=296,
    # diag_density_where.py ring). 이 네 요소 이외의 몸체 요소는 근거 없다.
    #
    # 폭 결정(AC#1, 실측): '링 15% 균일 확대'는 기하가 막는다 — 실측
    # band_w/canvas_w 0.827 → 유리 폭 ≥ ~0.84 → 측면 몸체는 편당 ≤ ~0.08.
    # 상단은 band_cy 0.391 − band_h/2(≤0.27) → ≤ ~0.12, 하단은 band 하단
    # (≤ ~0.73) → ≤ ~0.14 여유. 비대칭 확대: 좌우 1~7%, 상 3~12%·하 3~14%.
    # 30% 는 타이트 크롭(전변 0.5~2%, 실물 타이트 GM 박스).
    if lay:
        # 마진은 위에서 캔버스 종횡비를 낼 때 이미 정해졌다 — 같은 비율을
        # 그대로 픽셀로 옮긴다. 그래야 유리 종횡비도 스트립 두께도 기기에
        # 붙어 있고, 장마다 달라지는 것은 크롭 여유(_z)뿐이다.
        mg_l = max(2, int(round(W * _fl / (1 + _fl + _fr))))
        mg_r = max(2, int(round(W * _fr / (1 + _fl + _fr))))
        mg_t = max(2, int(round(H * _ft / (1 + _ft + _fb))))
        mg_b = max(2, int(round(H * _fb / (1 + _ft + _fb))))
    elif rng.random() < 0.30:
        mg_t = int(H * rng.uniform(0.005, 0.02))
        mg_b = int(H * rng.uniform(0.005, 0.02))
        mg_l = int(W * rng.uniform(0.005, 0.02))
        mg_r = int(W * rng.uniform(0.005, 0.02))
    else:
        mg_l = int(W * rng.uniform(0.01, 0.07))
        mg_r = int(W * rng.uniform(0.01, 0.07))
        mg_t = int(H * rng.uniform(0.03, 0.12))
        mg_b = int(H * rng.uniform(0.03, 0.14))
        if _wide_t is not None:
            # 가로형 tall 밴드(UltraMini 류, h 최대 0.86) 장면은 GM 박스가 유리에
            # 꽉 붙는다 — 상하 몸체가 깊으면 밴드가 유리에 못 들어와 기하가
            # 눌린다(재조준 2026-09-12, 칼럼 카드). 실측 밴드 높이에 맞춰 얇힌다.
            _vmax = max(8, int(H * (1.0 - _wide_t[1]) - 12))
            if mg_t + mg_b > _vmax:
                _vs = _vmax / (mg_t + mg_b)
                mg_t, mg_b = max(3, int(mg_t * _vs)), max(3, int(mg_b * _vs))
    # 몸체 플라스틱 톤은 기기의 것이다(흰 Gmate · 남색 OneTouch · 은색
    # Performa). 배경(bg_col)은 촬영 장소라 장마다 다르다.
    body_col = int(_fix("body_u", 50, 190))
    bg_col = int(body_col * rng.uniform(0.25, 0.55))   # 몸체 바깥(배경·표면)
    img = np.full((H, W), body_col, np.uint8)
    # 몸체 표면 — 완만한 상→하 기울기(플라스틱 조명)
    grad = np.linspace(rng.uniform(-18, -4), rng.uniform(4, 18), H,
                       dtype=np.float32)[:, None]
    img = np.clip(img.astype(np.float32) + grad, 0, 255).astype(np.uint8)
    # 액정 바탕·잉크의 '맨 톤'도 기기의 것이다 — 촬영이 바꾸는 것은 아래
    # 대비 열화 계수와 광학 단(명암·비네팅)이다. 구판은 여기서도 렌더마다
    # 뽑아 같은 기기의 액정이 장마다 다른 색이었다.
    if inverted:
        panel_col = int(_fix("panel_u", 35, 95))
        ink_digit = int(_fix("ink_u", 185, 245))
        ink_small = int(_fix("ink_u", 150, 210))
    else:
        panel_col = int(_fix("panel_u", 150, 215))
        ink_digit = int(_fix("ink_u", 20, 90))
        ink_small = int(_fix("ink_u", 60, 130))
    # 밴드 대비 열화(카드 「합성 열화 상한」): 잉크-패널 간극에 계수를 곱한다.
    # 실사진 대비 분포(median 99 · p10 60 · p90 178 · min 21 · 40미만 1.1%,
    # real_baseline.json polarity, n=264)의 아래쪽 폭은 씻긴 화면·역광·저조도
    # 촬영에서 온다 — 글자와 바탕의 간극이 줄어드는 물리 현상이라 렌더 파라미터
    # 로 낸다(렌더 후 버리지 않는다, AC#5). 숫자·보조 잉크에 같은 계수 — 화면
    # 전체의 세척 상태는 기기·촬영 단위라 함께 움직인다.
    _c = rng.uniform(0.40, 1.0)
    ink_digit = int(round(panel_col + (ink_digit - panel_col) * _c))
    ink_small = int(round(panel_col + (ink_small - panel_col) * _c))

    # 몸체 윤곡 곡선 — 캔버스 모서리를 라운드로 깎아 배경이 보이게(713·722·
    # 92·97·100). 회전·원근 크롭의 모서리는 몸체 곡면 바깥이 프레임에 들어온
    # 실사진 크롭과 같은 모양새다.
    body_text = None
    # 재조준(2026-09-12): 확률 0.65→0.45, 반경 0.04~0.10→0.03~0.08 — 1차 값은
    # 폐기된 n=84 링 목표(2.84%)에 맞춘 것이라 과했다(새 목표 1.90±0.5%,
    # real_baseline.json ring, n=263).
    # 몸체 모서리는 기기의 형상이다 — 둥근 기기는 언제 찍어도 둥글다.
    _corner_u = ident["corner_u"] if ident is not None else (
        rng.random() if rng.random() < 0.42 else None)
    if _corner_u is not None:
        rr = int(min(W, H) * (0.03 + 0.05 * _corner_u))
        sil = np.zeros((H, W), np.uint8)
        cv2.rectangle(sil, (rr, 0), (W - 1 - rr, H - 1), 255, -1)
        cv2.rectangle(sil, (0, rr), (W - 1, H - 1 - rr), 255, -1)
        for cx_, cy_ in ((rr, rr), (W - 1 - rr, rr),
                         (rr, H - 1 - rr), (W - 1 - rr, H - 1 - rr)):
            cv2.circle(sil, (cx_, cy_), rr, 255, -1)
        img[sil == 0] = bg_col
        img = cv2.GaussianBlur(img, (3, 3), 0)   # 곡면 부드러운 전이

    px0, py0, px1, py1 = mg_l, mg_t, W - mg_r, H - mg_b
    # 움푹한 베젤 + 그림자(233·235) — 유리 직전 홈(어두운 선)과 홈 바깥
    # 그림자 띠(위쪽 진하게), 가장자리 하이라이트 한 줄.
    # 재조준(2026-09-12): 확률 0.7→0.4, 그림자 강도 0.45→0.36·0.26→0.22,
    # 띠 폭 1.5~3.0→1.2~2.2 — n=84 링 목표에 맞춘 과다였다(위와 같은 근거).
    # 대비 열화 카드에서 링이 상한(2.40%)에 붙어 0.45→0.40 으로 한 단계 더
    # 내렸다(seed 32000 에서 2.42% — 재측정 기록은 synth-degradation-cap.md).
    # 움푹한 베젤 홈도 기기의 형상이다(홈 깊이 포함).
    _groove = (ident["groove"] if ident is not None else rng.random() < 0.40)
    if _groove:
        _gu = ident["groove_u"] if ident is not None else rng.random()
        sh = max(3, int(min(W, H) * (0.008 + 0.012 * _gu)))
        dark = np.clip(panel_col * 0.35, 8, 60)
        cv2.rectangle(img, (px0 - sh, py0 - sh), (px1 + sh, py1 + sh),
                      int(dark), 2)
        shadow = np.zeros((H, W), np.float32)
        top_w = int(sh * rng.uniform(1.2, 2.2))
        for k in range(sh, 0, -1):
            f = 0.36 * (1 - k / sh)
            cv2.rectangle(shadow, (px0 - k, py0 - k), (px1 + k, py1 + k), f, 1)
        cv2.rectangle(shadow, (px0 - sh - top_w, py0 - sh - top_w),
                      (px1 + sh + top_w, py1 + sh + top_w), 0.22, 1)
        shadow *= (255.0 - dark) / max(1.0, shadow.max() * 255)
        img = np.clip(img.astype(np.float32) * (1 - shadow),
                      0, 255).astype(np.uint8)
        hi = int(min(255, body_col + 40))
        cv2.rectangle(img, (px0 - sh - 3, py0 - sh - 3),
                      (px1 + sh + 3, py1 + sh + 3), hi, 1)
    # 유리-몸체 경계 — 실사진에서 이 경계는 오목한 홈의 부드러운 전이다. 하드
    # 채움(img[...] = panel_col)은 판 전체 둘레에 계단을 만들어 Canny 가 통째로
    # 잡았고, 그 사각형이 링 엣지의 약 25% 를 혼자 냈다(재측정 2026-09-12: 링
    # 2.42% 중 경계 ±6px 띠 기여 ~25%, n=120). 2~6px 램프로 페더링한다(초점
    # 흔들림 분포). 날카로운 경계선이 필요한 장은 홈 코드(위, 확률적)가 담당한다.
    feather = rng.uniform(2.0, 6.0)
    _pmask = np.zeros((H, W), np.float32)
    cv2.rectangle(_pmask, (px0, py0), (px1, py1), 1.0, -1)
    _pmask = cv2.GaussianBlur(_pmask, (0, 0), feather / 2.5)
    img = np.clip(img.astype(np.float32) * (1 - _pmask) + panel_col * _pmask,
                  0, 255).astype(np.uint8)

    # 어두운 창(meter 기기) — 액정을 감싼 검은 면. 근거 267·270: 흰 몸체와
    # 액정 사이에 검은 창이 한 겹 있고 미터기 점 열이 그 위에 인쇄돼 있다.
    # 몸체 인쇄(브랜드명)보다 먼저 깐다 — 브랜드명은 흰 몸체 위에 있다.
    if profile.get("meter"):
        _wk_r = max(6, int(mg_r * 0.92))
        _wk_t = max(3, int(mg_t * 0.45))
        _wk_b = max(3, int(mg_b * 0.45))
        _wk_l = max(3, int(mg_l * 0.55))
        _wcol = int(np.clip(body_col * 0.22, 12, 70))
        # 유리 '바깥' 테두리만 칠한다 — 유리 안을 덮으면 이미 그린 액정 바탕과
        # 페더링이 날아간다.
        for _r in ((px0 - _wk_l, py0 - _wk_t, px1 + _wk_r, py0),
                   (px0 - _wk_l, py1, px1 + _wk_r, py1 + _wk_b),
                   (px0 - _wk_l, py0, px0, py1),
                   (px1, py0, px1 + _wk_r, py1)):
            cv2.rectangle(img, (_r[0], _r[1]), (_r[2], _r[3]), _wcol, -1)

    # 몸체 인쇄 — 브랜드·모델명. 문자열은 프로파일 근거(BEZEL_TEXTS)대로,
    # 몸체 인쇄 자체의 근거 사진은 713·722(Gmate)·92·97·100(CareTouch·
    # MM1000·Boryung). 스트립이 글자를 온전히 담을 때만 그린다(잘리지 않는다).
    # 재조준(2026-09-12): 상단 게이트 0.6→0.45, 내부 확률 0.8→0.65 — n=84 링
    # 목표에 맞춘 확률이었다(새 목표는 real_baseline.json ring, n=263).
    # 몸체 인쇄는 기기의 것이다 — 어느 변에 무슨 글자가 찍혀 있는지는 장마다
    # 바뀌지 않는다. 근거 사진 9종 전부 몸체에 브랜드·모델명이 찍혀 있다
    # (842 Gmate · 1058 ONETOUCH Ultra/LIFESCAN · 475 ACURA PLUS · 267
    # ACCU-CHEK Instant · 1911 CareSens N Premier · 120 Premium · 228 GC
    # 녹십자MS ONE · 1781 GREEN Doctor · 1186 ACCU-CHEK Performa, 2026-09-13
    # 눈검). 그래서 기기 고정 기기는 확률 게이트 없이 항상 그린다 — 자리가
    # 모자라면(스트립이 얇은 크롭) 그때만 빠진다.
    # 몸체 인쇄는 변마다 다를 수 있다 — OneTouch Ultra 는 화면 '위'에
    # 'OneTouch Ultra', '아래'에 'LIFESCAN' 이다(실물 1058·2110). 구판은 둘 중
    # 하나만 골라 한 변에 찍었다(사람 지적 2026-09-13: 베젤 렌더링 틀렸다).
    _bz_edges = (("top", mg_t), ("bottom", mg_b))
    _bz_map = {}
    if ident is not None:
        _bz = profile.get("bezel") or {}
        if _bz.get("per_edge"):
            _bz_map = dict(_bz["per_edge"])
        elif _bz.get("edge") and _bz.get("texts"):
            _bz_map = {_bz["edge"]: _bz["texts"][
                ident["bezel_i"] % len(_bz["texts"])]}
    for edge, m_side in _bz_edges:
        if ident is None:
            if edge == "top" and rng.random() >= 0.45:
                continue
            if rng.random() >= 0.55:
                continue
        elif _bz_map and edge not in _bz_map:
            continue          # 기기가 선언한 변에만 찍힌다
        if m_side < 14 or pid not in BEZEL_TEXTS:
            continue
        # 글자 높이는 몸체의 성질이라 유리 폭에 비례한다. 구판은 스트립
        # 두께(m_side)에 비례시켜, 크롭이 달라질 때마다 브랜드명 크기가
        # 같이 변했다(사람 지적 2026-09-13).
        bh = (max(8, int((px1 - px0) * ident["bezel_h"])) if ident is not None
              else max(8, int(m_side * 0.45)))
        if ident is not None and _bz_map:
            text = _bz_map[edge]
        else:
            _bt = BEZEL_TEXTS[pid]
            text = _bt[(ident["bezel_i"] if ident is not None
                        else rng.randrange(8)) % len(_bt)]
        scale = bh / 22.0
        (tw, thh), bl = cv2.getTextSize(text, _BEZEL_FONTS[0], scale, 1)
        if tw > (px1 - px0) * 0.95:
            # 긴 이름은 유리 폭에 맞춰 줄인다(구판은 그냥 포기했다).
            scale *= (px1 - px0) * 0.95 / tw
            bh = max(8, int(22.0 * scale))
            (tw, thh), bl = cv2.getTextSize(text, _BEZEL_FONTS[0], scale, 1)
        if thh + bl + 4 > m_side:
            # 스트립이 글자보다 얇으면 '안 그린다'가 아니라 '잘려 찍힌다'.
            # 실물 GM 크롭이 그렇다 — 475·267 도 브랜드명 윗동이 잘려 있다.
            # 구판은 여기서 포기해 몸체 인쇄가 78장 -> 19장으로 줄었다
            # (유리 폭 기준으로 글자를 키운 직후, 2026-09-13).
            if m_side < (thh + bl) * 0.35:
                continue
        # 인쇄 자리도 기기의 것이다 — 같은 기기에서 브랜드명이 좌우로 떠다니면
        # 다른 물건으로 보인다. 실물은 대개 중앙이다(842·1058·475·267).
        _bfx = (0.5 if ident is not None else rng.uniform(0.2, 0.55))
        bx = mg_l + max(6, int((W - mg_l - mg_r - tw) * _bfx))
        t_ink = int(bg_col * 0.6) if body_col > 110 else int(min(255, body_col + 70))
        # 글자가 유리를 침범하면 안 된다(사람 지적 2026-09-13). 스트립이
        # 얇아 잘릴 때는 캔버스 '바깥쪽'으로 잘리게 민다 — 구판은 스트립
        # 가운데에 놓아 아래쪽이 액정으로 넘어갔다.
        if edge == "top":
            by = min((mg_t - (thh + bl)) // 2, py0 - (thh + bl) - 1)
        else:
            by = max(H - mg_b + (mg_b - (thh + bl)) // 2, py1 + 1)
        cv2.putText(img, text, (bx, by + thh), _BEZEL_FONTS[0], scale,
                    t_ink, 1, cv2.LINE_AA)
        body_text = text
        if not (ident is not None and len(_bz_map) > 1):
            break   # 변마다 다른 글자를 선언한 기기만 둘 다 찍는다

    # 미터기 눈금(카드 「합성 글리프 네 결함」 AC#5) — LCD 창 '바깥' 오른쪽
    # 회색 띠에 인쇄된 점 열(약 10개). 근거 Instant 34장(2026-09-13): 점 열의
    # 모양·위치·밝기가 장마다 같다 — 세그먼트가 아니라 인쇄다. 화살표 요소가
    # 이 열을 가리킨다(arrow 의 meter 가 같은 프로파일에만 있다).
    if profile.get("meter") and mg_r >= 7:
        # 근거 사진 270(2026-09-13 눈검): 점 열은 흰 몸체가 아니라 액정을
        # 감싼 '검은 창' 위에 있다. 구판은 몸체 마진에 그려 밝은 플라스틱
        # 위에 회색 점이 떠 있었다. 창을 먼저 깔고 그 위에 점을 얹는다.
        _nd = 10
        _colh = int((py1 - py0) * 0.80)
        _gy0 = py0 + ((py1 - py0) - _colh) // 2
        _mcx = px1 + mg_r // 2
        _dr = max(1, min(2, mg_r // 6))
        # 점은 창보다 밝다(실물은 청록·붉은 인쇄) — 창 톤 기준으로 올린다.
        _mcol = int(np.clip(body_col * 0.22 + 90, 60, 235))
        for _k in range(_nd):
            _cy = _gy0 + int(_colh * (_k + 0.5) / _nd)
            cv2.circle(img, (_mcx, _cy), _dr, _mcol, -1)

    placer = Placer(px0 + 2, py0 + 2, px1 - 2, py1 - 2)

    # ── 숫자 밴드 — 실측 기하에서 역산. x0 는 '보이는 숫자줄'의 좌측이고
    #    빈 슬롯(잔상)은 그 바깥쪽에 그린다 — 쿼드는 사람 라벨처럼 보이는
    #    숫자줄만 감싼다(실측: 2자리 0.571 vs 3자리 0.810).
    #    기하 비율의 분모는 캔버스(=GM 박스)다(2026-09-12 재앵커). 실측
    #    band_w 0.827 의 분모도 GM 박스이고, 몸체 스트립이 생긴 지금 패널
    #    분모를 쓰면 밴드가 캔버스 대비 커져 기하 AC 가 깨진다. 대신 밴드가
    #    유리(px0..px1) 안에 들어가도록 아래 클램프가 지킨다(구판 우려는
    #    클램프+max_w 축소가 흡수한다).
    key = "portrait" if wh < 1.0 else "wide"
    g = BAND_GEOM[key]
    slots_spec = profile.get("slots") or len(label)
    slots = rng.choice(list(slots_spec)) if isinstance(slots_spec, (tuple,
                                                                    list))         else slots_spec
    slots = max(slots, len(label))
    pw, ph = px1 - px0, py1 - py0
    # _wide_t/_wide_row 는 캔버스 직후(스트립 얇힘과 공유)에서 이미 뽑았다.
    if lay is not None:
        # ── 상/중/하 3분할(사람 설계 2026-09-13) ─────────────────────────
        # "세로 레이아웃이니 혈당을 60~70% 가량 차지하게 하고 상하에 추가정보,
        #  가운데에 혈당정보를 표시하겠다."
        #
        # 밴드 높이를 실측에서 '뽑는' 대신, 위·아래 정보줄이 쓰는 높이를 빼고
        # 남는 가운데를 값이 채우게 한다. 구판은 실측 bh(0.39~0.47)를 그대로
        # 써서 숫자가 작고 아래가 비었다 — 그 실측값 자체가 '아래에 두 줄이
        # 오는 화면'의 결과라, 줄 수에서 역산하는 쪽이 layout 을 제대로 쓴다.
        _aux0 = max(7, int(ph * 0.085))        # 정보줄 글자 높이(잠정)
        _row = int(_aux0 * 1.45)               # 줄 하나가 쓰는 높이
        _n_top = 1 if (profile.get("glulabel")
                       or (profile.get("mem") or {}).get("pos", "").startswith("top")
                       or any(pos.startswith("top")
                              for _k, pos, _p in profile.get("icons", []))) else 0
        _n_bot = 0
        if (profile.get("unit") or {}).get("pos", "").startswith("below"):
            _n_bot += 1
        if (profile.get("time") or profile.get("daterow")
                or profile.get("dotrow_below") or profile.get("avgrow")):
            _n_bot += 1
        _pad_z = max(4, int(ph * 0.025))
        _top_h = _n_top * _row + _pad_z
        _bot_h = _n_bot * _row + _pad_z
        _mid_h = max(int(ph * 0.30), ph - _top_h - _bot_h)
        band_h = _mid_h * 0.96
        _zone_cy = py0 + _top_h + _mid_h / 2.0
    elif _wide_t is not None:
        band_h_frac = _wide_t[1]
        band_h = band_h_frac * H
    else:
        band_h_frac = rng.uniform(*g["h"])
        band_h = band_h_frac * H
    if _wide_row:
        # 행형 쿼드는 목표 폭·높이를 직접 쓰므로 유리 안으로 못 박는다 —
        # 실측 tw 최대 0.95 는 깊은 측면 스트립과 만나면 유리보다 커진다.
        band_h = min(band_h, py1 - py0 - 4)
        dh = int(band_h * 0.64)   # 숫자 64% + 아래 정보행(971·66·821 관찰 비)
        pad_y = max(4, int(band_h * 0.12))
    else:
        # 숫자는 밴드 높이의 92%(사람 지적 2026-09-13: 실물 라벨이 숫자를
        # 꽉 감싼다 — 구판 1.26 제수(79%)는 1차의 가정이라 숫자가 빈약했다.
        # 레이아웃 디버그 시트 layout_debug.png 실물 대비 확인.)
        dh = int(band_h * 0.92)
        pad_y = max(4, int((band_h - dh) / 2))
    # 글리프 폭 / 칸 피치 — 액정 셀의 기하라 기기 형질이다(촬영이 못 바꾼다).
    _g_r = (ident["glyph_in_cell"] if ident is not None
            else rng.uniform(*GLYPH_IN_CELL))
    if _wide_t is not None and not _wide_row:
        # 칼럼형: 목표 폭(tw·W)에서 피치를 역산한다. 세로형 육안 범위(0.50~0.60)
        # 보다 가는 칸(하한 0.24)도 실측이 요구한다 — UltraMini 가로형 밴드는
        # 좁고 높아(w~0.55·h~0.85) 0.50 이상으론 물리적으로 안 들어간다.
        pad_x0 = max(6, int(dh * 0.20))
        _pr = (_wide_t[0] * W - 2 * pad_x0) / max(1.0, dh * (slots - 1 + _g_r))
        pitch_r = min(0.75, max(0.21, _pr))
    else:
        # 하단행형 숫자는 세로형과 같은 비례(0.50~0.60) — 밴드가 넓은 건 옆
        # 단위·시간을 라벨이 포함해서지 숫자가 뚱뚱해서가 아니다.
        pitch_r = rng.uniform(*PITCH_RATIO)
    glyph_w = int(dh * pitch_r * _g_r)
    pitch = int(dh * pitch_r)
    gap = pitch - glyph_w
    n_vis = len(label)
    lead = slots - n_vis
    field_w = n_vis * pitch - gap
    # 쿼드는 슬롯 필드 전체(slots 칸 — 빈 앞칸 포함)를 감싼다. n=264 재측정에서
    # 사람 밴드 라벨의 2자리 폭은 3자리와 사실상 같다(세로형 median 2자리 0.866
    # vs 3자리 0.891, 2자리의 84% 가 폭 0.75 이상, n=32/185, 2026-09-12,
    # measure_panel_stats band + labels join). 구판의 '보이는 숫자줄만 감싼다
    # (2자리 0.571)' 은 84장 편향 표본에서 잰 값이라 버렸다. 기기 프로파일
    # 11종은 전부 slots=3 이므로 2자리 값도 3칸 필드에 놓이고 라벨도 그렇다.
    align = profile.get("align", "right")
    ghost_w = lead * pitch
    field_all_w = field_w + ghost_w
    quad_w = field_all_w + 2 * max(6, int(dh * 0.20))
    max_w = int(pw * 0.96)
    if quad_w > max_w:              # 폭이 막히면 높이를 줄여 맞춘다
        s = max_w / quad_w
        dh, glyph_w, pitch, gap = (int(dh * s), int(glyph_w * s),
                                   int(pitch * s), int(gap * s))
        field_w = n_vis * pitch - gap
        ghost_w = lead * pitch
        field_all_w = field_w + ghost_w
    # 높이도 유리 안에 들어와야 한다 — band_h 의 분모가 캔버스(H)라 몸체 스트립이
    # 깊은 가로형에서 쿼드가 유리보다 높아져 아래쪽 몸체로 넘쳤다(리뷰 2026-09-12:
    # wide 3/52, 최대 24px). 폭 클램프(max_w)는 폭만 잡는다 — 세로형은 한 장도
    # 발동하지 않는다(0/549, seed 31000 n=600).
    max_h = max(8, min(int(ph * 0.96), ph - 8))
    if dh + 2 * pad_y > max_h:
        s2 = max_h / (dh + 2 * pad_y)
        dh, glyph_w, pitch, gap = (int(dh * s2), int(glyph_w * s2),
                                   int(pitch * s2), int(gap * s2))
        pad_y = max(2, int(pad_y * s2))
        field_w = n_vis * pitch - gap
        ghost_w = lead * pitch
        field_all_w = field_w + ghost_w
    if lay is not None:
        # 밴드 폭도 기기 고정 — dh(높이에서 온 값)는 그대로 두고 피치 비율을
        # 목표 폭에서 역산한다(측정 박스에 숫자를 맞추는 방향). dh 를 불리면
        # 높이(band_h)가 함께 부풀어 두 실측값이 같이 못 박히지 않는다.
        # 폭이 피치 상한(0.85)으로 못 채우는 기기는 폭이 약간 짧아진다 —
        # 숫자를 무한히 납작하게 늘리는 것보다 낫다.
        _pad_x_t = max(6, int(dh * 0.20))
        # _allow 는 배치용 예약이고, **이 장에 실제로 그릴 요소만** 센다
        # (2026-09-15). 쿼드만 내용에 맞춰 줄이고 이걸 안 고치면, 숫자는
        # 그대로 왼쪽으로 밀린 채 쿼드만 오므라들어 빈 자리가 유리 쪽으로
        # 옮겨 갈 뿐이다 — 사람 지적: accuchek_instant 오른쪽 유리 여백이
        # 왼쪽의 2.8배(0.226 vs 0.081)였다.
        # 밴드 안 요소(단위·mem) 폭을 먼저 뗀다 — 실측 band_w 는 사람 라벨로
        # 단위까지 끌어안은 기기(gmate 0.995, 단위가 끝자리에 4~5px)가 있어
        # 숫자 필드가 밴드 전폭을 쓰면 단위가 들어갈 자리가 없다.
        _sl = SEG_SLANT if profile.get("italic") else 0.0
        _aux_est = max(7, int(dh * 0.17))
        _allow = 0
        _u_el = profile.get("unit")
        if (_u_el is not None and _u_el.get("pos") in (
                "right-baseline", "right-mid", "left-mid")
                and _wide_t is None and _shown("unit", _u_el["p"])):
            _uts = _u_el.get("texts") or LCD_UNITS
            _ut = _uts[zlib.crc32(pid.encode("utf-8")) % len(_uts)]
            _allow += (seg_text_width(_ut, _aux_est, _sl)
                       + int(sum(_u_el["gap"]) / 2))
        _mk_el = profile.get("mem")
        if (_mk_el is not None and _mk_el.get("pos") == "right-of-digits"
                and _shown("mem", _mk_el["p"])):
            _mt = {"mem": "mem", "memory": "memory", "M": "M"}.get(
                _mk_el.get("kind", "M"), "M")
            _allow += seg_text_width(_mt, _aux_est, _sl) + int(dh * 0.1)
        # 미터기 화살표 자리는 더 이상 떼지 않는다(2026-09-15). 화살표는 유리
        # 오른쪽 끝 트랙에 있고 숫자 옆이 아니다 — 여기서 폭을 떼면 숫자만
        # 왼쪽으로 밀리고 그만큼이 유리 오른쪽 여백으로 남는다. 겹침은
        # placer 가 막는다.
        _inner = _L["bw"] * pw - 2 * _pad_x_t - _allow
        _pr = _inner / max(1.0, dh * (slots - 1 + _g_r))
        pitch_r = min(0.85, max(0.21, _pr))
        glyph_w = int(dh * pitch_r * _g_r)
        pitch = int(dh * pitch_r)
        gap = pitch - glyph_w
        field_w = n_vis * pitch - gap
        ghost_w = lead * pitch
        field_all_w = field_w + ghost_w
    if lay is not None:
        cx = px0 + _L["cx"] * pw           # 유리 좌표계 — 이 장의 값
        # 세로형은 3분할 가운데에 앉힌다. 칼럼/행형 가로 기기는 실측 cy 그대로.
        cy = (py0 + _L["cy"] * ph) if _fam in ("column", "row") else _zone_cy
    elif _wide_t is not None:
        cx = _wide_t[2] * W
        cy = _wide_t[3] * H
    else:
        cx = rng.uniform(*g["cx"]) * W
        # cy 균등 재표본 — n=264 실측 median 0.407 이 p10~p90(0.365~0.473) 중앙
        # 0.419 와 사실상 같다. 구판의 u^1.6 좌치우침 보정은 편향 표본(median
        # 0.391)에 맞춘 것이라 뗐다(리뷰 2026-09-12 지적: median 만 맞추고 p90 를
        # 눌렀다).
        cy = rng.uniform(*g["cy"]) * H
    fx0 = int(cx - field_all_w / 2)      # 슬롯 필드 전체의 왼쪽
    y0 = int(cy - dh / 2)
    pad_x = max(6, int(dh * 0.20))
    if lay is not None:
        # 기기 고정: 밴드 박스는 실측 폭/중심(유리 안으로 클램프 — gmate 실측
        # 밴드는 유리를 0.75% 넘는다). 필드는 밴드 오른쪽에서 왼쪽으로 배치해
        # 밴드 안 요소(단위·mem) 자리(_allow)를 먼저 확보한다 — 중앙 배치면
        # 몫이 양쪽으로 갈라져 단위가 유리 밖으로 나갔다.
        _bw_eff = min(_L["bw"] * pw,
                      2 * min(cx - (px0 + 2), (px1 - 2) - cx))
        _qx0 = int(cx - _bw_eff / 2)
        _qx1 = int(cx + _bw_eff / 2)
        _u_pos = (profile.get("unit") or {}).get("pos")
        _left_allow = _allow if _u_pos == "left-mid" else 0
        fx0 = _qx0 + pad_x + _left_allow
        if _u_pos == "left-mid":
            x0 = fx0 + (ghost_w if align != "left" else 0)
        elif align != "left":
            x0 = int(_qx1 - pad_x - _allow - field_w)
        else:
            x0 = fx0
        x0 = max(fx0, x0)   # 숫자 필드가 밴드 박스 왼쪽을 못 넘게(2자리 등)
        y0 = max(py0 + 2 + pad_y, min(py1 - 2 - pad_y - dh, y0))
        quad = np.float32([[_qx0, y0 - pad_y], [_qx1, y0 - pad_y],
                           [_qx1, y0 + dh + pad_y], [_qx0, y0 + dh + pad_y]])
        # 하단행형 가로 기기(gluneo_plus 처럼 bw 가 넓은 장)는 아래 정보행
        # 코드가 qx0/qy0/qw 를 쓴다 — 기기 고정 경로에도 같은 이름을 준다.
        # 없으면 UnboundLocalError 로 죽는다(2026-09-13, 실측 분포로 bw 를
        # 흔들기 시작하면서 lay 기기도 행형에 들어갈 수 있게 됐다).
        qx0, qy0, qw = _qx0, y0 - pad_y, _qx1 - _qx0
    elif _wide_row:
        # 쿼드가 목표 폭 전체(단위·시간 포함 — 사람 라벨이 그렇게 감쌌다)
        qw = min(int(_wide_t[0] * W), px1 - px0 - 4)
        qx0 = int(max(px0 + 2, min(px1 - 2 - qw, cx - qw / 2)))
        qy0 = int(max(py0 + 2, min(py1 - 2 - band_h, cy - band_h / 2)))
        fx0 = int(max(qx0 + pad_x,
                      min(qx0 + qw - pad_x - field_all_w, cx - field_all_w / 2)))
        x0 = fx0 + (ghost_w if align != "left" else 0)
        y0 = int(max(qy0 + pad_y,
                     min(qy0 + band_h - pad_y - dh, cy - dh / 2)))
        quad = np.float32([[qx0, qy0], [qx0 + qw, qy0],
                           [qx0 + qw, qy0 + band_h], [qx0, qy0 + band_h]])
    else:
        fx0 = max(px0 + 2 + pad_x, min(px1 - 2 - pad_x - field_all_w, fx0))
        x0 = fx0 + (ghost_w if align != "left" else 0)   # 보이는 숫자줄의 왼쪽
        y0 = max(py0 + 2 + pad_y, min(py1 - 2 - pad_y - dh, y0))
        quad = np.float32([[fx0 - pad_x, y0 - pad_y],
                           [fx0 + field_all_w + pad_x, y0 - pad_y],
                           [fx0 + field_all_w + pad_x, y0 + dh + pad_y],
                           [fx0 - pad_x, y0 + dh + pad_y]])
    if lay is not None:
        # 기기 고정 레이아웃: 밴드 예약은 '보이는 숫자 필드'만 — 단위·meal·
        # 화살표는 밴드 패딩 안이 원래 자리라 쿼드 전체를 예약하면 못 들어간다.
        placer.reserve(x0, y0, x0 + field_w, y0 + dh, "band")
    else:
        placer.reserve(*(quad[0][0], quad[0][1], quad[2][0], quad[2][1]), "band")

    # ── 숫자 — DSEG, 균일 압축. 이탤릭은 폰트 변형(전역 shear 없음) ────────
    if lay is not None:
        # 세그먼트 종류도 기기 고정(사람 지침 2026-09-13) — weight 3종 중
        # 프로파일이 정한 하나. 랜덤 변형은 무명 풀(generic_v1)만.
        variant = (__import__("os").environ.get("SYNTH_FORCE_WEIGHT")
                   or lay.get("weight", "Regular"))
        if profile.get("italic"):
            variant = "Italic" if variant == "Regular" else variant + "Italic"
    else:
        variant = _pick_variant(rng, bool(profile.get("italic")))
    # 잔상 하향(2026-09-12): 2자리 값 실사진 3종(GC 녹십자 MS ONE 55 ·
    # SD CodeFree 84 · Gmate 98)에서 빈 앞칸에 아무 흔적이 없었다. 확률 0.3 ·
    # 농도 0.16 은 켜진 획과 구분이 어려울 만큼 자주·진하다.
    # 잔상은 액정 구동의 성질이라 기기 형질이다 — 같은 기기가 어떤 장만
    # 잔상이 있으면 다른 기기로 보인다.
    ghost = (ident["ghost"] if ident is not None
             else (rng.uniform(0.04, 0.11) if rng.random() < 0.15 else 0.0))
    glyph_cache = {}
    _band_clip = [0]        # 밴드 쿼드가 숫자 필드를 잘랐는가(자가검사)
    glyph_plane = np.zeros((H, W), np.uint8)
    for j in range(n_vis):
        ch = label[j]
        _draw_digit_uniform(img, x0 + j * pitch, y0, dh, ch, glyph_w,
                            ink_digit, variant, glyph_cache, plane=glyph_plane)
    for j in range(lead):               # 빈 슬롯 잔상 — 쿼드 안(필드 전체 폭)
        gx_ = x0 - (lead - j) * pitch if align != "left" \
            else x0 + field_w + j * pitch
        if align != "left" and gx_ < px0 + 2:
            continue
        if align == "left" and gx_ + glyph_w > px1 - 2:
            continue
        _draw_ghost(img, gx_, y0, dh, glyph_w, ink_digit, variant, ghost,
                    glyph_cache)

    dropped = []
    used_texts = set()   # 같은 문자열을 한 패널에 반복하지 않는다(몽타주 규칙)

    def maybe(placed, name):
        if not placed:
            dropped.append(name)
        return placed

    band_top, band_bot = y0 - pad_y, y0 + dh + pad_y
    band_l, band_r = fx0 - pad_x, fx0 + field_all_w + pad_x
    last_r = x0 + field_w

    # 보조 글자 크기 — 패널당 하나(AC#3, 카드 2026-09-13). 큰 숫자(dh)와
    # 보조(aux_h) 2종이 최대다. 실사진 722(Gmate)가 그렇다: 값·시간·단위·
    # days 줄의 보조 글자가 전부 같은 높이다. 구판은 요소별로 0.10~0.42dh
    # 여덟 종을 독립 계산해 한 패널에 4~5종이 났다(blind 8/8 지적).
    aux_h = max(7, int(dh * (0.17 if lay is not None
                             else rng.uniform(0.15, 0.19))))
    # 보조 글자의 굵기·기울기는 큰 숫자와 같은 DSEG 변형에서 파생(사람 리뷰
    # 2026-09-13: 세그먼트도 여러 종류). 한 패널 안에선 한 가지, 패널 사이엔
    # Light/Regular/Bold × 이탤릭이 섞인다(변형 분포는 _pick_variant 근거).
    aux_slant = SEG_SLANT if "Italic" in variant else 0.0
    # 보조 글자의 숫자도 큰 숫자와 같은 DSEG 변형을 쓴다 — 한 화면에 글리프
    # 체계가 둘이면 사람 눈에 바로 보인다(2026-09-13).
    _aux_cache = {}

    def _dmask(ch, hh):
        key = (ch, hh)
        if key not in _aux_cache:
            _aux_cache[key] = _glyph_mask(ch, variant, hh)
        return _aux_cache[key]

    def _dw(hh):
        m = _dmask("8", hh)
        return m.shape[1] if m is not None else None
    # 가로형 칼럼은 폭이 좁다 — 가장 긴 항목(시간 '00:00 PM')이 들어가도록
    # 보조 글자를 줄인다. 안 줄이면 단위·시간이 통째로 배치 실패로 빠져 칼럼이
    # 비어 나온다(2026-09-13 실측: UltraMini 칼럼 폭 유리의 19%).
    # 크기 종수는 늘지 않는다 — 가로형 패널의 보조 글자는 이 칼럼뿐이다.
    if _wide_t is not None and not _wide_row:
        _right_col = (fx0 + field_all_w / 2) < (px0 + px1) / 2
        _cw_est = ((px1 - 4) - (band_r + max(6, int(dh * 0.12))) if _right_col
                   else (band_l - max(6, int(dh * 0.12))) - (px0 + 4))
        if _cw_est > 20:
            # 실제로 들어갈 항목 중 가장 긴 것에 맞춘다(고정 문자열로 잡으면
            # 기기 표기가 그보다 길 때 또 탈락한다).
            _probe = [(profile.get("unit") or {}).get("texts", ["mg/dL"])[0],
                      "00-00"]
            _tf = (profile.get("time") or {}).get("fmts")
            _probe.append(_tf[0].format(h02="00", m02="00", M="0", M02="00",
                                        d="0", d02="00", am="pm", AM="PM")
                          if _tf else "00:00 PM")
            while (aux_h > 8 and max(seg_text_width(t, aux_h, aux_slant, _dw(aux_h))
                                     for t in _probe) > _cw_est):
                aux_h -= 1
    aux_t = max(2, int(round(aux_h * SEG_WEIGHTS[seg_weight_from_variant(variant)])))
    text_heights = {dh}   # 그은 글자 높이 기록(AC#3 — validate 하드 검사)

    # 기기 고정 배치 도구(2026-09-13 재구조): lay 는 요소 자리가 기기별로
    # 하나다 — place_fixed 로 두고, 밴드 아래 요소는 같은 x 구간이면 다음
    # 행으로 쌓는다(실물도 시간줄 위에 days 줄이 쌓인다).
    _below_row1 = []

    def _place(x, y, w, h, name, alts=()):
        if lay is not None:
            return placer.place_fixed(x, y, w, h, name)
        return placer.try_place(x, y, w, h, name, alternates=alts)

    def _below_y(x_, w_, near=False):
        """밴드 아래 요소의 y — 유리 '바닥'에 붙인다(사람 지적 2026-09-13:
        아래 공백이 과장 더해 40%다). 구판은 밴드 바로 밑(band_bot+4)에
        붙여서, 밴드가 화면 위쪽에 앉는 기기는 아래가 통째로 비었다.
        두 줄이 겹치면 바닥에서 위로 쌓는다 — 실물도 맨 아래줄이 바닥에
        붙고 그 위에 한 줄이 더 온다."""
        if lay is None:
            return band_bot + 4
        # near=True 는 '값 바로 아래' — 단위가 여기다. 단위는 날짜보다 혈당
        # 표시에 가까워야 한다(사람 지시 2026-09-13). 날짜·시간은 바닥이다.
        if near:
            return band_bot + max(4, int(ph * 0.02))
        _pad_b = max(4, int(ph * 0.03))
        row1 = py1 - _pad_b - aux_h
        row2 = row1 - aux_h - max(4, int(ph * 0.02))
        for bx0, bx1 in _below_row1:
            if x_ < bx1 + 6 and bx0 < x_ + w_ + 6:
                return max(band_bot + 4, row2)
        _below_row1.append((x_, x_ + w_))
        return max(band_bot + 4, row1)

    def _gx(f):
        """캔버스가 아니라 유리의 좌표계 — 구판 int(W*f) 슬롯은 마진이 깊으면
        유리 밖(드롭)으로 나갔다(2026-09-13 실측: active px0=216 vs 0.08W)."""
        return int(px0 + f * pw) if lay is not None else int(W * f)

    # ── 가로형 정보 배치 — 가로형 렌더에만(세로형 경로 무손상, AC#2) ──────
    # 실측 두 가족(정본 band.wide_raw n=39 + 눈검 9장, 2026-09-12):
    #   측면 칼럼형(27/39, band_w<0.75) — 숫자줄 옆에 단위·시간·날짜가 세로로
    #     쌓인다. 근거 951(3:47 PM·7-6·mg/dL·M)·1091(mg/dL·9:09 AM·26.5.2)·
    #     497(mg/dL 세로스택)·1590·1612(UltraMini). v0 재평가에서 검출기가 이
    #     칼럼을 숫자줄로 오인한 것이 최대 약점이었다.
    #   하단 행형(12/39, band_w>=0.75) — 숫자줄 아래 단위·시간 가로 행.
    #     근거 821(DATE·AM 1.29·12:23)·971(mg/dL·AM 9:48)·66(26·PM·12:36)·
    #     497 하단(1/10·11:38 AM).
    if _wide_t is not None:
        _uts = (profile.get("unit") or {}).get("texts") or LCD_UNITS
        _ut = _uts[zlib.crc32(pid.encode("utf-8")) % len(_uts)] \
            if (profile.get("unit") or {}).get("texts") else \
            _uts[rng.randrange(len(_uts))]
        if _wide_t[0] < 0.75:
            # 칼럼 쪽: 밴드가 유리 왼쪽에 치우쳤으면 오른쪽, 아니면 왼쪽
            _right = (fx0 + field_all_w / 2) < (px0 + px1) / 2
            _cg = max(6, int(dh * 0.12))
            if _right:
                _cx0 = min(band_r + _cg, px1 - 10)
                _cx1 = px1 - 4
            else:
                _cx0 = px0 + 4
                _cx1 = max(band_l - _cg, px0 + 10)
            _cw = _cx1 - _cx0
            if _cw > 26:
                # 칼럼 항목도 기기 고정이다 — UltraMini 8장 전부 시간·날짜·
                # 단위가 같은 자리에 쌓여 있다(1588·1590·1593·1596·1598·1602).
                # 'M'(메모리 회상)만 상태성이다.
                # 쌓는 순서는 실물대로 시간 -> 날짜 -> 단위다
                # (1588 '7:10PM / 8-20 / mg/dL', 1596·1598·1602 동일).
                _items = []
                if _shown("wide:time", 0.8):
                    _items.append(("time", _dot_time_text(
                        rng, ident["time_fmt_i"] if ident else None,
                        (profile.get("time") or {}).get("fmts"))))
                if _shown("wide:date", 0.6):
                    _items.append(("date", f"{rng.randint(1, 12)}-"
                                           f"{rng.randint(1, 31)}"))
                if _shown("wide:unit", 0.9):
                    _items.append(("unit", _ut))
                if rng.random() < (0.5 if ident is not None else 0.3):
                    _items.append(("mem", "M"))
                _cy_ = py0 + 6
                for _nm, _txt in _items:
                    _tw_ = seg_text_width(_txt, aux_h, aux_slant, _dw(aux_h))
                    if _tw_ > _cw:
                        continue
                    if maybe(placer.try_place(_cx0 + (_cw - _tw_) // 2, _cy_,
                                              _tw_, aux_h, f"wide:{_nm}"),
                             f"wide:{_nm}"):
                        _r = placer.rects[-1]
                        _lcd_text(img, _r[0], _r[1], _txt, aux_h, ink_small,
                                  "wide", heights=text_heights, thick=aux_t, slant=aux_slant,
                  digit_mask=_dmask, digit_w=_dw(aux_h))
                        used_texts.add(_txt)
                        _cy_ = _r[3] + max(6, int(dh * 0.10))
        else:
            # 하단행형 — 정보행은 쿼드 안(밴드 예약 영역)이라 Placer 없이 그린다.
            # 배치 근거: 821(DATE·AM 1.29·12:23)·971(mg/dL·AM 9:48)·
            # 66(26·PM·12:36)·497 하단(1/10·11:38 AM) — 단위 좌·시간 우.
            _ry = min(int(y0 + dh + max(4, int(dh * 0.10))),
                      int(qy0 + band_h - aux_h - 4))
            if _ry > y0 + dh - 2 and _ry + aux_h < qy0 + band_h:
                if rng.random() < 0.85:
                    _tw_ = seg_text_width(_ut, aux_h, aux_slant, _dw(aux_h))
                    if qx0 + 10 + _tw_ < fx0:
                        _lcd_text(img, qx0 + 10, _ry, _ut, aux_h, ink_small,
                                  "wide", heights=text_heights, thick=aux_t, slant=aux_slant,
                  digit_mask=_dmask, digit_w=_dw(aux_h))
                        used_texts.add(_ut)
                if rng.random() < 0.8:
                    _tt = _dot_time_text(rng)
                    _tw2 = seg_text_width(_tt, aux_h, aux_slant, _dw(aux_h))
                    _tx = int(qx0 + qw - 10 - _tw2)
                    if _tx > fx0 + field_all_w + 6:
                        _lcd_text(img, _tx, _ry, _tt, aux_h, ink_small,
                                  "wide", heights=text_heights, thick=aux_t, slant=aux_slant,
                  digit_mask=_dmask, digit_w=_dw(aux_h))
                        used_texts.add(_tt)

    # ── 액정 요소 — 전부 실폭 재서 배치, 패널 밖으로 못 나가게(AC#12) ──────
    # 가로형은 단위를 칼럼/하단행이 담당한다(위) — 프로파일 unit 요소는 세로형만.
    u = profile.get("unit")
    if u and _shown("unit", u["p"]) and _wide_t is None:
        # 단위 표기는 기기의 성질이다 — 같은 기기가 어떤 장은 mg/dL, 어떤 장은
        # mg/dl 이면 실물에 없는 변형을 가르친다(2026-09-12 정정). 프로파일이
        # 선언한 texts 를 쓰고, 여러 개면 프로파일 id 로 결정적으로 고른다.
        # 미식별 잔여 풀(generic_v1)만 전역 변형에서 뽑는다 — 그건 여러 기기를
        # 뭉뚱그린 풀이라 장마다 달라도 된다.
        _uts = u.get("texts")
        if _uts:
            ut = _uts[zlib.crc32(pid.encode("utf-8")) % len(_uts)]
        else:
            ut = LCD_UNITS[rng.randrange(len(LCD_UNITS))]
        # 높이는 aux_h 로 통일(AC#3) — 프로파일의 h_ratio 는 2종 규칙에 밀려
        # 폐기한다(실사진 722 도 단위·시간이 같은 높이다).
        uh = aux_h
        ug = int(sum(u["gap"]) / 2) if lay is not None             else int(rng.uniform(*u["gap"]))
        tw = seg_text_width(ut, uh, aux_slant)
        pos = u["pos"]
        # 단위는 혈당 값과 같은 줄에 놓이지 않는다(사람 규칙 2026-09-13,
        # raw Case 9). 근거 사진 9종 전부 숫자 '아래 오른쪽'이다 — 842(gmate)
        # ·1058(onetouch)·1911(caresens)·228(gc_ms_one)·475(acura)·267
        # (instant)·120(dorucos)·1186(performa)·1781(green_doctor).
        # 프로파일이 같은 줄 자리를 선언하면 여기서 죽는다.
        assert pos not in ("right-baseline", "right-mid", "left-mid"), \
            f"단위가 값과 같은 줄이다: {pid} pos={pos}"
        if pos == "below-right":
            # 숫자 필드 오른끝에 맞춰 값 '바로 아래'. 단위는 날짜보다 값에
            # 가깝다(사람 지시 2026-09-13).
            _ux = max(px0 + 2, min(px1 - 2 - tw, last_r - tw))
            cands = [(_ux, _below_y(_ux, tw, near=True)),
                     (px1 - 2 - tw, _below_y(px1 - 2 - tw, tw, near=True))]
        elif pos == "right-baseline":
            cands = [(last_r + ug, y0 + dh - uh), (last_r + ug, y0 + (dh - uh) // 2)]
        elif pos == "right-mid":
            cands = [(last_r + ug, y0 + (dh - uh) // 2), (last_r + ug, band_bot + 4)]
        elif pos == "left-mid":
            cands = [(x0 - ug - tw, y0 + (dh - uh) // 2),
                     (px0 + 2, band_bot + 4)]
        elif pos == "above-right":
            cands = [(last_r - tw, max(py0 + 2, band_top - uh - 4)),
                     (last_r - tw, py0 + 2)]
        else:  # below
            _ux0 = _gx(0.4)
            cands = [(_ux0, _below_y(_ux0, tw)), (px0 + 2, band_bot + 4)]
        if lay is None:
            cands = cands + [(px0 + 2, band_bot + 4), (px1 - 2 - tw, band_bot + 4)]
        if maybe(_place(cands[0][0], cands[0][1], tw, uh + 2, "unit",
                        alts=cands[1:]), "unit"):
            r = placer.rects[-1]
            _lcd_text(img, r[0], r[1], ut, uh, ink_small, "unit",
                      heights=text_heights, thick=aux_t, slant=aux_slant,
                  digit_mask=_dmask, digit_w=_dw(aux_h))
            used_texts.add(ut)

    meal = profile.get("meal")
    if meal and _shown("meal", meal["p"]):
        mt = meal["texts"][rng.randrange(len(meal["texts"]))]
        tw = seg_text_width(mt, aux_h, aux_slant, _dw(aux_h))
        if maybe(_place(last_r + int(dh * 0.1), band_bot - aux_h, tw,
                        aux_h + 2, "meal",
                        alts=((px1 - 2 - tw, band_bot - aux_h),)), "meal"):
            r = placer.rects[-1]
            _lcd_text(img, r[0], r[1], mt, aux_h, ink_small, "meal",
                      heights=text_heights, thick=aux_t, slant=aux_slant,
                  digit_mask=_dmask, digit_w=_dw(aux_h))
            used_texts.add(mt)

    # 메모리 표기(mem/memory/M)는 한 기기에 한 종류다 — 문자열이 달라도 같은
    # 라벨 부류이므로 하나를 쓰면 부류 전체를 소진 처리한다. used_texts 가
    # 문자열 단위라 이 처리를 빼면 mem 과 memory 가 한 화면에 같이 뜬다
    # (2026-09-12 montage_fix3 실측 — 12장 중 5장).
    mk = profile.get("mem")
    if mk and _shown("mem", mk["p"]):
        mh = aux_h
        mtxt = {"mem": "mem", "memory": "memory", "M": "M"}.get(mk["kind"], "M")
        mtw = seg_text_width(mtxt, mh, aux_slant)
        if mk["pos"] == "top-left":
            cands = ((_gx(0.06), py0 + 4), (_gx(0.08), band_top - mh - 4))
        elif mk["pos"] == "top-right":
            cands = ((_gx(0.6), py0 + 4), (_gx(0.6), band_top - mh - 4))
        elif mk["pos"] == "below-left":
            _mx0 = _gx(0.06)
            cands = ((_mx0, _below_y(_mx0, mtw)), (_mx0, py1 - 2 - mh))
        else:  # right-of-digits
            cands = ((last_r + int(glyph_w * 0.4), y0 + (dh - mh) // 2),
                     (last_r + int(glyph_w * 0.4), py0 + 4))
        cands = [(cx_, cy_) for cx_, cy_ in cands]
        if maybe(_place(cands[0][0], cands[0][1], mtw, mh, "mem",
                        alts=cands[1:]), "mem"):
            r = placer.rects[-1]
            if mk["kind"] == "M-box":
                # 상자 폭은 실제 그은 폭(seg_text_width) 기준 — 구판 mh+2 는
                # 'M' 진폭(셀+간격)보다 좁아 글자가 상자를 뚫었다.
                cv2.rectangle(img, (r[0] - 2, r[1]),
                              (r[0] + seg_text_width("M", mh, aux_slant) + 2,
                               r[3]), ink_small, 1)
                _lcd_text(img, r[0], r[1], "M", mh, ink_small, "mem",
                          heights=text_heights, thick=aux_t, slant=aux_slant,
                  digit_mask=_dmask, digit_w=_dw(aux_h))
                used_texts |= _MEM_VARIANTS
            else:
                t = {"mem": "mem", "memory": "memory", "M": "M"}.get(
                    mk["kind"], "M")
                _lcd_text(img, r[0], r[1], t, mh, ink_small, "mem",
                          heights=text_heights, thick=aux_t, slant=aux_slant,
                  digit_mask=_dmask, digit_w=_dw(aux_h))
                used_texts |= _MEM_VARIANTS

    gl = profile.get("glulabel")
    if gl and _shown("glulabel", gl.get("p", 0)):
        gtw = seg_text_width("GLU", aux_h, aux_slant, _dw(aux_h))
        if maybe(_place(x0, max(py0 + 2, band_top - aux_h - 4), gtw, aux_h,
                        "glulabel", alts=((x0, band_bot + 4),)), "glulabel"):
            r = placer.rects[-1]
            _lcd_text(img, r[0], r[1], "GLU", aux_h, ink_small, "glulabel",
                      heights=text_heights, thick=aux_t, slant=aux_slant,
                  digit_mask=_dmask, digit_w=_dw(aux_h))
            used_texts.add("GLU")

    a = profile.get("arrow")
    if a and _shown("meter_arrow" if profile.get("meter") else "arrow",
                    a["p"]):
        # 1판에서 320px 용 size(18~30) 를 패널 배율로 곧이곧대로 키운 실수 대신,
        # 글리프 높이 비율로 잡는다 — 실관찰상 화살표는 숫자 높이의 2~3할.
        # 크기를 줄였다(사람 지시 2026-09-13) — 구판 0.24·dh 는 실물보다
        # 컸다. 실물 Instant 의 ▶ 는 숫자 높이의 1.5할쯤이다.
        s = max(6, int(dh * (0.15 if lay is not None
                             else rng.uniform(0.12, 0.20))))
        kinds = [k for k in a["kinds"] if k in LCD_ICONS]
        # 화살표-숫자 간격도 기기의 자리다(구판은 렌더마다 흔들렸다).
        ag = int((sum(a["gap"]) / 2 if ident is not None
                  else rng.uniform(*a["gap"])) * max(1, dh / 56.0))
        # lay 예약박스는 삼각형 잉크 폭(s) — 2s 박스로 잡으면 밴드 필드에
        # 걸려 하드 검사(overlaps)가 허위 양성을 낸다(실측 2026-09-13).
        _ab = s if lay is not None else 2 * s
        if profile.get("meter"):
            # 미터기 지시 화살표(AC#5): 세로 위치는 혈당값에 대응한다. 실측
            # Instant 34장(값 100~511, 2026-09-13 눈검 inst_all 시트): v100
            # 하단 · v119 하중단 · v123~126 중앙 · v131~135 중상단 · v141~150
            # 상단 상승 · v159+ 상단 포화. y=clamp((v-95)/70, 0, 1) (1=위)이
            # 34장 전부와 어울린다. 후보를 떠다니게 하지 않는다(구판 결함).
            yf = min(1.0, max(0.0, (value - 95) / 70.0))
            ay = int(py0 + 0.10 * (py1 - py0)
                     + (1.0 - yf) * 0.72 * (py1 - py0) - _ab // 2)
            cands = [(px1 - 2 - _ab, ay)]
        else:
            # 오른쪽으로 한정한다(사람 지시 2026-09-13). 구판은 왼쪽·아래까지
            # 후보로 두어 같은 기기에서 화살표가 돌아다녔다.
            ay = y0 + int(dh * 0.30)
            cands = [(last_r + ag, ay), (px1 - 2 - _ab, ay),
                     (px1 - 2 - _ab, band_top - _ab - 4)]
        if maybe(_place(cands[0][0], cands[0][1], _ab, _ab, "arrow",
                        alts=cands[1:]), "arrow"):
            r = placer.rects[-1]
            _icon(img, kinds[0] if ident is not None
                  else kinds[rng.randrange(len(kinds))],
                  (r[0] + r[2]) // 2, (r[1] + r[3]) // 2, s, ink_small)

    for kind, pos, p in profile.get("icons", []):
        # 구판은 lay·p>=0.85 에서 `rng.random() > 0.0` 이라 아이콘을 늘
        # 건너뛰었다(항상 그리려던 의도의 반대). _shown 이 그 자리다.
        if kind not in LCD_ICONS or not _shown(f"icon:{kind}", p):
            continue
        s = max(8, int(dh * (0.34 if lay is not None
                             else rng.uniform(0.28, 0.4))))
        # lay 예약박스는 잉크 폭(s) — 2s 박스는 밴드/이웃과 허위 겹침(arrow 와
        # 같은 사유). 중심은 구판 자리 그대로. right-mid 는 숫자 필드 오른쪽
        # 남은 띠에 맞게 크기를 줄인다 — 밴드가 유리의 9할을 쓰는 기기
        # (caresens 0.918·green_doctor 0.919)의 플래그는 실물도 가장자리에
        # 작게 붙는다.
        _ib = s if lay is not None else 2 * s
        if lay is not None and pos in ("right-mid", "right-of-digits"):
            # 오른쪽 끝에 붙인다 — 크기는 숫자 필드 오른쪽 남은 폭이 정한다.
            _avail = max(0, px1 - 4 - (x0 + field_w))
            _ib = min(_ib, max(10, int(_avail)))
            s = _ib
            cands = ((px1 - 2 - _ib, y0 + int(dh * 0.45) - _ib // 2),)
            _placed = _place(cands[0][0], cands[0][1], _ib, _ib,
                             f"icon:{kind}")
            if _placed:
                r = placer.rects[-1]
                _icon(img, kind, (r[0] + r[2]) // 2, (r[1] + r[3]) // 2, s,
                      ink_small, pos=pos)
            maybe(_placed, f"icon:{kind}")
            continue
        _sh = (2 * s - _ib) // 2
        if pos == "top-right":
            cands = ((px1 - 2 - 2 * s + _sh, py0 + 2),
                     (px1 - 2 - 2 * s, band_top - 2 * s - 4))
        elif pos == "top-left":
            cands = ((px0 + 2, py0 + 2), (px0 + 2, band_top - 2 * s - 4))
        else:  # right-mid
            cands = ((px1 - 2 - 2 * s + _sh, y0 + int(dh * 0.45) + _sh),
                     (px1 - 2 - 2 * s, band_bot + 4))
        if maybe(_place(cands[0][0], cands[0][1], _ib, _ib,
                        f"icon:{kind}", alts=cands[1:]), f"icon:{kind}"):
            r = placer.rects[-1]
            _icon(img, kind, (r[0] + r[2]) // 2, (r[1] + r[3]) // 2, s,
                  ink_small, pos=pos)

    # 도트매트릭스 줄은 실제로 도트 패널인 기기만(AC#1) — dorucos_premium
    # (dot_panel, 근거 120·694·695). 다른 프로파일의 dotrow_* 요소는 실사진이
    # 세그먼트라(228·800·1903·1911 확인, 2026-09-13) 세그먼트로 그린다.
    _dotp = bool(profile.get("dot_panel"))
    da = profile.get("dotrow_above")
    if da and _shown("dotrow_above", da["p"]):
        txt = da["texts"][(ident["dotrow_i"] if ident is not None
                           else rng.randrange(8)) % len(da["texts"])]
        if _dotp:
            glyph = max(3, (aux_h - 4) // 2)
            wpx = int(len(txt) * glyph * 1.2)
            hpx = glyph * 2 + 4
        else:
            glyph = None
            wpx = seg_text_width(txt, aux_h, aux_slant, _dw(aux_h))
            hpx = aux_h
        _da0 = _gx(0.06)
        if maybe(_place(_da0, py0 + 2, wpx, hpx, "dotrow_above"),
                 "dotrow_above"):
            r = placer.rects[-1]
            if _dotp:
                dot_text(img, r[0], r[1], txt, glyph, ink_small)
            else:
                _lcd_text(img, r[0], r[1], txt, aux_h, ink_small,
                          "dotrow_above", heights=text_heights, thick=aux_t, slant=aux_slant,
                  digit_mask=_dmask, digit_w=_dw(aux_h))
            used_texts.add(txt)
    db = profile.get("dotrow_below")
    if db and _shown("dotrow_below", db["p"]):
        txt = _dot_time_text(rng, ident["time_fmt_i"] if ident else None,
                             db.get("fmts"))
        if _dotp:
            glyph = max(3, (aux_h - 4) // 2)
            wpx = int(len(txt) * glyph * 1.2)
            hpx = glyph * 2 + 4
        else:
            glyph = None
            wpx = seg_text_width(txt, aux_h, aux_slant, _dw(aux_h))
            hpx = aux_h
        _db0 = _gx(0.06)
        if maybe(_place(_db0, _below_y(_db0, wpx), wpx, hpx,
                        "dotrow_below"), "dotrow_below"):
            r = placer.rects[-1]
            if _dotp:
                dot_text(img, r[0], r[1], txt, glyph, ink_small)
            else:
                _lcd_text(img, r[0], r[1], txt, aux_h, ink_small,
                          "dotrow_below", heights=text_heights, thick=aux_t, slant=aux_slant,
                  digit_mask=_dmask, digit_w=_dw(aux_h))
            used_texts.add(txt)

    t = profile.get("time")
    # 가로형은 시간·날짜·단위를 칼럼/하단행이 이미 그렸다(위) — 여기서 또
    # 그리려다 배치에 실패하고 'time' 이 뺀 요소로 잡혔다(2026-09-13, n=150
    # 에서 8건). 단위(unit)와 같은 규칙으로 세로형에만 건다.
    if t and _wide_t is None and _shown("time", t["p"]):
        # 시간줄도 보조 글자 크기(AC#3 — 실사진 722 는 시간·단위가 같은 높이).
        # 7-세그 + 사각 점 콜론으로 그은다(구판 put_7seg_text 는 폭을 임의
        # 폭으로 늘려 숫자 비율이 깨졌다 — seg_text 는 글리프 비율 유지).
        hh = f"{rng.randint(0, 23):02d}:{rng.randint(0, 59):02d}"
        tw = seg_text_width(hh, aux_h, aux_slant, _dw(aux_h))
        if t["pos"] == "below-right":
            cands = ((_gx(0.55), band_bot + 4), (px1 - 2 - tw, band_bot + 4))
        else:
            cands = ((_gx(0.08), band_bot + 4), (px0 + 2, py1 - 2 - aux_h))
        _tx0, _ty0 = cands[0]
        if lay is not None:
            _ty0 = _below_y(_tx0, tw)
        if maybe(_place(_tx0, _ty0, tw, aux_h, "time", alts=cands[1:]), "time"):
            r = placer.rects[-1]
            _lcd_text(img, r[0], r[1], hh, aux_h, ink_small, "time",
                      heights=text_heights, thick=aux_t, slant=aux_slant,
                  digit_mask=_dmask, digit_w=_dw(aux_h))

    _avp = profile.get("avgrow", {}).get("p", 0)
    if _avp and _shown("avgrow", _avp):
        txt = f"{rng.choice(['7', '14'])} DAY AVG"
        num = f"{rng.randint(1, 999):03d}"
        tw = seg_text_width(txt + "  " + num, aux_h, aux_slant, _dw(aux_h))
        _ax0 = _gx(0.08)
        if maybe(_place(_ax0, _below_y(_ax0, tw), tw, aux_h + 2, "avgrow"),
                 "avgrow"):
            r = placer.rects[-1]
            w1 = _lcd_text(img, r[0], r[1], txt, aux_h, ink_small, "avgrow",
                           heights=text_heights, thick=aux_t, slant=aux_slant,
                  digit_mask=_dmask, digit_w=_dw(aux_h))
            _lcd_text(img, r[0] + w1 + max(2, aux_h // 3), r[1], num, aux_h,
                      ink_small, "avgrow", heights=text_heights, thick=aux_t, slant=aux_slant,
                  digit_mask=_dmask, digit_w=_dw(aux_h))
            used_texts.add(txt)

    _dtp = profile.get("daterow", {}).get("p", 0)
    if _dtp and _shown("daterow", _dtp):
        # '#기록번호' 는 뺐다 — 사람이 실물에서 본 적 없다고 했다(2026-09-13).
        txt = f"{rng.randint(1, 12)}-{rng.randint(1, 31)}"
        tw = seg_text_width(txt, aux_h, aux_slant, _dw(aux_h))
        _dx0 = _gx(0.06)
        if maybe(_place(_dx0, _below_y(_dx0, tw), tw, aux_h + 2, "daterow"),
                 "daterow"):
            r = placer.rects[-1]
            _lcd_text(img, r[0], r[1], txt, aux_h, ink_small, "daterow",
                      heights=text_heights, thick=aux_t, slant=aux_slant,
                  digit_mask=_dmask, digit_w=_dw(aux_h))
            used_texts.add(txt)

    # 밀도 채움 블록은 지웠다(2026-09-13, 사람 지시). 실사진 엣지 밀도는
    # 조도·광원·그림자가 크게 좌우하는 값이라 합성의 목표로 쓸 수 없다 —
    # 목표로 쓰면 렌더러가 조명 때문에 생긴 숫자를 '내용'으로 맞추려 들고,
    # 근거 없는 도트줄·mem·아이콘을 화면에 채워 넣는다. 화면에 무엇이 있는지는
    # 기기가 정한다. 밀도는 렌더 뒤에 재서 보고만 한다(manifest.density).

    # ── 밴드 쿼드를 실제로 그려진 것에서 다시 만든다 (2026-09-14) ──────────
    # 그 전에는 쿼드 폭을 실측 분포(_L["bw"])에서 먼저 뽑고 숫자를 그 안에
    # 오른쪽 정렬로 끼워 넣었다. 그래서 쿼드와 내용이 어긋날 수 있었고,
    # _allow(단위·mem·화살표 자리)를 프로파일 '선언' 기준으로 떼어 놓은 탓에
    # 그 요소가 이 장에 안 그려지면 오른쪽에 빈 자리가 남았다. 그 빈 자리가
    # 그대로 정답이 되어 "저기까지가 숫자줄이다" 를 가르쳤다.
    #   측정(40k): 오른쪽 여백/밴드높이 median
    #     onetouch_ultramini 0.461 · caresens_n_premier 0.443 · accuchek_instant 0.397
    #     나머지 11종 0.13~0.19 (= pad_x, 좌우 대칭이라 정상)
    # 이제 순서를 뒤집는다 — 다 그린 뒤에 그린 것을 감싼다. 여백은 좌우 대칭
    # 패딩 하나뿐이고, 예약해 놓고 안 쓴 자리는 쿼드에 들어오지 않는다.
    #
    # 감싸는 것: 슬롯 필드 전체(빈 앞자리 포함 — 사람 라벨 규약과 같다) +
    # 밴드 줄에 실제로 놓인 요소(단위·mem·meal·화살표). '밴드 줄'은 세로
    # 중심이 숫자 높이 안에 든 것으로 판정한다 — 아래 정보줄을 끌어들이지 않는다.
    # 슬롯 필드는 **실제로 숫자가 놓인 x0** 에서 잡는다. fx0 를 쓰면 안 된다 —
    # fx0 는 옛 밴드(_bw_eff)의 왼쪽 + 패딩이라 숫자가 어디 놓였는지와 무관하고,
    # 그걸 기준으로 삼으면 옛 밴드의 남는 폭을 그대로 물려받는다(2026-09-15,
    # 사람 지적: acura_plus · caresens_n_premier · accuchek_instant ·
    # wide_unknown · onetouch_ultramini 에서 우측 여백이 그대로였다).
    # 빈 슬롯(ghost_w)은 정렬 방향의 반대편에 붙는다 — 오른쪽 정렬이면 왼쪽에.
    if align != "left":
        _bx0, _bx1 = float(x0 - ghost_w), float(x0 + field_w)
    else:
        _bx0, _bx1 = float(x0), float(x0 + field_w + ghost_w)
    _by0, _by1 = float(y0), float(y0 + dh)
    # 세로로 겹친다고 다 넣으면 안 된다 — 미터기 화살표는 유리 오른쪽 끝
    # '트랙'에 있는 지시자라 숫자줄에서 멀리 떨어져 있는데, 세로 중심만 보면
    # 밴드 줄에 든 것으로 잡혀 그 사이 빈 공간까지 통째로 삼킨다
    # (2026-09-15 사람 지적: accuchek_instant, 유리 오른쪽 여백이 왼쪽의
    # 2.7배). 그래서 **가로로 붙어 있는 것만** 넣는다.
    # 화살표는 아예 넣지 않는다(2026-09-15). 거리 조건(dh*0.6)으로 걸러 봤지만
    # accuchek_instant 처럼 트랙이 숫자에 가까운 기기에서는 여전히 들어왔다.
    # 화살표는 값을 가리키는 **지시자**이지 숫자줄의 일부가 아니다 — 거리로
    # 판정할 일이 아니라 종류로 뺄 일이었다.
    # 밴드는 **숫자줄**이다. 단위·M·식사표시는 넣지 않는다(2026-09-15).
    # 넣어 봤더니 M 이 숫자 옆에 있는 기기에서 쿼드가 M 까지 감쌌고, 사람이
    # "단위는 딴 데 두고 M 만 숫자 옆? 넌센스" 라고 지적했다. 무엇을 넣을지
    # 거리로 판정하려던 것부터가 틀렸다 — 규약이 '숫자줄' 하나면 규칙도 하나다.
    # 규약을 '숫자+단위' 로 바꾸기로 하면 여기 한 줄만 되살리면 된다.
    # 유리로 클램프하되 **패딩만** 줄인다. 내용 경계를 넘어 자르면 안 된다 —
    # 숫자가 유리 가장자리에 가까운 기기에서 밴드가 숫자를 잘라 먹는다
    # (2026-09-15 사람 지적: caresens_n_premier · accuchek_instant ·
    # acura_plus). min(_b*, ...) 이 그 하한을 지킨다.
    # 밴드 = **슬롯 필드**다. 잉크가 아니라 칸이 기준이다(사람 지침 2026-09-15:
    # "7-seg 니까 왼쪽이 1로 시작하면 여백을 충분히 줘야지. 반대로 오른쪽 끝
    # 숫자는 여백이 너무 크면 안 된다"). 앞자리가 1이면 칸은 그대로 있고 잉크만
    # 좁다 — 잉크에 맞추면 그 칸이 사라진다.
    #
    # 좌우 패딩은 붙이지 않는다. 슬롯 필드의 양 끝이 곧 밴드의 양 끝이다.
    # (전에는 pad_x 를 덧붙여 오른쪽 끝에 없는 여백이 생겼다.)
    _qx0, _qx1 = _bx0, _bx1
    _qy0, _qy1 = _by0, _by1
    # 캔버스 밖으로는 못 나간다(쿼드 어서션이 뒤에서 잡는다).
    _qx0 = max(0.0, _qx0); _qy0 = max(0.0, _qy0)
    _qx1 = min(float(W - 1), _qx1); _qy1 = min(float(H - 1), _qy1)
    if _qx1 - _qx0 >= 8 and _qy1 - _qy0 >= 8:
        quad = np.float32([[_qx0, _qy0], [_qx1, _qy0],
                           [_qx1, _qy1], [_qx0, _qy1]])
        # 자가검사: 밴드 쿼드는 숫자 필드를 통째로 담아야 한다. 사람이 눈으로
        # 찾아야 했던 결함이라 여기서 센다 — generate() 가 합계를 인쇄한다.
        if not (_qx0 <= _bx0 + 0.5 and _qx1 >= _bx1 - 0.5
                and _qy0 <= _by0 + 0.5 and _qy1 >= _by1 - 0.5):
            _band_clip[0] += 1

    # ── 광학 — 노이즈·블러·명암·비네팅·국소 그림자·연한 반사패치(결함 (7)) ──
    # 광학 노이즈도 넘겨받은 rng 에서 파생시킨다 — np.random 전역을 쓰면
    # 호출자가 np.random.seed 를 부른 경우에만 재현되고, 그렇지 않은 경로
    # (synth_panel.py gen)는 같은 시드로도 매번 다른 그림을 낸다(2026-09-13
    # 전수 검토). 렌더러 비결정성 카드의 나머지 갈래다.
    _npr = np.random.default_rng(rng.getrandbits(63))
    img = np.clip(img.astype(np.float32)
                  + _npr.normal(0, rng.uniform(2, 9), img.shape),
                  0, 255).astype(np.uint8)
    if rng.random() < 0.4:
        img = cv2.GaussianBlur(img, (3, 3), rng.uniform(0.3, 1.0))
    if rng.random() < 0.3:
        img = cv2.GaussianBlur(img, (5, 5), rng.uniform(0.5, 1.2))
    a_, b_ = rng.uniform(0.75, 1.25), rng.uniform(-25, 25)
    img = np.clip(img.astype(np.float32) * a_ + b_, 0, 255).astype(np.uint8)
    yy, xx = np.mgrid[0:H, 0:W]
    d2 = ((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 2)) ** 2
    img = np.clip(img.astype(np.float32) * (1.0 - rng.uniform(0.08, 0.22) * d2),
                  0, 255).astype(np.uint8)
    if rng.random() < 0.35:
        img = add_local_shadow(img, rng)
    # 개수도 줄인다(2026-09-12): 크기만 줄였더니 작은 얼룩이 서너 개 겹쳐
    # 실물에 없는 반점 무늬가 됐다. 대부분 0~1개, 가끔 2개.
    for _ in range(rng.choice([0, 0, 1, 1, 1, 2])):
        # 가장자리에 붙은 연한 타원 반사 — 전폭 강선은 폐지했다(1판 결함 (7)).
        edge = rng.randrange(4)
        if edge == 0:
            ecx, ecy = rng.uniform(0, W), rng.uniform(0, H * 0.2)
        elif edge == 1:
            ecx, ecy = rng.uniform(0, W), rng.uniform(H * 0.8, H)
        elif edge == 2:
            ecx, ecy = rng.uniform(0, W * 0.2), rng.uniform(0, H)
        else:
            ecx, ecy = rng.uniform(W * 0.8, W), rng.uniform(0, H)
        # 반장축 0.38W 는 패널 폭의 76%를 덮는다 — 패치가 아니라 도포다.
        # 1판의 '대각선 흰 줄' 을 없앴더니 이번엔 넓은 쐐기가 됐다(2026-09-12).
        ax_ = rng.uniform(0.05, 0.20) * W
        ay_ = rng.uniform(0.04, 0.15) * H
        # 몸체 위 반사는 몸체 톤 기준 — 타원 중심 픽셀에서 시작한다(구판은
        # 패널색 고정이라 어두운 몸체에 하얀 도포가 얹혔다).
        gc_y = min(H - 1, max(0, int(ecy)))
        gc_x = min(W - 1, max(0, int(ecx)))
        glare = min(255, int(img[gc_y, gc_x]) + rng.uniform(40, 90))
        msk = np.zeros((H, W), np.float32)
        cv2.ellipse(msk, (int(ecx), int(ecy)), (int(ax_), int(ay_)),
                    rng.uniform(0, 180), 0, 360, 1, -1)
        msk *= rng.uniform(0.08, 0.22)
        img = np.clip(img.astype(np.float32) * (1 - msk) + glare * msk,
                      0, 255).astype(np.uint8)

    # ── 기하: 키스톤 -> 회전, 이미지와 쿼드·글리프 마스크가 같은 행렬을
    #    같은 순서로 통과한다(AC#3·#8). 전역 shear 는 없다 — 카메라가 평면을
    #    찍으면 사다리꼴이지 평행사변형이 아니다. 쿼드(점 집합)는 이미지 워프와
    #    수학적으로 같은 변환의 점 전용 경로(perspectiveTransform·transform)로
    #    돌린다 — 이미지 워프 함수에 점을 넣는 것은 값/좌표 혼동이다.
    quad0 = quad.copy()
    gp0 = glyph_plane.copy()
    pre = img.copy()
    fillc = int(body_col)   # 워프 경계색 — 몸체 톤(구판 베젤 링 잔여)
    do_key = rng.random() < 0.35
    fx = [rng.uniform(0, 0.05) for _ in range(4)]
    fy = [rng.uniform(0, 0.05) for _ in range(4)]
    do_rot = rng.random() < 0.7
    ang = rng.uniform(-1.5, 1.5)
    src = np.float32([[0, 0], [W - 1, 0], [W - 1, H - 1], [0, H - 1]])

    def _mats(shrink):
        Mk = Mr = None
        if do_key and shrink > 0:
            dst = np.float32([
                [fx[0] * shrink * W, fy[0] * shrink * H],
                [(W - 1) - fx[1] * shrink * W, fy[1] * shrink * H],
                [(W - 1) - fx[2] * shrink * W, (H - 1) - fy[2] * shrink * H],
                [fx[3] * shrink * W, (H - 1) - fy[3] * shrink * H],
            ])
            Mk = cv2.getPerspectiveTransform(src, dst)
        if do_rot and shrink > 0:
            Mr = cv2.getRotationMatrix2D((W / 2, H / 2), ang * shrink, 1.0)
        return Mk, Mr

    def _warp_img(im, interp, Mk, Mr, border=None):
        # border=None 이면 이미지용 몸체 톤(fillc). 글리프 평면은 0 을 넘겨야
        # 한다 — 몸체색이 127 을 넘는 패널에서 마스크 경계가 sel 로 뒤집혀
        # glyph_plane_check 가 붕괴했다(2026-09-12, check 0.15, sel 9.4만px).
        # 구판은 베젤색 40~90 이 항상 127 밑이라 우연히 안 터졌다.
        bv = fillc if border is None else border
        out = im
        if Mk is not None:
            out = cv2.warpPerspective(out, Mk, (W, H), flags=interp,
                                      borderMode=cv2.BORDER_CONSTANT,
                                      borderValue=bv)
        if Mr is not None:
            out = cv2.warpAffine(out, Mr, (W, H), flags=interp,
                                 borderMode=cv2.BORDER_CONSTANT,
                                 borderValue=bv)
        return out

    def _warp_pts(q, Mk, Mr):
        out = q.reshape(-1, 1, 2).astype(np.float32)
        if Mk is not None:
            out = cv2.perspectiveTransform(out, Mk)
        if Mr is not None:
            out = cv2.transform(out, Mr)
        return out.reshape(-1, 2)

    def _in(q):
        return (q[:, 0].min() >= 0 and q[:, 0].max() <= W - 1
                and q[:, 1].min() >= 0 and q[:, 1].max() <= H - 1)

    quad = quad0
    Mk = Mr = None
    for shrink in (1.0, 0.5, 0.25, 0.0):
        Mk, Mr = _mats(shrink)
        quad = _warp_pts(quad0, Mk, Mr)
        if _in(quad):
            img = _warp_img(pre, cv2.INTER_LINEAR, Mk, Mr)
            break
    glyph_warped = _warp_img(gp0, cv2.INTER_NEAREST, Mk, Mr, border=0)
    # 유리(=실사진의 GM 화면 쿼드에 해당) 도 같은 행렬을 통과시킨다. 리더
    # 프레이밍이 이 쿼드에서 나온다 — 실사진 팔은 GM 쿼드 + BOX_MARGIN 이고
    # 합성도 같아야 한다(reader_onnx_spec.md 프레임 조립).
    glass_quad = _warp_pts(
        np.float32([[px0, py0], [px1, py0], [px1, py1], [px0, py1]]), Mk, Mr)

    # 글리프 평면 자가검사(AC#8) — 점수 계산과 bg·문턱 선정 이력은
    # glyph_plane_score / _gpc_bg_contrast 안에 있다. bg 후보 셋 다 결함이
    # 있었다(2026-09-12): 전체 중앙값은 몸체가 절반을 차지한 뒤 몸체 톤
    # (p10 0.99→0.56), 워프 전 유리 좌표는 회전·키스톤 장에서 몸체를 집고,
    # 쿼드 안 중앙값은 대형 숫자 패널에서 숫자 톤에 떨어진다(panel_31000_
    # 149, 반전·check 0.088). 쿼드 '바깥 유리'가 정답이다.
    if glyph_warped.max() > 0:
        gpc = glyph_plane_score(img, quad, glyph_warped,
                                (px0, py0, px1, py1))
    else:
        gpc = 0.0

    dens = _density_outside(img, quad)
    return dict(panel=img, quad=np.asarray(quad, np.float32), label=label,
                band_clip=int(_band_clip[0]),
                glass_quad=np.asarray(glass_quad, np.float32),
                rects=placer.rects, dropped=dropped, wh=W / H, W=W, H=H,
                profile=pid, inverted=bool(inverted),
                glyph_plane_check=round(gpc, 4),
                glyph_warped=glyph_warped,
                density=dens if dens is not None else 0.0,
                bezel=body_text, margin=max(mg_t, mg_b, mg_l, mg_r),
                margins=[mg_t, mg_b, mg_l, mg_r],
                text_heights=sorted(text_heights))


def _density_outside(img, quad):
    q = np.asarray(quad, np.float64)
    H, W = img.shape[:2]
    return edge_density_outside(
        img, (q[:, 0].min() / W, q[:, 1].min() / H,
              q[:, 0].max() / W, q[:, 1].max() / H), exclude_frame=0.03)


def reader_view(sample):
    """리더 입력(320x160). 실사진 팔과 **같은 자**로 만든다 —
    build_cache_v2.framed_src_rect(GM 쿼드의 축정렬 박스를 BOX_MARGIN 10% 로
    사방 확장) -> 원근 워프. 정본은 reader_onnx_spec.md '프레임 조립'이다.

    2026-09-13 정정: 구판은 패널 캔버스 '전체'를 워프했다. 그런데 합성 캔버스의
    몸체 마진은 기기 형질이라 사방 1~15% 로 제각각이고, 실사진 팔은 언제나
    10% 다. 학습-추론 전처리가 갈라지면 그 자체가 성능 저하다(spec 3항).
    기하 구현을 여기서 다시 짜지 않는다 — 같은 함수를 부른다
    (antipatterns/duplicated-geometry-implementation).
    """
    img = sample["panel"]
    src = framed_src_rect(img, sample["glass_quad"])
    dst = np.float32([[0, 0], [IN_W - 1, 0], [IN_W - 1, IN_H - 1],
                      [0, IN_H - 1]])
    Mp = cv2.getPerspectiveTransform(src, dst)
    warped = cv2.warpPerspective(img, Mp, (IN_W, IN_H))
    rq = cv2.perspectiveTransform(sample["quad"][None, :, :], Mp)[0]
    return warped, np.asarray(rq, np.float32)


def generate(count, seed0, out_dir, with_reader=False):
    out = Path(out_dir)
    (out / "images").mkdir(parents=True, exist_ok=True)
    rng = random.Random(seed0)
    manifest = []
    viol_total = 0
    clip_total = 0          # 밴드 쿼드가 숫자 필드를 자른 장 수(자가검사)
    for i in range(count):
        val = sample_value(rng)
        s = render_panel(val, rng)
        name = f"panel_{seed0}_{i}"
        cv2.imwrite(str(out / "images" / f"{name}.png"), s["panel"])
        q = np.round(s["quad"], 2)
        assert q[:, 0].min() >= 0 and q[:, 0].max() <= s["W"] - 1, \
            f"쿼드가 캔버스 밖: {name}"
        assert q[:, 1].min() >= 0 and q[:, 1].max() <= s["H"] - 1, \
            f"쿼드가 캔버스 밖: {name}"
        assert s["label"].isdigit()
        viol = _count_overlaps(s["rects"])
        viol_total += viol
        clip_total += int(s.get("band_clip", 0))
        rec = dict(
            id=name, profile=s["profile"], w=s["W"], h=s["H"],
            wh=round(s["wh"], 4), quad=q.tolist(), label=s["label"],
            # 유리 쿼드 — 리더 프레이밍의 입력(실사진의 GM 쿼드에 해당).
            glass_quad=np.round(s["glass_quad"], 2).tolist(),
            inverted=s["inverted"], glyph_plane_check=s["glyph_plane_check"],
            text_heights=s["text_heights"],
            density=round(float(s["density"]), 5),
            rects=[[round(float(v), 1) for v in r[:4]] + [r[4]]
                   for r in s["rects"]],
            dropped=s["dropped"], overlaps=viol,
            margin=s["margin"],
            margins=s["margins"],
        )
        if s["bezel"]:
            rec["bezel"] = s["bezel"]
        if with_reader:
            rv, rq = reader_view(s)
            (out / "reader").mkdir(exist_ok=True)
            cv2.imwrite(str(out / "reader" / f"{name}.png"), rv)
            rec["quad_reader"] = np.round(rq, 2).tolist()
        manifest.append(rec)
    with open(out / "manifest.jsonl", "w", encoding="utf-8") as f:
        for m in manifest:
            f.write(json.dumps(m, ensure_ascii=False) + "\n")
    print(f"generated {count} panels -> {out}")
    print(f"layout overlap violations: {viol_total}")
    print(f"band quad clipped digits: {clip_total}")
    return viol_total


def _count_overlaps(rects):
    n = 0
    for i in range(len(rects)):
        for j in range(i + 1, len(rects)):
            a, b = rects[i], rects[j]
            if a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]:
                n += 1
    return n


def montage(out_png, images_dir, manifest, n=12, with_quad=True, quad_key="quad"):
    """검증 몽타주. 오버레이 없는 판과 함께 남긴다(지시서 — 1판에서 오버레이
    때문에 글리프 품질 판정을 못 했다)."""
    rows = []
    picks = [manifest[i] for i in range(0, len(manifest),
                                        max(1, len(manifest) // n))][:n]
    for m in picks:
        img = cv2.imread(str(Path(images_dir) / f"{m['id']}.png"),
                         cv2.IMREAD_GRAYSCALE)
        if img is None:
            continue
        if with_quad and quad_key in m:
            q = np.asarray(m[quad_key], np.int32)
            cv2.polylines(img, [q.reshape(-1, 1, 2)], True, 255, 3)
            cv2.polylines(img, [q.reshape(-1, 1, 2)], True, 0, 1)
        h = 224
        w = int(img.shape[1] * h / img.shape[0])
        rows.append(cv2.resize(img, (max(1, w), h)))
    wmax = max(r.shape[1] for r in rows)
    nrows = (len(rows) + 3) // 4
    canvas = np.zeros((224 * nrows + 8 * (nrows + 1), (wmax + 8) * 4 + 8),
                      np.uint8)
    for i, r in enumerate(rows):
        y, x = 8 + (i // 4) * (224 + 8), 8 + (i % 4) * (wmax + 8)
        canvas[y:y + r.shape[0], x:x + r.shape[1]] = r
    cv2.imwrite(str(out_png), canvas)
    print(f"montage {len(rows)} -> {out_png}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["gen", "montage"])
    ap.add_argument("--count", type=int, default=500)
    ap.add_argument("--wide-share", type=float, default=None,
                    help="가로형(선언 family=column/row) 프로파일의 합계 비중. "
                         "생략하면 균등(2/15=13.3%%). 예: 0.40")
    ap.add_argument("--seed", type=int, default=22000)
    ap.add_argument("--out", default=str(HERE / "synth_panels_v2"))
    ap.add_argument("--reader", action="store_true")
    ap.add_argument("--images")
    ap.add_argument("--manifest")
    ap.add_argument("--n", type=int, default=12)
    ap.add_argument("--quad-key", default="quad")
    args = ap.parse_args()
    if args.cmd == "gen":
        set_wide_share(args.wide_share)
        v = generate(args.count, args.seed, args.out, with_reader=args.reader)
        if v:
            sys.exit(1)
    else:
        rows = [json.loads(l) for l in Path(args.manifest).read_text(
            encoding="utf-8").splitlines() if l.strip()]
        montage(args.out, args.images, rows, n=args.n, quad_key=args.quad_key)
