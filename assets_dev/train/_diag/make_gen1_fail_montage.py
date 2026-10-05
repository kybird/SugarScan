# GEN1 검출기(gen1_v1) 전량 e2e 실패 장 검수판(2026-10-04, 사람: "내 눈으로
# 보게 GEN1 의 실패 검출 이미지들 보여줘").
#
# 16장 중 90도 회전 5장(1213·1226·1565·940·283)은 사람 지시로 제외 — 학습
# 축(roll ±15도) 밖 도메인이라 실패가 예정된 장들이다. 남은 11장을 그린다.
#
# 카드: 사진 + 주황(gen1 게이트 전 최상위 후보) + 초록(사람 라벨, 있는 장만).
# 캡션: id · 지속(TG도 실패)/신규(TG는 잡음) · sc점수 · 면적% · 기종.
# 상자 출처: _diag/fail19_raw_probe_gen1.json(구 TG실패분) +
# fail19_raw_probe_gen1new.json(신규실패분) — 같은 gen1_v1 체크포인트.
#
# 사용: python _diag/make_gen1_fail_montage.py
import json
import sys
from pathlib import Path

import cv2
import numpy as np

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))
from eval_reader import load_gray  # noqa: E402

UPSTREAM = HERE.parent / "upstream" / "datumo"

OLD = ["1762", "1781", "2317", "2414"]              # TG도 실패(회전 제외)
NEW = ["1639", "1709", "1780", "1840", "2074", "2431", "818"]  # TG는 잡음
CW, CH, PAD, COLS = 360, 330, 8, 4


def boxes():
    out = {}
    for f in ("fail19_raw_probe_gen1.json", "fail19_raw_probe_gen1new.json"):
        for r in json.loads((HERE / "_diag" / f).read_text(encoding="utf-8")):
            if "box" in r:
                out[r["id"]] = (r["box"], r["score"])
    return out


def main():
    probe = boxes()
    hum = {}
    for ln in (HERE / "band_boxes.jsonl").read_text(encoding="utf-8").splitlines():
        if ln.strip():
            r = json.loads(ln)
            q = r["quad"]
            xs = [p[0] for p in q]
            ys = [p[1] for p in q]
            hum[r["id"]] = (min(xs), min(ys), max(xs), max(ys))
    dev = {}
    for ln in (HERE / "device_labels.jsonl").read_text(encoding="utf-8").splitlines():
        if ln.strip():
            r = json.loads(ln)
            dev[r["id"]] = (r.get("brand") or "?") + (
                " " + r["model"] if r.get("model") else "")

    cards = [("지속", s) for s in OLD] + [("신규", s) for s in NEW]
    ROWS = (len(cards) + COLS - 1) // COLS
    canvas = np.full((PAD + 24 + ROWS * (CH + PAD), PAD + COLS * (CW + PAD)),
                     16, np.uint8)
    canvas = cv2.cvtColor(canvas, cv2.COLOR_GRAY2BGR)
    cv2.putText(canvas, "GEN1 detector fails (rot-excluded 11) - orange=gen1 raw "
                "top-1, green=human", (10, 16),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (220, 220, 220), 1)
    for k, (tag, s) in enumerate(cards):
        pid = "glucose_batch1/" + s
        img = load_gray(UPSTREAM / "extracted" / "TILDE" /
                        (pid.replace("/", "\\") + ".jpg"))
        if img is None:
            continue
        H, W = img.shape
        sc = 300 / max(W, H)
        th = cv2.resize(img, (max(2, int(W * sc)), max(2, int(H * sc))),
                        interpolation=cv2.INTER_AREA)
        rgb = cv2.cvtColor(th, cv2.COLOR_GRAY2BGR)
        g = hum.get(pid)
        if g:
            cv2.rectangle(rgb, (int(g[0] * sc), int(g[1] * sc)),
                          (int(g[2] * sc), int(g[3] * sc)), (0, 220, 0), 2)
        b, pr = probe[pid]
        cv2.rectangle(rgb, (int(b[0] * sc), int(b[1] * sc)),
                      (int(b[2] * sc), int(b[3] * sc)), (0, 140, 255), 2)
        frac = (b[2] - b[0]) * (b[3] - b[1]) / max(1.0, W * H) * 100
        cap = (f"{s} {tag} sc{pr:.2f} {frac:.1f}% "
               f"{dev.get(pid, '?')[:20]}")
        rgb = cv2.copyMakeBorder(rgb, 0, 26, 0, 0, cv2.BORDER_CONSTANT,
                                 value=(16, 16, 16))
        cv2.putText(rgb, cap[:48], (4, CH - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.45,
                    (210, 210, 210), 1)
        y0 = PAD + 24 + (k // COLS) * (CH + PAD)
        x0 = PAD + (k % COLS) * (CW + PAD)
        h2, w2 = rgb.shape[:2]
        canvas[y0:y0 + h2, x0:x0 + w2] = rgb
    out = HERE / "_diag" / "gen1_fail11_montage.png"
    cv2.imwrite(str(out), canvas)
    print(out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
