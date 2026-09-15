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
# 폰트: DSEG v0.46 (keshikan, SIL OFL 1.1) — fonts/dseg/ 에 원문 라이선스 동봉.
# 변형 선택 근거(눈 검증, _diag/synth_real_atlas/dseg_variant_check.png):
# 실기기 8종 숫자 밴드와 나란히 놓아 Classic 계열이 전체적으로 가장 가깝고
# (모따기 끝단 근사), 굵기는 기기별로 Light/Regular/Bold 가 다 나오며,
# 이탤릭 기기(OneTouch 계열)엔 Italic 변형, 일부 가는획 기기엔 Modern-Light.
# 라이선스(RFN 'DSEG'): 폰트 파일은 수정·재배포하지 않고 렌더에만 쓴다.
# 글리프 획 부풀림 비율(높이 대비). 0 이면 폰트 그대로.
# 획 부풀림 — 글리프 높이 대비 비율. 0 이면 끈다.
# 2026-09-14 재측정: 합성 획굵기/밴드높이 median 0.061 vs 실사진 0.093 (n=272).
# 실사진 p25(0.085)가 합성 p75(0.069)보다 커서 분포가 거의 겹치지 않았다.
# 값은 추측하지 않고 스윕으로 맞춘다 — SYNTH_GLYPH_DILATE 로 덮어 잰다.
GLYPH_DILATE = float(__import__("os").environ.get("SYNTH_GLYPH_DILATE", "0.0"))

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
    m = cv2.resize(m, (max(2, int(m.shape[1] * h / m.shape[0])), h),
                   interpolation=cv2.INTER_NEAREST) > 96
    # 획 부풀림은 되돌렸다(사람 지시 2026-09-13) — 상/중/하 3분할로 숫자가
    # 커지면 굵기도 같이 해결될 것이라는 판단이다. GLYPH_DILATE 를 0 보다
    # 크게 두면 다시 켜진다.
    k = max(1, int(round(h * GLYPH_DILATE)))
    if GLYPH_DILATE > 0 and k > 1:
        m = cv2.dilate(m.astype(np.uint8), np.ones((k, k), np.uint8)) > 0
    return m


def _pick_variant(rng, italic):
    w = __import__("os").environ.get("SYNTH_FORCE_WEIGHT") or         DSEG_WEIGHTS[rng.randrange(len(DSEG_WEIGHTS))]
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
        evidence=["glucose_batch1/267", "glucose_batch1/270",
                  "glucose_batch2/2610", "glucose_batch1/2492",
                  "glucose_batch1/2039"],
        # 화살표-끝자리 갭 실측 72~84px(스트립 12장) — 넓은 범위로 흔들어
        # '거의 닿는' 배치까지 재현한다(AC#5).
        unit=dict(texts=["mg/dL"], pos="below-right", gap=(2, 80), p=0.9),
        # 미터기 지시 화살표(AC#5): 검은 창 안 오른쪽 가장자리의 흰 ▶ 이
        # 몸체에 인쇄된 점 눈금 열을 가리킨다. 근거 Instant 34장 — 화살표는
        # 값에 대응해 위로 오르고 v159+ 에서 상단에 포화된다(2026-09-13
        # 실측). 단독 아이콘이 아니라 지시자라 kinds 는 tri-right 하나다.
        arrow=dict(kinds=["tri-right"], gap=(2, 80), p=0.95),
        meter=True,
        time=dict(pos="below-left", p=0.9),
        bezel=dict(texts=["ACCU-CHEK", "Instant"], edge="top", p=0.9),
    ),
    dict(
        id="gmate", slots=3, align="right", italic=False,
        evidence=["glucose_batch1/842", "glucose_batch1/843",
                  "glucose_batch1/731", "glucose_batch1/727"],
        # 단위 글리프가 끝자리에 4~5px 로 붙는다(아틀라스 재고표) — 실패 서명.
        unit=dict(texts=["mg/dL", "mg /dL"], pos="below-right", gap=(3, 8), p=1.0),
        meal=dict(texts=["AC", "PC"], p=0.3),
        mem=dict(kind="M", pos="below-left", p=0.5),
        time=dict(pos="below-left", p=0.85),
        bezel=dict(texts=["Gmate"], edge="top", p=0.9),
    ),
    dict(
        # align 은 right 다(2026-09-13 정정) — left 면 2자리 값의 빈 슬롯이
        # 오른쪽에 생긴다. 실물은 숫자가 오른쪽에 맞고 빈칸이 왼쪽이다.
        id="dorucos_premium", slots=3, align="right", italic=False,
        evidence=["glucose_batch1/120", "glucose_batch1/694",
                  "glucose_batch1/695"],
        # 도트 패널이 아니다(2026-09-13 정정). 근거 사진 120 을 3배 확대해
        # 보면 큰 숫자가 꼭짓점 뾰족한 7-세그먼트이고, 694·695 도 같다.
        # 화면 아래 한 줄은 '3.21  08:41 AM' — 날짜+시간이고 역시 세그먼트다.
        # 'OK'·'CHECK STRIP' 윗줄은 세 장 어디에도 없다. 도트 렌더를 쓰는
        # 프로파일은 이제 하나도 없다.
        unit=dict(texts=["mg/dL"], pos="below-right", gap=(8, 14), p=0.9),
        dotrow_below=dict(fmts=["{M}.{d02}  {h02}:{m02} {AM}"], p=1.0),
        bezel=dict(texts=["Premium"], edge="bottom", p=1.0),
    ),
    dict(
        id="green_doctor", slots=3, align="right", italic=False,
        evidence=["glucose_batch1/1781", "glucose_batch1/2498"],
        glulabel=dict(p=0.9),
        unit=dict(texts=["mg/dL"], pos="below-right", gap=(6, 14), p=0.6),
        mem=dict(kind="M-box", pos="top-left", p=0.7),
        # 자리는 기기 안에서 고정돼야 한다(사람 지적 2026-09-15: 어떤 장은
        # 좌상단에 삼각형, 어떤 장은 M 이 떴다). mem 이 top-left 를 쓰므로
        # 삼각형은 top-right 하나만 둔다 — 한 자리를 둘이 다투지 않게.
        icons=[("triangle", "top-right", 0.4),
               ("blood-drop", "right-mid", 0.3)],
        time=dict(pos="below-left", p=0.7),
        bezel=dict(texts=["GREEN Doctor"], edge="top", p=0.8),
        buttons=True,
    ),
    dict(
        id="onetouch_ultra", slots=3, align="right", italic=True,
        evidence=["glucose_batch1/1058", "glucose_batch1/2110"],
        unit=dict(texts=["mg/dL"], pos="below-right", gap=(8, 40), p=0.9),
        mem=dict(kind="mem", pos="top-right", p=0.4),
        time=dict(pos="below-left", p=0.5),
        # 실물 1058·2110: 화면 위에 'OneTouch Ultra', 아래에 'LIFESCAN' —
        # 둘 중 하나가 아니라 둘 다 찍혀 있다(사람 지적 2026-09-13).
        bezel=dict(per_edge={"top": "OneTouch Ultra", "bottom": "LIFESCAN"},
                   texts=["OneTouch Ultra", "LIFESCAN"], p=1.0),
    ),
    dict(
        id="gc_ms_one", slots=3, align="right", italic=False,
        evidence=["glucose_batch1/228", "glucose_batch1/373",
                  "glucose_batch1/800"],
        glulabel=dict(p=0.9),
        unit=dict(texts=["mg/dL"], pos="below-right", gap=(2, 8), p=0.9),
        mem=dict(kind="M-box", pos="top-left", p=0.9),
        # 아래줄은 하나다 — 시간·날짜를 한 줄에 같이 쓴다(실물 228 의
        # '9:10  3:22'). 구판은 time(0.8)과 dotrow_below(0.4)를 따로 굴려
        # 같은 기기 안에서 아래줄이 장마다 달랐다(사람 지적 2026-09-13).
        dotrow_below=dict(fmts=["{h02}:{m02}   {M}-{d}"], p=1.0),
        # 228 몸체 상단 'GC 녹십자MS / ONE' — 한글은 Hershey 가 못 그려
        # 라틴 부분만 쓴다(없는 글자를 지어내지 않는다).
        bezel=dict(texts=["ONE"], edge="top", p=0.8),
    ),
    dict(
        id="acura_plus", slots=3, align="right", italic=False,
        evidence=["glucose_batch1/475", "glucose_batch1/477",
                  "glucose_batch1/2357"],
        unit=dict(texts=["mg/dL"], pos="below-right", gap=(4, 12), p=0.8),
        # avgrow('07 DAY AVG 019') 철회(2026-09-13) — 근거 사진 475·477·
        # 2357 어디에도 없다. 셋 다 화면 맨 아래가 '04-22  16:45'(날짜+시간)
        # 한 줄이다. 배치 실패로 120장 중 12장에서 빠지던 요소이기도 했다.
        dotrow_below=dict(fmts=["{M02}-{d02}   {h02}:{m02}"], p=1.0),
        bezel=dict(texts=["ACURA PLUS"], edge="top", p=1.0),
    ),
    dict(
        id="caresens_n_premier", slots=3, align="right", italic=False,
        evidence=["glucose_batch1/1911", "glucose_batch1/1903"],
        unit=dict(texts=["mg/dL"], pos="below-right", gap=(10, 18), p=0.9),
        # 세로형에서 M 은 숫자 옆이 아니라 상단이다(사람 판정 2026-09-15).
        # 근거 사진 1911·1903 을 다시 볼 것 — 선언을 바꾼 것이라 확인이 필요하다.
        mem=dict(kind="M", pos="top-left", p=0.5),
        icons=[("mem-flag", "right-of-digits", 0.5), ("battery", "top-right", 1.0)],
        dotrow_below=dict(fmts=DOT_FMTS, p=0.9),
        bezel=dict(texts=["CareSens N", "Premier"], edge="top", p=0.8),
    ),
    dict(
        id="performa_silver", slots=3, align="right", italic=False,
        evidence=["glucose_batch1/1186"],
        unit=dict(texts=["mg/dL"], pos="below-right", gap=(4, 10), p=0.9),
        mem=dict(kind="memory", pos="top-left", p=0.6),
        daterow=dict(p=0.8),    # '7-1' '#5' — 기록번호 포함
        bezel=dict(texts=["Performa"], edge="bottom", p=0.7),
        icons=[("battery", "top-right", 1.0), ("blood-drop", "right-mid", 0.3)],
    ),
    dict(
        # Performa 와 이름만 형제다(사람 2026-09-13). 1019~1086 여덟 장은
        # 파랗게 빛나는 백라이트 액정에 흰 숫자다 — 은색 Performa(1186 등
        # 여덟 장, 반사식·검은 숫자)와 다른 물건이다. 한 프로파일로 묶어
        # 극성을 평균(mixed 0.5) 내던 것을 쪼갠다. 기하는 측정이 두 기기를
        # 합쳐 잰 값 하나뿐이라 당분간 같이 쓴다(별도 측정 전까지).
        id="performa_nano", slots=3, align="right", italic=False,
        evidence=["glucose_batch1/1019", "glucose_batch1/1060",
                  "glucose_batch1/1073", "glucose_batch1/1086"],
        unit=dict(texts=["mg/dL"], pos="below-right", gap=(4, 10), p=0.9),
        mem=dict(kind="memory", pos="top-left", p=0.9),
        daterow=dict(p=0.9),
        bezel=dict(texts=["Performa Nano"], edge="top", p=0.7),
    ),
    dict(
        id="accuchek_active", slots=3, align="center", italic=False,
        evidence=["glucose_batch1/1329", "glucose_batch2/2502",
                  "glucose_batch2/2513", "glucose_batch2/2519"],
        # 상단에 시간(왼쪽)·날짜(오른쪽) 작은 줄, 숫자는 중앙 대형,
        # mg/dL 은 숫자 아래 오른쪽(1329 '0:00 0-0' + 하단 mg/dL 관찰).
        unit=dict(texts=["mg/dL"], pos="below-right", gap=(4, 12), p=0.9),
        time=dict(pos="top-left", p=0.85),
        daterow=dict(p=0.8),
        bezel=dict(texts=["Active"], edge="top", p=0.6),
    ),
    dict(
        id="gluneo_plus", slots=3, align="center", italic=False,
        evidence=["glucose_batch1/1435", "glucose_batch1/1438",
                  "glucose_batch1/1440", "glucose_batch1/1449"],
        # 대형 중앙 숫자, mg/dL 은 숫자 아래 오른쪽, 하단 줄 왼쪽에 아래
        # 화살표 아이콘 + 오른쪽 시간(1435~1449 전 관찰). 온도 표기 '28C' 는
        # 화이트리스트 밖이라 렌더하지 않는다(보고서 명시).
        unit=dict(texts=["mg/dL"], pos="below-right", gap=(4, 12), p=0.9),
        time=dict(pos="below-right", p=0.9),
        # 구판의 '왼쪽 아래 아래화살표' 는 뺐다(2026-09-13). 실물
        # 821·2016·838·2003 의 그 자리는 온도(29C) 옆 온도계 아이콘이지
        # 화살표가 아니다. 화살표를 오른쪽으로 옮기면 없는 것을 지어내는
        # 셈이라 선언 자체를 거둔다.
        bezel=dict(texts=["GluNEO plus"], edge="top", p=0.8),
    ),
    dict(
        # 가로형 1 — 숫자 왼쪽 큰 자리 + 오른쪽 정보 칼럼(시간·날짜·mg/dL·M).
        # 근거 1588·1590·1593·1596·1598·1602(8장 눈검 2026-09-13). 남색 몸체에
        # 은색 띠, 브랜드는 화면 '왼쪽' 몸체에 인쇄돼 있어 상/하 베젤 경로로는
        # 못 그린다 — bezel 을 선언하지 않는다. 극성은 정상(검은 숫자).
        # 기하는 실측: device_layout_stats --wide, n=28.
        id="onetouch_ultramini", slots=3, align="right", italic=False,
        family="column",
        evidence=["glucose_batch1/1588", "glucose_batch1/1590",
                  "glucose_batch1/1596", "glucose_batch1/1598",
                  "glucose_batch1/1602"],
        unit=dict(texts=["mg/dL"], pos="below-right", gap=(4, 10), p=1.0),
        # M 은 좌측 상단이다(사람 판정 2026-09-15). 가로형이라도 그렇다 —
        # 오른쪽은 시간·날짜·단위가 쌓인 정보 칼럼이라 M 이 낄 자리가 아니고,
        # 숫자 옆은 단위를 딴 데 두고 M 만 붙는 셈이라 앞뒤가 안 맞는다.
        mem=dict(kind="M", pos="top-left", p=0.5),
        # 칼럼의 시간은 시각만이다 — 날짜는 아래 별도 줄이다(1588 '7:10PM'
        # + '8-20'). 전역 DOT_FMTS 에는 날짜까지 붙은 긴 형식이 섞여 있어
        # 칼럼 폭을 넘겨 통째로 탈락했다.
        time=dict(pos="column", fmts=["{h02}:{m02} {AM}"], p=1.0),
    ),
    dict(
        # 가로형 2 — 같은 칼럼 가족인데 반전 액정(흰 숫자)이고 더 납작하다.
        # 숫자가 화면 맨 왼쪽에 붙는다(실측 cx 0.092). 근거 1091·1094·1815·
        # 1622·1624·1627·1822. 기종 미상이라 베젤 문자열이 없다.
        id="wide_unknown", slots=3, align="left", italic=False,
        family="column",
        evidence=["glucose_batch1/1091", "glucose_batch1/1094",
                  "glucose_batch1/1815"],
        unit=dict(texts=["mg /dL"], pos="below-right", gap=(4, 10), p=1.0),
        time=dict(pos="column", fmts=["{h02}:{m02}{AM}"], p=1.0),
    ),
    dict(
        id="generic_v1", legacy=True, evidence=[],
        # 기존 무작위 레이아웃(synth_lcd.render_screen) 그대로. 8종 프로파일에
        # 없는 배치의 다양성 하한을 지킨다.
        # 칸 수는 3 고정이다. 사람 밴드 라벨 규약이 '빈 앞칸을 포함한 슬롯
        # 필드 전체'인데(2026-09-12 재측정: 2자리 밴드 폭이 3자리와 사실상
        # 같다), slots=2 로 그리면 앞 빈칸이 없어 라벨 규약과 어긋난다
        # (사람 지적 2026-09-13: "나한테는 라벨링할 때 빈자리 넣으라더니").
        slots=3,
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
# ── 기기 고정 레이아웃 — 실측 분포(p10, 중앙, p90) ────────────────────────
# device_layout_stats.py --emit 산출을 그대로 붙인다(weight 만 손으로 잇는다 —
# 실측 축이 아니라 눈검 배정이다). 숫자는 손으로 고치지 않는다.
#
# 2026-09-13 2차: 기기당 '한 점'(중앙값)이던 것을 세 점으로 바꿨다. 한 점으로
# 못박으니 합성 코퍼스가 기기 수만큼의 점이 되고 검출기가 그 사이를 못 메웠다
# — 실사진 게이트 IoU 가 0.717 -> 0.680 으로 떨어졌다(v0 vs v1, 2026-09-13).
# 실물은 같은 기기도 촬영 각도·거리로 화면 종횡비와 밴드 비율이 흔들린다
# (UltraMini ar p10/p90 1.627/2.463, 세로형은 대개 ±5~10%). 기기가 중심을
# 정하고 촬영이 그 주위를 흔드는 구조로 되돌린다.
#
# 값은 전부 GM 쿼드 기준이다: ar = 쿼드 w/h, bw·bh·cx·cy = 쿼드 대비 비율.
# 세로·가로를 한 번에 재므로 기기가 어느 쪽인지도 실측이 정한다 — gluneo_plus
# 는 ar 1.161 로 가로형인데 구판은 세로 전용 측정의 폴백(0.792)을 쓰고 있었다.
# ── 기기 고정 레이아웃 — 실측 분포(p10, 중앙, p90) ────────────────────────
# device_layout_stats.py --emit 산출을 그대로 붙인다(weight 만 손으로 잇는다 —
# 실측 축이 아니라 눈검 배정이다). 숫자는 손으로 고치지 않는다.
#
# 2026-09-13 2차: 기기당 '한 점'(중앙값)이던 것을 세 점으로 바꿨다. 한 점으로
# 못박으니 합성 코퍼스가 기기 수만큼의 점이 되고 검출기가 그 사이를 못 메웠다
# — 실사진 게이트 IoU 가 0.717 -> 0.680 으로 떨어졌다(v0 vs v1, 2026-09-13).
# 실물은 같은 기기도 촬영 각도·거리로 화면 종횡비와 밴드 비율이 흔들린다
# (UltraMini ar p10/p90 1.627/2.463, 세로형은 대개 ±5~10%). 기기가 중심을
# 정하고 촬영이 그 주위를 흔드는 구조로 되돌린다.
#
# 값은 전부 GM 쿼드 기준이다: ar = 쿼드 w/h, bw·bh·cx·cy = 쿼드 대비 비율.
# 세로·가로를 한 번에 재므로 기기가 어느 쪽인지도 실측이 정한다 — gluneo_plus
# 는 ar 1.161 로 가로형인데 구판은 세로 전용 측정의 폴백(0.792)을 쓰고 있었다.
LAYOUTS = {
    "onetouch_ultramini": dict(weight="Regular", ar=(2.306, 2.64, 2.736), bw=(0.382, 0.496, 0.556), bh=(0.696, 0.798, 0.849),
                            cx=(0.328, 0.357, 0.424), cy=(0.502, 0.52, 0.539), n=30),
    "wide_unknown": dict(weight="Regular", ar=(1.815, 2.103, 3.516), bw=(0.339, 0.579, 0.618), bh=(0.698, 0.807, 0.84),
                      cx=(0.28, 0.318, 0.394), cy=(0.475, 0.491, 0.505), n=16),
    "performa_nano": dict(weight="Regular", ar=(0.756, 0.784, 0.847), bw=(0.751, 0.773, 0.842), bh=(0.372, 0.395, 0.444),
                       cx=(0.474, 0.493, 0.521), cy=(0.399, 0.439, 0.448), n=8),
    "performa_silver": dict(weight="Light", ar=(0.716, 0.774, 0.793), bw=(0.841, 0.859, 0.895), bh=(0.374, 0.4, 0.438),
                         cx=(0.493, 0.527, 0.572), cy=(0.416, 0.432, 0.452), n=8),
    "accuchek_active": dict(weight="Regular", ar=(0.783, 0.808, 0.832), bw=(0.774, 0.85, 0.875), bh=(0.389, 0.42, 0.447),
                         cx=(0.486, 0.495, 0.51), cy=(0.441, 0.46, 0.471), n=7),
    "accuchek_instant": dict(weight="Bold", ar=(0.807, 0.863, 0.917), bw=(0.764, 0.791, 0.852), bh=(0.398, 0.439, 0.458),
                          cx=(0.453, 0.47, 0.5), cy=(0.442, 0.467, 0.491), n=4),
    "acura_plus": dict(weight="Bold", ar=(0.928, 0.941, 0.983), bw=(0.83, 0.884, 0.936), bh=(0.544, 0.585, 0.6),
                    cx=(0.498, 0.502, 0.504), cy=(0.385, 0.394, 0.402), n=4),
    "caresens_n_premier": dict(weight="Light", ar=(0.72, 0.8, 0.862), bw=(0.817, 0.889, 0.959), bh=(0.433, 0.471, 0.511),
                            cx=(0.503, 0.514, 0.538), cy=(0.366, 0.389, 0.412), n=4),
    "green_doctor": dict(weight="Regular", ar=(0.766, 0.866, 0.924), bw=(0.847, 0.901, 0.985), bh=(0.398, 0.427, 0.454),
                      cx=(0.507, 0.539, 0.566), cy=(0.423, 0.481, 0.507), n=4),
    "gc_ms_one": dict(weight="Regular", ar=(0.79, 0.836, 0.909), bw=(0.89, 0.989, 1.016), bh=(0.419, 0.462, 0.483),
                   cx=(0.504, 0.515, 0.544), cy=(0.489, 0.514, 0.537), n=4),
    "gmate": dict(weight="Regular", ar=(0.708, 0.71, 0.74), bw=(0.99, 0.995, 1.002), bh=(0.374, 0.39, 0.41),
               cx=(0.492, 0.51, 0.531), cy=(0.386, 0.408, 0.451), n=4),
    "onetouch_ultra": dict(weight="Light", ar=(0.926, 0.972, 1.032), bw=(0.848, 0.917, 0.966), bh=(0.408, 0.464, 0.505),
                        cx=(0.494, 0.523, 0.549), cy=(0.382, 0.392, 0.404), n=4),
    "gluneo_plus": dict(weight="Regular", ar=(1.113, 1.185, 1.239), bw=(0.74, 0.791, 0.863), bh=(0.435, 0.466, 0.478),
                     cx=(0.523, 0.533, 0.546), cy=(0.361, 0.421, 0.442), n=4),
    "dorucos_premium": dict(weight="Regular", ar=(0.822, 0.83, 0.833), bw=(0.878, 0.916, 0.924), bh=(0.451, 0.468, 0.486),
                         cx=(0.51, 0.526, 0.528), cy=(0.395, 0.403, 0.424), n=3),
}
# ── 극성은 재는 것이 아니라 선언하는 것이다(사람 지시 2026-09-13) ─────────
# 액정이 음각(반전)인지 양각인지는 기기의 성질이고 사람이 이미 안다. 사진에서
# 달라 보이는 것은 극성이 아니라 대비이고, 대비는 별도 축으로 이미 재고 있다
# (real_baseline.polarity.contrast, 렌더의 열화 계수).
#
# 측정으로 되찾으려던 시도는 실패했다 — 사람 정답 30장에 자를 채점했더니
# 최선의 정의도 26/30 이고, 남은 오차가 하필 프로파일 기기에 몰렸다:
# Green Doctor 3/4 반전(사진 4장 전부 정상) · ACURA PLUS 4/4 반전(3장 전부
# 정상) · Gmate 1/4(4장 전부 정상). 자를 더 깎을 자리가 아니다.
#
# 근거는 각 값 옆 사진 id — 2026-09-13 에 사람이 눈으로 확인한 장들이다.
# 프로파일 <-> 코퍼스 기기 이름. 극성 파생에 쓰던 표였는데 극성이 사람 선언으로
# 바뀌면서 2026-09-13 에 같이 지웠다가 되살린다 — 파생용이 아니라 '이 프로파일이
# 코퍼스의 어느 기기인가' 라는 사실 자체이고, 실측 자(device_layout_stats)가
# 프로파일 기기만 골라 재는 데 쓴다.
PROFILE_DEVICES = {
    "accuchek_instant": ["ACCU-CHEK Instant"],
    "gmate": ["Gmate"],
    "dorucos_premium": ["도루코S Premium"],
    "green_doctor": ["GC 녹십자 MS Green Doctor"],
    "onetouch_ultra": ["OneTouch Ultra"],
    "gc_ms_one": ["GC 녹십자 MS ONE"],
    "acura_plus": ["ACURA PLUS"],
    "caresens_n_premier": ["CareSens N Premier"],
    "performa_silver": ["ACCU-CHEK Performa"],
    "performa_nano": ["ACCU-CHEK Performa Nano"],
    "accuchek_active": ["ACCU-CHEK Active"],
    "gluneo_plus": ["GluNEO plus"],
    # 가로형 — 프로파일은 아직 없다(2026-09-13). 실측 자가 이 이름으로
    # 기하를 뽑을 수 있게 먼저 적어 둔다.
    "onetouch_ultramini": ["OneTouch UltraMini"],
    "wide_unknown": ["이름모를 가로형모델"],
}

PROFILE_INVERTED = {
    "gmate": False,               # 842·843·731·727 검은 숫자
    "onetouch_ultra": False,      # 1058
    "gc_ms_one": False,           # 228
    "acura_plus": False,          # 475·477·2357
    "dorucos_premium": False,     # 120·694·695
    "performa_silver": False,     # 1186 외 은색 반사식 8장
    "green_doctor": False,        # 1759·1780·2500·648·1781
    "accuchek_active": False,     # 1329·2502·2519·2520·2525·2601·2606
    "gluneo_plus": False,         # 1435·1438·1449
    "caresens_n_premier": True,   # 1911·819·1899 어두운 액정·밝은 숫자
    "accuchek_instant": True,     # 267·270 검은 창·흰 숫자
    "performa_nano": True,        # 1019~1086 백라이트 액정·흰 숫자
    "onetouch_ultramini": False,  # 1588·1590·1596·1598·1602 검은 숫자
    "wide_unknown": True,         # 1091·1094·1815 흰 숫자·어두운 액정
}


def lay_val(lay, key, rng):
    """레이아웃 축 하나를 뽑는다 — (p10, 중앙, p90) 삼각분포.
    한 렌더 안에서 축마다 한 번만 뽑아 재사용한다 — 같은 축을 두 번 뽑으면
    밴드 폭과 위치가 서로 다른 장의 것이 섞인다."""
    lo, mid, hi = lay[key]
    if hi - lo < 1e-6:
        return mid
    return rng.triangular(lo, hi, mid)


def lay_val(lay, key, rng):
    """레이아웃 축 하나를 뽑는다 — (p10, 중앙, p90) 삼각분포.
    한 렌더 안에서 축마다 한 번만 뽑아 재사용한다 — 같은 축을 두 번 뽑으면
    밴드 폭과 위치가 서로 다른 장의 것이 섞인다."""
    lo, mid, hi = lay[key]
    if hi - lo < 1e-6:
        return mid
    return rng.triangular(lo, hi, mid)

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
        bezel_h=r.uniform(0.055, 0.085),   # 몸체 인쇄 글자 높이 / 유리 폭
        mg_l=r.uniform(0.01, 0.07), mg_r=r.uniform(0.01, 0.07),
        mg_t=r.uniform(0.04, 0.13), mg_b=r.uniform(0.04, 0.15),
        time_fmt_i=r.randrange(len(DOT_FMTS)),
        dotrow_i=r.randrange(8),
        polarity_u=r.random(),       # mixed 기기의 극성을 한 번에 확정
        # 칸 피치(숫자 높이 대비)도 액정 셀의 기하라 기기 형질이다. 구판은
        # 세로형에서 렌더마다 rng.uniform 을 뽑아 같은 기기의 칸 비례가
        # 장마다 흔들렸다. **맨 끝에 추가한다** — 중간에 넣으면 뒤따르는
        # 형질의 난수가 전부 밀려 기존 기기 외형이 통째로 바뀐다.
        pitch_u=r.random(),
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
# 배터리는 상태성이 아니다 — 기기가 가졌으면 언제나 표시한다(사람 지시
# 2026-09-13). 실물 혈당계의 배터리 표시는 잔량계라 늘 켜져 있다.
# 화살표는 상태성이 아니다 — 기기가 가졌으면 계속 표시한다(사람 지시
# 2026-09-13). 나머지(mem·meal·bluetooth·mem-flag·blood-drop·smile)는 전부
# 옵션이다: 켜 있을 수도 꺼 있을 수도 있다.
STATEFUL_ELEMENTS = {"mem", "meal", "icon:bluetooth",
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
    """진행 삼각형(▶ 등) — fillPoly 자체 그림.
    구판은 "right" 와 그 밖(=위)만 알았다. curved-right/left 아이콘이
    "down" 을 넘기고 있었는데 위 삼각형이 그려졌다(2026-09-13 전수 검토)."""
    if direction == "right":
        pts = [[cx - s, cy - s], [cx - s, cy + s], [cx + s, cy]]
    elif direction == "left":
        pts = [[cx + s, cy - s], [cx + s, cy + s], [cx - s, cy]]
    elif direction == "down":
        pts = [[cx - s, cy - s], [cx + s, cy - s], [cx, cy + s]]
    else:  # up
        pts = [[cx, cy - s], [cx - s, cy + s], [cx + s, cy + s]]
    cv2.fillPoly(img, [np.array(pts, np.int32)], ink)


def tri_dir_for(pos):
    """자리 이름에서 삼각형이 향할 방향을 정한다(사람 규칙 2026-09-15):
    오른쪽에 있으면 오른쪽, 왼쪽이면 왼쪽, 혈당 아래면 아래, 위면 위.

    전에는 `triangle` 이 자리와 무관하게 늘 오른쪽을 가리켰다 — green_doctor
    왼쪽 위 삼각형이 오른쪽을 향했다. 방향은 자리에서 나오는 것이지 종류에
    붙는 성질이 아니다."""
    p = (pos or "").lower()
    if "left" in p:
        return "left"
    if "right" in p:
        return "right"
    if p.startswith("below") or "bottom" in p or "down" in p:
        return "down"
    if p.startswith("top") or "above" in p:
        return "up"
    return "right"


def _icon(img, kind, cx, cy, s, ink, pos=None):
    """아이콘 — 실사진 관찰 묘사를 단순 벡터로 흉내(외부 자산 아님, 자체 그림).

    pos 를 주면 방향성 아이콘(triangle)이 그 자리에 맞는 쪽을 향한다."""
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
    elif kind == "triangle":
        # 방향은 자리에서 나온다 — pos 가 없으면 옛 기본값(오른쪽).
        _tri(img, cx, cy, max(3, s // 2), ink, tri_dir_for(pos))
    elif kind == "tri-right":
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
        # 구판은 '원 테두리 + 그 위에 뜬 삼각형' 이라 물방울로 안 보였다
        # (사람 지적 2026-09-15: "원 위에 검은 삼각형 올려논건 뭘 표현하고
        # 싶은거지?"). 아래 둥근 몸통과 위 뾰족한 꼭지가 **한 덩어리**로
        # 이어져야 물방울이다 — 채운 원과 채운 삼각형을 겹쳐 붙인다.
        r = max(2, s // 3)
        bx, by = cx, cy + s // 5
        cv2.circle(img, (bx, by), r, ink, -1)
        pts = np.array([[cx, cy - s // 2],
                        [bx - r, by - r // 3],
                        [bx + r, by - r // 3]], np.int32)
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


# ── 은퇴한 320x160 렌더러(2026-09-13) ────────────────────────────────────
# render_profiled / render_any / generate_profiled 를 여기서 지웠다.
#
# 리더의 합성 팔이 이 함수들을 썼고, 검출기의 합성 팔은 synth_panel 을 썼다.
# 두 렌더러가 같은 축에서 서로 다른 답을 들고 있었다 — 극성(여기: rng<0.5
# 동전던지기 / 저기: 사람 선언), 글리프 폭 비율(0.58·dh / 0.78~0.84·피치),
# 단위 자리(숫자 옆 / 숫자 아래), 기기 개념(없음 / 12종 형질 고정).
# 리더를 다시 구우면 두 모델이 서로 다른 세계를 배우게 돼 있었다.
#
# 이제 리더도 synth_panel 을 본다(build_profiled_cache -> render_panel ->
# reader_view). 프레이밍도 실사진 팔과 같은 함수를 통과한다
# (build_cache_v2.framed_src_rect, BOX_MARGIN 10%).
#
# 되살릴 일이 있으면 git 에서 꺼낸다 — 커밋 메시지에 이 사정이 적혀 있다.
# draw_digit_dseg 와 USE_DSEG 도 이 경로 전용이라 함께 나갔다.


# ── 영역 선언 — 액정 설계자가 화면을 잡는 방식(lcd_layout.build_layout)
# 유리 안쪽 패딩을 두고, 남은 면을 top/mid/bottom 이 **빈틈없이** 나눈다.
# mid 가 숫자 자리다. 미터기 기기는 오른쪽 트랙을 따로 떼고, 가로형은
# 오른쪽 정보 칼럼을 뗀다.
#
# 초안은 실측(LAYOUTS 의 bh·cy·bw)에서 유도했다 — 구조를 바꾸면서
# 그림까지 튀면 무엇이 원인인지 못 가린다. 기기별 조정은 사진을 보고
# 사람이 한다.
REGIONS = {
    "accuchek_instant": dict(pad=(0.104, 0.020, 0.060, 0.060), rows=(0.188, 0.439, 0.253), track_right=0.12),
    "gmate": dict(pad=(0.020, 0.020, 0.060, 0.060), rows=(0.153, 0.390, 0.337)),
    "dorucos_premium": dict(pad=(0.042, 0.042, 0.059, 0.060), rows=(0.110, 0.468, 0.303)),
    "green_doctor": dict(pad=(0.049, 0.049, 0.060, 0.060), rows=(0.207, 0.427, 0.245)),
    "onetouch_ultra": dict(pad=(0.041, 0.041, 0.056, 0.060), rows=(0.104, 0.464, 0.316)),
    "gc_ms_one": dict(pad=(0.020, 0.020, 0.060, 0.060), rows=(0.223, 0.462, 0.195)),
    "acura_plus": dict(pad=(0.058, 0.058, 0.036, 0.060), rows=(0.066, 0.585, 0.254)),
    "caresens_n_premier": dict(pad=(0.055, 0.055, 0.054, 0.060), rows=(0.100, 0.471, 0.316)),
    "performa_silver": dict(pad=(0.071, 0.071, 0.060, 0.060), rows=(0.172, 0.400, 0.308)),
    "performa_nano": dict(pad=(0.113, 0.113, 0.060, 0.060), rows=(0.181, 0.395, 0.303)),
    "accuchek_active": dict(pad=(0.075, 0.075, 0.060, 0.060), rows=(0.190, 0.420, 0.270)),
    "gluneo_plus": dict(pad=(0.104, 0.104, 0.060, 0.060), rows=(0.128, 0.466, 0.286)),
    "onetouch_ultramini": dict(pad=(0.03, 0.03, 0.042, 0.028), column_right=0.444, rows=(0.0, 1.0, 0.0)),
    "wide_unknown": dict(pad=(0.03, 0.03, 0.031, 0.037), column_right=0.361, rows=(0.0, 1.0, 0.0)),
}
