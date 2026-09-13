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
# 각진 세그먼트 글자고 콜론은 사각 점 두 개('1:27'). 아래 스트로크 표는 실물
# 글자 모양을 보고 자체 정의한 것이다(외부 폰트 자산 아님 — 라이선스 정돈
# 불필요). 좌표는 글자 셀 안 0..1 (x 오른쪽, y 아래).
SEG_STROKES = {
    # 대문자
    "A": [(0, 1, 0, .45), (0, .45, .5, 0), (.5, 0, 1, .45), (1, .45, 1, 1), (.14, .62, .86, .62)],
    "B": [(0, 0, 0, 1), (0, 0, .8, 0), (.8, 0, 1, .18), (1, .18, 1, .44), (1, .44, .8, .58), (.8, .58, 0, .58), (0, .58, .8, .58), (.8, .58, 1, .74), (1, .74, 1, .82), (1, .82, .8, 1), (.8, 1, 0, 1)],
    "C": [(1, .12, .5, 0), (.5, 0, 0, .12), (0, .12, 0, .88), (0, .88, .5, 1), (.5, 1, 1, .88)],
    "D": [(0, 0, 0, 1), (0, 0, .7, 0), (.7, 0, 1, .25), (1, .25, 1, .75), (1, .75, .7, 1), (.7, 1, 0, 1)],
    "E": [(1, 0, 0, 0), (0, 0, 0, 1), (0, 1, 1, 1), (0, .55, .8, .55)],
    "F": [(1, 0, 0, 0), (0, 0, 0, 1), (0, .55, .8, .55)],
    "G": [(1, .12, .5, 0), (.5, 0, 0, .12), (0, .12, 0, .88), (0, .88, .5, 1), (.5, 1, 1, .88), (1, .88, 1, .55), (1, .55, .55, .55)],
    "H": [(0, 0, 0, 1), (1, 0, 1, 1), (0, .55, 1, .55)],
    "I": [(.5, 0, .5, 1), (0, 0, 1, 0), (0, 1, 1, 1)],
    "K": [(0, 0, 0, 1), (1, 0, 0, .58), (0, .58, 1, 1)],
    "L": [(0, 0, 0, 1), (0, 1, 1, 1)],
    "M": [(0, 1, 0, 0), (0, 0, .5, .5), (.5, .5, 1, 0), (1, 0, 1, 1)],
    "N": [(0, 1, 0, 0), (0, 0, 1, 1), (1, 1, 1, 0)],
    "O": [(0, .12, 0, .88), (0, .88, .5, 1), (.5, 1, 1, .88), (1, .88, 1, .12), (1, .12, .5, 0), (.5, 0, 0, .12)],
    "P": [(0, 1, 0, 0), (0, 0, .8, 0), (.8, 0, 1, .18), (1, .18, 1, .4), (1, .4, .8, .58), (.8, .58, 0, .58)],
    "R": [(0, 1, 0, 0), (0, 0, .8, 0), (.8, 0, 1, .18), (1, .18, 1, .4), (1, .4, .8, .58), (.8, .58, 0, .58), (.35, .58, 1, 1)],
    "S": [(1, .1, .5, 0), (.5, 0, 0, .12), (0, .12, 0, .44), (0, .44, .5, .58), (.5, .58, 1, .7), (1, .7, 1, .9), (1, .9, .5, 1), (.5, 1, 0, .9)],
    "T": [(0, 0, 1, 0), (.5, 0, .5, 1)],
    "U": [(0, 0, 0, .88), (0, .88, .5, 1), (.5, 1, 1, .88), (1, .88, 1, 0)],
    "V": [(0, 0, .5, 1), (.5, 1, 1, 0)],
    "Y": [(0, 0, .5, .45), (1, 0, .5, .45), (.5, .45, .5, 1)],
    # 소문자 — 실물 LCD 보조 글자는 소문자도 각진 대형(722 'days'·'mem')
    "a": [(0, 1, 0, .5), (0, .5, .5, .42), (.5, .42, 1, .55), (1, .55, 1, 1), (1, 1, 0, 1), (.5, .42, .5, 1)],
    "b": [(0, 0, 0, 1), (0, 1, .8, 1), (.8, 1, 1, .8), (1, .8, 1, .6), (1, .6, .8, .45), (.8, .45, 0, .45)],
    "c": [(1, .58, .5, .45), (.5, .45, 0, .58), (0, .58, 0, .88), (0, .88, .5, 1), (.5, 1, 1, .88)],
    "d": [(1, 0, 1, 1), (1, 1, .2, 1), (.2, 1, 0, .8), (0, .8, 0, .6), (0, .6, .2, .45), (.2, .45, 1, .45)],
    "e": [(0, .58, 0, .88), (0, .88, .5, 1), (.5, 1, 1, .88), (1, .88, 1, .72), (1, .72, 0, .58), (0, .58, 1, .58)],
    "g": [(1, 0, 1, .88), (1, .88, .5, 1), (.5, 1, 0, .88), (0, .88, 0, .68), (0, .68, .5, .55), (.5, .55, 1, .68), (1, .68, 1, 1.12), (1, 1.12, .4, 1.12)],
    "h": [(0, 0, 0, 1), (0, .45, .8, .45), (.8, .45, 1, .62), (1, .62, 1, 1)],
    "k": [(0, 0, 0, 1), (1, .45, 0, .72), (0, .72, 1, 1)],
    "l": [(.5, 0, .5, 1)],
    "m": [(0, .45, 0, 1), (0, .45, .27, .38), (.27, .38, .5, .45), (.5, .45, .73, .38), (.73, .38, 1, .45), (1, .45, 1, 1)],
    "n": [(0, .45, 0, 1), (0, .45, .55, .45), (.55, .45, 1, .62), (1, .62, 1, 1)],
    "o": [(0, .58, 0, .88), (0, .88, .5, 1), (.5, 1, 1, .88), (1, .88, 1, .58), (1, .58, .5, .45), (.5, .45, 0, .58)],
    "p": [(0, .45, 0, 1.12), (0, .45, .8, .45), (.8, .45, 1, .62), (1, .62, 1, .8), (1, .8, .8, 1), (.8, 1, 0, 1)],
    "r": [(0, .45, 0, 1), (0, .45, .6, .45), (.6, .45, 1, .58)],
    "s": [(1, .52, .5, .45), (.5, .45, 0, .55), (0, .55, 0, .72), (0, .72, .5, .82), (.5, .82, 1, .9), (1, .9, .5, 1), (.5, 1, 0, .92)],
    "t": [(.4, .2, .4, .85), (.4, .85, .7, 1), (.7, 1, 1, .85), (0, .45, .8, .45)],
    "u": [(0, .45, 0, .88), (0, .88, .5, 1), (.5, 1, 1, .88), (1, .88, 1, .45), (0, .45, 1, .45)],
    "v": [(0, .45, .5, 1), (.5, 1, 1, .45)],
    "y": [(0, .45, .5, .8), (1, .45, .5, .8), (.5, .8, .5, 1), (.5, 1, 1, 1.12)],
    # 숫자·기호
    "/": [(1, .95, 0, .05)],
    "-": [(.1, .55, .9, .55)],
    ".": [(.35, .85, .35, 1.0)],
    "#": [(.25, 0, .25, 1), (.7, 0, .7, 1), (0, .3, 1, .3), (0, .72, 1, .72)],
    "+": [(.5, .2, .5, .9), (.1, .55, .9, .55)],
}
# 소문자 g·p·y 처럼 밑으로 내려오는 활자 — 셀 아래 0.12 여유가 필요하다.
SEG_DESCEND = set("gpy")
SEG_ADVANCE = {"/": .55, "-": .8, ".": .55, "#": 1.0, "+": 1.0, " ": .55, ":": .5}


def seg_text_width(text, h):
    """seg_text 가 그을 폭(px) — 배치 사각형 계산용."""
    w = 0
    for ch in text:
        if ch in SEG_MAP:
            w += h * 0.62
        elif ch in SEG_STROKES:
            w += h * 0.72
        else:
            w += h * SEG_ADVANCE.get(ch, 0.55)
    return int(round(w)) + 2


def seg_text(img, x, y, text, h, ink, thick=None):
    """세그먼트 보조 글자 줄(AC#1). 숫자는 7-세그(SEG_MAP), 글자는 직선
    스트로크, 콜론은 사각 점 두 개(put_7seg_text 와 같은 관례, 근거 722
    '1:27'). 반환값: 그은 폭 px."""
    t = thick or max(1, int(round(h / 8.0)))
    cx = x
    for ch in text:
        if ch == " ":
            cx += int(h * SEG_ADVANCE[" "])
            continue
        if ch == ":":
            r = max(2, h // 7)
            cv2.rectangle(img, (cx, y + int(h * .30)), (cx + 2 * r, y + int(h * .30) + 2 * r), ink, -1)
            cv2.rectangle(img, (cx, y + int(h * .68)), (cx + 2 * r, y + int(h * .68) + 2 * r), ink, -1)
            cx += int(h * SEG_ADVANCE[":"])
            continue
        if ch in SEG_MAP:
            dw = int(h * 0.62)
            draw_digit(img, cx, y, dw, h, ch, ink, thickness=t)
            cx += dw + max(1, h // 8)
            continue
        strokes = SEG_STROKES.get(ch)
        if strokes is None:
            continue
        cw = int(h * 0.72)
        depth = h * (1.12 if ch in SEG_DESCEND else 1.0)
        for sx0, sy0, sx1, sy1 in strokes:
            p0 = (cx + int(sx0 * cw), y + int(sy0 * depth))
            p1 = (cx + int(sx1 * cw), y + int(sy1 * depth))
            cv2.line(img, p0, p1, ink, t, cv2.LINE_AA)
        cx += cw + max(1, h // 8)
    return cx - x


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
