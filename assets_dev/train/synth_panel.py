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
#   (8) 극성 반전 58%(실물 21~27%) -> 극성은 프로파일 속성. 실사진 84장에서
#           기기별로 재서 반전 기기에만 inverted 를 매긴다(measure_polarity.py)
#   (9) 브랜드명을 액정 안에 그림 -> 베젤 인쇄는 패널 바깥 링에만 그린다.
#           액정 문자열은 화이트리스트 토큰으로 assert 고정한다
#
# 렌더 규약(AC#7) — 한 렌더에서 출력 3종:
#   1. 패널 이미지 — 긴 변 896px, 최종 캔버스 w/h 는 GM 박스 실측 분포
#   2. 밴드 쿼드 — 최종 캔버스 픽셀 좌표계 4점(TL,TR,BR,BL). 정의: 사람 라벨과
#      같게 '보이는 숫자줄'만 감싼다(2자리 값은 빈 슬롯을 포함하지 않는다 —
#      실측: 밴드 w/panelw 2자리 0.571 vs 3자리 0.810, measure 2026-09-12).
#      쿼드는 이미지와 같은 행렬·같은 순서를 통과한 뒤의 좌표다.
#   3. 값 라벨 — 숫자만. isdigit() assert.
#
# 실측 근거(전부 2026-09-12, 이 저장소 도구로 직접 측정):
#   종횡비   GM 쿼드 2,497장 — w/h 중앙 0.792, p10 0.705, p90 0.975,
#            세로(<1.0) 91.7%, 매우 가로(>2.0) 0.8% (measure_panel_stats aspect)
#   밴드기하 세로 n=51 — band w/panelw 0.827[0.651,0.951], h/panelh 0.458[0.378,0.543],
#            cx 0.520[0.466,0.586], cy 0.391[0.360,0.460]
#            가로 n=33 — w 0.587[0.431,0.806], h 0.798[0.690,0.865],
#            cx 0.464[0.043,0.575], cy 0.517[0.473,0.543] (measure_panel_stats band)
#   밀도     GM 크롭 84장, 밴드 밖 엣지(frame 3% 제외) 중앙 2.25%[0.56,3.97].
#            카드 본문의 7.51%는 이 자로 재현되지 않는다(전체 크롭 2.23%, 밴드 외
#            무제외 2.52%) — 본 렌더는 같은 자 잰 값 84개를 렌더별 목표로 쓰고
#            합성과 실사진을 같은 자로 나란히 보고한다.
#   극성     밴드 라벨 84장 — 반전 27.4%. 기기별: 이름모를 가로형 14장 100%,
#            Performa Nano 3장 100%, BAROZEN II 2장 100%, Active 2장 50%,
#            OneTouch UltraMini 30장 3.3%, CareSens N 19장 0% (measure_polarity)
#   대비     밴드 p95-p5 중앙 104, p10 60, 40 미만 1.2% (measure_polarity)
#   자릿수   코퍼스 2,512행 — 2자리 20.5%, 3자리 79.5% (measure_polarity digits)
#   칸 폭    실사진 밴드 크롭 육안 + DSEG 측정: 칸 피치 ≈ 0.50~0.60·높이,
#            글리프 폭 ≈ 피치의 0.78~0.84, DSEG7 '8' 자연 폭 0.615·높이,
#            '1' 0.065~0.18·높이(균일 압축으로 상대 폭 보존)
import argparse
import json
import random
import sys
from pathlib import Path

import cv2
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from synth_profiles import (  # noqa: E402
    PROFILES, DOT_FMTS, dot_text, _icon, _pick_variant, _glyph_mask,
)
from synth_lcd import put_7seg_text, add_local_shadow  # noqa: E402
from measure_panel_stats import edge_density_outside  # 같은 자(AC#4)  # noqa: E402

LONG_SIDE = 896

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
_BINS = [b for b, _ in ASPECT_BINS]
_WEIGHTS = np.asarray([n for _, n in ASPECT_BINS], np.float64)

# 밴드 기하 — 실측 p10~p90 균등 재표본(measure_panel_stats band 원문).
BAND_GEOM = {
    "portrait": dict(h=(0.378, 0.543), cx=(0.466, 0.586), cy=(0.360, 0.460)),
    "wide": dict(h=(0.690, 0.865), cx=(0.15, 0.575), cy=(0.473, 0.543)),
}
PITCH_RATIO = (0.50, 0.60)   # 칸 피치 / 글리프 높이 — 실사진 밴드 크롭 육안
GLYPH_IN_CELL = (0.78, 0.84)  # 글리프 폭 / 피치 — 같은 육안 근거

# 밀도 목표 — 실사진 GM 크롭 84장을 같은 자로 잰 값(frame 3% 제외,
# measure_panel_stats density). 렌더마다 여기서 재표본한다.
REAL_DENSITY = [
    0.0, 0.00011, 0.00023, 0.00149, 0.00165, 0.00215, 0.00236, 0.0024,
    0.00477, 0.00739, 0.00796, 0.00913, 0.00925, 0.00967, 0.0098, 0.01021,
    0.01096, 0.01232, 0.01326, 0.01511, 0.01584, 0.01672, 0.01679, 0.01711,
    0.01802, 0.01819, 0.01851, 0.01894, 0.01926, 0.01945, 0.01963, 0.01978,
    0.01991, 0.02019, 0.02028, 0.02056, 0.02123, 0.02136, 0.02179, 0.02197,
    0.02217, 0.02243, 0.02248, 0.02359, 0.02388, 0.02421, 0.02548, 0.02639,
    0.02647, 0.02656, 0.02659, 0.02729, 0.02763, 0.02801, 0.02814, 0.02814,
    0.02892, 0.03036, 0.03132, 0.03193, 0.03207, 0.03221, 0.03379, 0.03384,
    0.03437, 0.03474, 0.03591, 0.03617, 0.03621, 0.03668, 0.03723, 0.0381,
    0.03831, 0.03869, 0.03928, 0.03981, 0.04035, 0.04041, 0.04164, 0.04194,
    0.0441, 0.0449, 0.04748, 0.04868,
]

# ── 액정 화이트리스트(AC#14·#15) ─────────────────────────────────────────────
# 액정 안에 그릴 수 있는 알파벳 토큰 전부다. 각 근거는 실사진 id(아틀라스 요소
# 재고표 2026-09-11 + 프로파일 evidence). 이 토큰 밖의 알파벳을 액정에 그리면
# _draw_text 가 assert 로 죽는다 — GLUCOSEDATE 같은 지어낸 문자열 차단.
LCD_TOKENS = {
    "GLU",                    # 1781, 2498 (green_doctor glulabel)
    "M", "mem", "memory",     # 727, 2498, 1186
    "AC", "PC",               # 식전후 마커 — 관찰 0건, AC#14 목록 요구로 소수 렌더
    "DAY", "AVG",             # 231, 2443, 1911 (+요일수 7·14)
    "OK", "CHECK", "STRIP",   # 120, 694, 695 (도루코 도트줄)
    "am", "pm", "AM", "PM",   # 497
}
LCD_UNITS = ["mg/dL", "mg /dL", "mg/dl"]   # 843(gmate), 1991, 1058, 1903, #33 99
LCD_ICONS = ["battery", "bluetooth", "curved-right", "curved-left",
             "tri-right", "tri-down", "triangle", "blood-drop", "mem-flag",
             "smile"]
# 베젤 인쇄(액정 밖 링 전용) — 지시서 베젤 목록 중 프로파일이 있는 것만.
BEZEL_TEXTS = {
    "accuchek_active": ["Active"],
    "dorucos_premium": ["Premium"],
    "green_doctor": ["GREEN Doctor"],
    "onetouch_ultra": ["ONETOUCH Ultra", "LIFESCAN"],
    "acura_plus": ["ACURA PLUS"],
    "performa_silver": ["Performa", "Performa Nano"],
    "gmate": ["Gmate"],
    "accuchek_instant": ["ACCU-CHEK", "Instant"],
}
_BEZEL_FONTS = [cv2.FONT_HERSHEY_SIMPLEX, cv2.FONT_HERSHEY_TRIPLEX,
                cv2.FONT_HERSHEY_COMPLEX]

# 프로파일별 패널 속성 — 극성은 실측(measure_polarity polarity 원문) 기준.
# 미측정 기기는 정상(밝은 화면)이 기본이다: 측정된 8종 중 6종이 정상 우세였고
# 반전을 추측으로 매기는 쪽이 더 위험하다. generic_v1 은 기기 미상의 잔여 풀이므로
# 렌더마다 실측 코퍼스 반전률 27.4%로 뽑는다(기기 속성이 없으니 기기 일관성
# 제약도 없다 — 이 판단과 근거는 보고서에 적는다).
# inverted="mixed" 는 실측에서 두 상태가 모두 관찰된 기기 — 렌더마다 mixed_p 로
# 뽑는다. ACCU-CHEK Active: 밴드 라벨 2장 중 1장 반전(measure_polarity).
# 기기 특성상 백라이트 유무로 두 상태가 나타나는 것으로 보인다(n=2, 표본 작음).
PANEL_ATTRS = {
    "performa_silver": dict(inverted=True),       # Performa Nano 3/3 반전
    "accuchek_active": dict(inverted="mixed", mixed_p=0.5),
}
GENERIC_INVERTED_P = 0.274


def sample_wh(rng):
    i = rng.choices(range(len(_BINS)), weights=_WEIGHTS, k=1)[0]
    lo, hi = _BINS[i]
    return rng.uniform(lo, hi)


def sample_value(rng):
    """코퍼스 자릿수 분포: 2자리 20.5%, 3자리 79.5%(2,512행 실측)."""
    if rng.random() < 0.205:
        return rng.randint(30, 99)
    return rng.randint(100, 511)


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


def _text_size(text, h):
    """_draw_text 와 같은 파라미터의 실폭·실높이 — 배치 예약은 이 값으로
    한다(추정 폭이 어긋나면 그린 글자가 예약 밖으로 나와 이웃과 겹친다 —
    1판 및 본판 초기('memory' 위에 'mem') 실측)."""
    scale = h / 22.0
    th = max(1, int(round(h / 9.0)))
    (tw, thh), base = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, scale, th)
    return tw, thh + base


def _draw_text(img, x, y, text, h, ink, name=""):
    """액정 인쇄 글자 — 채움 획(AC#11). 알파벳 토큰 화이트리스트 assert(AC#14).
    (x,y) 는 좌상단. 굵기 h/9 — 1판의 속 빈 글자(AVG 7 DAY) 결함 대응."""
    alpha_ok = LCD_TOKENS | {w for u in LCD_UNITS for w in u.split(" ")
                             if w.isalpha()}
    for w in text.split(" "):
        if w.isalpha() and len(w) >= 2:
            assert w in alpha_ok, f"액정 토큰 위반: {w!r} ({name})"
    scale = h / 22.0
    th = max(1, int(round(h / 9.0)))
    (tw, thh), base = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, scale, th)
    cv2.putText(img, text, (x, y + thh), cv2.FONT_HERSHEY_SIMPLEX, scale, ink,
                th, cv2.LINE_AA)
    return tw


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


def _dot_time_text(rng):
    fmt = DOT_FMTS[rng.randrange(len(DOT_FMTS))]
    return fmt.format(h02=f"{rng.randint(0, 12):02d}",
                      m02=f"{rng.randint(0, 59):02d}",
                      M=f"{rng.randint(1, 12)}", M02=f"{rng.randint(1, 12):02d}",
                      d=f"{rng.randint(1, 31)}", d02=f"{rng.randint(1, 31):02d}",
                      am=random.choice(["am", "pm"]),
                      AM=random.choice(["AM", "PM"]))


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
        profile = PROFILES[rng.randrange(len(PROFILES))]
    pid = profile.get("id", "generic_v1")
    if profile.get("legacy"):
        profile = dict(id="generic_v1", slots=(2, 3), align="right",
                       italic=False)
        pid = "generic_v1"
    attrs = PANEL_ATTRS.get(pid, {})
    if pid == "generic_v1":
        inverted = rng.random() < GENERIC_INVERTED_P
    elif attrs.get("inverted") == "mixed":
        inverted = rng.random() < attrs.get("mixed_p", 0.5)
    else:
        inverted = bool(attrs.get("inverted", False))
    target = REAL_DENSITY[rng.randrange(len(REAL_DENSITY))]
    fill = target
    best = None
    for _ in range(3):
        s = _render_once(value, rng, profile, pid, inverted, fill)
        if best is None or s["density"] > best["density"]:
            best = s
        if best["density"] >= fill:
            break
        fill = fill + (target - best["density"])   # 광학 감쇠분을 보탠다
    best["target_density"] = round(target, 5)
    return best


def _render_once(value, rng, profile, pid, inverted, fill_target):
    label = str(value)
    assert label.isdigit(), f"라벨 오염: {label!r}"

    # ── 캔버스 — 실측 종횡비, 긴 변 896(AC#1·#6) ──────────────────────────
    wh = sample_wh(rng)
    if wh >= 1.0:
        W, H = LONG_SIDE, max(64, int(round(LONG_SIDE / wh)))
    else:
        W, H = max(64, int(round(LONG_SIDE * wh))), LONG_SIDE

    # ── 두 층: 베젤 링(플라스틱) + 액정 패널(AC#13) ────────────────────────
    # 링 두께: 대부분 2~8px(타이트한 GM 박스). 35% 는 느슨한 크롭으로 14~36px
    # 링이 생기고, 링이 충분할 때만 프로파일 베젤 문자를 링에 그린다(AC#15 —
    # 관찰된 문자열만, 프로파일 evidence). 액정 안에는 절대 그리지 않는다.
    loose = rng.random() < 0.35
    m = int(rng.uniform(14, 36)) if loose else int(rng.uniform(2, 8))
    bezel_col = int(rng.uniform(40, 90))
    img = np.full((H, W), bezel_col, np.uint8)
    if inverted:
        panel_col = int(rng.uniform(35, 95))
        ink_digit = int(rng.uniform(185, 245))
        ink_small = int(rng.uniform(150, 210))
    else:
        panel_col = int(rng.uniform(150, 215))
        ink_digit = int(rng.uniform(20, 90))
        ink_small = int(rng.uniform(60, 130))
    px0, py0, px1, py1 = m, m, W - m, H - m
    img[py0:py1, px0:px1] = panel_col

    # 베젤 인쇄 — 링 높이의 55%로 링 안에 완전히 들어오게(잘리지 않는다)
    bezel_text = None
    if loose and pid in BEZEL_TEXTS and rng.random() < 0.8:
        bh = max(8, int(m * 0.55))
        text = BEZEL_TEXTS[pid][rng.randrange(len(BEZEL_TEXTS[pid]))]
        scale = bh / 22.0
        (tw, thh), _ = cv2.getTextSize(text, _BEZEL_FONTS[0], scale, 1)
        if tw < W - 2 * m - 8:
            bx = m + int((W - 2 * m - tw) * rng.uniform(0.15, 0.6))
            if rng.random() < 0.6:      # 아랫링 우세(실물 관례)
                by = H - m + (m - thh) // 2
            else:
                by = (m - thh) // 2
            cv2.putText(img, text, (bx, by + thh), _BEZEL_FONTS[0], scale,
                        int(rng.uniform(120, 200)), 1, cv2.LINE_AA)
            bezel_text = text

    placer = Placer(px0 + 2, py0 + 2, px1 - 2, py1 - 2)

    # ── 숫자 밴드 — 실측 기하에서 역산. x0 는 '보이는 숫자줄'의 좌측이고
    #    빈 슬롯(잔상)은 그 바깥쪽에 그린다 — 쿼드는 사람 라벨처럼 보이는
    #    숫자줄만 감싼다(실측: 2자리 0.571 vs 3자리 0.810).
    #    기하 비율의 분모는 패널(액정)이다 — 캔버스 기준으로 뽑으면 링 여유가
    #    큰 패널에서 밴드가 패널보다 커져 패널 안쪽 클리핑이 난다(실측:
    #    panel_23000_213, 가로형 + margin 33).
    key = "portrait" if wh < 1.0 else "wide"
    g = BAND_GEOM[key]
    slots_spec = profile.get("slots") or len(label)
    slots = rng.choice(list(slots_spec)) if isinstance(slots_spec, (tuple,
                                                                    list))         else slots_spec
    slots = max(slots, len(label))
    pw, ph = px1 - px0, py1 - py0
    band_h_frac = rng.uniform(*g["h"])
    band_h = band_h_frac * ph
    dh = int(band_h / 1.26)              # 세로 여유 13% 씩(실사진 밴드 크롭 기준)
    pad_y = max(4, int((band_h - dh) / 2))
    pitch_r = rng.uniform(*PITCH_RATIO)
    glyph_w = int(dh * pitch_r * rng.uniform(*GLYPH_IN_CELL))
    pitch = int(dh * pitch_r)
    gap = pitch - glyph_w
    n_vis = len(label)
    lead = slots - n_vis
    field_w = n_vis * pitch - gap
    quad_w = field_w + 2 * max(6, int(dh * 0.20))
    max_w = int(pw * 0.96)
    if quad_w > max_w:              # 폭이 막히면 높이를 줄여 맞춘다
        s = max_w / quad_w
        dh, glyph_w, pitch, gap = (int(dh * s), int(glyph_w * s),
                                   int(pitch * s), int(gap * s))
        field_w = n_vis * pitch - gap
    cx = px0 + rng.uniform(*g["cx"]) * pw
    cy = py0 + rng.uniform(*g["cy"]) * ph
    x0 = int(cx - field_w / 2)
    y0 = int(cy - dh / 2)
    pad_x = max(6, int(dh * 0.20))
    x0 = max(px0 + 2 + pad_x, min(px1 - 2 - pad_x - field_w, x0))
    y0 = max(py0 + 2 + pad_y, min(py1 - 2 - pad_y - dh, y0))
    quad = np.float32([[x0 - pad_x, y0 - pad_y],
                       [x0 + field_w + pad_x, y0 - pad_y],
                       [x0 + field_w + pad_x, y0 + dh + pad_y],
                       [x0 - pad_x, y0 + dh + pad_y]])
    placer.reserve(*(quad[0][0], quad[0][1], quad[2][0], quad[2][1]), "band")

    # ── 숫자 — DSEG, 균일 압축. 이탤릭은 폰트 변형(전역 shear 없음) ────────
    variant = _pick_variant(rng, bool(profile.get("italic")))
    ghost = rng.uniform(0.08, 0.16) if rng.random() < 0.3 else 0.0
    glyph_cache = {}
    glyph_plane = np.zeros((H, W), np.uint8)
    align = profile.get("align", "right")
    for j in range(n_vis):
        ch = label[j]
        _draw_digit_uniform(img, x0 + j * pitch, y0, dh, ch, glyph_w,
                            ink_digit, variant, glyph_cache, plane=glyph_plane)
    for j in range(lead):               # 빈 슬롯 잔상 — 쿼드 밖
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
    last_r = x0 + field_w

    # ── 액정 요소 — 전부 실폭 재서 배치, 패널 밖으로 못 나가게(AC#12) ──────
    u = profile.get("unit")
    if u and rng.random() < u["p"]:
        ut = LCD_UNITS[rng.randrange(len(LCD_UNITS))]   # 관찰된 변형만(AC#15)
        uh = max(7, int(dh * rng.uniform(*u["h_ratio"])))
        ug = int(rng.uniform(*u["gap"]))
        (tw, _), _b = cv2.getTextSize(ut, cv2.FONT_HERSHEY_SIMPLEX, uh / 22.0,
                                      max(1, uh // 9))
        pos = u["pos"]
        if pos == "right-baseline":
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
            cands = [(int(W * 0.5), band_bot + 4), (px0 + 2, band_bot + 4)]
        cands = cands + [(px0 + 2, band_bot + 4), (px1 - 2 - tw, band_bot + 4)]
        if maybe(placer.try_place(cands[0][0], cands[0][1], tw, uh + 2, "unit",
                                  alternates=cands[1:]), "unit"):
            r = placer.rects[-1]
            _draw_text(img, r[0], r[1], ut, uh, ink_small, "unit")
            used_texts.add(ut)

    meal = profile.get("meal")
    if meal and rng.random() < meal["p"]:
        mh = max(7, int(dh * 0.16))
        mt = meal["texts"][rng.randrange(len(meal["texts"]))]
        (tw, _), _b = cv2.getTextSize(mt, cv2.FONT_HERSHEY_SIMPLEX, mh / 22.0, 1)
        if maybe(placer.try_place(last_r + int(dh * 0.1), band_bot - mh, tw,
                                  mh + 2, "meal",
                                  alternates=((px1 - 2 - tw, band_bot - mh),)),
                 "meal"):
            r = placer.rects[-1]
            _draw_text(img, r[0], r[1], mt, mh, ink_small, "meal")
            used_texts.add(mt)

    mk = profile.get("mem")
    if mk and rng.random() < mk["p"]:
        mh = max(8, int(dh * 0.22))
        if mk["pos"] == "top-left":
            cands = ((int(W * 0.08), py0 + 4), (int(W * 0.08), band_top - mh - 4))
        elif mk["pos"] == "top-right":
            cands = ((int(W * 0.7), py0 + 4), (int(W * 0.7), band_top - mh - 4))
        elif mk["pos"] == "below-left":
            cands = ((int(W * 0.1), band_bot + 4), (int(W * 0.1), py1 - 2 - mh))
        else:  # right-of-digits
            cands = ((last_r + int(glyph_w * 0.4), y0 + (dh - mh) // 2),
                     (last_r + int(glyph_w * 0.4), py0 + 4))
        mtxt = {"mem": "mem", "memory": "memory", "M": "M"}.get(mk["kind"], "M")
        mtw, mth = _text_size(mtxt, mh)
        cands = [(cx_, cy_) for cx_, cy_ in cands]
        if maybe(placer.try_place(cands[0][0], cands[0][1], mtw, mth,
                                  "mem", alternates=cands[1:]), "mem"):
            r = placer.rects[-1]
            if mk["kind"] == "M-box":
                cv2.rectangle(img, (r[0] - 2, r[1]), (r[0] + mh + 2, r[3]),
                              ink_small, 1)
                _draw_text(img, r[0], r[1], "M", mh, ink_small, "mem")
                used_texts.add("M")
            else:
                t = {"mem": "mem", "memory": "memory", "M": "M"}.get(
                    mk["kind"], "M")
                _draw_text(img, r[0], r[1], t, mh, ink_small, "mem")
                used_texts.add(t)

    gl = profile.get("glulabel")
    if gl and rng.random() < gl.get("p", 0):
        gh = max(8, int(dh * 0.2))
        gtw, gth = _text_size("GLU", gh)
        if maybe(placer.try_place(x0, max(py0 + 2, band_top - gh - 4),
                                  gtw, gth, "glulabel",
                                  alternates=((x0, band_bot + 4),)), "glulabel"):
            r = placer.rects[-1]
            _draw_text(img, r[0], r[1], "GLU", gh, ink_small, "glulabel")
            used_texts.add("GLU")

    a = profile.get("arrow")
    if a and rng.random() < a["p"]:
        # 1판에서 320px 용 size(18~30) 를 패널 배율로 곧이곧대로 키운 실수 대신,
        # 글리프 높이 비율로 잡는다 — 실관찰상 화살표는 숫자 높이의 2~3할.
        s = max(8, int(dh * rng.uniform(0.18, 0.30)))
        kinds = [k for k in a["kinds"] if k in LCD_ICONS]
        ag = int(rng.uniform(*a["gap"]) * max(1, dh / 56.0))
        ay = y0 + int(dh * rng.uniform(0.15, 0.55))
        cands = [(last_r + ag, ay), (last_r + ag, band_bot + 4),
                 (px1 - 2 - 2 * s, ay), (px1 - 2 - 2 * s, band_top - 2 * s - 4),
                 (px0 + 2, ay)]
        if maybe(placer.try_place(cands[0][0], cands[0][1], 2 * s, 2 * s,
                                  "arrow", alternates=cands[1:]), "arrow"):
            r = placer.rects[-1]
            _icon(img, kinds[rng.randrange(len(kinds))],
                  (r[0] + r[2]) // 2, (r[1] + r[3]) // 2, s, ink_small)

    for kind, pos, p in profile.get("icons", []):
        if rng.random() > p or kind not in LCD_ICONS:
            continue
        s = max(8, int(dh * rng.uniform(0.28, 0.4)))
        if pos == "top-right":
            cands = ((px1 - 2 - 2 * s, py0 + 4), (px1 - 2 - 2 * s, band_top - 2 * s - 4))
        elif pos == "top-left":
            cands = ((px0 + 2, py0 + 4), (px0 + 2, band_top - 2 * s - 4))
        else:  # right-mid
            cands = ((px1 - 2 - 2 * s, y0 + int(dh * 0.45)),
                     (px1 - 2 - 2 * s, band_bot + 4))
        if maybe(placer.try_place(cands[0][0], cands[0][1], 2 * s, 2 * s,
                                  f"icon:{kind}", alternates=cands[1:]),
                 f"icon:{kind}"):
            r = placer.rects[-1]
            _icon(img, kind, (r[0] + r[2]) // 2, (r[1] + r[3]) // 2, s,
                  ink_small)

    da = profile.get("dotrow_above")
    if da and rng.random() < da["p"]:
        glyph = int(rng.uniform(4, 6)) * max(1, dh // 48)
        txt = da["texts"][rng.randrange(len(da["texts"]))]
        wpx = int(len(txt) * glyph * 1.2)
        if maybe(placer.try_place(int(W * 0.08), py0 + 2, wpx, glyph * 2 + 4,
                                  "dotrow_above"), "dotrow_above"):
            r = placer.rects[-1]
            dot_text(img, r[0], r[1], txt, glyph, ink_small)
            used_texts.add(txt)
    db = profile.get("dotrow_below")
    if db and rng.random() < db["p"]:
        glyph = int(rng.uniform(4, 6)) * max(1, dh // 48)
        txt = _dot_time_text(rng)
        wpx = int(len(txt) * glyph * 1.2)
        if maybe(placer.try_place(int(W * 0.08), band_bot + 4, wpx,
                                  glyph * 2 + 4, "dotrow_below"), "dotrow_below"):
            r = placer.rects[-1]
            dot_text(img, r[0], r[1], txt, glyph, ink_small)
            used_texts.add(txt)

    t = profile.get("time")
    if t and rng.random() < t["p"]:
        th = int(dh * rng.uniform(0.28, 0.42))
        hh = f"{rng.randint(0, 23):02d}:{rng.randint(0, 59):02d}"
        tw = int(W * 0.30)
        if t["pos"] == "below-right":
            cands = ((int(W * 0.55), band_bot + 4), (px1 - 2 - tw, band_bot + 4))
        else:
            cands = ((int(W * 0.1), band_bot + 4), (px0 + 2, py1 - 2 - th))
        if maybe(placer.try_place(cands[0][0], cands[0][1], tw, th, "time",
                                  alternates=cands[1:]), "time"):
            r = placer.rects[-1]
            put_7seg_text(img, r[0], r[1], tw, th, hh, ink_small)

    if profile.get("avgrow", {}).get("p", 0) > rng.random():
        ah = int(dh * rng.uniform(0.24, 0.34))
        txt = f"{rng.choice(['7', '14'])} DAY AVG"
        (tw, _), _b = cv2.getTextSize(txt, cv2.FONT_HERSHEY_SIMPLEX, ah / 22.0,
                                      max(1, ah // 9))
        if maybe(placer.try_place(int(W * 0.1), band_bot + 4, tw + int(W * 0.16),
                                  ah + 2, "avgrow"), "avgrow"):
            r = placer.rects[-1]
            _draw_text(img, r[0], r[1], txt, ah, ink_small, "avgrow")
            used_texts.add(txt)
            put_7seg_text(img, r[2] - int(W * 0.15), r[1], int(W * 0.15), ah,
                          f"{rng.randint(1, 999):03d}", ink_small)

    if profile.get("daterow", {}).get("p", 0) > rng.random():
        rh = max(7, int(dh * 0.18))
        txt = f"{rng.randint(1, 12)}-{rng.randint(1, 31)}  #{rng.randint(1, 9)}"
        tw = int(len(txt) * rh * 0.85)
        if maybe(placer.try_place(int(W * 0.08), band_bot + int(H * 0.02), tw,
                                  rh + 2, "daterow"), "daterow"):
            r = placer.rects[-1]
            _draw_text(img, r[0], r[1], txt, rh, ink_small, "daterow")
            used_texts.add(txt)

    # ── 밀도 채움 — 실관찰 요소만(인쇄 라벨·도트 시간줄·아이콘), Placer 검사.
    #    목표는 실사진 84장 분포에서 재표본한 값. 자는 measure_panel_stats 와
    #    동일(AC#4).
    filler_pool = ["OK", "CHECK STRIP", "GLU", "mem"]
    for attempt in range(48):
        if attempt % 3 == 0 or attempt == 47:
            d = _density_outside(img, quad)
            if d is not None and d >= fill_target:
                break
        kind = rng.random()
        if kind < 0.5:
            text = _dot_time_text(rng)
            glyph = max(4, int(dh * rng.uniform(0.10, 0.16)))
            wpx = max(16, int(len(text) * glyph * 1.2))
            hpx = glyph * 2 + 4
            draw = ("dot", text, glyph)
        elif kind < 0.8:
            fresh = [t for t in filler_pool if t not in used_texts]
            if not fresh:
                continue
            text = fresh[rng.randrange(len(fresh))]
            fh = max(9, int(dh * rng.uniform(0.18, 0.30)))
            wpx, hpx = _text_size(text, fh)
            draw = ("print", text, fh)
        else:
            icon = LCD_ICONS[rng.randrange(len(LCD_ICONS))]
            s = max(8, int(dh * rng.uniform(0.22, 0.34)))
            wpx = hpx = 2 * s
            draw = ("icon", icon, s)
        # 남은 영역: 밴드 위/아래(세로 패널은 넉넉히), 밴드 좌/우(가로 패널)
        regions = []
        top_h = band_top - 4 - (py0 + 4) - hpx
        bot_h = (py1 - 4) - band_bot - hpx
        left_w = (x0 - pad_x) - (px0 + 4) - wpx
        right_w = (px1 - 4) - (x0 + field_w + pad_x) - wpx
        if top_h > 4:
            regions.append(((px1 - px0) * top_h, px0 + 4, px1 - 4 - wpx,
                            py0 + 4, band_top - 4 - hpx))
        if bot_h > 4:
            regions.append(((px1 - px0) * bot_h, px0 + 4, px1 - 4 - wpx,
                            band_bot + 4, py1 - 4 - hpx))
        if left_w > 4:
            regions.append((left_w * max(dh, 40), px0 + 4, x0 - pad_x - 4 - wpx,
                            y0, y0 + max(4, dh - hpx)))
        if right_w > 4:
            regions.append((right_w * max(dh, 40), x0 + field_w + pad_x + 4,
                            px1 - 4 - wpx, y0, y0 + max(4, dh - hpx)))
        if not regions:
            continue
        _, x_lo, x_hi, y_lo, y_hi = regions[rng.randrange(len(regions))]
        px = int(rng.uniform(x_lo, max(x_lo, x_hi)))
        py = int(rng.uniform(y_lo, max(y_lo, y_hi)))
        if placer.try_place(px, py, wpx, hpx, f"filler{attempt}"):
            r = placer.rects[-1]
            if draw[0] == "dot":
                dot_text(img, r[0], r[1], draw[1], draw[2], ink_small)
                used_texts.add(draw[1])
            elif draw[0] == "print":
                _draw_text(img, r[0], r[1], draw[1], draw[2], ink_small,
                           "filler")
                used_texts.add(draw[1])
            else:
                _icon(img, draw[1], (r[0] + r[2]) // 2, (r[1] + r[3]) // 2,
                      draw[2], ink_small)

    # ── 광학 — 노이즈·블러·명암·비네팅·국소 그림자·연한 반사패치(결함 (7)) ──
    img = np.clip(img.astype(np.float32)
                  + np.random.normal(0, rng.uniform(2, 9), img.shape),
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
    for _ in range(rng.randint(1, 2)):
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
        ax_ = rng.uniform(0.18, 0.38) * W
        ay_ = rng.uniform(0.10, 0.30) * H
        glare = min(255, panel_col + rng.uniform(40, 90))
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
    fillc = int(bezel_col)
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

    def _warp_img(im, interp, Mk, Mr):
        out = im
        if Mk is not None:
            out = cv2.warpPerspective(out, Mk, (W, H), flags=interp,
                                      borderMode=cv2.BORDER_CONSTANT,
                                      borderValue=fillc)
        if Mr is not None:
            out = cv2.warpAffine(out, Mr, (W, H), flags=interp,
                                 borderMode=cv2.BORDER_CONSTANT,
                                 borderValue=fillc)
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
    glyph_warped = _warp_img(gp0, cv2.INTER_NEAREST, Mk, Mr)

    # 글리프 평면 자가검사(AC#8): 같은 변환을 통과한 글리프 마스크 자리가
    # 최종 이미지에서 실제 잉크(배경과 유의미하게 다른 픽셀)인지 비율로.
    # 주의: 워프가 마스크 밖을 borderValue(베젤색) 로 채우므로 0 이 아니라
    # 127 로 문턱을 낸다 — 0 비교는 캔버스 전체가 sel 이 된다.
    if glyph_warped.max() > 0:
        bg = float(np.median(img))
        sel = glyph_warped > 127
        ink = np.abs(img.astype(np.float32) - bg) > 30
        gpc = float((ink & sel).sum()) / max(1, sel.sum())
    else:
        gpc = 0.0

    dens = _density_outside(img, quad)
    return dict(panel=img, quad=np.asarray(quad, np.float32), label=label,
                rects=placer.rects, dropped=dropped, wh=W / H, W=W, H=H,
                profile=pid, inverted=bool(inverted),
                glyph_plane_check=round(gpc, 4),
                glyph_warped=glyph_warped,
                density=dens if dens is not None else 0.0,
                bezel=bezel_text, margin=m)


def _density_outside(img, quad):
    q = np.asarray(quad, np.float64)
    H, W = img.shape[:2]
    return edge_density_outside(
        img, (q[:, 0].min() / W, q[:, 1].min() / H,
              q[:, 0].max() / W, q[:, 1].max() / H), exclude_frame=0.03)


def reader_view(sample):
    """파이프라인과 같은 워프 — 패널 캔버스 전체를 320x160 으로(AC#2 참고
    산출물). 세로 패널은 가로로 약 2.5배 늘어난 납작한 글리프가 된다."""
    img, H, W = sample["panel"], sample["H"], sample["W"]
    src = np.float32([[0, 0], [W - 1, 0], [W - 1, H - 1], [0, H - 1]])
    dst = np.float32([[0, 0], [319, 0], [319, 159], [0, 159]])
    Mp = cv2.getPerspectiveTransform(src, dst)
    warped = cv2.warpPerspective(img, Mp, (320, 160))
    rq = cv2.perspectiveTransform(sample["quad"][None, :, :], Mp)[0]
    return warped, np.asarray(rq, np.float32)


def generate(count, seed0, out_dir, with_reader=False):
    out = Path(out_dir)
    (out / "images").mkdir(parents=True, exist_ok=True)
    rng = random.Random(seed0)
    manifest = []
    viol_total = 0
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
        rec = dict(
            id=name, profile=s["profile"], w=s["W"], h=s["H"],
            wh=round(s["wh"], 4), quad=q.tolist(), label=s["label"],
            inverted=s["inverted"], glyph_plane_check=s["glyph_plane_check"],
            density=round(float(s["density"]), 5),
            target_density=s["target_density"],
            rects=[[round(float(v), 1) for v in r[:4]] + [r[4]]
                   for r in s["rects"]],
            dropped=s["dropped"], overlaps=viol,
            margin=s["margin"],
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
    ap.add_argument("--seed", type=int, default=22000)
    ap.add_argument("--out", default=str(HERE / "synth_panels_v2"))
    ap.add_argument("--reader", action="store_true")
    ap.add_argument("--images")
    ap.add_argument("--manifest")
    ap.add_argument("--n", type=int, default=12)
    ap.add_argument("--quad-key", default="quad")
    args = ap.parse_args()
    if args.cmd == "gen":
        v = generate(args.count, args.seed, args.out, with_reader=args.reader)
        if v:
            sys.exit(1)
    else:
        rows = [json.loads(l) for l in Path(args.manifest).read_text(
            encoding="utf-8").splitlines() if l.strip()]
        montage(args.out, args.images, rows, n=args.n, quad_key=args.quad_key)
