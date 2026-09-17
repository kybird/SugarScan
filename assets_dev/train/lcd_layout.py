# LCD 레이아웃 모델 — 액정 설계자가 화면을 잡는 방식 그대로.
#
# 유리 → 안쪽 패딩 → 영역(Region)들이 남은 면을 **빈틈없이** 나눈다.
# 요소는 자기 영역 안에서만 배치되고, 영역 밖으로 나갈 수 없다.
#
# 왜 이 구조인가(2026-09-15):
#   구판은 요소마다 후보 좌표를 만들고 막히면 대체 자리로 밀어냈다. 그래서
#   같은 기기인데 장마다 요소 자리가 달라졌고(좌상단을 M 과 삼각형이 다툼),
#   한 군데를 고치면 다른 데가 터졌다. 밴드 쿼드도 실측 폭에서 역산해 내용과
#   어긋났다. 영역이 먼저 정해지면 이 세 문제가 동시에 사라진다:
#     · 자리가 고정된다 (영역이 곧 자리다)
#     · 밴드 쿼드 = mid 영역의 슬롯 필드 — 따로 계산할 것이 없다
#     · 빈 면이 없다 (영역이 유리를 빈틈없이 나누므로)
#
# 좌표계: 유리(glass) 픽셀. 모든 사각형은 (x0, y0, x1, y1) 실수.

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Rect:
    x0: float
    y0: float
    x1: float
    y1: float

    @property
    def w(self):
        return self.x1 - self.x0

    @property
    def h(self):
        return self.y1 - self.y0

    @property
    def cx(self):
        return (self.x0 + self.x1) / 2.0

    @property
    def cy(self):
        return (self.y0 + self.y1) / 2.0

    def inset(self, l=0.0, r=0.0, t=0.0, b=0.0):
        return Rect(self.x0 + l, self.y0 + t, self.x1 - r, self.y1 - b)

    def contains(self, o, tol=0.5):
        return (self.x0 <= o.x0 + tol and self.y0 <= o.y0 + tol
                and self.x1 >= o.x1 - tol and self.y1 >= o.y1 - tol)

    def as_tuple(self):
        return (self.x0, self.y0, self.x1, self.y1)


# ── 밴드 여백 — 규약의 정본 ────────────────────────────────────────────
# 밴드 쿼드는 숫자 슬롯 필드에 사방 이만큼(숫자 높이 배수)을 더한 것이다.
#
# 이 값은 **측정에서 오지 않는다.** 사람은 기계적으로 같은 여백을 못 만들므로
# 사람 라벨을 재서 합성을 맞추면 기준이 사람의 손떨림이 된다(2026-09-15 사람
# 지침: "니가 기준을 주고 사람이 따라해야지"). 합성이 정확한 값을 낼 수 있는
# 쪽이므로 합성이 기준을 정하고, 라벨 지침이 그 기준을 말하고, 게이트가 사람의
# 오차를 흡수한다.
#
# 0.10 을 고른 이유 — 학습에 미치는 영향으로:
#   · 0 이면 예측이 조금만 작아도 획이 잘린다. 잘린 획은 리더가 복구 못 한다.
#     비대칭 손해다 — 조금 넓은 크롭은 해가 거의 없고 잘린 크롭은 값을 잃는다.
#   · 검출기의 모서리 오차가 밴드 높이의 1.15%(합성 홀드아웃 실측)다.
#     0.10*숫자높이 는 그 8배 이상이라 예측 오차를 삼킨다.
#   · 너무 크면 이웃 줄(단위·날짜)을 끌어들이고 리더의 유효 해상도를 깎는다.
#     0.10 은 줄 간격(보통 0.3 이상)보다 한참 작다.
#
# 0.10 -> 0.20 을 하루 썼다가 **되돌렸다**(2026-09-16). 이 값은 밴드를 키우는
# 손잡이가 아니다 — 같은 값이 slot_field 의 해법에도 들어가고, 거기서 밴드가
# 영역을 꽉 채우도록 풀기 때문에 **밴드 크기는 마진과 무관하게 영역 그대로**다.
# 고정 영역 560x300 에 슬롯 3·비율 0.60·자간 0.15 로 재면:
#     m     숫자높이   밴드폭   밴드높이
#   0.10     250.0     560.0    300.0
#   0.20     214.3     560.0    300.0
#   0.30     187.5     560.0    300.0
# 움직이는 것은 숫자뿐이다. 0.20 으로 올렸을 때 게이트가 4.4% -> 34.7% 로
# 오른 것은 밴드가 커져서가 아니라 **숫자가 14% 작아져** 밴드 안 여백이
# 늘었기 때문이고, 그만큼 리더가 받을 해상도를 깎아서 산 점수다.
#
# 그러므로 이 값의 뜻은 "밴드 테두리와 숫자 사이의 갭"이다. 밴드를 실제로
# 키우려면 영역(REGIONS rows/pad)을 키우거나, 검출기 출력을 추론 때 부풀린다.
# [[coupled-budget-loop-defeats-per-element-tuning]]
#
# 라벨 지침(webtool 밴드 모드)과 이 상수는 같은 것을 말해야 한다. 바꾸면
# 양쪽을 같이 바꾼다.
BAND_MARGIN = 0.10

# ── 레이아웃 여백 — **그림** 쪽 (2026-09-16 분리) ─────────────────────────
# BAND_MARGIN 은 원래 두 일을 했다: slot_field 가 숫자 크기를 역산할 때도
# 쓰이고, band_quad 가 정답 쿼드를 그릴 때도 쓰였다. 그래서 **라벨을 넓히려고
# 값을 올리면 합성 이미지의 숫자가 작아졌다**. 실측(유리 대비, 프로세스 분리):
#     m      밴드/유리   숫자/유리
#   0.10      0.515      0.429
#   0.20      0.514      0.367     <- 밴드는 그대로, 숫자만 14% 줄었다
#   0.30      0.514      0.321
# 밴드가 영역을 꽉 채우도록 푸니 마진이 커진 만큼 숫자가 물러난 것이고,
# 정답 상자는 한 픽셀도 안 커졌다. 바꾸려던 것과 반대의 결과다.
#
# 그래서 갈랐다:
#   LAYOUT_MARGIN  그림 — 숫자가 영역 안에서 물러나는 정도. **고정**이다.
#                  기기 생김새의 일부이므로 실험으로 흔들지 않는다.
#   BAND_MARGIN    라벨 — 정답 쿼드가 숫자 필드를 넘어 감싸는 정도.
#                  **이것만 바꾸면 그림은 그대로, 정답 상자만 커진다.**
# [[coupled-budget-loop-defeats-per-element-tuning]]
LAYOUT_MARGIN = 0.10

# 7-seg 칸의 폭/높이가 물리적으로 놓이는 범위. 영역을 채우려고 칸 비율을 풀
# 때 이 밖으로 나가지 않는다 — 벗어나면 숫자가 납작하거나 홀쭉해져 실물에
# 없는 글자가 된다. 그럴 때는 채우기를 포기하고 남는 면을 둔다.
ASPECT_MIN, ASPECT_MAX = 0.42, 0.78


def band_quad(field, digit_h, clip=None, margin=None):
    """슬롯 필드 -> 밴드 쿼드. 사방에 margin*digit_h.

    clip 을 주면 그 사각형(보통 유리) 안으로 자르되 **내용은 자르지 않는다** —
    여백만 줄어든다. 숫자가 유리 가장자리에 가까운 기기에서 밴드가 숫자를
    잘라먹던 결함(2026-09-15)의 자리다.
    """
    # 기본값을 인자 자리에 두면 **모듈을 읽을 때 한 번 굳는다** — 실험에서
    # BAND_MARGIN 을 바꿔도 여기만 옛 값을 써서 없는 현상을 봤다(2026-09-16).
    m = (BAND_MARGIN if margin is None else margin) * digit_h
    r = Rect(field.x0 - m, field.y0 - m, field.x1 + m, field.y1 + m)
    if clip is None:
        return r
    return Rect(min(field.x0, max(clip.x0, r.x0)),
                min(field.y0, max(clip.y0, r.y0)),
                max(field.x1, min(clip.x1, r.x1)),
                max(field.y1, min(clip.y1, r.y1)))


# ── 영역 이름 — 프로파일이 쓰는 어휘 ────────────────────────────────────
# 세로형 기본은 top/mid/bottom 3분할. track 은 선언한 기기만 생긴다.
TOP, MID, BOTTOM = "top", "mid", "bottom"
TRACK_R, TRACK_L = "track-right", "track-left"
COLUMN_R = "column-right"          # 가로형: 숫자 오른쪽 정보 칼럼
ALL_REGIONS = (TOP, MID, BOTTOM, TRACK_R, TRACK_L, COLUMN_R)


@dataclass
class LcdLayout:
    """한 장의 화면 레이아웃. 유리 사각형과 영역 사전을 들고 있다."""
    glass: Rect
    inner: Rect
    regions: dict = field(default_factory=dict)

    def __getitem__(self, name):
        return self.regions[name]

    def get(self, name, default=None):
        return self.regions.get(name, default)

    def has(self, name):
        return name in self.regions

    def covered_fraction(self):
        """영역이 안쪽 면을 얼마나 덮는가. 1.0 이어야 한다(빈틈 없음)."""
        a = sum(r.w * r.h for r in self.regions.values())
        return a / max(1e-6, self.inner.w * self.inner.h)


def _frac(v, total):
    """비율(0~1)이면 total 에 곱하고, 1 보다 크면 픽셀로 본다."""
    return v * total if 0.0 <= v <= 1.0 else float(v)


def build_layout(glass, spec):
    """유리 사각형 + 프로파일의 layout 선언 -> LcdLayout.

    spec 예(세로형):
        dict(pad=(0.04, 0.04, 0.05, 0.05),      # 좌 우 상 하 (유리 대비)
             rows=(0.22, 0.52, 0.26))           # top mid bottom (안쪽 높이 대비)

    spec 예(세로형 + 미터기 트랙):
        dict(pad=(0.04, 0.04, 0.05, 0.05),
             rows=(0.18, 0.56, 0.26), track_right=0.12)

    spec 예(가로형 — 숫자 왼쪽 + 정보 칼럼 오른쪽):
        dict(pad=(0.03, 0.03, 0.05, 0.05), column_right=0.42,
             rows=(0.0, 1.0, 0.0))

    rows 는 합이 1 이 아니어도 된다 — 정규화한다. 0 인 줄은 영역을 만들지
    않는다(그 기기에 그 줄이 없다는 뜻).
    """
    if not isinstance(glass, Rect):
        glass = Rect(*glass)
    pl, pr, pt, pb = spec.get("pad", (0.0, 0.0, 0.0, 0.0))
    inner = glass.inset(_frac(pl, glass.w), _frac(pr, glass.w),
                        _frac(pt, glass.h), _frac(pb, glass.h))
    regions = {}

    # 세로 트랙/칼럼을 먼저 떼고 남은 폭을 행이 쓴다.
    x0, x1 = inner.x0, inner.x1
    tr = spec.get("track_right") or spec.get("column_right")
    if tr:
        w = _frac(tr, inner.w)
        name = TRACK_R if spec.get("track_right") else COLUMN_R
        regions[name] = Rect(x1 - w, inner.y0, x1, inner.y1)
        x1 -= w
    tl = spec.get("track_left")
    if tl:
        w = _frac(tl, inner.w)
        regions[TRACK_L] = Rect(x0, inner.y0, x0 + w, inner.y1)
        x0 += w

    rows = spec.get("rows", (0.0, 1.0, 0.0))
    tot = float(sum(rows)) or 1.0
    y = inner.y0
    for name, frac in zip((TOP, MID, BOTTOM), rows):
        if frac <= 0:
            continue
        h = inner.h * (frac / tot)
        regions[name] = Rect(x0, y, x1, y + h)
        y += h
    if MID not in regions:
        raise ValueError("mid 영역이 없다 — 숫자를 놓을 자리가 없다")
    return LcdLayout(glass=glass, inner=inner, regions=regions)


# ── 영역 안 배치 ────────────────────────────────────────────────────────
# 요소는 (region, align) 으로 자리를 선언한다. 후보 목록도 대체 자리도 없다.
# 같은 영역에 여러 요소가 오면 align 이 다르거나, 같은 align 이면 순서대로
# 쌓는다(stack). 자리가 모자라면 **그리지 않는다** — 밀어내지 않는다.

H_ALIGN = {"left": 0.0, "center": 0.5, "right": 1.0}
V_ALIGN = {"top": 0.0, "middle": 0.5, "bottom": 1.0}


def place_in(region, w, h, align="center", valign="middle",
             margin=0.0, used=()):
    """영역 안에 w x h 를 놓는다. 못 놓으면 None.

    used 는 같은 영역에 이미 놓인 사각형들 — 가로로 겹치면 그만큼 비켜
    쌓는다(align 방향으로). 영역을 벗어나면 None 을 돌려준다.
    """
    if w > region.w + 0.5 or h > region.h + 0.5:
        return None
    ax = H_ALIGN.get(align, 0.5)
    ay = V_ALIGN.get(valign, 0.5)
    x = region.x0 + margin + (region.w - w - 2 * margin) * ax
    y = region.y0 + margin + (region.h - h - 2 * margin) * ay
    r = Rect(x, y, x + w, y + h)

    for u in used:
        if not (r.x1 <= u.x0 or u.x1 <= r.x0 or r.y1 <= u.y0 or u.y1 <= r.y0):
            # 같은 줄에서 비켜난다 — align 이 오른쪽이면 왼쪽으로.
            if ax >= 0.5:
                r = Rect(u.x0 - w - margin, r.y0, u.x0 - margin, r.y1)
            else:
                r = Rect(u.x1 + margin, r.y0, u.x1 + margin + w, r.y1)
    if r.x0 < region.x0 - 0.5 or r.x1 > region.x1 + 0.5:
        return None
    if r.y0 < region.y0 - 0.5 or r.y1 > region.y1 + 0.5:
        return None
    return r


def slot_field(region, slots, aspect, gap_ratio=0.12, fill=1.0,
               margin=None):
    """mid 영역 안의 숫자 슬롯 필드. **영역 폭을 다 쓴다**(액정 설계 원칙:
    유리에 빈 면을 남기지 않는다 — 사람 지침 2026-09-15).

    slots  칸 수(보통 3). 값이 2자리여도 칸은 3개다 — 앞 빈칸이 남는다.
    aspect 숫자 한 칸의 폭/높이. 기기 형질.
    gap_ratio 칸 사이 간격(숫자 높이 대비).
    fill   영역 폭을 얼마나 쓸지(1.0 = 꽉).

    반환 (field_rect, digit_h, pitch). 높이와 폭 중 먼저 걸리는 쪽에 맞춘다.
    """
    gap_h = gap_ratio
    # **밴드 여백까지 포함해** 영역에 들어가게 푼다(2026-09-15). 필드만 영역
    # 폭에 맞추면 여백 자리가 안 남아 band_quad 의 clip 이 여백을 깎는다 —
    # dorucos_premium·acura_plus 에서 좌우 여백이 0 이 됐다. 밴드(필드+여백)가
    # 영역을 꽉 채우는 것이 맞다.
    # **그림** 쪽 여백이다. 라벨 여백(BAND_MARGIN)을 여기 쓰면 라벨을 넓힐
    # 때마다 숫자가 작아진다.
    m = LAYOUT_MARGIN if margin is None else margin
    # 폭: slots*asp*h + (slots-1)*gap*h + 2*m*h = W
    denom = slots * aspect + (slots - 1) * gap_h + 2 * m
    # 밴드는 **영역을 양쪽으로 채운다**(2026-09-15). 숫자 높이는 영역 높이가
    # 정하고(여백 제외), 칸 비율은 그 높이에서 폭을 채우도록 푼다.
    #
    # 왜 양방향인가: 한쪽만 채우면 반대쪽이 논다. 처음에는 높이에 걸릴 때만
    # 폭을 늘렸는데, 그 반대(폭에 걸려 세로가 남는 경우)를 안 고쳤다 —
    # accuchek_instant·acura_plus 가 mid 높이의 81% 만 쓰고 18.7% 를 놀렸다.
    # 그래서 검출기가 세로로 짧은 밴드를 배웠고, 실사진에서 **위아래로 숫자를
    # 잘랐다**(사람 검토 2026-09-15: "위아래에서 잘리네. 좌우는 넉넉한데").
    # 액정 설계자는 어느 방향으로도 빈 면을 남기지 않는다.
    h = region.h / (1.0 + 2 * m)
    avail = region.w * fill - 2 * m * h - (slots - 1) * gap_h * h
    asp = avail / max(slots * h, 1e-6)
    # 칸 비율이 물리적 범위를 벗어나면 그쪽에 맞춘다 — 숫자를 납작하거나
    # 홀쭉하게 찌그러뜨리지 않는다.
    asp = min(ASPECT_MAX, max(ASPECT_MIN, asp))
    need_w = slots * h * asp + (slots - 1) * h * gap_h + 2 * m * h
    if need_w > region.w * fill:
        h = (region.w * fill) / max(slots * asp + (slots - 1) * gap_h + 2 * m, 1e-6)
    elif slots > 1 and need_w < region.w * fill:
        # 폭이 남으면 **자간을 늘려 채운다**(사람 지침 2026-09-15: "자간을
        # 늘려서 폭을 채우는 방법도 있지"). 구판은 남는 면을 그냥 뒀고, 그건
        # 액정 설계 원칙과 어긋난다 — 유리에 빈 면을 남기지 않는다.
        #
        # 글리프를 늘리는 것과 다르다: 숫자 모양(asp)은 그대로 두고 **칸 사이
        # 간격만** 벌린다. 7-seg 는 글리프가 고정 너비라 늘리면 모양이 깨진다.
        slack = region.w * fill - need_w
        gap_h = gap_h + slack / ((slots - 1) * h)
    pitch = h * asp + h * gap_h
    field_w = slots * h * asp + (slots - 1) * h * gap_h
    x = region.x0 + (region.w - field_w) / 2.0
    y = region.y0 + (region.h - h) / 2.0
    return Rect(x, y, x + field_w, y + h), h, pitch
