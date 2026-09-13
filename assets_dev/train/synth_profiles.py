# 기기 프로파일 합성 렌더러 — 「합성에 기기 프로파일 도입」 카드 (2026-09-11).
#
# synth_lcd.render_screen(레거시 무작위 레이아웃)은 그대로 둔다 — 이것이 기준선
# 팔(합성만 학습 → 실사진 평가 0/1,138)의 생성기다. 이 모듈은 그 위에
# '기기' 개념을 얹는다: 실사진에서 관찰한 배치를 프로파일로 정의하고 렌더가
# 그중 하나를 골라 그린다.
#
# 모든 수치는 워프 좌표계(320x160) 실측. 정본:
#   docs/reports/synth-vs-real-atlas-2026-09-11.md (요소 재고표·차이 항목표)
#   _diag/synth_real_atlas/ (몽타주·스트립·측정 시트)
# 프로파일은 실사진에서 읽은 것만 담는다(카드 Notes — 상상 금지). 근거 id 는
# 각 프로파일의 evidence. 길이 (min,max) 는 렌더 흔들림 범위이고 gap 은
# '마지막 자릿수(숫자 블록 가장자리)에서 요소까지의 최소 간격 px'다.
#
# 라벨 오염 금지(카드 AC#3): 아이콘·화살표·단위·보조줄은 렌더만 하고 라벨
# 문자열에는 절대 넣지 않는다 — 모델이 그 자리에 blank 를 내도록 배운다.
import json
import random
import zlib
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

from synth_lcd import (  # 레거시 구성요소 재사용 + 세그먼트 스트로크 폰트(2026-09-13)
    draw_digit, put_7seg_text, render_screen, seg_text, seg_text_width,
    add_local_shadow, add_reflection_stripe, apply_shear, apply_keystone,
)

# ── DSEG 글리프 렌더 — 「DSEG 폰트 기반 글리프 렌더러 교체」 카드 ────────────
USE_DSEG = True   # False 면 rect 세그먼트 팔(직전 A/B 재현)
# 폰트: DSEG v0.46 (keshikan, SIL OFL 1.1) — fonts/dseg/ 에 원문 라이선스 동봉.
# 변형 선택 근거(눈 검증, _diag/synth_real_atlas/dseg_variant_check.png):
# 실기기 8종 숫자 밴드와 나란히 놓아 Classic 계열이 전체적으로 가장 가깝고
# (모따기 끝단 근사), 굵기는 기기별로 Light/Regular/Bold 가 다 나오며,
# 이탤릭 기기(OneTouch 계열)엔 Italic 변형, 일부 가는획 기기엔 Modern-Light.
# 라이선스(RFN 'DSEG'): 폰트 파일은 수정·재배포하지 않고 렌더에만 쓴다.
FONT_DIR = Path(__file__).resolve().parent / "fonts" / "dseg"
DSEG_FILES = {
    "Light": "DSEG7Classic-Light.ttf", "Regular": "DSEG7Classic-Regular.ttf",
    "Bold": "DSEG7Classic-Bold.ttf", "Italic": "DSEG7Classic-Italic.ttf",
    "LightItalic": "DSEG7Classic-LightItalic.ttf",
    "BoldItalic": "DSEG7Classic-BoldItalic.ttf",
    "ModernLight": "DSEG7Modern-Light.ttf",
}
# 굵기·이탤릭 변인: 한 화면 안에서는 일정(카드 AC#2) — 표본마다 뽑는다.
DSEG_WEIGHTS = ("Light", "Regular", "Regular", "Bold")   # Regular 2배 가중
_fonts = {}


def _font(variant, px):
    key = (variant, px)
    if key not in _fonts:
        _fonts[key] = ImageFont.truetype(str(FONT_DIR / DSEG_FILES[variant]), px)
    return _fonts[key]


def _glyph_mask(ch, variant, h):
    """DSEG 글리프를 h 높이에 맞춘 이진 마스크로. NEAREST 리사이즈로 획을
    뭉개지 않게 한다(획 굵기는 폰트 변형이 담당 — 파일 수정 금지, RFN)."""
    font = _font(variant, int(h * 1.35))
    pil = Image.new("L", (int(h * 1.4), int(h * 1.5)), 0)
    ImageDraw.Draw(pil).text((2, 2), ch, font=font, fill=255)
    a = np.asarray(pil)
    ys, xs = np.nonzero(a > 96)
    if len(xs) == 0:
        return None
    m = a[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
    return cv2.resize(m, (max(2, int(m.shape[1] * h / m.shape[0])), h),
                      interpolation=cv2.INTER_NEAREST) > 96


def draw_digit_dseg(img, x, y, h, ch, ink, variant="Regular", ghost=0.0):
    """DSEG 숫자 한 자. ghost>0 이면 꺼진 세그먼트 잔상('8' 전체 획을 배경과
    잉크 사이 옅은 농도로) 먼저 깔고 진한 글리프를 얹는다(카드 AC#3).
    잔상은 '생각보다 훨씬 약하다'(2026-09-11 실사진 정정) — 확률적으로,
    농도 흔들림 포함. 폭은 글리프 비율이 정한다(배치 계산 불변)."""
    if ghost > 0:
        g = _glyph_mask("8", variant, h)
        if g is not None:
            panel_est = img[max(0, y):y + h, x:x + g.shape[1]].astype(np.float32)
            blend = panel_est * (1 - ghost) + ink * ghost
            region = img[max(0, y):y + h, x:x + g.shape[1]]
            region[g[:region.shape[0], :region.shape[1]]] = \
                blend[:region.shape[0], :region.shape[1]][
                    g[:region.shape[0], :region.shape[1]]].astype(np.uint8)
    m = _glyph_mask(ch, variant, h)
    if m is None:
        return 0
    region = img[y:y + h, x:x + m.shape[1]]
    region[m[:region.shape[0], :region.shape[1]]] = ink
    return m.shape[1]


def _pick_variant(rng, italic):
    w = DSEG_WEIGHTS[rng.randrange(len(DSEG_WEIGHTS))]
    if rng.random() < 0.12:            # 가는획+둥근끝 소수 기기
        return "ModernLight"
    if italic:
        return w + "Italic" if w != "Regular" else "Italic"
    return w

# 실사진에서 관찰된 날짜·시간 표기 여덟 형식(카드 Notes (4) 그대로).
DOT_FMTS = [
    "{h02}:{m02}", "{h02}-{m02}", "{h02} {m02}", "{M}-{d} {h02}:{m02}",
    "{h02}:{m02} {am}", "{h02}-{m02} {am}", "{M02}-{d02} {h02}:{m02}",
    "{d}-{h02}:{m02} {AM}",
]

PROFILES = [
    dict(
        id="accuchek_instant", slots=3, align="right", italic=False,
        digit_h=(0.30, 0.40),
        evidence=["glucose_batch1/267", "glucose_batch1/270",
                  "glucose_batch2/2610", "glucose_batch1/2492",
                  "glucose_batch1/2039"],
        # 화살표-끝자리 갭 실측 72~84px(스트립 12장) — 넓은 범위로 흔들어
        # '거의 닿는' 배치까지 재현한다(AC#5).
        unit=dict(texts=["mg/dL"], pos="below-right", gap=(2, 80),
                  h_ratio=(0.14, 0.20), p=0.9),
        # 미터기 지시 화살표(AC#5): 검은 창 안 오른쪽 가장자리의 흰 ▶ 이
        # 몸체에 인쇄된 점 눈금 열을 가리킨다. 근거 Instant 34장 — 화살표는
        # 값에 대응해 위로 오르고 v159+ 에서 상단에 포화된다(2026-09-13
        # 실측). 단독 아이콘이 아니라 지시자라 kinds 는 tri-right 하나다.
        arrow=dict(kinds=["tri-right"], gap=(2, 80), size=(18, 30), p=0.95),
        meter=True,
        time=dict(pos="below-left", p=0.9),
    ),
    dict(
        id="gmate", slots=3, align="right", italic=False,
        digit_h=(0.42, 0.52),
        evidence=["glucose_batch1/842", "glucose_batch1/843",
                  "glucose_batch1/731", "glucose_batch1/727"],
        # 단위 글리프가 끝자리에 4~5px 로 붙는다(아틀라스 재고표) — 실패 서명.
        unit=dict(texts=["mg/dL", "mg /dL"], pos="below-right", gap=(3, 8),
                  h_ratio=(0.16, 0.22), p=1.0),
        meal=dict(texts=["AC", "PC"], p=0.3),
        mem=dict(kind="M", pos="below-left", p=0.5),
        time=dict(pos="below-left", p=0.85),
    ),
    dict(
        id="dorucos_premium", slots=3, align="left", italic=False,
        digit_h=(0.50, 0.58),
        evidence=["glucose_batch1/120", "glucose_batch1/694",
                  "glucose_batch1/695"],
        # 도트 패널 기기(120·694·695) — 도트매트릭스 렌더를 쓰는 유일한
        # 프로파일이다(카드 2026-09-13 AC#1). 다른 기기의 시간·날짜줄은
        # 실사진에서 전부 세그먼트다(228·800·1903·1911 확인).
        dot_panel=True,
        unit=dict(texts=["mg/dL"], pos="below-right", gap=(8, 14),
                  h_ratio=(0.12, 0.16), p=0.9),
        dotrow_above=dict(texts=["OK", "CHECK STRIP", "GLUCOSE"],
                          glyph=(4, 6), p=1.0),
        dotrow_below=dict(fmts=DOT_FMTS, glyph=(4, 6), p=0.8),
        bezel=dict(texts=["Premium"], edge="bottom", p=1.0),
    ),
    dict(
        id="green_doctor", slots=3, align="right", italic=False,
        digit_h=(0.36, 0.46),
        evidence=["glucose_batch1/1781", "glucose_batch1/2498"],
        glulabel=dict(p=0.9),
        unit=dict(texts=["mg/dL"], pos="below-right", gap=(6, 14),
                  h_ratio=(0.14, 0.18), p=0.6),
        mem=dict(kind="M-box", pos="top-left", p=0.7),
        icons=[("triangle", "top-left", 0.4), ("triangle", "top-right", 0.4),
               ("blood-drop", "right-mid", 0.3), ("bluetooth", "top-right", 0.2)],
        time=dict(pos="below-left", p=0.7),
        bezel=dict(texts=["GREEN Doctor"], edge="top", p=0.8),
        buttons=True,
    ),
    dict(
        id="onetouch_ultra", slots=3, align="right", italic=True,
        digit_h=(0.34, 0.44),
        evidence=["glucose_batch1/1058", "glucose_batch1/2110"],
        unit=dict(texts=["mg/dL"], pos="below-right", gap=(8, 40),
                  h_ratio=(0.14, 0.20), p=0.9),
        mem=dict(kind="mem", pos="top-right", p=0.4),
        time=dict(pos="below-left", p=0.5),
        bezel=dict(texts=["ONETOUCH Ultra", "LIFESCAN"], edge="bottom", p=0.8),
    ),
    dict(
        id="gc_ms_one", slots=3, align="right", italic=False,
        digit_h=(0.34, 0.44),
        evidence=["glucose_batch1/228", "glucose_batch1/373",
                  "glucose_batch1/800"],
        glulabel=dict(p=0.9),
        unit=dict(texts=["mg/dL"], pos="below-right", gap=(2, 8),
                  h_ratio=(0.12, 0.16), p=0.9),
        mem=dict(kind="M-box", pos="top-left", p=0.9),
        time=dict(pos="below-left", p=0.8),
        dotrow_below=dict(fmts=DOT_FMTS[:4], glyph=(4, 6), p=0.4),
    ),
    dict(
        id="acura_plus", slots=3, align="right", italic=False,
        digit_h=(0.36, 0.46),
        evidence=["glucose_batch1/475", "glucose_batch1/477",
                  "glucose_batch1/2357"],
        unit=dict(texts=["mg/dL"], pos="below-right", gap=(4, 12),
                  h_ratio=(0.13, 0.18), p=0.8),
        avgrow=dict(p=0.9),     # '07 DAY AVG 019' — 작은 7세그 + 인쇄 라벨 혼합
        time=dict(pos="below-right", p=0.6),
        bezel=dict(texts=["ACURA PLUS"], edge="top", p=1.0),
    ),
    dict(
        id="caresens_n_premier", slots=3, align="right", italic=False,
        digit_h=(0.38, 0.48),
        evidence=["glucose_batch1/1911", "glucose_batch1/1903"],
        unit=dict(texts=["mg/dL"], pos="below-right", gap=(10, 18),
                  h_ratio=(0.14, 0.18), p=0.9),
        mem=dict(kind="M", pos="right-of-digits", p=0.5),
        icons=[("mem-flag", "right-of-digits", 0.5), ("battery", "top-right", 0.3)],
        dotrow_below=dict(fmts=DOT_FMTS, glyph=(4, 6), p=0.9),
    ),
    dict(
        id="performa_silver", slots=3, align="right", italic=False,
        digit_h=(0.40, 0.50),
        evidence=["glucose_batch1/1186"],
        unit=dict(texts=["mg/dL"], pos="below-right", gap=(4, 10),
                  h_ratio=(0.12, 0.16), p=0.9),
        mem=dict(kind="memory", pos="top-left", p=0.6),
        daterow=dict(p=0.8),    # '7-1' '#5' — 기록번호 포함
        bezel=dict(texts=["Performa", "Performa Nano"], edge="bottom", p=0.7),
        icons=[("battery", "top-right", 0.4), ("blood-drop", "right-mid", 0.3)],
    ),
    dict(
        id="accuchek_active", slots=3, align="center", italic=False,
        digit_h=(0.48, 0.58),
        evidence=["glucose_batch1/1329", "glucose_batch2/2502",
                  "glucose_batch2/2513", "glucose_batch2/2519"],
        # 상단에 시간(왼쪽)·날짜(오른쪽) 작은 줄, 숫자는 중앙 대형,
        # mg/dL 은 숫자 아래 오른쪽(1329 '0:00 0-0' + 하단 mg/dL 관찰).
        unit=dict(texts=["mg/dL"], pos="below-right", gap=(4, 12),
                  h_ratio=(0.12, 0.16), p=0.9),
        time=dict(pos="top-left", p=0.85),
        daterow=dict(p=0.8),
        bezel=dict(texts=["Active"], edge="top", p=0.6),
    ),
    dict(
        id="gluneo_plus", slots=3, align="center", italic=False,
        digit_h=(0.50, 0.60),
        evidence=["glucose_batch1/1435", "glucose_batch1/1438",
                  "glucose_batch1/1440", "glucose_batch1/1449"],
        # 대형 중앙 숫자, mg/dL 은 숫자 아래 오른쪽, 하단 줄 왼쪽에 아래
        # 화살표 아이콘 + 오른쪽 시간(1435~1449 전 관찰). 온도 표기 '28C' 는
        # 화이트리스트 밖이라 렌더하지 않는다(보고서 명시).
        unit=dict(texts=["mg/dL"], pos="below-right", gap=(4, 12),
                  h_ratio=(0.12, 0.16), p=0.9),
        time=dict(pos="below-right", p=0.9),
        arrow=dict(kinds=["tri-down"], gap=(4, 10), size=(10, 16),
                   pos="below-left", p=0.85),
    ),
    dict(
        id="generic_v1", legacy=True, evidence=[],
        # 기존 무작위 레이아웃(synth_lcd.render_screen) 그대로. 8종 프로파일에
        # 없는 배치의 다양성 하한을 지킨다.
        slots=(2, 3),   # 익명 풀은 칸 수도 흔든다(카드 AC#3)
    ),
]


# ── 기기 고정 레이아웃(사람 지침 2026-09-13) ──────────────────────────────
# 하나의 디바이스는 레이아웃이 고정이다 — LCD 종횡비·밴드 기하·요소 자리를
# 기기별로 통일하고, 랜덤은 촬영(프레이밍·광학)에만 남긴다. 값은 전부
# device_layout_stats.py 의 실측 중앙값(device_labels + 밴드 라벨 join)이다.
#   panel_ar 유리 w/h · band_w/h/cx/cy 밴드/유리 비(사람 밴드 라벨 기준)
#   weight  세그먼트 굵기 3종 중 하나(초기 배정 — 아틀라스 눈검으로 조정)
# p>=0.85 인 요소는 항상 렌더(always), 그 아래는 상태성 옵션으로 렌더마다
# 결정된다(자리는 고정). gluneo_plus 는 밴드 라벨이 없어 전역 세로 중앙값
# 폴백(real_baseline band portrait, n=217).
LAYOUTS = {
    "accuchek_instant": dict(panel_ar=0.775, band_w=0.814, band_h=0.386,
                             band_cx=0.524, band_cy=0.459, weight="Bold", font="hershey",
                             n=4),
    "gmate": dict(panel_ar=0.710, band_w=0.995, band_h=0.390,
                  band_cx=0.510, band_cy=0.408, weight="Regular", font="hershey", n=4),
    "dorucos_premium": dict(panel_ar=0.830, band_w=0.916, band_h=0.468,
                            band_cx=0.526, band_cy=0.403, weight="Regular", font="hershey",
                            n=3),
    "green_doctor": dict(panel_ar=0.800, band_w=0.919, band_h=0.402,
                         band_cx=0.548, band_cy=0.467, weight="Regular", font="hershey", n=4),
    "onetouch_ultra": dict(panel_ar=0.950, band_w=0.965, band_h=0.471,
                           band_cx=0.519, band_cy=0.391, weight="Light", font="hershey",
                           n=3),
    "gc_ms_one": dict(panel_ar=0.836, band_w=0.989, band_h=0.473,
                      band_cx=0.508, band_cy=0.500, weight="Regular", font="hershey", n=4),
    "acura_plus": dict(panel_ar=0.941, band_w=0.884, band_h=0.585,
                       band_cx=0.502, band_cy=0.394, weight="Bold", font="hershey", n=4),
    "caresens_n_premier": dict(panel_ar=0.760, band_w=0.918, band_h=0.473,
                               band_cx=0.514, band_cy=0.384, weight="Light", font="hershey",
                               n=4),
    "performa_silver": dict(panel_ar=0.774, band_w=0.859, band_h=0.400,
                            band_cx=0.527, band_cy=0.432, weight="Light", font="hershey",
                            n=8),
    "accuchek_active": dict(panel_ar=0.808, band_w=0.850, band_h=0.420,
                            band_cx=0.495, band_cy=0.460, weight="Regular", font="hershey",
                            n=7),
    "gluneo_plus": dict(panel_ar=0.792, band_w=0.888, band_h=0.447,
                        band_cx=0.512, band_cy=0.407, weight="Regular", font="hershey",
                        n=0),
}
for _p in PROFILES:
    if _p["id"] in LAYOUTS:
        _p["layout"] = LAYOUTS[_p["id"]]


# ── 기기 형질 / 촬영 변인의 분리(사람 지침 2026-09-13) ─────────────────────
# 하나의 기기는 렌더마다 같아야 한다. 그런데 실측이 있는 축(유리 종횡비·밴드
# 기하·세그먼트 굵기)만 LAYOUTS 로 고정돼 있고, 실측이 없는 축(몸체색·모서리
# 반경·베젤 홈·칸 비율·표기 포맷·잔상)은 렌더마다 rng 에서 뽑혔다. 그래서 같은
# 기기가 장마다 다른 물건으로 보였다.
#
# 해법은 '고정값을 정한다'가 아니다 — 실측이 없으니 정할 근거가 없다. 대신
# **뽑는 시점을 기기로 옮긴다**: 기기 id 로 씨를 만들어 형질을 한 번 뽑고
# 캐시한다. 프로세스·시드·렌더 순서와 무관하게 같은 기기는 같은 형질을 받는다
# (crc32 는 파이썬 hash 와 달리 실행 간 안정적이다 — PYTHONHASHSEED 무관).
#
# 경계: 여기 있는 것은 전부 '기기가 가진 것'이다. 촬영이 바꾸는 것(프레이밍·
# 각도·조명·대비·노이즈·반사)과 기기 상태가 바꾸는 것(mem 표기·식전후 마커·
# 배터리·블루투스)은 여기 없다 — 그건 렌더 rng 가 계속 뽑는다.
_IDENTITY_CACHE = {}


def device_identity(pid):
    """기기 고정 형질. 같은 pid 면 언제·어디서 불러도 같은 값을 돌려준다.
    값은 0~1 분수로 준다 — 실제 범위(몸체색 50~190 등)는 소비처가 정한다."""
    if pid in _IDENTITY_CACHE:
        return _IDENTITY_CACHE[pid]
    r = random.Random(zlib.crc32(("device:" + pid).encode("utf-8")))
    t = dict(
        body_u=r.random(),           # 몸체 플라스틱 톤(밝기 범위 안 위치)
        panel_u=r.random(),          # 액정 바탕 톤
        ink_u=r.random(),            # 잉크 톤(대비 열화 전)
        corner_u=r.random() if r.random() < 0.45 else None,  # 라운드 반경(없으면 각진 몸체)
        groove=r.random() < 0.45,    # 움푹한 베젤 홈 유무
        groove_u=r.random(),         # 홈 깊이(있을 때)
        glyph_in_cell=r.uniform(*GLYPH_IN_CELL_RANGE),       # 글리프 폭 / 칸 피치
        ghost=r.uniform(0.04, 0.11) if r.random() < 0.15 else 0.0,
        bezel_i=r.randrange(8),      # 베젤 인쇄 문자열 선택(소비처가 나머지 연산)
        time_fmt_i=r.randrange(len(DOT_FMTS)),
        dotrow_i=r.randrange(8),
        polarity_u=r.random(),       # mixed 기기의 극성을 한 번에 확정
    )
    _IDENTITY_CACHE[pid] = t
    return t


# 글리프 폭/칸 피치 — 육안 근거 범위(synth_panel.GLYPH_IN_CELL 과 같은 값).
# 여기 둔 이유: 이 축은 촬영이 아니라 기기의 액정 셀 기하라서 기기 형질이다.
GLYPH_IN_CELL_RANGE = (0.78, 0.84)

# 상태성 요소 — 기기는 같아도 장마다 켜지고 꺼진다. 자리·크기·모양은 고정이고
# 켜짐 여부만 렌더 rng 가 정한다. 근거: 메모리 표기는 회상 모드에서만(1058
# mem), 식전후 마커는 태그가 있을 때만, 배터리·블루투스는 상태 표시다.
# 미터기 화살표는 여기 없다 — Instant 34장 전부에 있고 값에 묶인 지시자다.
STATEFUL_ELEMENTS = {"mem", "meal", "arrow", "icon:battery", "icon:bluetooth",
                     "icon:mem-flag", "icon:blood-drop", "icon:smile"}


def sample_corpus_value(rng):
    """값 샘플 — 코퍼스 자릿수 비율 반영(카드 「프로파일 확장」 AC#3).
    2,512행 실측: 2자리 20.5%, 3자리 79.5%(2026-09-12 measure_polarity digits).
    균일 randint(30, 511) 는 2자리가 14.5% 로 과소 대표됐다."""
    if rng.random() < 0.205:
        return rng.randint(30, 99)
    return rng.randint(100, 511)


def dot_text(img, x, y, text, glyph, ink):
    """도트매트릭스 문자 줄 — 작게 그린 글자를 2px 점 격자로 양자화.
    glyph 는 글자 높이 px(실측 4~10). 반환값: 그은 폭 px."""
    if glyph < 3:
        glyph = 3
    ch = glyph * 4 + 6
    cw = max(16, ch * len(text))
    canvas = np.zeros((ch, cw), np.uint8)
    cv2.putText(canvas, text, (2, ch - 5), cv2.FONT_HERSHEY_SIMPLEX,
                glyph / 20.0, 255, 1, cv2.LINE_8)
    dots = cv2.resize(canvas, (cw // 2, ch // 2),
                      interpolation=cv2.INTER_AREA) > 40
    H, W = img.shape[:2]
    for gy in range(dots.shape[0]):
        yy = y + gy
        if yy >= H:
            break
        for gx in range(dots.shape[1]):
            xx = x + gx
            if xx < W and dots[gy, gx]:
                img[yy, xx] = ink
    return cw // 2


def _tri(img, cx, cy, s, ink, direction="right"):
    """진행 삼각형(▶ 등) — fillPoly 자체 그림."""
    if direction == "right":
        pts = np.array([[cx - s, cy - s], [cx - s, cy + s], [cx + s, cy]], np.int32)
    else:  # up
        pts = np.array([[cx, cy - s], [cx - s, cy + s], [cx + s, cy + s]], np.int32)
    cv2.fillPoly(img, [pts], ink)


def _icon(img, kind, cx, cy, s, ink):
    """아이콘 — 실사진 관찰 묘사를 단순 벡터로 흉내(외부 자산 아님, 자체 그림)."""
    if kind == "curved-right":
        cv2.ellipse(img, (cx - s // 3, cy), (s // 2, s // 2), 0, -75, 75,
                    ink, 1, cv2.LINE_AA)
        _tri(img, cx + s // 6, cy - s // 2 + 2, 4, ink, "down")
    elif kind == "curved-left":
        cv2.ellipse(img, (cx + s // 3, cy), (s // 2, s // 2), 0, 105, 255,
                    ink, 1, cv2.LINE_AA)
        _tri(img, cx - s // 6, cy - s // 2 + 2, 4, ink, "down")
    elif kind == "tri-down":
        # 아래 화살표 — GluNEO plus 하단 시간줄 왼쪽(1435·1438·1440·1449 관찰)
        pts = np.array([[cx, cy + s], [cx - s, cy - s], [cx + s, cy - s]],
                       np.int32)
        cv2.fillPoly(img, [pts], ink)
    elif kind in ("tri-right", "triangle"):
        _tri(img, cx, cy, max(3, s // 2), ink, "right")
    elif kind == "battery":
        # 722(Gmate) 상단 우측: 얇은 외곽선 + 오른쪽 돌기 + 부분 채움(가는
        # 세로 막대 2개). 구판의 통짜 블록 둘은 진행 막대처럼 보였다(사람
        # blind 8/8 지적, 카드 2026-09-13 AC#4).
        cv2.rectangle(img, (cx - s, cy - s // 3), (cx + s, cy + s // 3), ink, 1)
        cv2.rectangle(img, (cx + s + 1, cy - s // 6), (cx + s + 3, cy + s // 6),
                      ink, -1)
        bw = max(2, s // 3)
        for k in range(2):
            bx = cx - s + 3 + k * (bw + 2)
            cv2.rectangle(img, (bx, cy - s // 3 + 3), (bx + bw, cy + s // 3 - 3),
                          ink, -1)
    elif kind == "blood-drop":
        cv2.ellipse(img, (cx, cy + s // 4), (s // 3, s // 3), 0, 0, 360, ink, 1)
        pts = np.array([[cx, cy - s // 2], [cx - s // 4, cy + s // 8],
                        [cx + s // 4, cy + s // 8]], np.int32)
        cv2.fillPoly(img, [pts], ink)
    elif kind == "bluetooth":
        cv2.circle(img, (cx, cy), s // 2, ink, 1)
        cv2.line(img, (cx - 3, cy - 5), (cx + 3, cy + 5), ink, 1, cv2.LINE_AA)
        cv2.line(img, (cx - 3, cy + 5), (cx + 3, cy - 5), ink, 1, cv2.LINE_AA)
    elif kind == "mem-flag":
        cv2.drawMarker(img, (cx, cy), ink, cv2.MARKER_SQUARE, s // 2, 1,
                       cv2.LINE_AA)
        cv2.line(img, (cx, cy - s // 2), (cx + 3, cy - s // 2 - 4), ink, 1)
    elif kind == "smile":
        cv2.circle(img, (cx, cy), s // 2, ink, 1)
        cv2.circle(img, (cx - s // 6, cy - s // 8), 1, ink, -1)
        cv2.circle(img, (cx + s // 6, cy - s // 8), 1, ink, -1)
        cv2.ellipse(img, (cx, cy + s // 10), (s // 3, s // 5), 0, 20, 160, ink, 1)


def render_profiled(value, rng, profile, size=(320, 160)):
    """프로파일 렌더. 라벨은 언제나 str(value) — 다른 요소는 라벨에 없다."""
    W, H = size
    label = str(value)
    panel = int(rng.uniform(150, 215))
    img = np.full((H, W), panel, dtype=np.uint8)
    polarity = rng.random() < 0.5
    if polarity:
        panel = int(rng.uniform(35, 95))
        ink_digit = int(rng.uniform(185, 245))
        ink_small = int(rng.uniform(150, 210))
    else:
        panel = int(rng.uniform(150, 215))
        ink_digit = int(rng.uniform(20, 90))
        ink_small = int(rng.uniform(60, 130))
    bez = int(rng.uniform(2, 8))
    cv2.rectangle(img, (0, 0), (W - 1, H - 1), int(rng.uniform(40, 90)),
                  thickness=bez)

    # 숫자 필드: slots 칸 전체(값이 아니라 칸 — 밴드 정의 2026-09-11 과 동일).
    # 앞쪽 빈 칸은 꺼진 슬롯으로 남는다. slots 에 튜플을 허용한다 — 카드
    # 「프로파일 확장」 AC#3: 칸 수가 3으로 고정되지 않게(익명 풀 등).
    slots_spec = profile.get("slots") or len(label)
    slots = rng.choice(list(slots_spec)) if isinstance(slots_spec, (tuple,
                                                                    list)) \
        else slots_spec
    slots = max(slots, len(label))
    dh = int(H * rng.uniform(*profile["digit_h"]))
    dw = int(dh * 0.58)
    pitch = dw + int(dw * 0.25)
    field_w = slots * dw + int(dw * 0.25) * (slots - 1)
    align = profile.get("align", "right")
    if align == "right":
        x0 = W - int(W * rng.uniform(0.04, 0.12)) - field_w
    elif align == "left":
        x0 = int(W * rng.uniform(0.06, 0.16))
    else:
        x0 = (W - field_w) // 2
    y0 = int(H * rng.uniform(0.18, 0.34))
    lead = slots - len(label)
    if USE_DSEG:
        # DSEG 팔 — 굵기·이탤릭은 표본마다 한 번 뽑고 화면 내내 일정(AC#2).
        # 잔상: 15% 표본에서만, 농도는 0.08~0.20 흔들림(2026-09-11 정정 —
        # 실물 잔상은 '생각보다 훨씬 약하다', 없음이 기본).
        variant = _pick_variant(rng, bool(profile.get("italic")))
        ghost = rng.uniform(0.08, 0.20) if rng.random() < 0.15 else 0.0
        for s in range(slots):
            if s < lead:
                continue
            draw_digit_dseg(img, x0 + s * pitch, y0, dh, label[s - lead],
                            ink_digit, variant, ghost)
        # 이탤릭은 폰트 변형이 담당 — 패널을 기울이는 전역 shear 는 쓰지
        # 않는다(광학 카드의 지적 그대로).
    else:
        for s in range(slots):
            if s < lead:
                continue
            draw_digit(img, x0 + s * pitch, y0, dw, dh, label[s - lead], ink_digit)
        if profile.get("italic"):   # rect 팔 — 기존 동작 재현
            sh = rng.uniform(0.18, 0.30)
            img = cv2.warpAffine(img, np.float32([[1, sh, -sh * H / 2], [0, 1, 0]]),
                                 (W, H), borderMode=cv2.BORDER_REPLICATE)
    last_r = x0 + field_w

    if profile.get("glulabel", {}).get("p", 0) > rng.random():
        gh = max(8, int(dh * 0.2))
        cv2.putText(img, "GLU", (x0 + int(field_w * rng.uniform(0.0, 0.3)),
                                 max(12, y0 - int(H * rng.uniform(0.04, 0.10)))),
                    cv2.FONT_HERSHEY_SIMPLEX, gh / 26.0, ink_small, 1, cv2.LINE_AA)

    # 단위 — 표기 변형을 섞는다(하나로 몰지 않는다, 카드 Notes).
    u = profile.get("unit")
    unit_right = last_r + int(dw * 0.3)
    if u and rng.random() < u["p"]:
        ut = u["texts"][rng.randrange(len(u["texts"]))]
        uh = max(7, int(dh * rng.uniform(*u["h_ratio"])))
        gap = int(rng.uniform(*u["gap"]))
        pos = u["pos"]
        if pos == "right-baseline":
            ux, uy = last_r + gap, y0 + dh - uh
        elif pos == "right-mid":
            ux, uy = last_r + gap, y0 + (dh - uh) // 2
        elif pos == "left-mid":
            ux = max(2, x0 - gap - int(uh * 2.4))
            uy = y0 + (dh - uh) // 2
        elif pos == "above-right":
            ux, uy = last_r - int(uh * 2.2), max(9, y0 - int(H * rng.uniform(0.05, 0.12)))
        else:  # below
            ux, uy = int(W * rng.uniform(0.5, 0.62)), y0 + dh + int(H * 0.05)
        cv2.putText(img, ut, (ux, uy + uh), cv2.FONT_HERSHEY_SIMPLEX,
                    uh / 26.0, ink_small, 1, cv2.LINE_AA)
        unit_right = ux + int(uh * 2.6)

    # 식전·식후 마커. 실물 관례 표기(AC/PC) — 이 40장 표본에서 관찰은 0건이고
    # AC#5 요건으로 렌더한다(보고서에 관찰 0건 명시).
    meal = profile.get("meal")
    if meal and rng.random() < meal["p"]:
        mh = max(7, int(dh * 0.16))
        cv2.putText(img, meal["texts"][rng.randrange(2)],
                    (min(W - 20, unit_right + 4), y0 + dh - mh),
                    cv2.FONT_HERSHEY_SIMPLEX, mh / 26.0, ink_small, 1, cv2.LINE_AA)

    m = profile.get("mem")
    if m and rng.random() < m["p"]:
        mh = max(8, int(dh * 0.22))
        if m["pos"] == "top-left":
            mx, my = int(W * 0.06), int(H * 0.14)
        elif m["pos"] == "top-right":
            mx, my = int(W * 0.72), int(H * 0.14)
        elif m["pos"] == "below-left":
            mx, my = int(W * 0.08), y0 + dh + int(H * 0.08)
        else:  # right-of-digits
            mx, my = last_r + int(dw * 0.4), y0 + (dh - mh) // 2 + mh
        if m["kind"] == "M-box":
            cv2.rectangle(img, (mx - 2, my - mh - 2), (mx + mh + 2, my + 2),
                          ink_small, 1)
        cv2.putText(img, m["kind"][:3] if m["kind"] != "M-box" else "M",
                    (mx, my), cv2.FONT_HERSHEY_SIMPLEX, mh / 24.0,
                    ink_small, 1, cv2.LINE_AA)

    a = profile.get("arrow")
    if a and rng.random() < a["p"]:
        s = int(rng.uniform(*a["size"]))
        gap = int(rng.uniform(*a["gap"]))
        kind = a["kinds"][rng.randrange(len(a["kinds"]))]
        if a.get("pos") == "below-left":
            # 숫자 아래 왼쪽 — GluNEO plus 하단 화살표(1435 등 4장 관찰)
            ax = int(W * rng.uniform(0.06, 0.14))
            ay = y0 + dh + int(H * rng.uniform(0.05, 0.09))
        else:
            ax = min(W - s, last_r + gap)
            ay = y0 + int(dh * rng.uniform(0.15, 0.55))
        _icon(img, kind, ax, ay, s, ink_small)

    for kind, pos, p in profile.get("icons", []):
        if rng.random() > p:
            continue
        s = max(8, int(dh * rng.uniform(0.28, 0.4)))
        if pos == "top-right":
            cx, cy = W - int(W * rng.uniform(0.06, 0.12)), int(H * rng.uniform(0.08, 0.16))
        elif pos == "top-left":
            cx, cy = int(W * rng.uniform(0.05, 0.10)), int(H * rng.uniform(0.08, 0.16))
        else:  # right-mid — 숫자 밴드 오른쪽(혈액방울 실측 285~315,60~90)
            cx, cy = W - int(W * rng.uniform(0.04, 0.10)), y0 + int(dh * rng.uniform(0.3, 0.6))
        _icon(img, kind, cx, cy, s, ink_small)

    da = profile.get("dotrow_above")
    if da and rng.random() < da["p"]:
        g = int(rng.uniform(*da["glyph"]))
        dot_text(img, int(W * rng.uniform(0.05, 0.30)), int(H * rng.uniform(0.06, 0.14)),
                 da["texts"][rng.randrange(len(da["texts"]))], g, ink_small)
    db = profile.get("dotrow_below")
    if db and rng.random() < db["p"]:
        g = int(rng.uniform(*db["glyph"]))
        fmt = db["fmts"][rng.randrange(len(db["fmts"]))]
        txt = fmt.format(h02=f"{rng.randint(0, 12):02d}", m02=f"{rng.randint(0, 59):02d}",
                         M=f"{rng.randint(1, 12)}", M02=f"{rng.randint(1, 12):02d}",
                         d=f"{rng.randint(1, 31)}", d02=f"{rng.randint(1, 31):02d}",
                         am=random.choice(["am", "pm"]), AM=random.choice(["AM", "PM"]))
        dot_text(img, int(W * rng.uniform(0.05, 0.35)),
                 y0 + dh + int(H * rng.uniform(0.05, 0.10)), txt, g, ink_small)

    t = profile.get("time")
    if t and rng.random() < t["p"]:
        th = int(dh * rng.uniform(0.28, 0.42))
        ty = y0 + dh + int(H * rng.uniform(0.04, 0.08))
        hh = f"{rng.randint(0, 23):02d}:{rng.randint(0, 59):02d}"
        if t["pos"] == "below-right":
            tx = int(W * rng.uniform(0.5, 0.65))
        elif t["pos"] == "top-left":
            # 숫자 위 왼쪽 — ACCU-CHEK Active 상단 시간줄(1329·2519 관찰)
            tx = int(W * rng.uniform(0.06, 0.15))
            ty = max(th, y0 - int(H * rng.uniform(0.10, 0.16)))
        elif t["pos"] == "top-right":
            tx = int(W * rng.uniform(0.68, 0.80))
            ty = max(th, y0 - int(H * rng.uniform(0.10, 0.16)))
        elif t["pos"] == "below-right":
            pass
        else:
            tx = int(W * rng.uniform(0.06, 0.30))
        put_7seg_text(img, tx, ty, int(W * 0.3), th, hh, ink_small)

    if profile.get("avgrow", {}).get("p", 0) > rng.random():
        ah = int(dh * rng.uniform(0.24, 0.34))
        ay2 = y0 + dh + int(H * rng.uniform(0.05, 0.09))
        cv2.putText(img, f"{rng.randint(1, 30):02d} DAY AVG",
                    (int(W * rng.uniform(0.08, 0.20)), ay2 + ah),
                    cv2.FONT_HERSHEY_SIMPLEX, ah / 26.0, ink_small, 1, cv2.LINE_AA)
        put_7seg_text(img, int(W * rng.uniform(0.45, 0.60)), ay2, int(W * 0.2), ah,
                      f"{rng.randint(1, 999):03d}", ink_small)

    if profile.get("daterow", {}).get("p", 0) > rng.random():
        rh = max(7, int(dh * 0.18))
        ry = y0 + dh + int(H * rng.uniform(0.08, 0.13))
        cv2.putText(img, f"{rng.randint(1, 12)}-{rng.randint(1, 31)}  #{rng.randint(1, 9)}",
                    (int(W * rng.uniform(0.06, 0.25)), ry),
                    cv2.FONT_HERSHEY_SIMPLEX, rh / 24.0, ink_small, 1, cv2.LINE_AA)

    b = profile.get("bezel")
    if b and rng.random() < b["p"]:
        face = [cv2.FONT_HERSHEY_SIMPLEX, cv2.FONT_HERSHEY_TRIPLEX,
                cv2.FONT_HERSHEY_COMPLEX][rng.randrange(3)]
        text = b["texts"][rng.randrange(len(b["texts"]))]
        if b["edge"] == "top":
            bx, by = int(W * rng.uniform(0.25, 0.6)), int(H * 0.10)
        else:
            bx, by = int(W * rng.uniform(0.2, 0.55)), H - 6
        cv2.putText(img, text, (bx, by), face, 0.42, ink_small, 1, cv2.LINE_AA)
    if profile.get("buttons"):
        for bxx in (int(W * 0.2), int(W * 0.78)):
            _tri(img, bxx, H - 8, 5, ink_small, "up")

    # 광학·노이즈·기하 계층 — 레거시와 같은 배치·같은 확률(변인 통제).
    img = np.clip(img.astype(np.float32)
                  + np.random.normal(0, rng.uniform(2, 9), img.shape),
                  0, 255).astype(np.uint8)
    if rng.random() < 0.4:
        img = cv2.GaussianBlur(img, (3, 3), rng.uniform(0.3, 1.0))
    if rng.random() < 0.3:
        img = cv2.GaussianBlur(img, (5, 5), rng.uniform(0.5, 1.2))
    a_, b_ = rng.uniform(0.75, 1.25), rng.uniform(-25, 25)
    img = np.clip(img.astype(np.float32) * a_ + b_, 0, 255).astype(np.uint8)
    for _ in range(rng.randint(0, 2)):
        ex, ey = rng.randint(0, W - 1), rng.randint(0, H - 1)
        ax_, ay_ = rng.randint(W // 12, W // 5), rng.randint(H // 12, H // 5)
        glare = int(min(255, panel + rng.uniform(50, 100)))
        msk = np.zeros((H, W), np.float32)
        cv2.ellipse(msk, (ex, ey), (ax_, ay_), rng.uniform(0, 180), 0, 360, 1, -1)
        msk *= rng.uniform(0.15, 0.3)
        img = np.clip(img.astype(np.float32) * (1 - msk) + glare * msk,
                      0, 255).astype(np.uint8)
    yy, xx = np.mgrid[0:H, 0:W]
    d2 = ((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 2)) ** 2
    img = np.clip(img.astype(np.float32) * (1.0 - rng.uniform(0.08, 0.22) * d2),
                  0, 255).astype(np.uint8)
    if rng.random() < 0.35:
        img = add_local_shadow(img, rng)
    if rng.random() < 0.30:
        img = add_reflection_stripe(img, rng)
    if rng.random() < 0.15:   # 프로파일은 자릿수 이탤릭을 별도 처리하므로 전역
        img = apply_shear(img, rng)   # shear 확률을 0.20 -> 0.15 로 낮춘다
    if rng.random() < 0.25:
        img = apply_keystone(img, rng)
    if rng.random() < 0.7:
        M2 = cv2.getRotationMatrix2D((W / 2, H / 2), rng.uniform(-1.5, 1.5), 1.0)
        img = cv2.warpAffine(img, M2, (W, H), borderValue=int(rng.uniform(30, 80)))
    return img, label


def render_any(value, rng, size=(320, 160), profile=None):
    """프로파일 지정 렌더. None 이면 PROFILES 에서 균등 추출."""
    if profile is None:
        profile = PROFILES[rng.randrange(len(PROFILES))]
    if profile.get("legacy"):
        return render_screen(value, rng, size)
    return render_profiled(value, rng, profile, size)


def generate_profiled(count, seed0, out_dir, size=(320, 160)):
    """균등 프로파일(레거시 generic_v1 포함). 산출 형식은 synth_lcd.generate 와
    동일(images/*.png + labels_{seed}.json) — build_cache_v2 가 그대로 흡수한다."""
    rng = random.Random(seed0)
    out = Path(out_dir)
    (out / "images").mkdir(parents=True, exist_ok=True)
    labels = {}
    for i in range(count):
        val = sample_corpus_value(rng)
        img, label = render_any(val, rng, size)
        name = f"synth_{seed0}_{i}"
        cv2.imwrite(str(out / "images" / f"{name}.png"), img)
        labels[name] = label
    (out / f"labels_{seed0}.json").write_text(
        json.dumps(labels, ensure_ascii=False, indent=0), encoding="utf-8")
    print(f"generated {count} profiled -> {out}")


if __name__ == "__main__":
    import sys
    count = int(sys.argv[1]) if len(sys.argv) > 1 else 3000
    seed = int(sys.argv[2]) if len(sys.argv) > 2 else 19000
    out = sys.argv[3] if len(sys.argv) > 3 else "synth_screens_profiled"
    generate_profiled(count, seed, out)
