# 고전 CV 로 숫자줄을 찾을 수 있는가 — 타당성 판정 파인더(최종). 밴드 라벨 86장.
#
# 왜: 리더 크롭은 GM 검출기의 LCD 박스인데, 가로형에서는 밴드가 박스 밖으로
# 나간다(46장 중 17장, 대부분 왼쪽). 검출기를 다시 학습하려면 라벨이 필요하다 —
# 학습 없는 고전 CV 로 되는지가 이 파일의 질문이다. 결과는
# docs/reports/cv-band-viability.md 참조.
#
# 살아남은 설계(전부 실측 근거):
#  * CLAHE 를 쓰지 않는다. 흐린 획을 죽인다(1000: 무CLAHE 적응형에서만 숫자
#    생존, clipLimit 2.0·4.0 전멸). 1판이 세로형에서 무넝진 게 이것이다.
#  * Otsu·적응형을 양 극성 모두 내서 후보 풀을 만들고 행 점수로 고른다.
#    Otsu 는 백라이트 가로형에, 적응형은 어두운 배경이 섞인 세로형에 강하다.
#  * 글자는 외곽선(RETR_EXTERNAL) 기반 — 적응형의 속 빈 획도 글자로 산다.
#    잉크(실제 획 픽셀)는 (채운 실루엣 ∧ 이진화)로 계산한다.
#  * 줄 묶기는 중심y 정렬 + 키 유사(0.4~1.15배). 키 조건을 빼면 날짜·단위
#    텍스트가 흡수돼 박스가 옆으로 수 밴드폭 늘어난다(1612 실측).
#  * 찾은 행의 스트립을 국소 스트레치해 재이진화(_refine_row) — 배경과
#    Δ40 안팎의 흐린 선행 '1' 을 회수한다(1005 실측).
#  * pad_x 로 가로 방향만 GM 폭만큼 더 넓힌다. 가로형 이탈 클러스터가
#    0.90~0.96배에서 나오기 때문(대칭 pad 0.45 는 세로형을 무너뜨린다).
#
# 판정 이력: 1판(단일 이진화+CLAHE) 다담음 13/68 → 2판(채도+부풀림 최대덩이)
# 기각 → 3판(CLAHE 유지) 세로형 9/13 완전실패로 악화 → 4판부터 무CLAHE.
#
# 과적합 방지: 튜닝은 --split train(캐시 real_train_ids) 에서만. holdout 은
# 최종 1회. 86장에 손잡이를 다 맞추면 튜닝이 아니라 암기다.
import argparse, json, sys
from pathlib import Path

import cv2
import numpy as np

from eval_reader import load_gray  # EXIF 규약 한 곳에서만

HERE = Path(__file__).resolve().parent
DATUMO = HERE.parent / "upstream" / "datumo"

WORK_H = 400   # 작업 해상도. 원본 해상도에서 크기 비례 커널을 쓰면 65px 짜리
               # 커널이 나와 화면 전체를 한 덩어리로 뭉갠다(실측).
               # 획 두께 실측(중앙 7px, p10 5, p90 11)도 이 해상도 기준이다.

# 기본 파라미터. 물리적 근거가 있는 값만 들어 있다 — 스윕은 train 에서.
DEFAULTS = dict(
    pad=0.30,        # GM 박스를 사방으로 넓혀 탐색(가로형은 박스가 밴드를 안 담는다)
    pad_x=1.00,      # 가로 방향 추가 확장. 가로형 이탈 클러스터(실측 0.90~0.96배)가
                     # pad 0.3 을 넘는다 — GM 폭만큼 왼쪽으로 나가는 장들이 있다
    glare=0.0,       # 반사광 상한 백분위. 0이면 끈다(3판까지 CLAHE 가리개 역할이었음)
    clahe=0.0,       # CLAHE clipLimit. 0이면 끈다 — 흐린 획을 죽인다(1000 실측)
    panel=0,         # 1이면 LCD 패널 마스크 안에서만 찾는다(베젤 흡수 차단)
    adap_win=31,     # 적응형 창(px). 획 두께 중앙의 4배 이상은 되어야 한다
    refine=1,        # 1이면 행 스트립을 국소 스트레치해 재이진화(흐린 '1' 회수)
    bar_join=1,      # 1이면 행 옆의 키 큰 얇은 막대('1'의 외톨이 막대)를 흡수
    hmin=0.08, hmax=0.60,   # 숫자 높이 / 크롭 높이 범위
    wmax=0.45,       # 숫자 폭 / 크롭 폭 상한
    ar_lo=0.12, ar_hi=2.0,  # 숫자 하나의 가로세로비 범위
    ink_min=0.08,    # 박스 대비 실제 획 픽셀 하한(그림자 윤곽 따위 걸러낸다)
    row_tol=0.45,    # 줄 묶기: 중심y 허용 편차(기준 숫자 높이 배수)
    pad_x_tall=0.10,  # 세로형 가로 여백. 가로형(pad_x)과 따로 둔다
    lead_one=1,      # 선행 글자가 막대(1)면 자리 경계까지 왼쪽 확장
    lead_one_ar=0.45,  # 이 가로세로비 미만이면 막대로 본다
    grow_x=0.30, grow_y=0.10,  # 찾은 상자의 가로/세로 여백 비율(최종 운영점)
)


def suppress_glare(g, pct=99.0):
    """반사광을 상한에서 눌러 붙인다. 하이라이트가 이진화를 지배하지 않게."""
    hi = float(np.percentile(g, pct))
    if hi <= 0:
        return g
    return np.clip(g.astype(np.float32) * (255.0 / hi), 0, 255).astype(np.uint8)


def panel_mask(g):
    """양극성 Otsu 중 가장 큰 매끈한 덩어리 = LCD 패널. 못 찾으면 None."""
    h, w = g.shape
    best = None
    for inv in (cv2.THRESH_BINARY, cv2.THRESH_BINARY_INV):
        _, bwp = cv2.threshold(g, 0, 255, inv + cv2.THRESH_OTSU)
        bwp = cv2.morphologyEx(bwp, cv2.MORPH_CLOSE,
                               cv2.getStructuringElement(cv2.MORPH_RECT, (15, 15)))
        n, lab, st, _ = cv2.connectedComponentsWithStats(bwp, 8)
        for i in range(1, n):
            x, y, cw, ch, area = st[i]
            if (0.15 < area / (h * w) < 0.95 and area / (cw * ch) > 0.55
                    and ch > h * 0.3 and cw > w * 0.3):
                if best is None or area > best[0]:
                    best = (area, lab == i)
    if best is None:
        return None
    return cv2.dilate(best[1].astype(np.uint8) * 255,
                      cv2.getStructuringElement(cv2.MORPH_RECT, (9, 9)))


def _binarize(g, method, inv, win):
    if method == "otsu":
        _, bw = cv2.threshold(g, 0, 255, inv + cv2.THRESH_OTSU)
    else:
        bw = cv2.adaptiveThreshold(g, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                   inv, win, 8)
    # 세그먼트 사이 틈만 메운다. 숫자끼리 붙을 만큼 크면 안 된다.
    return cv2.morphologyEx(bw, cv2.MORPH_CLOSE,
                            cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5)))


def _glyphs(bw, h, w, P):
    """외곽선 기반 글자 후보. 속 빈 획(적응형 부작용)도 글자로 산다.

    잉크 = (채운 실루엣 ∧ 이진화) — 속 빈 "0" 의 다각형 면적은 꽉 찬 것과
    같아서 면적을 그대로 쓰면 점수가 부풀고 노이즈를 못 걸러낸다.
    """
    bwb = bw > 0
    out = []
    cnts, _ = cv2.findContours(bw, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    for c in cnts:
        x, y, cw, ch = cv2.boundingRect(c)
        if ch < h * P["hmin"] or ch > h * P["hmax"]:
            continue                      # 작으면 날짜·아이콘, 크면 배경·베젤
        if cw < 3 or cw > w * P["wmax"]:
            continue
        if not (P["ar_lo"] < (cw / ch) < P["ar_hi"]):
            continue                      # 7세그 숫자 하나의 가로세로비
        solid = np.zeros((ch, cw), np.uint8)
        cv2.drawContours(solid, [c - [x, y]], -1, 1, -1)
        ink = int(solid[bwb[y:y+ch, x:x+cw]].sum())
        if ink < cw * ch * P["ink_min"]:
            continue
        out.append((x, y, cw, ch, ink, c))
    return out


def _rows(glyphs, tol, h_lo=0.40, h_hi=1.15):
    """키 큰 글자부터 줄을 만든다. 모든 줄이 후보다 — 날짜줄이 이기면 점수 탓.

    같은 줄의 조건은 중심y 정렬 **더하기 키 유사**이다. 키 조건을 빼면
    날짜·단위 텍스트가 줄에 끌려들어와 박스가 옆으로 수 밴드폭만큼 늘어난다
    (1612 실측: R 과잉 1.3밴드폭).
    """
    glyphs = sorted(glyphs, key=lambda g: -g[3])
    rows, used = [], [False] * len(glyphs)
    for i, g in enumerate(glyphs):
        if used[i]:
            continue
        cy = g[1] + g[3] / 2
        grp = [g]; used[i] = True
        for j, d in enumerate(glyphs):
            if used[j]:
                continue
            if abs((d[1] + d[3] / 2) - cy) >= max(g[3], d[3]) * tol:
                continue
            if not (h_lo * g[3] <= d[3] <= h_hi * g[3]):
                continue
            grp.append(d); used[j] = True
        rows.append(grp)
    return rows


def _refine_row(g, best):
    """찾은 행의 스트립을 국소 스트레치해 재이진화 — 흐린 선행 '1' 회수.

    흐린 막대는 배경과 Δ40 안팎이라 적응형 임계가 국소 평균에 끌려 못 넘는다
    (1005 실측: 첫 막대 Δ37, 창을 81px 로 올려도 이진화 불가). 행을 이미
    알았으므로 스트립 통계로 정규화하는 건 순환이 아니라 2단계 정제다.
    """
    _, grp, (x0, y0, x1, y1), _ang = best
    hmax = max(g5[3] for g5 in grp)
    sy0 = max(0, int(y0 - hmax * 0.2)); sy1 = min(g.shape[0], int(y1 + hmax * 0.2))
    strip = g[sy0:sy1]
    lo, hi = np.percentile(strip, (2, 98))
    if hi - lo < 10:
        return best
    st = np.clip((strip.astype(np.float32) - lo) / (hi - lo) * 255, 0, 255).astype(np.uint8)
    bw = cv2.adaptiveThreshold(st, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                               cv2.THRESH_BINARY_INV, 81, 5)
    bw = cv2.morphologyEx(bw, cv2.MORPH_CLOSE,
                          cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5)))
    n, lab, stt, _ = cv2.connectedComponentsWithStats(bw, 8)
    pitch = None
    dg = [g5 for g5 in grp if g5[3] >= 0.6 * hmax]
    if len(dg) >= 2:
        cx = sorted(d5[0] + d5[2] / 2 for d5 in dg)
        pitch = float(np.median(np.diff(cx)))
    new = list(grp)
    nx0, ny0, nx1, ny1 = x0, y0, x1, y1
    for i in range(1, n):
        x, y, cw, ch, area = stt[i]
        gy = y + sy0
        vy0, vy1 = gy, gy + ch
        ov = min(y1, vy1) - max(y0, vy0)
        if ov < (vy1 - vy0) * 0.5:
            continue
        near = (x0 - (pitch or hmax) <= x + cw) and (x <= x1 + (pitch or hmax))
        if not near:
            continue
        if any(abs((c[1] + c[3] / 2) - (gy + ch / 2)) < hmax * 0.5
               and not (c[0] + c[2] < x or x + cw < c[0]) for c in new):
            continue
        if (hmax * 0.6 <= ch <= hmax * 1.3 and 3 <= cw <= ch * 1.2
                and area >= cw * ch * 0.2):
            new.append((x, gy, cw, ch, int(area), None))
            nx0 = min(nx0, x); ny0 = min(ny0, gy)
            nx1 = max(nx1, x + cw); ny1 = max(ny1, gy + ch)
        elif (x + cw <= x0 + hmax * 0.2 and cw < ch * 0.5 and cw >= 3
                and hmax * 0.25 <= ch <= hmax * 1.3
                and area >= cw * ch * 0.3):
            # 흐린 선행 '1' 조각 — 보이는 core 만 이진화돼 키가 짧다.
            # 왼쪽의 세로 막대 모양만 받는다: 오른쪽 조각은 단위 텍스트를
            # 흡수해 IoU 를 깎는다(가로형 실측 0.96→0.64). x만 늘리고 y 는
            # 행에 스냅한다.
            new.append((x, y0, cw, y1 - y0, int(area), None))
            nx0 = min(nx0, x)
    if (nx0, ny0, nx1, ny1) == (x0, y0, x1, y1):
        return best
    pts = [c5[5] for c5 in new if c5[5] is not None]
    ang = cv2.minAreaRect(np.vstack(pts))[2] if pts else _ang
    return (best[0], new, (nx0, ny0, nx1, ny1), ang)


def _join_bars(grp, glyphs):
    """행 옆의 '1' 외톨이 막대를 행에 흡수한다.

    7세그 '1' 은 세로 막대 두 개다. 이진화에서 둘이 붙으면 글자 하나로 나오지만
    흐리면 한 막대만 살아남는다(1005 실측). 행과 세로로 겹치고 키가 행 최고 키의
    0.6배 이상인 얇은 성분(w < h*0.35)을 좌우 이웃으로 흡수한다.
    """
    if not grp:
        return grp
    hmax = max(g[3] for g in grp)
    y0 = min(g[1] for g in grp); y1 = max(g[1] + g[3] for g in grp)
    x0 = min(g[0] for g in grp); x1 = max(g[0] + g[2] for g in grp)
    out = list(grp)
    gap = hmax * 0.6          # 흡수 허용 간격 — 숫자 피치보다 작게
    for g in glyphs:
        if g in out:
            continue
        gw, gh = g[2], g[3]
        if gw > gh * 0.35 or gh < hmax * 0.6:
            continue                       # 막대 모양이 아니거나 키가 작다
        vy0, vy1 = g[1], g[1] + gh
        ov = min(y1, vy1) - max(y0, vy0)
        if ov < min(y1 - y0, vy1 - vy0) * 0.5:
            continue                       # 세로로 절반 이상 안 겹친다
        if x0 - gap <= g[0] + gw and g[0] <= x1 + gap:
            out.append(g)
    return out


def find_band(gray, P=None):
    """숫자줄 상자를 원본 crop 좌표로 돌려준다. (박스, minAreaRect 각도) 또는 None.

    각도는 측정값일 뿐이다 — 회전 보정은 이 파이프라인의 범위가 아니다.
    """
    P = {**DEFAULTS, **(P or {})}
    H, W = gray.shape
    sc = WORK_H / H
    g = cv2.resize(gray, (max(1, int(W * sc)), WORK_H), interpolation=cv2.INTER_AREA)
    if P["glare"]:
        g = suppress_glare(g, P["glare"])
    if P["clahe"]:
        g = cv2.createCLAHE(clipLimit=P["clahe"], tileGridSize=(8, 8)).apply(g)
    h, w = g.shape
    pm = panel_mask(g) if P["panel"] else None

    best = None
    # 밝은 획/어두운 획 둘 다 본다 — 백라이트 화면은 극성이 뒤집힌다.
    maps = []
    win = int(P["adap_win"]) | 1
    for inv in (cv2.THRESH_BINARY_INV, cv2.THRESH_BINARY):
        maps.append(("otsu", _binarize(g, "otsu", inv, win)))
        maps.append(("adaptive", _binarize(g, "adaptive", inv, win)))
    for tag, bw in maps:
        if pm is not None:
            bw = cv2.bitwise_and(bw, pm)
        glyphs = _glyphs(bw, h, w, P)
        for grp in _rows(glyphs, P["row_tol"]):
            if len(grp) < 2:          # 값은 한 자리가 아니다(20~600, LO, HI)
                continue
            if P["bar_join"]:
                grp = _join_bars(grp, glyphs)
            ink = sum(g5[4] for g5 in grp)
            score = ink * len(grp)
            if best is None or score > best[0]:
                x0 = min(g5[0] for g5 in grp); y0 = min(g5[1] for g5 in grp)
                x1 = max(g5[0] + g5[2] for g5 in grp)
                y1 = max(g5[1] + g5[3] for g5 in grp)
                pts = np.vstack([g5[5] for g5 in grp])
                # OpenCV 4.x minAreaRect 각도는 [0,90) 규약이라 너비<높이면
                # 90 근처가 나온다. 긴 변 기준으로 바꿔 장비 기울기 지표로 쓴다.
                rect = cv2.minAreaRect(pts)
                ang = rect[2] if rect[1][0] >= rect[1][1] else (rect[2] + 90.0) % 180.0
                if ang >= 90.0:
                    ang -= 180.0
                best = (score, grp, (x0, y0, x1, y1), ang)
    if best is None:
        return None
    if P["refine"]:
        best = _refine_row(g, best)
    x0, y0, x1, y1 = best[2]
    if P["lead_one"]:
        # **선행 `1` 보정.** 7세그 `1` 은 오른쪽 두 획만 켜져 자리 폭의 오른쪽
        # 끝에만 잉크가 있다. 사람 라벨은 그 자리 전체를 감싸므로, 잉크만 쫓는
        # 파인더는 정의상 그 왼쪽을 못 담는다.
        #
        # 실측(2026-09-09, 밴드 라벨 86장): GT 가 1 로 시작하는 장이 66장(77%)
        # 이고 그 장들의 라벨 왼쪽 여백 중앙은 0.202(밴드폭 대비). 1 로 시작하지
        # 않는 20장은 0.074 다. 즉 세로형 다담음 부진의 대부분이 알고리즘이
        # 아니라 이 글자 모양이다.
        #
        # GLM 의 empty_left 는 "검출 글자가 정확히 2개"일 때만 작동해서 이
        # 현상(3글자인데 첫 글자가 1)을 못 잡았다.
        hs = [q[3] for q in best[1]]
        H = max(hs) if hs else 0
        dg = sorted([q for q in best[1] if q[3] >= 0.6 * H], key=lambda q: q[0])
        if len(dg) >= 2 and H > 0:
            lead = dg[0]
            if lead[2] / lead[3] < P["lead_one_ar"]:      # 막대 모양 = 1
                cx = [q[0] + q[2] / 2 for q in dg]
                pitch = min(cx[i + 1] - cx[i] for i in range(len(cx) - 1))
                if pitch > 0.5 * H:
                    x0 = min(x0, lead[0] + lead[2] - pitch)
    box = (x0 / sc, y0 / sc, x1 / sc, y1 / sc)   # grow 전 — 후처리에서 한다
    return box, best[3]


def grow_box(box, P):
    """찾은 상자의 사방 여백(grow). find_band 뒤의 순수 후처리라 스윕이 공짜다."""
    gx = (box[2] - box[0]) * P["grow_x"]
    gy = (box[3] - box[1]) * P["grow_y"]
    return (box[0] - gx, box[1] - gy, box[2] + gx, box[3] + gy)


def iou(a, b):
    x0, y0 = max(a[0], b[0]), max(a[1], b[1])
    x1, y1 = min(a[2], b[2]), min(a[3], b[3])
    i = max(0.0, x1 - x0) * max(0.0, y1 - y0)
    ua = (a[2]-a[0])*(a[3]-a[1]) + (b[2]-b[0])*(b[3]-b[1]) - i
    return i / ua if ua > 0 else 0.0


def contains(pred, true, tol=0.02):
    """예측 상자가 정답 밴드를 (여유 tol 안에서) 다 담았는가."""
    wt = true[2] - true[0]; ht = true[3] - true[1]
    return (pred[0] <= true[0] + wt*tol and pred[1] <= true[1] + ht*tol and
            pred[2] >= true[2] - wt*tol and pred[3] >= true[3] - ht*tol)


def load_eval_sets():
    band = {}
    for l in (HERE / "band_boxes.jsonl").read_text(encoding="utf-8").splitlines():
        if l.strip():
            j = json.loads(l); q = np.array(j["quad"], float)
            band[j["id"]] = (q[:,0].min(), q[:,1].min(), q[:,0].max(), q[:,1].max())
    gm = {}
    for l in (HERE / "gmscreen_quads.jsonl").read_text(encoding="utf-8").splitlines():
        if l.strip():
            j = json.loads(l); q = np.array(j["quad"], float)
            gm[j["id"]] = (q[:,0].min(), q[:,1].min(), q[:,0].max(), q[:,1].max())
    rot = {json.loads(l)["id"]
           for l in (HERE / "band_rotation.jsonl").read_text(encoding="utf-8").splitlines()
           if l.strip()}
    wide = set(json.loads((HERE / "_diag" / "wide_all" / "wide_ids.json")
                          .read_text(encoding="utf-8")))
    z = np.load(HERE / "data_cache_v2.npz", allow_pickle=True)
    tr = set(str(x) for x in z["real_train_ids"])
    ho = set(str(x) for x in z["real_holdout_ids"])
    return band, gm, rot, wide, tr, ho


def crop_for(gray, g, pad, pad_x=None):
    """GM 박스를 넓힌 탐색 크롭. pad_x 로 가로만 더 넓힐 수 있다 —
    가로형은 밴드가 박스 왼쪽으로 나가는 경우가 있어서다."""
    gw, gh = g[2]-g[0], g[3]-g[1]
    px = pad if pad_x is None else pad_x
    x0 = max(0, int(g[0] - gw*px)); y0 = max(0, int(g[1] - gh*pad))
    x1 = min(gray.shape[1], int(g[2] + gw*px))
    y1 = min(gray.shape[0], int(g[3] + gh*pad))
    return x0, y0, x1, y1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", default="train", choices=["train", "holdout", "all"],
                    help="채점 대상. 튜닝은 train 으로만 — holdout 은 최종 1회")
    for k, v in DEFAULTS.items():
        ap.add_argument(f"--{k.replace('_','-')}", type=float, default=v)
    ap.add_argument("--dump", default=None, help="오버레이 png 를 저장할 폴더")
    ap.add_argument("--json", default=None, help="이미지별 결과 json 경로")
    a = ap.parse_args()
    P = {k: getattr(a, k.replace("-", "_")) for k in DEFAULTS}

    band, gm, rot, wide, tr, ho = load_eval_sets()
    dump = Path(a.dump) if a.dump else None
    if dump:
        dump.mkdir(parents=True, exist_ok=True)

    def keep(cid):
        if a.split == "train":
            return cid in tr
        if a.split == "holdout":
            return cid in ho
        return True

    res = {}   # (split, stratum) -> [(cid, iou, cont, found, angle, pred, true)]
    for cid, tb in sorted(band.items()):
        if cid not in gm or not keep(cid):
            continue
        p = DATUMO / "extracted" / "TILDE" / f"{cid}.jpg"
        if not p.exists():
            continue
        gray = load_gray(p)
        # **탐색 여백은 박스 형태에 따라 다르다.**
        # 가로형은 밴드가 GM 박스 밖으로 나가는 장이 46장 중 14장이라 넓게
        # 봐야 한다. 세로형은 GM 박스가 밴드를 **항상** 담으므로(귀무모델
        # 21/21) 넓히면 방해물만 들어온다 — 실측: pad_x=1.0 이면 크롭에 기기
        # 버튼 행이 들어와 파인더가 그쪽을 고른다(1002. 점수가 잉크×글자수라
        # 숫자 2개보다 버튼 3개가 이긴다).
        gb = gm[cid]
        is_wide = (gb[2] - gb[0]) / max(1e-6, gb[3] - gb[1]) > 1.2
        _px = P["pad_x"] if is_wide else P["pad_x_tall"]
        x0, y0, x1, y1 = crop_for(gray, gb, P["pad"], _px)
        sub = gray[y0:y1, x0:x1]
        if sub.size == 0:
            continue
        r = find_band(sub, P)
        key = "회전" if cid in rot else ("가로형" if cid in wide else "세로형")
        split = "train" if cid in tr else "holdout"
        if r is None:
            res.setdefault((split, key), []).append(
                (cid, 0.0, False, False, None, None, tb))
            continue
        box, ang = r
        box = grow_box(box, P)
        pred = (box[0]+x0, box[1]+y0, box[2]+x0, box[3]+y0)
        res.setdefault((split, key), []).append(
            (cid, iou(pred, tb), contains(pred, tb), True, ang, pred, tb))
        if dump:
            v = cv2.cvtColor(sub, cv2.COLOR_GRAY2BGR)
            cv2.rectangle(v, (int(box[0]), int(box[1])), (int(box[2]), int(box[3])),
                          (0, 0, 255), 6)
            cv2.rectangle(v, (int(tb[0]-x0), int(tb[1]-y0)),
                          (int(tb[2]-x0), int(tb[3]-y0)), (0, 255, 255), 6)
            s = 900 / max(v.shape[:2])
            cv2.imwrite(str(dump / f"{cid.replace('/','__')}.png"),
                        cv2.resize(v, None, fx=s, fy=s))

    print(f"split={a.split} " + " ".join(f"{k}={P[k]:g}" for k in DEFAULTS))
    recs = []
    for (split, key) in sorted(res):
        v = res[(split, key)]
        ious = np.array([x[1] for x in v])
        cont = sum(1 for x in v if x[2])
        nf = sum(1 for x in v if not x[3])
        print(f"  {split:<7} {key:<3} n={len(v):<3} 다담음 {cont:>3}/{len(v):<3}"
              f" ({cont/len(v)*100:5.1f}%)   완전실패 {nf:>2}   "
              f"IoU중앙 {np.median(ious):.3f}")
        for cid, iv, cv, fv, ang, pred, tb2 in v:
            recs.append(dict(id=cid, split=split, stratum=key, iou=round(iv, 4),
                             contained=bool(cv), found=bool(fv),
                             pred=[round(p, 1) for p in pred] if pred else None,
                             true=[round(p, 1) for p in tb2],
                             angle=None if ang is None else round(float(ang), 2)))
    if a.json:
        Path(a.json).parent.mkdir(parents=True, exist_ok=True)
        Path(a.json).write_text(json.dumps(recs, ensure_ascii=False, indent=1),
                                encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
