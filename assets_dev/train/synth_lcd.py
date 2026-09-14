# 합성 LCD 화면 렌더러 — CTC 리더 학습 데이터 무한 생성.
# 실사진에서 관찰된 요소를 모두 포함: 회색 패널, 7세그 숫자 1~3개(우정렬),
# 소수점(가끔), 작은 시간줄(아래), 단위 텍스트(오른쪽/아래 랜덤), mem 표시(가끔),
# 극성 반전, 노이즈·블러·밝기 변화, 살짝 기울임.
#
# G27(2026-09-05) 실화면화 — 사용자 오류 보고 5종에서 나온 빠진 요소 넷:
#   국소 그림자 경계(1717·694) · 선형 반사 줄무늬(488·845) · shear 이탤릭(101)
#   · 키스톤(사다리꼴 원근). 확률·범위는 지시서 값 그대로다.
import random
from pathlib import Path

import cv2
import numpy as np

SEG_MAP = {
    "0": "abcdef", "1": "bc", "2": "abged", "3": "abgcd", "4": "fgbc",
    "5": "afgcd", "6": "afgedc", "7": "abc", "8": "abcdefg", "9": "abcdfg",
}


def draw_digit(img, x, y, w, h, ch, ink, thickness=None):
    t = thickness or max(3, int(w * 0.22))
    m = max(2, int(t * 0.6))
    on = SEG_MAP[ch]
    hw = (w - 2 * m) // 2
    hh = (h - 2 * m) // 2
    segs = {
        "a": (x + m, y, w - 2 * m, t),
        "d": (x + m, y + h - t, w - 2 * m, t),
        "g": (x + m, y + h // 2 - t // 2, w - 2 * m, t),
        "f": (x, y + m, t, hh),
        "b": (x + w - t, y + m, t, hh),
        "e": (x, y + h // 2 + m, t, hh),
        "c": (x + w - t, y + h // 2 + m, t, hh),
    }
    for s in on:
        if s in segs:
            sx, sy, sw, sh = segs[s]
            cv2.rectangle(img, (sx, sy), (sx + sw - 1, sy + sh - 1), ink, -1)


def put_7seg_text(img, x, y, w, h, text, ink, gap_ratio=0.25):
    cw = int(w / max(1, len(text)))
    for i, ch in enumerate(text):
        if ch == ":":
            r = max(2, h // 8)
            cx = x + i * cw + cw // 2
            cv2.rectangle(img, (cx - r, y + h // 3), (cx + r, y + h // 3 + 2 * r), ink, -1)
            cv2.rectangle(img, (cx - r, y + 2 * h // 3), (cx + r, y + 2 * h // 3 + 2 * r), ink, -1)
        elif ch == " ":
            continue
        elif ch in SEG_MAP:
            draw_digit(img, x + i * cw, y, int(cw * 0.72), h, ch, ink)


# ── 세그먼트 스트로크 폰트 — 카드 「합성 글리프 네 결함」(2026-09-13) ──────────
# LCD 보조 글자는 Hershey 벡터 폰트의 곡선을 쓸 수 없다 — 세그먼트 LCD 의 획은
# 전부 직선이다. 근거: glucose_batch1/722(Gmate) — 값·시간·단위·days 줄이 전부
# 각진 세그먼트 글자고 콜론은 사각 점 두 개('1:27'). 스트로크 표는 실물 계산기
# 세그먼트 글자 관례(대부분 축정렬, 굳은 모서리)를 따라 자체 정의했다(외부
# 폰트 자산 아님). 좌표는 글자 셀 안 0..1 (x 오른쪽, y 아래). 소문자 x-높이
# 상단 0.42, 대문자는 전 높이.
#
# 2026-09-13 2차(사람 리뷰): 1차 지그재그 대각선 글자('m' 등)가 작은 크기에서
# 깨져 보였고, 예약 폭(seg_text_width)이 실제 그은 폭보다 글자당 간격(h/8)
# 만큼 적어 단위·mem 이 배치 박스를 뚫고 나갔다(실측 'mg/dL' +10px, h=30).
# 글자를 계산기식 블록 형태로 바꾸고 폭 계산을 seg_char_advance 단일 소스로
# 통일했다. 굵기·이탤릭 변형은 큰 숫자의 DSEG 변형(_pick_variant)과 같은
# 계열을 따른다 — 한 패널 안에서 숫자와 보조 글자의 굵기·기울기가 일치.
# ── 작은 글자는 세그먼트가 아니다(2026-09-13 확정) ───────────────────────
# 한때 14-세그 행렬(SEG14_GEO/SEG14_MAP/SEG14_RAW)로 알파벳을 그렸다. 근거로
# 든 사진 722(Gmate)를 확대해 보니 반대였다 — 722·713·842 셋 다 날짜·시간
# '숫자'는 세그먼트인데 'mg/dL'·'pm'·'Review'·'Average' 는 일반 폰트다
# ('g' 의 내림획, 'R' 의 곡선). 물리적으로도 그렇다: 그 글자들은 유리에 인쇄된
# 고정 범례이고, 세그먼트로 구동되는 것은 값이 변하는 자리(숫자)뿐이다.
#
# 그래서 행렬과 font 파라미터를 지웠다. 규칙은 하나로 남는다:
#   숫자·콜론 -> 세그먼트 · 글자·기호 -> 폰트
# 행렬이 필요해지면 git 에서 꺼낸다(기호 / - . # 항목이 없어 미완성이었다 —
# seg14 모드에서 폭만 예약하고 잉크는 안 그렸다).
# 굵기 변형 — 큰 숫자의 DSEG 변형(DSEG_WEIGHTS, 실기기 8종 눈검 근거)과
# 같은 3계열. 두께/높이 비율.
SEG_WEIGHTS = {"Light": .08, "Regular": .11, "Bold": .15}
# 이탤릭 전단 계수(양수=오른쪽 기울임) — DSEG Italic 관례각 ~10°.
SEG_SLANT = 0.17


def seg_weight_from_variant(variant):
    """DSEG 변형 이름(put_7seg_text 큰 숫자용) -> 보조 글자 굵기 키."""
    if "Bold" in variant:
        return "Bold"
    if "Light" in variant:      # ModernLight 포함
        return "Light"
    return "Regular"


_HERSHEY_W = {}
_GLYPH_CACHE = {}
_LEGEND_FONT = {}

# 인쇄 범례는 좁다 — 폭을 눌러 콘덴스드로 만든다(842·1058·267 눈검).
LEGEND_SQUEEZE = 0.82


def _legend_font(px):
    """인쇄 범례용 TTF. Hershey 획 폰트는 글자가 둥글고 넓어 'mg/dL' 이
    벌어져 보였다(사람 지적 세 번, 2026-09-13: "폰트 변경이 필요하면 변경하라").
    DejaVuSans-Bold 는 sugartrain 환경의 matplotlib 이 이미 갖고 있고 라이선스가
    허용적이다(Bitstream Vera 계열). 없으면 Hershey 로 떨어진다."""
    if px in _LEGEND_FONT:
        return _LEGEND_FONT[px]
    f = None
    try:
        import matplotlib
        from pathlib import Path as _P
        from PIL import ImageFont
        d = _P(matplotlib.__file__).parent / "mpl-data" / "fonts" / "ttf"
        f = ImageFont.truetype(str(d / "DejaVuSans-Bold.ttf"), px)
    except Exception:
        f = None
    _LEGEND_FONT[px] = f
    return f


def _letter_ink(ch, h, thick):
    """글자 한 자의 (마스크, 잉크 폭, 베이스라인 오프셋).

    세로 위치는 폰트 메트릭이 정한다 — 잉크 상자만 잘라 바닥에 맞추면
    하이픈·마침표처럼 잉크가 작은 글자가 베이스라인으로 떨어진다
    (2026-09-13 '2-25' 에서 그랬다). 글자를 고정 베이스라인에 그린 뒤
    가로로만 잘라 내고, 그릴 때 베이스라인을 맞춘다."""
    key = (ch, h, thick)
    if key in _GLYPH_CACHE:
        return _GLYPH_CACHE[key]
    font = _legend_font(max(6, int(round(h * 1.36))))
    if font is not None:
        from PIL import Image, ImageDraw
        asc, desc = font.getmetrics()
        box_h = asc + desc + 4
        pil = Image.new("L", (int(h * 2.6) + 8, box_h), 0)
        ImageDraw.Draw(pil).text((4, 0), ch, font=font, fill=255)
        a = np.asarray(pil)
        xs = np.nonzero(a.max(0) > 96)[0]
        if len(xs):
            m = a[:, xs.min():xs.max() + 1] > 96
            w2 = max(2, int(round(m.shape[1] * LEGEND_SQUEEZE)))
            m = cv2.resize(m.astype(np.uint8) * 255, (w2, m.shape[0]),
                           interpolation=cv2.INTER_AREA) > 96
            _GLYPH_CACHE[key] = (m, m.shape[1], asc)
            return _GLYPH_CACHE[key]
    t = max(1, thick)
    (w0, h0), b0 = cv2.getTextSize("M", cv2.FONT_HERSHEY_SIMPLEX, 1.0, t)
    scale = h / max(1, h0 + b0)
    (w, hh), bb = cv2.getTextSize(ch, cv2.FONT_HERSHEY_SIMPLEX, scale, t)
    pad = max(2, t + 2)
    cv = np.zeros((hh + bb + 2 * pad, w + 2 * pad), np.uint8)
    cv2.putText(cv, ch, (pad, pad + hh), cv2.FONT_HERSHEY_SIMPLEX, scale, 255,
                t, cv2.LINE_AA)
    xs = np.nonzero(cv.max(0) > 96)[0]
    if len(xs) == 0:
        _GLYPH_CACHE[key] = (None, 0, 0)
    else:
        m = cv[:, xs.min():xs.max() + 1] > 96
        _GLYPH_CACHE[key] = (m, m.shape[1], pad + hh)
    return _GLYPH_CACHE[key]


def seg_char_advance(ch, h, slant=0.0, digit_w=None):
    """글자 하나의 진폭(px) — 그리기와 폭 계산이 같은 값을 쓴다(단일 소스).
    1차 결함: seg_text_width 가 간격을 빼먹어 실제 그은 폭보다 적었다."""
    # 자간은 글자 종류마다 다르다(2026-09-13). 7-세그 숫자는 칸 사이가 실제로
    # 벌어져 있지만(실물 '103'·'125' 의 자리 간격), 인쇄 범례는 붙어 있다 —
    # 842·1058·267 의 'mg/dL' 은 글자끼리 거의 닿는다. 구판은 둘 다 0.13h 를
    # 써서 'mg/dL' 이 'm g / d L' 로 벌어졌고, 가로형 정보 칼럼에서는 그 폭
    # 때문에 단위·시간이 통째로 배치 실패로 탈락했다(칼럼이 비어 나왔다).
    dgap = max(1, int(round(h * 0.13)))    # 숫자·콜론 — 세그먼트 칸 간격
    # 인쇄 범례는 글자끼리 거의 닿는다(842·1058·267 의 mg/dL). Hershey 는
    # 글리프 좌우에 자체 여백을 갖고 있어, 간격을 0 으로 둬도 벌어져 보인다 —
    # 그 여백만큼 당긴다(사람 지적 2026-09-13, 두 번째).
    # 진폭이 잉크 폭이므로 간격은 실제 글자 사이 간격 그대로다.
    lgap = max(1, int(round(h * 0.055)))   # 글자·기호 — 인쇄 자간
    if ch == " ":
        return int(round(h * 0.42))
    if ch == ":":
        # 콜론은 획 굵기와 같은 사각 점 두 개다. 앞뒤로 숫자 간격을 준다 —
        # 구판은 뒤에만 줘서 앞 글자에 붙어 나왔다(사람 지적 3회, 2026-09-13).
        return max(2, int(round(h * 0.12))) + 2 * dgap
    if ch in "-.":
        # 날짜의 '-' 는 폰트 하이픈이 아니라 7-세그의 가운데 획(g)이다. '.' 도
        # 세그먼트 점이다. 폰트로 그리면 굵기와 성격이 숫자와 달라진다
        # (사람 지적 2026-09-13). 진폭도 숫자 칸에서 낸다.
        _c = digit_w if digit_w else h * 0.62
        return int(round(_c * (0.62 if ch == "-" else 0.30))) + dgap
    if ch in SEG_MAP:                      # 숫자 — 큰 숫자와 같은 글리프
        cell = digit_w if digit_w else h * 0.62
        gap = dgap
    else:                                  # 글자·기호 — 언제나 폰트
        _m, cell, _ = _letter_ink(ch, h, max(2, int(round(h * 0.11))))
        gap = lgap
    lean = int(slant * h) if slant else 0   # 기운 글자가 위에서 차지하는 폭
    return int(round(cell)) + gap + lean


def _seg_lead(h):
    """줄 앞 여유 — 첫 글자 획의 왼쪽 반침(획 중심 원점 기준). 두께는
    변형에 따라 최대 Bold(0.15h) 까지라 그 절반+안티앨리어싱 1px."""
    return int(round(h * 0.075)) + 1


def _seg_trailing(h, slant=0.0):
    """줄 끝 여유 — 마지막 글자 획의 오른쪽 반침(최대 굵기 Bold 0.15h 기준)
    + 이탤릭 끝글자 기움이 간격(0.13h)을 넘는 몫."""
    return int(round(h * 0.15)) + 4 + (int(round(h * 0.05)) if slant else 0)


def seg_text_width(text, h, slant=0.0, digit_w=None):
    """seg_text 가 그을 폭(px) — 배치 사각형 계산용. seg_char_advance 합
    + 줄 끝 여유. seg_text 반환값과 같은 공식이다."""
    return sum(seg_char_advance(ch, h, slant, digit_w) for ch in text) \
        + _seg_trailing(h, slant)


def _seg_draw_upright(canvas, x, y, text, h, thick, slant=0.0,
                      digit_mask=None, digit_w=None):
    """오프스크린 캔버스에 정자로 그린다(값 255). 이탤릭 전단은 seg_text
    에서 한다 — 다만 진폭은 slant 를 포함해 잡아 전단 뒤 글자끼리 겹치지
    않게 한다(이탤릭 활자가 넓은 이유와 같다). 숫자는 7-세그, 콜론은 사각
    점 두 개(근거 722), 글자·기호는 폰트."""
    cx = x
    for ch in text:
        if ch == " ":
            cx += seg_char_advance(ch, h, slant, digit_w)
            continue
        if ch == ":":
            # 사각 점 두 개 — 크기는 획 굵기, 자리는 획이 놓이는 높이다.
            r = max(2, int(round(h * 0.12)))
            gx = cx + max(1, int(round(h * 0.13)))
            for fy in (0.28, 0.62):
                cv2.rectangle(canvas, (gx, y + int(h * fy)),
                              (gx + r, y + int(h * fy) + r), 255, -1)
            cx += seg_char_advance(ch, h, slant, digit_w)
            continue
        if ch in "-.":
            # 7-세그 획으로 그린다 — 굵기·색이 숫자와 같아진다.
            _c = digit_w if digit_w else int(h * 0.62)
            if ch == "-":
                bw = max(2, int(round(_c * 0.62)))
                yy = y + h // 2 - max(1, thick // 2)
                cv2.rectangle(canvas, (cx, yy), (cx + bw, yy + thick), 255, -1)
            else:
                r = max(2, thick)
                cv2.rectangle(canvas, (cx, y + h - r), (cx + r, y + h), 255, -1)
            cx += seg_char_advance(ch, h, slant, digit_w)
            continue
        if ch in SEG_MAP:
            # 작은 숫자도 큰 숫자와 같은 글리프를 쓴다(digit_mask 주입).
            # 구판은 여기서만 사각형 세그먼트(draw_digit)를 그려, 한 화면에
            # 두 가지 글리프 체계가 섞였다(사람 지적 2026-09-13: 큰 숫자는
            # DSEG 인데 시간줄은 다른 물건으로 보인다).
            if digit_mask is not None:
                m = digit_mask(ch, h)
                if m is not None:
                    reg = canvas[y:y + m.shape[0], cx:cx + m.shape[1]]
                    hh = min(reg.shape[0], m.shape[0])
                    ww = min(reg.shape[1], m.shape[1])
                    reg[:hh, :ww][m[:hh, :ww]] = 255
            else:
                draw_digit(canvas, cx, y, int(h * 0.62), h, ch, 255,
                           thickness=thick)
            cx += seg_char_advance(ch, h, slant, digit_w)
            continue
        m, iw, base = _letter_ink(ch, h, thick)
        if m is not None:
            # 베이스라인을 글자 줄 바닥에 맞춘다.
            oy = max(0, y + h - base)
            reg = canvas[oy:oy + m.shape[0], cx:cx + m.shape[1]]
            h2 = min(reg.shape[0], m.shape[0])
            w2 = min(reg.shape[1], m.shape[1])
            reg[:h2, :w2][m[:h2, :w2]] = 255
        cx += seg_char_advance(ch, h, slant, digit_w)


def seg_text(img, x, y, text, h, ink, thick=None, slant=0.0,
             digit_mask=None, digit_w=None):
    """세그먼트 보조 글자 줄. 숫자는 7-세그(SEG_MAP), 콜론은 사각 점
    두 개(put_7seg_text 와 같은 관례, 근거 722 '1:27'). 글자·기호는 폰트다 —
    실물에서 그 자리는 세그먼트가 아니라 유리에 인쇄된 고정 범례다
    (722·713·842, 2026-09-13).
    thick: 획 두께(기본 Regular). slant: 이탤릭 전단(0.17 ≈ DSEG Italic) —
    숫자·콜론까지 통째로 기울인다(오프스크린 전단). 반환값: 그은 폭 px.
    폭은 seg_char_advance 단일 소스라 seg_text_width 와 어긋나지 않는다."""
    t = thick or max(2, int(round(h * SEG_WEIGHTS["Regular"])))
    lead = _seg_lead(h)
    ov = t // 2 + 1          # 획 중심이 아닌 왼쪽 가장자리를 원점에 맞추는 몫
    w = seg_text_width(text, h, slant, digit_w)
    t_pad = t + 2
    ch_box = h + 2 * t_pad                  # 14-세그는 내림글자가 없다
    canvas = np.zeros((ch_box + t_pad, w + 2 * t_pad), np.uint8)
    _seg_draw_upright(canvas, t_pad + lead + ov, t_pad, text, h, t, slant,
                      digit_mask, digit_w)
    if slant:
        sh = slant * (canvas.shape[0] - 1)
        M = np.float32([[1, -slant, sh], [0, 1, 0]])
        canvas = cv2.warpAffine(canvas, M, (canvas.shape[1], canvas.shape[0]),
                                flags=cv2.INTER_NEAREST,
                                borderMode=cv2.BORDER_CONSTANT, borderValue=0)
    # 캔버스 안 글자 원점은 t_pad+lead+ov(ov=획 반침 몫) — 합성은
    # (x-t_pad-lead, y-t_pad) 에 대고 붙인다. 잉크의 왼쪽 가장자리가 x 에,
    # 오른쪽은 trailing 안에 들어온다.
    ox = x - t_pad - lead
    reg = img[max(0, y - t_pad):y - t_pad + canvas.shape[0],
              max(0, ox):ox + canvas.shape[1]]
    m = canvas[:reg.shape[0], :reg.shape[1]] > 128
    reg[m] = ink
    return w


def put_small_text(img, x, y, text, h, ink):
    cv2.putText(img, text, (x, y + h), cv2.FONT_HERSHEY_SIMPLEX,
                max(0.35, h / 28.0), ink, max(1, h // 14), cv2.LINE_AA)


def add_local_shadow(img, rng):
    """국소 그림자 — 임의 방향 직선 경계 한쪽을 밝기 계수 0.55~0.85 로 낮춘다.

    1717(그림자 경계가 293 을 가로질러 29 는 어둡고 3 은 밝다)·694(상단 그림자로
    7 의 윗획이 배경으로) 재현. 경계는 폭 5~25px 가우시안 블러로 부드럽게.
    """
    H, W = img.shape[:2]
    k = rng.uniform(0.55, 0.85)          # 어두운 쪽 밝기 계수
    t = int(rng.uniform(5, 25))          # 경계 부드러움 폭(px)
    ang = rng.uniform(0, 180)            # 경계선 방향
    cx, cy = rng.uniform(0, W), rng.uniform(0, H)
    yy, xx = np.mgrid[0:H, 0:W]
    ca, sa = np.cos(np.radians(ang)), np.sin(np.radians(ang))
    d = (xx - cx) * ca + (yy - cy) * sa  # 경계선 법선 좌표
    hard = ((d < 0) * (1.0 - k)).astype(np.float32)
    ksz = max(3, t) | 1                  # 홀수 커널
    soft = cv2.GaussianBlur(hard, (ksz, ksz), 0)
    return np.clip(img.astype(np.float32) * (1.0 - soft), 0, 255).astype(np.uint8)


def add_reflection_stripe(img, rng):
    """선형 반사 줄무늬 — 폭 3~12px, 대각선의 0.3~0.9배 길이, 밝기 +30~90.

    488(거울 반사의 희미한 선을 세그먼트로 오인)·845(반사광 155→1559) 재현.
    포화(255) 는 클리프 — 실제로도 채도된 반사광은 하얗게 붕괴된다.
    """
    H, W = img.shape[:2]
    w = rng.uniform(3, 12)                              # 폭(px)
    ln = rng.uniform(0.3, 0.9) * (W * W + H * H) ** 0.5  # 길이(px)
    ang = rng.uniform(0, 180)
    cx, cy = rng.uniform(0, W), rng.uniform(0, H)
    add = rng.uniform(30, 90)
    yy, xx = np.mgrid[0:H, 0:W]
    ca, sa = np.cos(np.radians(ang)), np.sin(np.radians(ang))
    du = (xx - cx) * ca + (yy - cy) * sa     # 줄 방향 좌표
    dv = -(xx - cx) * sa + (yy - cy) * ca    # 줄 법선 좌표
    prof = np.exp(-(dv ** 2) / (2 * (w / 2) ** 2))       # 폭 방향 가우시안
    taper = np.clip(1.0 - (np.abs(du) / (ln / 2)) ** 2, 0, 1)  # 길이 방향 테이퍼
    return np.clip(img.astype(np.float32) + add * prof * taper,
                   0, 255).astype(np.uint8)


def apply_shear(img, rng):
    """shear(이탤릭) — x 방향 −0.25~+0.25. 101(숫자가 이탤릭체) 재현.

    참고: 7seg-image-generator(Apache-2.0)는 −10~30° 를 쓴다(±0.25 ≈ ∓14°).
    """
    H, W = img.shape[:2]
    sh = rng.uniform(-0.25, 0.25)
    M = np.float32([[1, sh, -sh * H / 2], [0, 1, 0]])
    return cv2.warpAffine(img, M, (W, H), borderMode=cv2.BORDER_REPLICATE)


def apply_keystone(img, rng):
    """키스톤 — 네 모서리를 화면 폭·높이의 0~6% 안에서 안쪽으로 밀어 원근 흉내."""
    H, W = img.shape[:2]
    fx = [rng.uniform(0, 0.06) for _ in range(4)]
    fy = [rng.uniform(0, 0.06) for _ in range(4)]
    src = np.float32([[0, 0], [W - 1, 0], [W - 1, H - 1], [0, H - 1]])
    dst = np.float32([
        [fx[0] * W, fy[0] * H],
        [(W - 1) - fx[1] * W, fy[1] * H],
        [(W - 1) - fx[2] * W, (H - 1) - fy[2] * H],
        [fx[3] * W, (H - 1) - fy[3] * H],
    ])
    M = cv2.getPerspectiveTransform(src, dst)
    return cv2.warpPerspective(img, M, (W, H), borderMode=cv2.BORDER_REPLICATE)


def render_screen(value, rng, size=(320, 160)):
    """value: int(30~511). returns (gray uint8 image, label str)."""
    W, H = size
    label = str(value)
    panel = int(rng.uniform(150, 215))
    img = np.full((H, W), panel, dtype=np.uint8)
    # 패널 밖(베젤) — 화면 가장자리에 어두운 띠
    bez = int(rng.uniform(2, 8))
    cv2.rectangle(img, (0, 0), (W - 1, H - 1), int(rng.uniform(40, 90)), thickness=bez)

    # 극성: 정상(밝은 패널+어두운 숫자) / 반전(어두운 패널+밝은 숫자)
    polarity = rng.random() < 0.5
    if polarity:
        panel = int(rng.uniform(35, 95))
        ink_digit = int(rng.uniform(185, 245))
        ink_small = int(rng.uniform(150, 210))
    else:
        panel = int(rng.uniform(150, 215))
        ink_digit = int(rng.uniform(20, 90))
        ink_small = int(rng.uniform(60, 130))

    # 숫자 행: 우측 정렬 블록, 위쪽 45~75% 높이
    dh = int(H * rng.uniform(0.30, 0.42))
    dw = int(dh * 0.58)
    y0 = int(H * rng.uniform(0.10, 0.30))
    n = len(label)
    block_w = n * dw + int(dw * 0.25 * (n - 1))
    x0 = W - int(W * rng.uniform(0.04, 0.12)) - block_w
    ink = (ink_digit, ink_digit, ink_digit) if False else (ink_digit,)
    xcur = x0
    for i, ch in enumerate(label):
        wj = int(dw * rng.uniform(0.88, 1.12))
        draw_digit(img, xcur, y0, wj, dh, ch, ink_digit)
        xcur += wj + int(dw * 0.25)

    # 소수점 (10% 확률, 마지막 자리 뒤)
    if rng.random() < 0.10:
        r = max(2, dh // 10)
        px = x0 + block_w + int(dw * 0.1)
        py = y0 + dh - r * 2
        cv2.rectangle(img, (px, py), (px + r * 2, py + r * 2), ink_digit, -1)

    # 시간 줄 (아래, 작게) — 70% 확률
    if rng.random() < 0.7:
        th = int(dh * rng.uniform(0.30, 0.45))
        ty = y0 + dh + int(H * 0.04)
        tx = int(W * rng.uniform(0.06, 0.30))
        hh = f"{rng.randint(0,23):02d}:{rng.randint(0,59):02d}"
        put_7seg_text(img, tx, ty, int(W * rng.uniform(0.28, 0.45)), th, hh, ink_small)
        if rng.random() < 0.5:
            put_small_text(img, tx + int(W * 0.25), ty, "DAY", th, ink_small)

    # 단위 텍스트 (오른쪽 or 아래, 80% 확률)
    if rng.random() < 0.8:
        uh = max(9, int(dh * rng.uniform(0.18, 0.32)))
        if rng.random() < 0.5:
            put_small_text(img, x0 + block_w + 4, y0 + dh - uh, "mg/dL", uh, ink_small)
        else:
            put_small_text(img, int(W * 0.62), y0 + dh + int(H * 0.05), "mg/dL", uh, ink_small)

    # mem 표시 (가끔, 좌상단)
    if rng.random() < 0.35:
        put_small_text(img, int(W * 0.08), int(H * 0.08), "mem", max(8, int(dh * 0.25)), ink_small)

    # 노이즈·블러·밝기
    img = np.clip(img.astype(np.float32)
                  + np.random.normal(0, rng.uniform(2, 9), img.shape), 0, 255).astype(np.uint8)
    if rng.random() < 0.4:
        img = cv2.GaussianBlur(img, (3, 3), rng.uniform(0.3, 1.0))
    if rng.random() < 0.3:
        img = cv2.GaussianBlur(img, (5, 5), rng.uniform(0.5, 1.2))
    a = rng.uniform(0.75, 1.25)
    b = rng.uniform(-25, 25)
    img = np.clip(img.astype(np.float32) * a + b, 0, 255).astype(np.uint8)

    # 광택(스페큘러) 블롭 — 유리 반사 흉내
    for _ in range(rng.randint(0, 2)):
        ex, ey = rng.randint(0, W - 1), rng.randint(0, H - 1)
        ax, ay = rng.randint(W // 12, W // 5), rng.randint(H // 12, H // 5)
        ang = rng.uniform(0, 180)
        glare_val = int(min(255, panel + rng.uniform(50, 100)))
        ov = rng.uniform(0.15, 0.3)
        m = np.zeros((H, W), np.float32)
        cv2.ellipse(m, (ex, ey), (ax, ay), ang, 0, 360, 1, -1)
        m *= ov
        img = np.clip(img.astype(np.float32) * (1 - m) + glare_val * m,
                      0, 255).astype(np.uint8)

    # 비네팅 — 가장자리 살짝 어둡게
    yy, xx = np.mgrid[0:H, 0:W]
    d2 = ((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 2)) ** 2
    vig = 1.0 - rng.uniform(0.08, 0.22) * d2
    img = np.clip(img.astype(np.float32) * vig, 0, 255).astype(np.uint8)

    # G27 실화면화 네 요소 — 조명(그림자·반사) 뒤 기하(shear·키스톤) 순서.
    if rng.random() < 0.35:
        img = add_local_shadow(img, rng)
    if rng.random() < 0.30:
        img = add_reflection_stripe(img, rng)
    if rng.random() < 0.20:
        img = apply_shear(img, rng)
    if rng.random() < 0.25:
        img = apply_keystone(img, rng)

    # 미세 회전 — 촬영 기울기 흉내
    if rng.random() < 0.7:
        ang = rng.uniform(-1.5, 1.5)
        M = cv2.getRotationMatrix2D((W / 2, H / 2), ang, 1.0)
        img = cv2.warpAffine(img, M, (W, H),
                             borderValue=int(rng.uniform(30, 80)))
    return img, label


def generate(count, seed0, out_dir, size=(320, 160)):
    import json
    rng = random.Random(seed0)
    out = Path(out_dir)
    (out / "images").mkdir(parents=True, exist_ok=True)
    labels = {}
    for i in range(count):
        val = rng.randint(30, 511)
        img, label = render_screen(val, rng, size)
        p = out / "images" / f"synth_{seed0}_{i}.png"
        cv2.imwrite(str(p), img)
        labels[f"synth_{seed0}_{i}"] = label
    (out / f"labels_{seed0}.json").write_text(
        json.dumps(labels, ensure_ascii=False, indent=0), encoding="utf-8")
    print(f"generated {count} → {out}")


if __name__ == "__main__":
    import sys
    count = int(sys.argv[1]) if len(sys.argv) > 1 else 3000
    seed = int(sys.argv[2]) if len(sys.argv) > 2 else 1
    out = sys.argv[3] if len(sys.argv) > 3 else r"D:\Project\sugarScan\assets_dev\train\synth_screens"
    generate(count, seed, out)
