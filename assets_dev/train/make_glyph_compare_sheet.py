# 글리프 대조 시트 — 실사진 숫자와 합성 숫자를 자릿수별로 나란히 놓는다.
#
# 재지 않는다. 나란히 보여 주고 **사람이 값을 부른다** —
# [[no-real-photo-ruler-for-synth]], make_unit_gap_sheet.py 와 같은 방식이다.
# 획 굵기·세그먼트 간격·기울기를 이 스크립트가 숫자로 뽑지 않는 것이 의도다.
#
# 슬롯 자르기 규약(둘 다 같게 적용한다 — 이게 이 시트가 공정한 이유다):
#   밴드 상자를 자릿수만큼 **균등 분할**해 슬롯 하나를 크롭한다.
#   3자리 값만 쓴다. 2자리 값은 기기에 따라 앞 빈자리가 밴드에 포함되기도
#   하고 아니기도 해서(band_label_slot_audit.py, 2026-09-14) 슬롯 번호와
#   글자가 어긋난다. 어긋난 채로 겹쳐 놓으면 시트가 거짓말을 한다.
#
# 실사진 쪽 밴드는 사람 라벨(band_boxes.jsonl, 읽기 전용)만 쓴다 — 검출기
# 출력을 쓰면 검출 오차가 글리프 차이로 보인다.
#
# 사용:
#   python make_glyph_compare_sheet.py --synth-count 400
import argparse
import json
import random
from pathlib import Path

import cv2
import numpy as np

HERE = Path(__file__).resolve().parent
DATUMO = HERE.parent / "upstream" / "datumo"
LABELS = DATUMO / "labels.jsonl"
BANDS = HERE / "band_boxes.jsonl"          # 읽기 전용 — 절대 쓰지 않는다

CELL_H = 150                                # 모든 글리프를 이 높이로 맞춘다


def rect(quad):
    q = np.asarray(quad, float)
    return [q[:, 0].min(), q[:, 1].min(), q[:, 0].max(), q[:, 1].max()]


def slot_crops(img, band, text):
    """밴드를 자릿수만큼 균등 분할해 (글자, 크롭) 목록을 낸다."""
    x0, y0, x1, y1 = [int(round(v)) for v in band]
    x0, y0 = max(0, x0), max(0, y0)
    x1, y1 = min(img.shape[1], x1), min(img.shape[0], y1)
    if x1 - x0 < len(text) * 4 or y1 - y0 < 8:
        return []
    w = (x1 - x0) / len(text)
    out = []
    for i, ch in enumerate(text):
        cx0 = int(x0 + i * w)
        cx1 = int(x0 + (i + 1) * w)
        c = img[y0:y1, cx0:cx1]
        if c.size:
            out.append((ch, c))
    return out


def crop_rect(img, r):
    x0, y0, x1, y1 = [int(round(v)) for v in r]
    x0, y0 = max(0, x0), max(0, y0)
    x1, y1 = min(img.shape[1], x1), min(img.shape[0], y1)
    if x1 - x0 < 4 or y1 - y0 < 8:
        return None
    return img[y0:y1, x0:x1]


def fit(c):
    s = CELL_H / c.shape[0]
    c = cv2.resize(c, (max(1, int(c.shape[1] * s)), CELL_H))
    return c


def collect_real(limit_per_digit):
    readings = {}
    for l in LABELS.read_text(encoding="utf-8").splitlines():
        if l.strip():
            j = json.loads(l)
            readings[j["id"]] = (str(j.get("reading", "")), j["image"])
    per = {str(d): [] for d in range(10)}
    for l in BANDS.read_text(encoding="utf-8").splitlines():
        if not l.strip():
            continue
        j = json.loads(l)
        if not j.get("quad") or j["id"] not in readings:
            continue
        text, rel = readings[j["id"]]
        if len(text) != 3 or not text.isdigit():
            continue
        if all(len(per[c]) >= limit_per_digit for c in text):
            continue
        img = cv2.imread(str(DATUMO / rel), cv2.IMREAD_GRAYSCALE)
        if img is None:
            continue
        for ch, c in slot_crops(img, rect(j["quad"]), text):
            if len(per[ch]) < limit_per_digit:
                per[ch].append((j["id"], fit(c)))
    return per


def collect_synth(count, seed, limit_per_digit):
    import synth_panel as sp
    rng = random.Random(seed)
    per = {str(d): [] for d in range(10)}
    for _ in range(count):
        if all(len(v) >= limit_per_digit for v in per.values()):
            break
        s = sp.render_panel(sp.sample_value(rng), rng)
        text = s["label"]
        if len(text) != 3:
            continue
        band = next((r for r in s["rects"] if r[4] == "band"), None)
        if band is None:
            continue
        img = cv2.cvtColor(s["panel"], cv2.COLOR_BGR2GRAY) \
            if s["panel"].ndim == 3 else s["panel"]
        # rects 는 **워프 전** 패널 좌표이고 panel 은 **워프 후** 그림이다.
        # 그대로 자르면 기울어진 장에서 이웃 칸과 mg/dL 이 끌려 들어온다
        # (2026-09-17 에 실제로 냈다 — [[unnamed-coordinate-frame]]).
        # quad_panel -> quad 가 같은 워프의 네 점 대응이라 호모그래피를 되찾아
        # 슬롯 네 귀를 옮긴 뒤 자른다.
        M = cv2.getPerspectiveTransform(
            np.float32(s["quad_panel"]), np.float32(s["quad"]))
        bx0, by0, bx1, by1 = band[:4]
        w = (bx1 - bx0) / len(text)
        for i, ch in enumerate(text):
            if len(per[ch]) >= limit_per_digit:
                continue
            corners = np.float32([[[bx0 + i * w, by0], [bx0 + (i + 1) * w, by0],
                                   [bx0 + (i + 1) * w, by1], [bx0 + i * w, by1]]])
            q = cv2.perspectiveTransform(corners, M)[0]
            c = crop_rect(img, rect(q))
            if c is not None:
                per[ch].append((s["profile"], fit(c)))
    return per


def row(items, n, pad=8):
    cells = []
    for _, c in items[:n]:
        cells.append(c)
        cells.append(np.full((CELL_H, pad), 30, np.uint8))
    if not cells:
        return np.full((CELL_H, pad), 30, np.uint8)
    return np.hstack(cells)


def overlay_sheet(real, synth, out_png, box=(120, 180)):
    """자릿수마다 실사진 평균과 합성 평균을 같은 상자에 겹쳐 놓는다.

    빨강=실사진, 초록=합성. 겹치면 노랑. 기울기와 획 굵기의 차이가 색 갈라짐
    으로 보인다. 숫자를 내지 않는 것이 의도다 — 이건 보는 판이지 재는 자가
    아니다([[no-real-photo-ruler-for-synth]]).

    극성이 섞여 있으므로(어두운 화면·밝은 숫자와 그 반대) 잉크가 밝은 쪽이
    되게 각 크롭을 정규화한 뒤 평균한다. 안 그러면 두 극성이 서로를 지운다.
    """
    def norm(c):
        c = cv2.resize(c, box).astype(np.float32)
        c = (c - c.min()) / max(1.0, c.max() - c.min())
        if c.mean() > 0.5:                 # 배경이 밝으면 뒤집어 잉크를 밝게
            c = 1.0 - c
        return c

    def center(c):
        """잉크 무게중심을 상자 한가운데로 옮긴다.

        안 옮기면 **자리**의 차이가 **모양**의 차이로 보인다. 슬롯 균등 분할이
        실사진과 합성에서 한 칸씩 어긋나기만 해도 겹친 판 전체가 옆으로 밀려
        기울기 차이처럼 읽힌다. 자리 차이는 따로 볼 판(_placed)에 남긴다.
        """
        m = c > 0.35
        if not m.any():
            return c
        ys, xs = np.nonzero(m)
        dy = int(round(c.shape[0] / 2 - ys.mean()))
        dx = int(round(c.shape[1] / 2 - xs.mean()))
        return np.roll(np.roll(c, dy, 0), dx, 1)

    tiles, tiles_placed = [], []
    for d in map(str, range(10)):
        r = [norm(c) for _, c in real[d]]
        s = [norm(c) for _, c in synth[d]]
        if not r or not s:
            continue
        pm_r, pm_s = np.mean(r, 0), np.mean(s, 0)
        bgr_p = np.zeros((box[1], box[0], 3), np.float32)
        bgr_p[..., 2], bgr_p[..., 1] = pm_r, pm_s
        tp = (np.clip(bgr_p, 0, 1) * 255).astype(np.uint8)
        cv2.putText(tp, d, (4, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.8,
                    (255, 255, 255), 2)
        tiles_placed.append(tp)

        rm = np.mean([center(c) for c in r], 0)
        sm = np.mean([center(c) for c in s], 0)
        bgr = np.zeros((box[1], box[0], 3), np.float32)
        bgr[..., 2] = rm            # 빨강 = 실사진
        bgr[..., 1] = sm            # 초록 = 합성
        t = (np.clip(bgr, 0, 1) * 255).astype(np.uint8)
        cv2.putText(t, d, (4, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.8,
                    (255, 255, 255), 2)
        cv2.putText(t, f"r{len(r)}/s{len(s)}", (4, box[1] - 8),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.4, (200, 200, 200), 1)
        tiles.append(t)
    def band(rows, text):
        g = np.hstack(rows)
        lg = np.full((30, g.shape[1], 3), 30, np.uint8)
        cv2.putText(lg, text, (6, 21), cv2.FONT_HERSHEY_SIMPLEX, 0.55,
                    (255, 255, 255), 1)
        return np.vstack([g, lg])

    sheet = np.vstack([
        band(tiles, "SHAPE (ink centred)  red=real  green=synth  yellow=agree"),
        band(tiles_placed,
             "PLACEMENT (as cropped)  offset here may be slot-splitting, not glyph"),
    ])
    cv2.imwrite(str(out_png), sheet)
    print(f"-> {out_png}  (위=모양(중심 맞춤) · 아래=자리(자른 그대로))")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--per-digit", type=int, default=6)
    ap.add_argument("--synth-count", type=int, default=400)
    ap.add_argument("--seed", type=int, default=20260917)
    ap.add_argument("--out", default=str(HERE / "_diag" / "glyph_compare"))
    args = ap.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    real = collect_real(args.per_digit)
    synth = collect_synth(args.synth_count, args.seed, args.per_digit)
    print(f"실사진 슬롯 (band_boxes.jsonl 사람 라벨 · 3자리 값만): "
          + " ".join(f"{d}:{len(real[d])}" for d in sorted(real)))
    print(f"합성 슬롯 (seed {args.seed}, 렌더 {args.synth_count}장): "
          + " ".join(f"{d}:{len(synth[d])}" for d in sorted(synth)))

    strips = []
    for d in map(str, range(10)):
        r = row(real[d], args.per_digit)
        s = row(synth[d], args.per_digit)
        w = max(r.shape[1], s.shape[1], 1)
        r = np.pad(r, ((0, 0), (0, w - r.shape[1])), constant_values=30)
        s = np.pad(s, ((0, 0), (0, w - s.shape[1])), constant_values=30)
        head = np.full((CELL_H * 2 + 6, 90), 30, np.uint8)
        cv2.putText(head, d, (20, CELL_H), cv2.FONT_HERSHEY_SIMPLEX, 3.0,
                    255, 6)
        cv2.putText(head, "real", (4, 26), cv2.FONT_HERSHEY_SIMPLEX, 0.6, 200, 1)
        cv2.putText(head, "synth", (4, CELL_H + 26), cv2.FONT_HERSHEY_SIMPLEX,
                    0.6, 200, 1)
        body = np.vstack([r, np.full((6, w), 80, np.uint8), s])
        strips.append(np.hstack([head, body]))
        strips.append(np.full((14, head.shape[1] + w), 60, np.uint8))

    overlay_sheet(real, synth, out / "glyph_overlay.png")

    w = max(s.shape[1] for s in strips)
    strips = [np.pad(s, ((0, 0), (0, w - s.shape[1])), constant_values=30)
              for s in strips]
    sheet = np.vstack(strips)
    p = out / "glyph_compare.png"
    cv2.imwrite(str(p), sheet)
    print(f"-> {p}  (각 자릿수: 위=실사진, 아래=합성. 같은 높이로 맞췄다)")
    print("이 시트는 재는 도구가 아니다 — 보고 사람이 값을 부른다.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
