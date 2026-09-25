# 볼록 세그먼트 스파이크 시트 v2 — DSEG 베이스에 렌더 시간 볼록 성형만 얹는다.
#
# 1차(파라메트릭 자체 그리기)는 사람 눈검에서 "실촬과 거리가 매우 멀다"로
# 기각됐다(2026-09-23, 카드 노트) — 볼록 유무보다 베이스 형상(평평한 막대+
# 직각 끝)이 DSEG Classic 의 사선 끝단·비율과 근본적으로 달랐다.
# 폰트 파일은 여전히 무수정(RFN) — 마스크로 구운 뒤 remap 변위만 준다.
#
# 성형: 글리프 중심에서 바깥으로 향하는 sin 변위장. 좌우 윤곽(세로 획 바깥
# 가장자리)은 x 방향로, 상하 윤곽(가로 획)은 y 방향으로 볼록. 가운데 G 는
# 두 방향이 만나 렌즈처럼 벌어진다. 진폭은 획 두께 비율(bulge).
#
# 재지 않는다 — 실사진 행은 사람이 값을 부르는 기준면일 뿐이다
# ([[no-real-photo-ruler-for-synth]]). 슬롯 규약·실사진 수집은
# make_glyph_compare_sheet 에서 그대로 가져온다.
#
# 사용:
#   python make_glyph_convex_sheet.py --per-digit 16
import argparse
from pathlib import Path

import cv2
import numpy as np

HERE = Path(__file__).resolve().parent
OUT = HERE / "_diag" / "glyph_convex_test"

from make_glyph_compare_sheet import collect_real, CELL_H  # noqa: E402

CELL_W = 110                                # 시트 한 칸 폭(중심 정렬)
LBL_W = 190                                 # 왼쪽 행 라벨 폭
SS = 3                                      # 고해상도 렌더 배율(warp 후 접는다)
STROKE = 0.12                               # DSEG 획 두께/높이 근사(warp 진폭 기준)


def dseg_mask(ch, variant, height):
    from synth_profiles import _glyph_mask
    mk = _glyph_mask(ch, variant, height)
    return None if mk is None else mk.astype(np.float32)


def dseg_warp_mask(ch, variant, height, bulge):
    """DSEG 글리프를 구워 외향 sin 변위장으로 볼록 성형한 마스크(0..255).
    bulge — 변위 진폭/획 두께."""
    m = dseg_mask(ch, variant, height * SS)
    if m is None:
        return None
    h, w = m.shape
    x = np.arange(w, dtype=np.float32)
    y = np.arange(h, dtype=np.float32)
    X, Y = np.meshgrid(x, y)
    cx, cy = (w - 1) / 2.0, (h - 1) / 2.0
    amp = STROKE * bulge * height * SS
    sx = np.sin(np.pi * np.clip(Y / h, 0, 1))    # 세로 획: 끝 0, 가운데 최대
    sy = np.sin(np.pi * np.clip(X / w, 0, 1))    # 가로 획: 끝 0, 가운데 최대
    mx = X + np.where(X < cx, -amp * sx, amp * sx)
    my = Y + np.where(Y < cy, -amp * sy, amp * sy)
    out = cv2.remap(m, mx, my, cv2.INTER_LINEAR,
                    borderMode=cv2.BORDER_CONSTANT, borderValue=0)
    w2 = max(1, int(round(out.shape[1] / SS)))    # 폭은 SS 배수가 아니다
    out = cv2.resize(out, (w2, height), interpolation=cv2.INTER_AREA)
    return (np.clip(out, 0, 1) * 255).astype(np.uint8)


def dseg_overlap_mask(ch, variant, height, delta=0.25, mirror=True,
                      soft=False, horz="outward"):
    """세그먼트(연결요소)마다 바깥 방향으로 겹친 사본을 얹는다(사람 제안
    2026-09-23: '반전한 후 겹친다 — 가로획은 위로, 세로획은 좌우로').
    mirror — 사본을 긴 축 기준 미리 뒤집는다('반전' 해석).
    soft — 겹침을 반투명(0.45) — 바깥 가장자리가 부드럽게 번진다.
    horz — 'literal': 가로획 전부 위로. 'outward': A 위·D 아래·G 양쪽."""
    mk = dseg_mask(ch, variant, height * 2)
    if mk is None:
        return None
    m = (mk > 0.5).astype(np.uint8)
    n, lab = cv2.connectedComponents(m)
    acc = m.astype(np.float32) if soft else m.astype(np.float32)
    H, W = m.shape
    comps, vws = [], []
    for i in range(1, n):
        ys, xs = np.nonzero(lab == i)
        if len(xs) < 8:
            continue
        x0, x1, y0, y1 = xs.min(), xs.max(), ys.min(), ys.max()
        w, h = x1 - x0 + 1, y1 - y0 + 1
        comps.append((i, x0, x1, y0, y1, w, h))
        if h > w:
            vws.append(w)
    t = float(np.median(vws)) if vws else 0.12 * H
    d = max(1, int(round(delta * t)))
    cx, cy = W / 2.0, H / 2.0
    for i, x0, x1, y0, y1, w, h in comps:
        comp = (lab[y0:y1 + 1, x0:x1 + 1] == i).astype(np.float32)
        if mirror:
            comp = comp[::-1, :] if w > h else comp[:, ::-1]
        dirs = []
        if w > h * 1.2:                       # 가로획
            mid_y = (y0 + y1) / 2
            if horz == "literal" or mid_y < cy * 0.92:
                dirs.append((-d, 0))          # 위로
            elif mid_y > cy * 1.08:
                dirs.append((d, 0))           # 아래로
            else:
                dirs += [(-d, 0), (d, 0)]     # 가운데 G — 양쪽
        elif h > w * 1.2:                     # 세로획
            dirs.append((0, -d if (x0 + x1) / 2 < cx else d))
        else:
            continue
        for dy, dx in dirs:
            yy0, yy1, xx0, xx1 = y0 + dy, y1 + 1 + dy, x0 + dx, x1 + 1 + dx
            if yy0 < 0 or xx0 < 0 or yy1 > H or xx1 > W:
                continue
            sh = np.zeros_like(acc)
            sh[yy0:yy1, xx0:xx1] = comp
            acc = np.maximum(acc, 0.45 * sh if soft else sh)
    out = cv2.resize(acc, (max(1, int(round(W / 2))), height),
                     interpolation=cv2.INTER_AREA)
    return (np.clip(out, 0, 1) * 255).astype(np.uint8)


def dseg_rot_overlap_mask(ch, variant, height, delta=0.0):
    """'반전'을 180도 회전으로 재해석한 겹침(사람 판정 '잘못 겹침' 2026-09-23
    이후 재해석). 근거 실측: 긴 축 미러(v3 해석)는 대칭 막대에 항등(면적차
    ≤5%)이라 v3 의 '반전'은 사실상 작동하지 않았고, 180도 회전은 끝단 사선
    방향을 뒤집는다(≤17.5%) — 사선 끝단이 서로 반대가 되어 겹치면 뾰족한
    끝이 채워진다. delta — 바깥 오프셋/획두께(0 이면 제자리 겹침)."""
    mk = dseg_mask(ch, variant, height * 2)
    if mk is None:
        return None
    m = (mk > 0.5).astype(np.uint8)
    n, lab = cv2.connectedComponents(m)
    acc = m.astype(np.float32)
    H, W = m.shape
    vws = []
    for i in range(1, n):
        ys, xs = np.nonzero(lab == i)
        if len(xs) >= 8:
            x0, x1, y0, y1 = xs.min(), xs.max(), ys.min(), ys.max()
            if (y1 - y0) > (x1 - x0):
                vws.append(x1 - x0 + 1)
    t = float(np.median(vws)) if vws else 0.12 * W
    d = max(0, int(round(delta * t)))
    cx, cy = W / 2.0, H / 2.0
    for i in range(1, n):
        ys, xs = np.nonzero(lab == i)
        if len(xs) < 8:
            continue
        x0, x1, y0, y1 = xs.min(), xs.max(), ys.min(), ys.max()
        comp = (lab[y0:y1 + 1, x0:x1 + 1] == i).astype(np.float32)[::-1, ::-1]
        dy = dx = 0
        if d:
            w, h = x1 - x0 + 1, y1 - y0 + 1
            if w > h * 1.2:                # 가로획 — 위로(문장 그대로)
                dy = -d
            elif h > w * 1.2:              # 세로획 — 바깥쪽으로
                dx = -d if (x0 + x1) / 2 < cx else d
        yy0, yy1 = y0 + dy, y1 + 1 + dy
        xx0, xx1 = x0 + dx, x1 + 1 + dx
        if yy0 < 0 or xx0 < 0 or yy1 > H or xx1 > W:
            continue
        sh = np.zeros_like(acc)
        sh[yy0:yy1, xx0:xx1] = comp
        acc = np.maximum(acc, sh)
    out = cv2.resize(acc, (max(1, int(round(W / 2))), height),
                     interpolation=cv2.INTER_AREA)
    return (np.clip(out, 0, 1) * 255).astype(np.uint8)


def dseg_attach_mask(ch, variant, height, overlap=0.5):
    """반전 사본을 양쪽에 동시에 나란히 붙인다(사람 지시 2026-09-24:
    '세로획은 반전 후 좌우를 동시에 나란히, 가로획은 반전 후 상하를
    위아래로 나란히 — 오프셋은 눈으로 조정').
    overlap — 원본·사본 겹침/획두께. 0=맞닿음(3층), 0.5=반쯤 겹침,
    1.0=제자리(union in-place). 사본 반전은 길이방향 뒤집기(가로획 상하반전,
    세로획 좌우반전 — v3 와 같은 연산). 양쪽 사본이 캔버스 밖으로 나가지
    않도록 마스크를 미리 패딩하고, 끝나면 내용물 꽉 찬 크롭으로 되돌린다."""
    mk = dseg_mask(ch, variant, height * 2)
    if mk is None:
        return None
    m0 = (mk > 0.5).astype(np.uint8)
    H0, W0 = m0.shape
    n0, lab0 = cv2.connectedComponents(m0)
    vws = []
    for i in range(1, n0):
        ys, xs = np.nonzero(lab0 == i)
        if len(xs) >= 8:
            x0, x1, y0, y1 = xs.min(), xs.max(), ys.min(), ys.max()
            if (y1 - y0) > (x1 - x0):
                vws.append(x1 - x0 + 1)
    t = float(np.median(vws)) if vws else 0.12 * H0
    step = max(0, int(round((1.0 - overlap) * t)))
    pd = int(round(1.6 * t)) + 2
    m = np.pad(m0, pd)
    H, W = m.shape
    n, lab = cv2.connectedComponents(m)
    acc = m.astype(np.float32)
    for i in range(1, n):
        ys, xs = np.nonzero(lab == i)
        if len(xs) < 8:
            continue
        x0, x1, y0, y1 = xs.min(), xs.max(), ys.min(), ys.max()
        comp = (lab[y0:y1 + 1, x0:x1 + 1] == i).astype(np.float32)
        w, h = x1 - x0 + 1, y1 - y0 + 1
        if w > h * 1.2:                 # 가로획 — 상하로 나란히
            comp = comp[::-1, :]
            dirs = [(-step, 0), (step, 0)]
        elif h > w * 1.2:               # 세로획 — 좌우로 나란히
            comp = comp[:, ::-1]
            dirs = [(0, -step), (0, step)]
        else:
            continue
        for dy, dx in dirs:
            yy0, yy1 = y0 + dy, y1 + 1 + dy
            xx0, xx1 = x0 + dx, x1 + 1 + dx
            sh = np.zeros_like(acc)
            sh[yy0:yy1, xx0:xx1] = comp
            acc = np.maximum(acc, sh)
    ys, xs = np.nonzero(acc > 0.5)
    if not len(ys):
        return None
    acc = acc[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
    w2 = max(1, int(round(acc.shape[1] * height / acc.shape[0])))
    out = cv2.resize(acc, (w2, height), interpolation=cv2.INTER_AREA)
    return (np.clip(out, 0, 1) * 255).astype(np.uint8)


def _barrel_bar(L, t, bulge, samples=180):
    """가로 방향 프리미티브 — 반원 끝단 + 바깥으로 휜(활) 옆면. 이진 마스크.
    L 전체 길이, t 두께, bulge 옆면 곡률/두께(0=곧은 stadium)."""
    a, b = L / 2.0, t / 2.0
    k = bulge * t
    pts = []
    span = max(1e-6, 2 * (a - b))
    xs = np.linspace(-(a - b), a - b, samples // 2)
    for x in xs:                                   # 윗변 — 위로 활
        pts.append((x, -b - k * np.sin(np.pi * (x + a - b) / span)))
    th = np.linspace(-np.pi / 2, np.pi / 2, samples // 4)
    for s in th:                                   # 오른쪽 반원 끝단
        pts.append((a - b + b * np.cos(s), b * np.sin(s)))
    for x in xs[::-1]:                             # 아랫변 — 아래로 활
        pts.append((x, b + k * np.sin(np.pi * (x + a - b) / span)))
    for s in th + np.pi:                           # 왼쪽 반원 끝단
        pts.append((-(a - b) + b * np.cos(s), b * np.sin(s)))
    pts = np.array(pts, np.float32)
    m = int(b + k) + 3
    W, H = 2 * (int(a) + m) + 1, 2 * (int(b + k) + 2) + 1
    canvas = np.zeros((H, W), np.uint8)
    cv2.fillPoly(canvas, [np.round(pts + [W / 2.0, H / 2.0]).astype(np.int32)], 1)
    return canvas.astype(np.float32)


def _lens_bar(L, t, tip_pow=0.8, samples=200):
    """렌즈형 획 — 양 옆면이 활처럼 휘어 양 끝에서 만나 뾰족해진다.
    사람 판정 2026-09-24: '볼록해지기는 하는데 실촬이 더 뾰족하다'(v6 반원
    끝단 기각) — 끝단이 반원보다 가늘게 조여드는 렌즈로 해석. tip_pow<1
    일수록 끝이 더 뾰족, 1.0=순수 사인 렌즈(완만한 점)."""
    a, k = L / 2.0, t / 2.0
    u = np.linspace(0.0, 1.0, samples)
    x = -a + 2 * a * u
    prof = k * np.sin(np.pi * u) ** tip_pow
    pts = np.vstack([np.stack([x, -prof], 1),
                     np.stack([x[::-1], prof[::-1]], 1)]).astype(np.float32)
    m = int(k) + 3
    W, H = 2 * (int(a) + m) + 1, 2 * int(k) + 7
    canvas = np.zeros((H, W), np.uint8)
    cv2.fillPoly(canvas, [np.round(pts + [W / 2.0, H / 2.0]).astype(np.int32)], 1)
    return canvas.astype(np.float32)


def _hexleaf_bar(L, t, taper=0.35, side_bulge=0.0, concave=False, asym=0.0,
                 soft=0.0, zone_t=None, samples=200):
    """평행 옆면 + 끝 테이퍼 프리미티브(8차 — 사람 판정 역산: v6 반원 끝은
    너무 뭉툭, v7 렌즈는 옆면까지 둥근 게 문제였다). taper — 길이 대비
    끝 테이퍼 구간 비. concave — 테이퍼를 오목(1-s^2)하게. side_bulge —
    평행 옆면에 얹는 볼록/두께. asym — 안팎 비대칭(사람 지시 2026-09-24:
    '바깥쪽 각도만 더 낮게 잘라라' + 정정 '안쪽에도 직선이 있어야 한다').
    0=대칭, 양수=바깥(위) 테이퍼만 축소(안쪽은 대칭 그대로 — 직선 유지),
    1=바깥 테이퍼 전무. 음수=방향 뒤집힘(안쪽만 축소). soft — 테이퍼 직선을
    smoothstep(3s²-2s³) 과 섞어 어깨·끝점 꺾임을 무디게 한다(사람 지시
    2026-09-24: '안팎 각도를 조금만 더 완화 — 현재 너무 뾰족'). 0=직선,
    1=완전 곡선."""
    a, k = L / 2.0, t / 2.0
    u = np.linspace(0.0, 1.0, samples)
    m = np.abs(u - 0.5)

    def side(zone_scale):
        # zone_t — 테이퍼 길이를 획두께 기준(전 획 동일 각도)으로 지정.
        # 미지정 시 taper 는 길이 비율이라 세로획이 가로획보다 가팔라진다
        # (사람 지시 2026-09-24: 바깥 획의 안쪽 기울기 = 가운데 획 기울기).
        if zone_t is not None:
            zone = max(1e-6, zone_t * t * max(0.0, zone_scale)) / max(1e-6, 2 * a)
        else:
            zone = max(1e-6, taper * max(0.0, zone_scale))
        flat = max(1e-6, 0.5 - zone)
        s = np.clip((m - flat) / zone, 0.0, 1.0)
        if concave:
            edge = 1.0 - s * s
        else:
            lin, sm = 1.0 - s, 1.0 - (3 * s * s - 2 * s * s * s)
            edge = (1.0 - soft) * lin + soft * sm
        return np.where(m <= flat, 1.0, edge) * k

    top = side(1.0 - asym)                 # 바깥(위) — asym 으로만 테이퍼 축소
    bot = side(1.0)                        # 안쪽(아래) — 대칭(v8) 그대로
    if side_bulge:
        bow = side_bulge * t * np.sin(np.pi * u)
        top, bot = top + bow, bot + bow
    pts = np.vstack([np.stack([u, -top], 1),
                     np.stack([u[::-1], bot[::-1]], 1)]).astype(np.float32)
    pts[:, 0] = pts[:, 0] * (2 * a) - a
    H = 2 * int(k + side_bulge * t) + 7
    W = 2 * int(a) + 7
    canvas = np.zeros((H, W), np.uint8)
    cv2.fillPoly(canvas, [np.round(pts + [W / 2.0, H / 2.0]).astype(np.int32)], 1)
    return canvas.astype(np.float32)


def param_swap_mask(ch, variant, height, bulge, trim=0.35, tip_pow=None,
                    taper=None, side_bulge=0.0, concave=False, asym=0.0,
                    soft=0.0, mid="auto", zone_t=None):
    """DSEG 의 배치(세그먼트 자리·두께·비율)는 그대로 쓰고 세그먼트 형상만
    프리미티브(반원 끝단+활 옆면)로 교체한다. 1차 파라메트릭 기각(2026-09-23)
    은 '평평한 막대+직각 끝단'이 원인 — 이번 형상은 사람 선언(볼록 옆면+둥근
    뭉툭 끝단, 전 기기 공통)을 직접 파라미터로 녹인다. trim — 끝단 축소/두께
    (코너에서 이웃 세그먼트와 붙지 않게; DSEG 은 베벨 갭 수 px 뿐이라 교체
    형상에서는 갭을 스스로 만들어야 한다)."""
    mk = dseg_mask(ch, variant, height * 2)
    if mk is None:
        return None
    m0 = (mk > 0.5).astype(np.uint8)
    n0, lab0 = cv2.connectedComponents(m0)
    vws = []
    for i in range(1, n0):
        ys, xs = np.nonzero(lab0 == i)
        if len(xs) >= 8:
            x0, x1, y0, y1 = xs.min(), xs.max(), ys.min(), ys.max()
            if (y1 - y0) > (x1 - x0):
                vws.append(x1 - x0 + 1)
    t0 = float(np.median(vws)) if vws else 0.12 * m0.shape[0]
    pd = int(round(2.5 * t0)) + 2
    H, W = m0.shape[0] + 2 * pd, m0.shape[1] + 2 * pd
    acc = np.zeros((H, W), np.float32)
    for i in range(1, n0):
        ys, xs = np.nonzero(lab0 == i)
        if len(xs) < 8:
            continue
        x0, x1, y0, y1 = xs.min(), xs.max(), ys.min(), ys.max()
        w, h = x1 - x0 + 1, y1 - y0 + 1
        t = float(min(w, h))
        L = max(1.0, float(max(w, h)) - 2 * trim * t)
        cx, cy = (x0 + x1) / 2.0 + pd, (y0 + y1) / 2.0 + pd
        horiz = w > h
        # '바깥' = 숫자 중심에서 먼 쪽(사람 지시 2026-09-24 안팎 비대칭 기준).
        # 가운데 가로획(G)은 바깥이 없어 방향이 임의였다 — 사람 지시
        # '글자 중앙의 단 하나의 가로획' 전용 처리(mid 노브).
        asym_eff = asym
        is_mid = False
        if horiz:
            cy0 = (m0.shape[0] - 1) / 2.0
            is_mid = abs((y0 + y1) / 2 - cy0) < 0.08 * m0.shape[0]
            out_down = (y0 + y1) / 2 >= cy0
            if is_mid and mid != "auto":
                asym_eff = 0.0 if mid == "sym" else 0.45
                out_down = (mid == "down")
        else:
            out_right = (x0 + x1) / 2 >= (m0.shape[1] - 1) / 2
        if tip_pow is not None:
            bar = _lens_bar(L, t, tip_pow)
        elif taper is not None:
            # 프리미티브는 '바깥=위'로 구운다 — 배치 시 각 획의 바깥 방향으로 맞춘다
            bar = _hexleaf_bar(L, t, taper, side_bulge, concave, asym_eff,
                               soft, zone_t)
        else:
            bar = _barrel_bar(L, t, bulge)
        if horiz:
            if taper is not None and asym_eff and out_down:
                bar = bar[::-1, :]
        else:
            if taper is not None and asym_eff:
                bar = np.rot90(bar) if not out_right else np.rot90(bar, 3)
            else:
                bar = np.rot90(bar)
        bh, bw = bar.shape
        yy0 = int(round(cy - bh / 2.0))
        xx0 = int(round(cx - bw / 2.0))
        acc[yy0:yy0 + bh, xx0:xx0 + bw] = np.maximum(
            acc[yy0:yy0 + bh, xx0:xx0 + bw], bar)
    ys, xs = np.nonzero(acc > 0.5)
    if not len(ys):
        return None
    acc = acc[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
    w2 = max(1, int(round(acc.shape[1] * height / acc.shape[0])))
    out = cv2.resize(acc, (w2, height), interpolation=cv2.INTER_AREA)
    return (np.clip(out, 0, 1) * 255).astype(np.uint8)


def norm_center(c, box):
    """실사진 크롭 정규화+중심 맞춤(glyph_overlay 와 같은 규약)."""
    c = cv2.resize(c, box).astype(np.float32)
    c = (c - c.min()) / max(1.0, c.max() - c.min())
    if c.mean() > 0.5:
        c = 1.0 - c
    m = c > 0.35
    if m.any():
        ys, xs = np.nonzero(m)
        c = np.roll(np.roll(c, int(round(c.shape[0] / 2 - ys.mean())), 0),
                    int(round(c.shape[1] / 2 - xs.mean())), 1)
    return c


# ── 메커니즘 판(--sheet mech) — '반전해 겹치면 무엇이 나오는가'를 획 하나
# 규모에서 보여 준다. cv2.putText 는 한글을 못 그리므로 라벨은 ASCII 로만.
def _largest_component(ch, variant, height, horizontal):
    m = (dseg_mask(ch, variant, height) > 0.5).astype(np.uint8)
    n, lab = cv2.connectedComponents(m)
    best = None
    for i in range(1, n):
        ys, xs = np.nonzero(lab == i)
        if len(xs) < 8:
            continue
        x0, x1, y0, y1 = xs.min(), xs.max(), ys.min(), ys.max()
        comp = (lab[y0:y1 + 1, x0:x1 + 1] == i).astype(np.float32)
        if ((comp.shape[1] > comp.shape[0]) != horizontal):
            continue
        if best is None or comp.sum() > best.sum():
            best = comp
    return best


def _shift(a, dy, dx):
    out = np.zeros_like(a)
    H, W = a.shape
    ys0, ys1 = max(0, dy), min(H, H + dy)
    xs0, xs1 = max(0, dx), min(W, W + dx)
    if ys1 > ys0 and xs1 > xs0:
        out[ys0:ys1, xs0:xs1] = a[ys0 - dy:ys1 - dy, xs0 - dx:xs1 - dx]
    return out


def _local_bow(comp, amp):
    """길이방향 가장자리를 바깥으로 휸 — v2 warp 를 개별 획에 적용한 것."""
    H, W = comp.shape
    x = np.arange(W, dtype=np.float32)
    y = np.arange(H, dtype=np.float32)
    X, Y = np.meshgrid(x, y)
    cx, cy = (W - 1) / 2.0, (H - 1) / 2.0
    if W > H:
        s = np.sin(np.pi * np.clip(X / W, 0, 1))
        mx = X
        my = Y + np.where(Y < cy, -amp * s, amp * s)
    else:
        s = np.sin(np.pi * np.clip(Y / H, 0, 1))
        mx = X + np.where(X < cx, -amp * s, amp * s)
        my = Y
    return cv2.remap(comp, mx, my, cv2.INTER_LINEAR,
                     borderMode=cv2.BORDER_CONSTANT, borderValue=0)


MECH_COLS = ["1 original", "2 flipped copy", "3 union in-place",
             "4 union offset(v3)", "5 intersect", "6 disk dilate",
             "7 local bow .20", "8 attach o=0", "9 attach o=.5"]


def _mech_ops(comp):
    """한 획에 각 연산을 적용한 마스크 목록(MECH_COLS 순서)."""
    H, W = comp.shape
    t = float(min(H, W))
    d = max(2, int(round(0.25 * t)))
    horiz = W > H
    flip = comp[::-1, :] if horiz else comp[:, ::-1]   # 길이방향 뒤집기(v3 연산)
    p = int(3 * t)
    base = cv2.copyMakeBorder(comp, p, p, p, p, cv2.BORDER_CONSTANT, value=0)
    flp = cv2.copyMakeBorder(flip, p, p, p, p, cv2.BORDER_CONSTANT, value=0)
    dy, dx = (-d, 0) if horiz else (0, d)              # 가로=위로, 세로=오른쪽
    k = max(3, int(round(0.5 * t)) | 1)
    dil = cv2.dilate(base, cv2.getStructuringElement(
        cv2.MORPH_ELLIPSE, (k, k))).astype(np.float32)

    def attach(overlap):
        """반전 사본을 양쪽에 나란히(사람 지시 2026-09-24). overlap=0 맞닿음,
        1 제자리(union in-place), 0.5 반쯤 겹침."""
        s = int(round((1.0 - overlap) * t))
        a = base
        for ddy, ddx in ((-s, 0), (s, 0)) if horiz else ((0, -s), (0, s)):
            a = np.maximum(a, _shift(flp, ddy, ddx))
        return a

    return [base, flp, np.maximum(base, flp),
            np.maximum(base, _shift(flp, dy, dx)), np.minimum(base, flp),
            dil, _local_bow(base, 0.20 * t), attach(0.0), attach(0.5)]


def build_mech_sheet(per_digit):
    CH, CW, LW = 300, 380, 150

    def cell(arr):
        img = np.full((CH, CW), 30, np.float32)
        if arr is not None:
            arr = np.clip(arr.astype(np.float32), 0, 1)
            s = min((CH - 24) / arr.shape[0], (CW - 24) / arr.shape[1])
            nw = max(1, int(arr.shape[1] * s))
            nh = max(1, int(arr.shape[0] * s))
            r = cv2.resize(arr, (nw, nh))
            y, x = (CH - nh) // 2, (CW - nw) // 2
            # 마스크는 0..1 — 배경 30 을 이기려면 0..255 스케일로 올려야 한다
            # (초판은 r*0.9 로 두어 max(30, 0.9)=30 → 빈 셀로 렌더됐다).
            img[y:y + nh, x:x + nw] = np.maximum(
                img[y:y + nh, x:x + nw], r * 235.0)
        return np.clip(img, 0, 255).astype(np.uint8)

    def strip(lbl, cells, header=False):
        img = np.full((CH, LW), 30, np.uint8)
        for i, ln in enumerate(lbl.split("\n")):
            cv2.putText(img, ln, (8, 60 + i * 26), cv2.FONT_HERSHEY_SIMPLEX,
                        0.55, (235, 235, 235), 1, cv2.LINE_AA)
        for c in cells:
            img = np.hstack([img, c])
        return img

    hseg = _largest_component("8", "Regular", 560, True)
    vseg = _largest_component("8", "Regular", 560, False)

    head = strip("OP ->", [cell(None) for _ in MECH_COLS])
    for j, name in enumerate(MECH_COLS):
        cv2.putText(head, name, (LW + j * CW + 8, 24),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, (235, 235, 235), 1,
                    cv2.LINE_AA)

    real = collect_real(per_digit)
    real_cells = []
    for dgt in "820":
        crops = real.get(dgt) or []
        if crops:
            c = norm_center(crops[0][1], (CW - 24, CH - 24))
            rc = (30 + np.clip(c, 0, 1) * 205).astype(np.uint8)
            rc = np.pad(rc, ((12, 12), (12, 12)),
                        constant_values=30)[:CH, :CW]
            real_cells.append(rc)
        else:
            real_cells.append(cell(None))
    row_real = strip("REAL x2\n(digit 8/2/0)",
                     real_cells + [cell(None)] * (len(MECH_COLS) - 3))
    row_h = strip("HORZ bar\nops", [cell(a) for a in _mech_ops(hseg)])
    row_v = strip("VERT bar\nops", [cell(a) for a in _mech_ops(vseg)])

    sep = lambda row: np.vstack([row, np.full((6, row.shape[1]), 60, np.uint8)])
    return np.vstack([sep(head), sep(row_real), sep(row_h), sep(row_v)])


def to_cell(mask):
    """마스크를 시트 칸(CELL_W×CELL_H, 어두운 배경)에 넣는다. 양측 나란히
    붙이기처럼 셀 폭을 넘는 넓은 글리프도 폭에 맞춰 축소해 중앙에 놓는다."""
    cell = np.full((CELL_H, CELL_W), 30, np.float32)
    if mask is None:
        return cell.astype(np.uint8)
    mask = mask.astype(np.float32)
    if mask.shape[0] != CELL_H or mask.shape[1] > CELL_W:
        s = min(CELL_H / mask.shape[0], CELL_W / mask.shape[1])
        mask = cv2.resize(mask, (max(1, int(round(mask.shape[1] * s))),
                                 max(1, int(round(mask.shape[0] * s)))))
    y = max(0, (CELL_H - mask.shape[0]) // 2)
    x = max(0, (CELL_W - mask.shape[1]) // 2)
    cell[y:y + mask.shape[0], x:x + mask.shape[1]] = np.maximum(
        cell[y:y + mask.shape[0], x:x + mask.shape[1]], mask * 0.9)
    return np.clip(cell, 0, 255).astype(np.uint8)


def label_strip(text, w, h):
    img = np.full((h, w), 30, np.uint8)
    for i, ln in enumerate(text.split("\n")):
        cv2.putText(img, ln, (8, 24 + i * 22), cv2.FONT_HERSHEY_SIMPLEX,
                    0.55, (235, 235, 235), 1, cv2.LINE_AA)
    return img


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--per-digit", type=int, default=16)
    ap.add_argument("--sheet", choices=["v3", "v4", "v5", "v6", "v7", "v8", "v9", "v10", "v11", "v12", "v13", "v14", "v15", "v16", "mech"], default="v4")
    args = ap.parse_args(argv)
    OUT.mkdir(parents=True, exist_ok=True)

    if args.sheet == "mech":
        sheet_img = build_mech_sheet(args.per_digit)
        out = OUT / "glyph_flip_mechanism.png"
        cv2.imwrite(str(out), sheet_img)
        print(f"-> {out}")
        print("메커니즘 판 — 반전·겹침·팽창·볼록이 각각 무엇을 만드는지 보여 준다.")
        return 0

    real = collect_real(args.per_digit)
    print("실사진 슬롯: " + " ".join(f"{d}:{len(real[d])}"
                                    for d in sorted(real)))

    if args.sheet == "v16":
        # 사람 판정 v15: 'UNI z=.60 매우매우 근접' — 최종 미세 스윕.
        rows = [
            ("REAL avg (n={})".format(args.per_digit), "real"),
            ("DSEG Regular (base)",
             lambda ch: dseg_mask(ch, "Regular", CELL_H)),
            ("z=.50",
             lambda ch: param_swap_mask(ch, "Regular", CELL_H, 0.0, taper=0.15,
                                        asym=0.30, mid="sym", zone_t=0.50)),
            ("z=.55",
             lambda ch: param_swap_mask(ch, "Regular", CELL_H, 0.0, taper=0.15,
                                        asym=0.30, mid="sym", zone_t=0.55)),
            ("z=.60 (v15 best)",
             lambda ch: param_swap_mask(ch, "Regular", CELL_H, 0.0, taper=0.15,
                                        asym=0.30, mid="sym", zone_t=0.60)),
            ("z=.65",
             lambda ch: param_swap_mask(ch, "Regular", CELL_H, 0.0, taper=0.15,
                                        asym=0.30, mid="sym", zone_t=0.65)),
            ("z=.70",
             lambda ch: param_swap_mask(ch, "Regular", CELL_H, 0.0, taper=0.15,
                                        asym=0.30, mid="sym", zone_t=0.70)),
        ]
        out_name = "glyph_convex_test_v16.png"

        ZH, ZW = 300, 380

        def zcell(img):
            c = np.full((ZH, ZW), 30, np.uint8)
            if img is None:
                return c
            s2 = min((ZH - 20) / img.shape[0], (ZW - 20) / img.shape[1])
            r = cv2.resize(img, (max(1, int(img.shape[1] * s2)),
                                 max(1, int(img.shape[0] * s2))))
            y, x = (ZH - r.shape[0]) // 2, (ZW - r.shape[1]) // 2
            c[y:y + r.shape[0], x:x + r.shape[1]] = np.maximum(
                c[y:y + r.shape[0], x:x + r.shape[1]], r)
            return c

        zlbl = np.full((ZH, 150), 30, np.uint8)
        for i, ln in enumerate(["ZOOM", "real-8 x2 /", "z-8"]):
            cv2.putText(zlbl, ln, (8, 110 + i * 26), cv2.FONT_HERSHEY_SIMPLEX,
                        0.55, (235, 235, 235), 1, cv2.LINE_AA)
        zcells = []
        for k in range(2):
            crops = real.get("8") or []
            zcells.append(zcell(None if not crops else (
                (30 + np.clip(norm_center(crops[k][1],
                                          (ZW - 20, ZH - 20)), 0, 1)
                 * 205).astype(np.uint8)) if len(crops) > k else None))
        mk = dseg_mask("8", "Regular", ZH - 20)
        zcells.append(zcell((np.clip(mk, 0, 1) * 205).astype(np.uint8)))
        for z in (0.50, 0.55, 0.60, 0.65, 0.70):
            mk = param_swap_mask("8", "Regular", ZH - 20, 0.0, taper=0.15,
                                 asym=0.30, mid="sym", zone_t=z)
            zcells.append(zcell(mk))
        zrow = np.hstack([zlbl] + zcells)
        zrow = np.vstack([zrow, np.full((6, zrow.shape[1]), 60, np.uint8)])
    elif args.sheet == "v15":
        # 사람 판정 v14: mid sym 확정 + '바깥 획의 안쪽 기울기 = 가운데 획
        # 기울기 일치' — 테이퍼를 획두께 기준(z)으로 통일해 전 획 같은 각도.
        rows = [
            ("REAL avg (n={})".format(args.per_digit), "real"),
            ("DSEG Regular (base)",
             lambda ch: dseg_mask(ch, "Regular", CELL_H)),
            ("v14 ref (len-based)",
             lambda ch: param_swap_mask(ch, "Regular", CELL_H, 0.0, taper=0.15,
                                        asym=0.30, mid="sym")),
            ("UNI z=.60 (steeper)",
             lambda ch: param_swap_mask(ch, "Regular", CELL_H, 0.0, taper=0.15,
                                        asym=0.30, mid="sym", zone_t=0.60)),
            ("UNI z=.74 (=G angle)",
             lambda ch: param_swap_mask(ch, "Regular", CELL_H, 0.0, taper=0.15,
                                        asym=0.30, mid="sym", zone_t=0.74)),
            ("UNI z=.85 (shallower)",
             lambda ch: param_swap_mask(ch, "Regular", CELL_H, 0.0, taper=0.15,
                                        asym=0.30, mid="sym", zone_t=0.85)),
        ]
        out_name = "glyph_convex_test_v15.png"

        ZH, ZW = 300, 380

        def zcell(img):
            c = np.full((ZH, ZW), 30, np.uint8)
            if img is None:
                return c
            s2 = min((ZH - 20) / img.shape[0], (ZW - 20) / img.shape[1])
            r = cv2.resize(img, (max(1, int(img.shape[1] * s2)),
                                 max(1, int(img.shape[0] * s2))))
            y, x = (ZH - r.shape[0]) // 2, (ZW - r.shape[1]) // 2
            c[y:y + r.shape[0], x:x + r.shape[1]] = np.maximum(
                c[y:y + r.shape[0], x:x + r.shape[1]], r)
            return c

        zlbl = np.full((ZH, 150), 30, np.uint8)
        for i, ln in enumerate(["ZOOM", "real-8 x2 /", "uni-8"]):
            cv2.putText(zlbl, ln, (8, 110 + i * 26), cv2.FONT_HERSHEY_SIMPLEX,
                        0.55, (235, 235, 235), 1, cv2.LINE_AA)
        zcells = []
        for k in range(2):
            crops = real.get("8") or []
            zcells.append(zcell(None if not crops else (
                (30 + np.clip(norm_center(crops[k][1],
                                          (ZW - 20, ZH - 20)), 0, 1)
                 * 205).astype(np.uint8)) if len(crops) > k else None))
        mk = dseg_mask("8", "Regular", ZH - 20)
        zcells.append(zcell((np.clip(mk, 0, 1) * 205).astype(np.uint8)))
        for kw in (dict(taper=0.15, asym=0.30, mid="sym"),
                   dict(taper=0.15, asym=0.30, mid="sym", zone_t=0.60),
                   dict(taper=0.15, asym=0.30, mid="sym", zone_t=0.74),
                   dict(taper=0.15, asym=0.30, mid="sym", zone_t=0.85)):
            mk = param_swap_mask("8", "Regular", ZH - 20, 0.0, **kw)
            zcells.append(zcell(mk))
        zrow = np.hstack([zlbl] + zcells)
        zrow = np.vstack([zrow, np.full((6, zrow.shape[1]), 60, np.uint8)])
    elif args.sheet == "v14":
        # 사람 판정 v13: OUT.40(IN.35) 아주 근접. 남은 갭 = 글자 중앙의 가로획
        # (7세그 명칭 G) — 현재 위·아래 각도가 거의 동일. 변형 4종 제시.
        rows = [
            ("REAL avg (n={})".format(args.per_digit), "real"),
            ("DSEG Regular (base)",
             lambda ch: dseg_mask(ch, "Regular", CELL_H)),
            ("v13 ref (mid auto)",
             lambda ch: param_swap_mask(ch, "Regular", CELL_H, 0.0, taper=0.15,
                                        asym=0.30)),
            ("MID sym (equal angles)",
             lambda ch: param_swap_mask(ch, "Regular", CELL_H, 0.0, taper=0.15,
                                        asym=0.30, mid="sym")),
            ("MID top-blunt",
             lambda ch: param_swap_mask(ch, "Regular", CELL_H, 0.0, taper=0.15,
                                        asym=0.30, mid="up")),
            ("MID bot-blunt",
             lambda ch: param_swap_mask(ch, "Regular", CELL_H, 0.0, taper=0.15,
                                        asym=0.30, mid="down")),
        ]
        out_name = "glyph_convex_test_v14.png"

        ZH, ZW = 300, 380

        def zcell(img):
            c = np.full((ZH, ZW), 30, np.uint8)
            if img is None:
                return c
            s = min((ZH - 20) / img.shape[0], (ZW - 20) / img.shape[1])
            r = cv2.resize(img, (max(1, int(img.shape[1] * s)),
                                 max(1, int(img.shape[0] * s))))
            y, x = (ZH - r.shape[0]) // 2, (ZW - r.shape[1]) // 2
            c[y:y + r.shape[0], x:x + r.shape[1]] = np.maximum(
                c[y:y + r.shape[0], x:x + r.shape[1]], r)
            return c

        zlbl = np.full((ZH, 150), 30, np.uint8)
        for i, ln in enumerate(["ZOOM", "real-8 x2 /", "mid-8"]):
            cv2.putText(zlbl, ln, (8, 110 + i * 26), cv2.FONT_HERSHEY_SIMPLEX,
                        0.55, (235, 235, 235), 1, cv2.LINE_AA)
        zcells = []
        for k in range(2):
            crops = real.get("8") or []
            zcells.append(zcell(None if not crops else (
                (30 + np.clip(norm_center(crops[k][1],
                                          (ZW - 20, ZH - 20)), 0, 1)
                 * 205).astype(np.uint8)) if len(crops) > k else None))
        mk = dseg_mask("8", "Regular", ZH - 20)
        zcells.append(zcell((np.clip(mk, 0, 1) * 205).astype(np.uint8)))
        for kw in (dict(taper=0.15, asym=0.30),
                   dict(taper=0.15, asym=0.30, mid="sym"),
                   dict(taper=0.15, asym=0.30, mid="up"),
                   dict(taper=0.15, asym=0.30, mid="down")):
            mk = param_swap_mask("8", "Regular", ZH - 20, 0.0, **kw)
            zcells.append(zcell(mk))
        zrow = np.hstack([zlbl] + zcells)
        zrow = np.vstack([zrow, np.full((6, zrow.shape[1]), 60, np.uint8)])
    elif args.sheet == "v13":
        # 사람 판정 v12: '가장 긴 직선(OUT.36 IN.28) 최근접 + 안·바깥 직선
        # 차이를 더 줄이고 양쪽 사선 각도도 더 줄일 것' — 테이퍼 구간을
        # 더 축소해 직선 연장·간극 축소.
        rows = [
            ("REAL avg (n={})".format(args.per_digit), "real"),
            ("DSEG Regular (base)",
             lambda ch: dseg_mask(ch, "Regular", CELL_H)),
            ("v12 ref OUT.36 IN.28",
             lambda ch: param_swap_mask(ch, "Regular", CELL_H, 0.0, taper=0.22,
                                        asym=0.35)),
            ("OUT.38 IN.32 (t.18 a.35)",
             lambda ch: param_swap_mask(ch, "Regular", CELL_H, 0.0, taper=0.18,
                                        asym=0.35)),
            ("OUT.37 IN.32 (t.18 a.30)",
             lambda ch: param_swap_mask(ch, "Regular", CELL_H, 0.0, taper=0.18,
                                        asym=0.30)),
            ("OUT.40 IN.35 (t.15 a.30)",
             lambda ch: param_swap_mask(ch, "Regular", CELL_H, 0.0, taper=0.15,
                                        asym=0.30)),
            ("OUT.42 IN.38 (t.12 a.35)",
             lambda ch: param_swap_mask(ch, "Regular", CELL_H, 0.0, taper=0.12,
                                        asym=0.35)),
        ]
        out_name = "glyph_convex_test_v13.png"

        ZH, ZW = 300, 380

        def zcell(img):
            c = np.full((ZH, ZW), 30, np.uint8)
            if img is None:
                return c
            s = min((ZH - 20) / img.shape[0], (ZW - 20) / img.shape[1])
            r = cv2.resize(img, (max(1, int(img.shape[1] * s)),
                                 max(1, int(img.shape[0] * s))))
            y, x = (ZH - r.shape[0]) // 2, (ZW - r.shape[1]) // 2
            c[y:y + r.shape[0], x:x + r.shape[1]] = np.maximum(
                c[y:y + r.shape[0], x:x + r.shape[1]], r)
            return c

        zlbl = np.full((ZH, 150), 30, np.uint8)
        for i, ln in enumerate(["ZOOM", "real-8 x2 /", "flat-8"]):
            cv2.putText(zlbl, ln, (8, 110 + i * 26), cv2.FONT_HERSHEY_SIMPLEX,
                        0.55, (235, 235, 235), 1, cv2.LINE_AA)
        zcells = []
        for k in range(2):
            crops = real.get("8") or []
            zcells.append(zcell(None if not crops else (
                (30 + np.clip(norm_center(crops[k][1],
                                          (ZW - 20, ZH - 20)), 0, 1)
                 * 205).astype(np.uint8)) if len(crops) > k else None))
        mk = dseg_mask("8", "Regular", ZH - 20)
        zcells.append(zcell((np.clip(mk, 0, 1) * 205).astype(np.uint8)))
        for kw in (dict(taper=0.22, asym=0.35), dict(taper=0.18, asym=0.35),
                   dict(taper=0.18, asym=0.30), dict(taper=0.15, asym=0.30),
                   dict(taper=0.12, asym=0.35)):
            mk = param_swap_mask("8", "Regular", ZH - 20, 0.0, **kw)
            zcells.append(zcell(mk))
        zrow = np.hstack([zlbl] + zcells)
        zrow = np.vstack([zrow, np.full((6, zrow.shape[1]), 60, np.uint8)])
    elif args.sheet == "v12":
        # 사람 판정: v11 에서 'v10 ref(sharp)' 최근접(soft 기각). 지시 3건 —
        # 안쪽 직선 < 바깥 직선 유지, 둘의 차 축소, 둘 다 길게. 직선 길이
        # (전체 길이 비) = 0.5 - 테이퍼구간 라벨에 직접 표기.
        rows = [
            ("REAL avg (n={})".format(args.per_digit), "real"),
            ("DSEG Regular (base)",
             lambda ch: dseg_mask(ch, "Regular", CELL_H)),
            ("v10 ref OUT.29 IN.15",
             lambda ch: param_swap_mask(ch, "Regular", CELL_H, 0.0, taper=0.35,
                                        asym=0.40)),
            ("OUT.32 IN.20 (t.30)",
             lambda ch: param_swap_mask(ch, "Regular", CELL_H, 0.0, taper=0.30,
                                        asym=0.40)),
            ("OUT.33 IN.22 (t.28)",
             lambda ch: param_swap_mask(ch, "Regular", CELL_H, 0.0, taper=0.28,
                                        asym=0.40)),
            ("OUT.30 IN.22 (t.28 a.30)",
             lambda ch: param_swap_mask(ch, "Regular", CELL_H, 0.0, taper=0.28,
                                        asym=0.30)),
            ("OUT.33 IN.25 (t.25 a.30)",
             lambda ch: param_swap_mask(ch, "Regular", CELL_H, 0.0, taper=0.25,
                                        asym=0.30)),
            ("OUT.36 IN.28 (t.22 a.35)",
             lambda ch: param_swap_mask(ch, "Regular", CELL_H, 0.0, taper=0.22,
                                        asym=0.35)),
        ]
        out_name = "glyph_convex_test_v12.png"

        ZH, ZW = 300, 380

        def zcell(img):
            c = np.full((ZH, ZW), 30, np.uint8)
            if img is None:
                return c
            s = min((ZH - 20) / img.shape[0], (ZW - 20) / img.shape[1])
            r = cv2.resize(img, (max(1, int(img.shape[1] * s)),
                                 max(1, int(img.shape[0] * s))))
            y, x = (ZH - r.shape[0]) // 2, (ZW - r.shape[1]) // 2
            c[y:y + r.shape[0], x:x + r.shape[1]] = np.maximum(
                c[y:y + r.shape[0], x:x + r.shape[1]], r)
            return c

        zlbl = np.full((ZH, 150), 30, np.uint8)
        for i, ln in enumerate(["ZOOM", "real-8 x2 /", "flat-8"]):
            cv2.putText(zlbl, ln, (8, 110 + i * 26), cv2.FONT_HERSHEY_SIMPLEX,
                        0.55, (235, 235, 235), 1, cv2.LINE_AA)
        zcells = []
        for k in range(2):
            crops = real.get("8") or []
            zcells.append(zcell(None if not crops else (
                (30 + np.clip(norm_center(crops[k][1],
                                          (ZW - 20, ZH - 20)), 0, 1)
                 * 205).astype(np.uint8)) if len(crops) > k else None))
        mk = dseg_mask("8", "Regular", ZH - 20)
        zcells.append(zcell((np.clip(mk, 0, 1) * 205).astype(np.uint8)))
        for kw in (dict(taper=0.35, asym=0.40), dict(taper=0.30, asym=0.40),
                   dict(taper=0.28, asym=0.40), dict(taper=0.28, asym=0.30),
                   dict(taper=0.25, asym=0.30), dict(taper=0.22, asym=0.35)):
            mk = param_swap_mask("8", "Regular", ZH - 20, 0.0, **kw)
            zcells.append(zcell(mk))
        zrow = np.hstack([zlbl] + zcells)
        zrow = np.vstack([zrow, np.full((6, zrow.shape[1]), 60, np.uint8)])
    elif args.sheet == "v11":
        rows = [
            ("REAL avg (n={})".format(args.per_digit), "real"),
            ("DSEG Regular (base)",
             lambda ch: dseg_mask(ch, "Regular", CELL_H)),
            ("v10 ref (sharp)",
             lambda ch: param_swap_mask(ch, "Regular", CELL_H, 0.0, taper=0.35,
                                        asym=0.40)),
            ("soft .50",
             lambda ch: param_swap_mask(ch, "Regular", CELL_H, 0.0, taper=0.35,
                                        asym=0.40, soft=0.50)),
            ("soft 1.00",
             lambda ch: param_swap_mask(ch, "Regular", CELL_H, 0.0, taper=0.35,
                                        asym=0.40, soft=1.00)),
            ("taper .28 sharp",
             lambda ch: param_swap_mask(ch, "Regular", CELL_H, 0.0, taper=0.28,
                                        asym=0.40)),
            ("taper .28 soft .50",
             lambda ch: param_swap_mask(ch, "Regular", CELL_H, 0.0, taper=0.28,
                                        asym=0.40, soft=0.50)),
        ]
        out_name = "glyph_convex_test_v11.png"

        ZH, ZW = 300, 380

        def zcell(img):
            c = np.full((ZH, ZW), 30, np.uint8)
            if img is None:
                return c
            s = min((ZH - 20) / img.shape[0], (ZW - 20) / img.shape[1])
            r = cv2.resize(img, (max(1, int(img.shape[1] * s)),
                                 max(1, int(img.shape[0] * s))))
            y, x = (ZH - r.shape[0]) // 2, (ZW - r.shape[1]) // 2
            c[y:y + r.shape[0], x:x + r.shape[1]] = np.maximum(
                c[y:y + r.shape[0], x:x + r.shape[1]], r)
            return c

        zlbl = np.full((ZH, 150), 30, np.uint8)
        for i, ln in enumerate(["ZOOM", "real-8 x2 /", "soft-8"]):
            cv2.putText(zlbl, ln, (8, 110 + i * 26), cv2.FONT_HERSHEY_SIMPLEX,
                        0.55, (235, 235, 235), 1, cv2.LINE_AA)
        zcells = []
        for k in range(2):
            crops = real.get("8") or []
            zcells.append(zcell(None if not crops else (
                (30 + np.clip(norm_center(crops[k][1],
                                          (ZW - 20, ZH - 20)), 0, 1)
                 * 205).astype(np.uint8)) if len(crops) > k else None))
        mk = dseg_mask("8", "Regular", ZH - 20)
        zcells.append(zcell((np.clip(mk, 0, 1) * 205).astype(np.uint8)))
        for kw in (dict(taper=0.35, asym=0.40),
                   dict(taper=0.35, asym=0.40, soft=0.50),
                   dict(taper=0.35, asym=0.40, soft=1.00),
                   dict(taper=0.28, asym=0.40),
                   dict(taper=0.28, asym=0.40, soft=0.50)):
            mk = param_swap_mask("8", "Regular", ZH - 20, 0.0, **kw)
            zcells.append(zcell(mk))
        zrow = np.hstack([zlbl] + zcells)
        zrow = np.vstack([zrow, np.full((6, zrow.shape[1]), 60, np.uint8)])
    elif args.sheet == "v10":
        rows = [
            ("REAL avg (n={})".format(args.per_digit), "real"),
            ("DSEG Regular (base)",
             lambda ch: dseg_mask(ch, "Regular", CELL_H)),
            ("hex .35 sym (v8)",
             lambda ch: param_swap_mask(ch, "Regular", CELL_H, 0.0, taper=0.35)),
            ("outer .30 (inner v8)",
             lambda ch: param_swap_mask(ch, "Regular", CELL_H, 0.0, taper=0.35,
                                        asym=0.30)),
            ("outer .40 (inner v8)",
             lambda ch: param_swap_mask(ch, "Regular", CELL_H, 0.0, taper=0.35,
                                        asym=0.40)),
            ("outer .50 (inner v8)",
             lambda ch: param_swap_mask(ch, "Regular", CELL_H, 0.0, taper=0.35,
                                        asym=0.50)),
            ("outer .70 (inner v8)",
             lambda ch: param_swap_mask(ch, "Regular", CELL_H, 0.0, taper=0.35,
                                        asym=0.70)),
        ]
        out_name = "glyph_convex_test_v10.png"

        ZH, ZW = 300, 380

        def zcell(img):
            c = np.full((ZH, ZW), 30, np.uint8)
            if img is None:
                return c
            s = min((ZH - 20) / img.shape[0], (ZW - 20) / img.shape[1])
            r = cv2.resize(img, (max(1, int(img.shape[1] * s)),
                                 max(1, int(img.shape[0] * s))))
            y, x = (ZH - r.shape[0]) // 2, (ZW - r.shape[1]) // 2
            c[y:y + r.shape[0], x:x + r.shape[1]] = np.maximum(
                c[y:y + r.shape[0], x:x + r.shape[1]], r)
            return c

        zlbl = np.full((ZH, 150), 30, np.uint8)
        for i, ln in enumerate(["ZOOM", "real-8 x2 /", "outer-8"]):
            cv2.putText(zlbl, ln, (8, 110 + i * 26), cv2.FONT_HERSHEY_SIMPLEX,
                        0.55, (235, 235, 235), 1, cv2.LINE_AA)
        zcells = []
        for k in range(2):
            crops = real.get("8") or []
            zcells.append(zcell(None if not crops else (
                (30 + np.clip(norm_center(crops[k][1],
                                          (ZW - 20, ZH - 20)), 0, 1)
                 * 205).astype(np.uint8)) if len(crops) > k else None))
        mk = dseg_mask("8", "Regular", ZH - 20)
        zcells.append(zcell((np.clip(mk, 0, 1) * 205).astype(np.uint8)))
        for kw in (dict(taper=0.35), dict(taper=0.35, asym=0.30),
                   dict(taper=0.35, asym=0.40), dict(taper=0.35, asym=0.50),
                   dict(taper=0.35, asym=0.70)):
            mk = param_swap_mask("8", "Regular", ZH - 20, 0.0, **kw)
            zcells.append(zcell(mk))
        zrow = np.hstack([zlbl] + zcells)
        zrow = np.vstack([zrow, np.full((6, zrow.shape[1]), 60, np.uint8)])
    elif args.sheet == "v9":
        rows = [
            ("REAL avg (n={})".format(args.per_digit), "real"),
            ("DSEG Regular (base)",
             lambda ch: dseg_mask(ch, "Regular", CELL_H)),
            ("hex .35 sym (v8)",
             lambda ch: param_swap_mask(ch, "Regular", CELL_H, 0.0, taper=0.35)),
            ("asym .40",
             lambda ch: param_swap_mask(ch, "Regular", CELL_H, 0.0, taper=0.35,
                                        asym=0.40)),
            ("asym .70",
             lambda ch: param_swap_mask(ch, "Regular", CELL_H, 0.0, taper=0.35,
                                        asym=0.70)),
            ("asym 1.00 (one-side)",
             lambda ch: param_swap_mask(ch, "Regular", CELL_H, 0.0, taper=0.35,
                                        asym=1.00)),
            ("asym MIRROR -.70",
             lambda ch: param_swap_mask(ch, "Regular", CELL_H, 0.0, taper=0.35,
                                        asym=-0.70)),
        ]
        out_name = "glyph_convex_test_v9.png"

        ZH, ZW = 300, 380

        def zcell(img):
            c = np.full((ZH, ZW), 30, np.uint8)
            if img is None:
                return c
            s = min((ZH - 20) / img.shape[0], (ZW - 20) / img.shape[1])
            r = cv2.resize(img, (max(1, int(img.shape[1] * s)),
                                 max(1, int(img.shape[0] * s))))
            y, x = (ZH - r.shape[0]) // 2, (ZW - r.shape[1]) // 2
            c[y:y + r.shape[0], x:x + r.shape[1]] = np.maximum(
                c[y:y + r.shape[0], x:x + r.shape[1]], r)
            return c

        zlbl = np.full((ZH, 150), 30, np.uint8)
        for i, ln in enumerate(["ZOOM", "real-8 x2 /", "asym-8"]):
            cv2.putText(zlbl, ln, (8, 110 + i * 26), cv2.FONT_HERSHEY_SIMPLEX,
                        0.55, (235, 235, 235), 1, cv2.LINE_AA)
        zcells = []
        for k in range(2):
            crops = real.get("8") or []
            zcells.append(zcell(None if not crops else (
                (30 + np.clip(norm_center(crops[k][1],
                                          (ZW - 20, ZH - 20)), 0, 1)
                 * 205).astype(np.uint8)) if len(crops) > k else None))
        mk = dseg_mask("8", "Regular", ZH - 20)
        zcells.append(zcell((np.clip(mk, 0, 1) * 205).astype(np.uint8)))
        for kw in (dict(taper=0.35), dict(taper=0.35, asym=0.40),
                   dict(taper=0.35, asym=0.70), dict(taper=0.35, asym=1.0),
                   dict(taper=0.35, asym=-0.70)):
            mk = param_swap_mask("8", "Regular", ZH - 20, 0.0, **kw)
            zcells.append(zcell(mk))
        zrow = np.hstack([zlbl] + zcells)
        zrow = np.vstack([zrow, np.full((6, zrow.shape[1]), 60, np.uint8)])
    elif args.sheet == "v8":
        rows = [
            ("REAL avg (n={})".format(args.per_digit), "real"),
            ("DSEG Regular (base)",
             lambda ch: dseg_mask(ch, "Regular", CELL_H)),
            ("hex taper=.25 (blunt)",
             lambda ch: param_swap_mask(ch, "Regular", CELL_H, 0.0, taper=0.25)),
            ("hex taper=.35",
             lambda ch: param_swap_mask(ch, "Regular", CELL_H, 0.0, taper=0.35)),
            ("hex taper=.45 (sharp)",
             lambda ch: param_swap_mask(ch, "Regular", CELL_H, 0.0, taper=0.45)),
            ("leaf taper=.35 (concave)",
             lambda ch: param_swap_mask(ch, "Regular", CELL_H, 0.0, taper=0.35,
                                        concave=True)),
            ("hex .35 + bulge .05",
             lambda ch: param_swap_mask(ch, "Regular", CELL_H, 0.0, taper=0.35,
                                        side_bulge=0.05)),
        ]
        out_name = "glyph_convex_test_v8.png"

        ZH, ZW = 300, 380

        def zcell(img):
            c = np.full((ZH, ZW), 30, np.uint8)
            if img is None:
                return c
            s = min((ZH - 20) / img.shape[0], (ZW - 20) / img.shape[1])
            r = cv2.resize(img, (max(1, int(img.shape[1] * s)),
                                 max(1, int(img.shape[0] * s))))
            y, x = (ZH - r.shape[0]) // 2, (ZW - r.shape[1]) // 2
            c[y:y + r.shape[0], x:x + r.shape[1]] = np.maximum(
                c[y:y + r.shape[0], x:x + r.shape[1]], r)
            return c

        zlbl = np.full((ZH, 150), 30, np.uint8)
        for i, ln in enumerate(["ZOOM", "real-8 x2 /", "hex-8"]):
            cv2.putText(zlbl, ln, (8, 110 + i * 26), cv2.FONT_HERSHEY_SIMPLEX,
                        0.55, (235, 235, 235), 1, cv2.LINE_AA)
        zcells = []
        for k in range(2):
            crops = real.get("8") or []
            zcells.append(zcell(None if not crops else (
                (30 + np.clip(norm_center(crops[k][1],
                                          (ZW - 20, ZH - 20)), 0, 1)
                 * 205).astype(np.uint8)) if len(crops) > k else None))
        mk = dseg_mask("8", "Regular", ZH - 20)
        zcells.append(zcell((np.clip(mk, 0, 1) * 205).astype(np.uint8)))
        for kw in (dict(taper=0.25), dict(taper=0.35), dict(taper=0.35,
                                                            concave=True),
                   dict(taper=0.35, side_bulge=0.05)):
            mk = param_swap_mask("8", "Regular", ZH - 20, 0.0, **kw)
            zcells.append(zcell(mk))
        zrow = np.hstack([zlbl] + zcells)
        zrow = np.vstack([zrow, np.full((6, zrow.shape[1]), 60, np.uint8)])
    elif args.sheet == "v7":
        rows = [
            ("REAL avg (n={})".format(args.per_digit), "real"),
            ("DSEG Regular (base)",
             lambda ch: dseg_mask(ch, "Regular", CELL_H)),
            ("lens p=.40 (sharp)",
             lambda ch: param_swap_mask(ch, "Regular", CELL_H, 0.0,
                                        tip_pow=0.40)),
            ("lens p=.60",
             lambda ch: param_swap_mask(ch, "Regular", CELL_H, 0.0,
                                        tip_pow=0.60)),
            ("lens p=.80",
             lambda ch: param_swap_mask(ch, "Regular", CELL_H, 0.0,
                                        tip_pow=0.80)),
            ("lens p=1.0 (soft)",
             lambda ch: param_swap_mask(ch, "Regular", CELL_H, 0.0,
                                        tip_pow=1.0)),
            ("ref round b=.20 (v6)",
             lambda ch: param_swap_mask(ch, "Regular", CELL_H, 0.20)),
        ]
        out_name = "glyph_convex_test_v7.png"

        ZH, ZW = 300, 380

        def zcell(img):
            c = np.full((ZH, ZW), 30, np.uint8)
            if img is None:
                return c
            s = min((ZH - 20) / img.shape[0], (ZW - 20) / img.shape[1])
            r = cv2.resize(img, (max(1, int(img.shape[1] * s)),
                                 max(1, int(img.shape[0] * s))))
            y, x = (ZH - r.shape[0]) // 2, (ZW - r.shape[1]) // 2
            c[y:y + r.shape[0], x:x + r.shape[1]] = np.maximum(
                c[y:y + r.shape[0], x:x + r.shape[1]], r)
            return c

        zlbl = np.full((ZH, 150), 30, np.uint8)
        for i, ln in enumerate(["ZOOM", "real-8 x2 /", "lens-8"]):
            cv2.putText(zlbl, ln, (8, 110 + i * 26), cv2.FONT_HERSHEY_SIMPLEX,
                        0.55, (235, 235, 235), 1, cv2.LINE_AA)
        zcells = []
        for k in range(2):
            crops = real.get("8") or []
            zcells.append(zcell(None if not crops else (
                (30 + np.clip(norm_center(crops[k][1],
                                          (ZW - 20, ZH - 20)), 0, 1)
                 * 205).astype(np.uint8)) if len(crops) > k else None))
        mk = dseg_mask("8", "Regular", ZH - 20)
        zcells.append(zcell((np.clip(mk, 0, 1) * 205).astype(np.uint8)))
        for p in (0.60, 0.80, 1.0):
            mk = param_swap_mask("8", "Regular", ZH - 20, 0.0, tip_pow=p)
            zcells.append(zcell(mk))
        mk = param_swap_mask("8", "Regular", ZH - 20, 0.20)
        zcells.append(zcell(mk))
        zrow = np.hstack([zlbl] + zcells)
        zrow = np.vstack([zrow, np.full((6, zrow.shape[1]), 60, np.uint8)])
    elif args.sheet == "v6":
        rows = [
            ("REAL avg (n={})".format(args.per_digit), "real"),
            ("DSEG Regular (base)",
             lambda ch: dseg_mask(ch, "Regular", CELL_H)),
            ("param b=.00 (round ends)",
             lambda ch: param_swap_mask(ch, "Regular", CELL_H, 0.0)),
            ("param b=.10",
             lambda ch: param_swap_mask(ch, "Regular", CELL_H, 0.10)),
            ("param b=.20",
             lambda ch: param_swap_mask(ch, "Regular", CELL_H, 0.20)),
            ("param b=.30",
             lambda ch: param_swap_mask(ch, "Regular", CELL_H, 0.30)),
        ]
        out_name = "glyph_convex_test_v6.png"

        # 확대 스트립 — 작은 셀로는 곡률·끝단이 안 보여 판정이 불가능하다.
        ZH, ZW = 300, 380

        def zcell(img):
            c = np.full((ZH, ZW), 30, np.uint8)
            if img is None:
                return c
            s = min((ZH - 20) / img.shape[0], (ZW - 20) / img.shape[1])
            r = cv2.resize(img, (max(1, int(img.shape[1] * s)),
                                 max(1, int(img.shape[0] * s))))
            y, x = (ZH - r.shape[0]) // 2, (ZW - r.shape[1]) // 2
            c[y:y + r.shape[0], x:x + r.shape[1]] = np.maximum(
                c[y:y + r.shape[0], x:x + r.shape[1]], r)
            return c

        zlbl = np.full((ZH, 150), 30, np.uint8)
        for i, ln in enumerate(["ZOOM", "real-8 x2 /", "param-8"]):
            cv2.putText(zlbl, ln, (8, 110 + i * 26), cv2.FONT_HERSHEY_SIMPLEX,
                        0.55, (235, 235, 235), 1, cv2.LINE_AA)
        zcells = []
        for k in range(2):                       # 실촌 8 확대 2장
            crops = real.get("8") or []
            zcells.append(zcell(None if not crops else (
                (30 + np.clip(norm_center(crops[k][1],
                                          (ZW - 20, ZH - 20)), 0, 1)
                 * 205).astype(np.uint8)) if len(crops) > k else None))
        mk = dseg_mask("8", "Regular", ZH - 20)
        zcells.append(zcell((np.clip(mk, 0, 1) * 205).astype(np.uint8)))
        for b in (0.0, 0.10, 0.20, 0.30):       # 파라메트릭 8 확대
            mk = param_swap_mask("8", "Regular", ZH - 20, b)
            zcells.append(zcell(mk))
        zrow = np.hstack([zlbl] + zcells)
        zrow = np.vstack([zrow, np.full((6, zrow.shape[1]), 60, np.uint8)])
    elif args.sheet == "v5":
        rows = [
            ("REAL avg (n={})".format(args.per_digit), "real"),
            ("DSEG Regular (base)",
             lambda ch: dseg_mask(ch, "Regular", CELL_H)),
            ("attach o=0.00 (3-layer)",
             lambda ch: dseg_attach_mask(ch, "Regular", CELL_H, 0.0)),
            ("attach o=0.25",
             lambda ch: dseg_attach_mask(ch, "Regular", CELL_H, 0.25)),
            ("attach o=0.50",
             lambda ch: dseg_attach_mask(ch, "Regular", CELL_H, 0.50)),
            ("attach o=0.75",
             lambda ch: dseg_attach_mask(ch, "Regular", CELL_H, 0.75)),
            ("attach o=1.00 (=in-place)",
             lambda ch: dseg_attach_mask(ch, "Regular", CELL_H, 1.00)),
        ]
        out_name = "glyph_convex_test_v5.png"
    elif args.sheet == "v4":
        rows = [
            ("REAL 평균(n={})".format(args.per_digit), "real"),
            ("DSEG Cls Regular(현행)",
             lambda ch: dseg_mask(ch, "Regular", CELL_H)),
            ("warp Reg .10",
             lambda ch: dseg_warp_mask(ch, "Regular", CELL_H, 0.10)),
            ("warp Reg .15",
             lambda ch: dseg_warp_mask(ch, "Regular", CELL_H, 0.15)),
            ("warp Reg .20",
             lambda ch: dseg_warp_mask(ch, "Regular", CELL_H, 0.20)),
            ("warp Reg .25",
             lambda ch: dseg_warp_mask(ch, "Regular", CELL_H, 0.25)),
            ("warp Bold .15",
             lambda ch: dseg_warp_mask(ch, "Bold", CELL_H, 0.15)),
            ("warp Bold .20",
             lambda ch: dseg_warp_mask(ch, "Bold", CELL_H, 0.20)),
            ("반전=180도회전 제자리겹침",
             lambda ch: dseg_rot_overlap_mask(ch, "Regular", CELL_H, 0.0)),
            ("반전=180도회전 바깥.25",
             lambda ch: dseg_rot_overlap_mask(ch, "Regular", CELL_H, 0.25)),
        ]
        out_name = "glyph_convex_test_v4.png"
    else:
        rows = [
            ("REAL 평균(n={})".format(args.per_digit), "real"),
            ("DSEG Cls Regular(현행)",
             lambda ch: dseg_mask(ch, "Regular", CELL_H)),
            ("A 미러반전+바깥겹침",
             lambda ch: dseg_overlap_mask(ch, "Regular", CELL_H)),
            ("B 반전없이+바깥겹침",
             lambda ch: dseg_overlap_mask(ch, "Regular", CELL_H, mirror=False)),
            ("C 가로획 전부 위로(문장그대로)",
             lambda ch: dseg_overlap_mask(ch, "Regular", CELL_H, horz="literal")),
            ("D 바깥 반투명 번짐",
             lambda ch: dseg_overlap_mask(ch, "Regular", CELL_H, soft=True)),
            ("E v2 warp .15(참조)",
             lambda ch: dseg_warp_mask(ch, "Regular", CELL_H, 0.15)),
        ]
        out_name = "glyph_convex_test_v3.png"

    header = label_strip("자릿수 →", LBL_W, CELL_H)
    for d in map(str, range(10)):
        c = np.full((CELL_H, CELL_W), 30, np.uint8)
        cv2.putText(c, d, (CELL_W // 2 - 14, CELL_H // 2 + 18),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.6, (120, 120, 120), 3)
        header = np.hstack([header, c])
    sheet = [header, np.full((4, header.shape[1]), 80, np.uint8)]

    for lbl, f in rows:
        line = label_strip(lbl, LBL_W, CELL_H)
        for d in map(str, range(10)):
            if f == "real":
                crops = real[d]
                if crops:
                    img = np.mean([norm_center(c, (CELL_W, CELL_H))
                                   for _, c in crops], 0)
                    cell = (30 + np.clip(img, 0, 1) * 205).astype(np.uint8)
                else:
                    cell = np.full((CELL_H, CELL_W), 30, np.uint8)
            else:
                mk = f(d)
                cell = to_cell(None if mk is None
                               else (np.clip(mk, 0, 1) * 255).astype(np.uint8)
                               if mk.dtype != np.uint8 else mk)
            line = np.hstack([line, cell])
        sheet.append(line)
        sheet.append(np.full((6, line.shape[1]), 60, np.uint8))

    body = np.vstack(sheet)
    if args.sheet in ("v6", "v7", "v8", "v9", "v10", "v11", "v12", "v13", "v14", "v15", "v16"):
        w = max(body.shape[1], zrow.shape[1])
        body = np.hstack([
            body, np.full((body.shape[0], w - body.shape[1]), 30, np.uint8)])
        zrow = np.hstack([
            zrow, np.full((zrow.shape[0], w - zrow.shape[1]), 30, np.uint8)])
        body = np.vstack([body, zrow])
    out = OUT / out_name
    cv2.imwrite(str(out), body)
    print(f"-> {out}")
    print("이 판은 재는 도구가 아니다 — 보고 사람이 판정한다.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
