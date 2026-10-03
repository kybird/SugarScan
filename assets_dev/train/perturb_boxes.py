# 정확한 검출 상자에 '그럴듯한 검출기 오차'를 인위적으로 주입한다.
#
# 배경(2026-10-03 리더 시리즈): 리더 끝단의 결정 축은 학습 크롭의 다양성
# 이었다 — v2.1(88.9%)은 옛 상자 파일의 우연한 어긋남+지터가, 정확한
# 상자로 만든 v3~v6(81~88%)은 그 다양성이 없어 못 미쳤다. 이 자는 그
# 우연을 설계로 옮긴다(v7).
#
# 편차(장마다 독립 뽑기, 30% 장은 원 상자 그대로):
#   중심 시프트  x ±12%w · y ±10%h   — 숫자를 자르지 않는 이동 위주
#   스케일       w·h 각 0.88~1.12     — 여백 변화
# 균일 랜덤 지터(v3_1 실패)와 다른 점: 시프트와 스케일을 **별도 축으로**
# 뽑고 스케일 하한을 0.88 로 막아 '숫자 잘린 크롭'을 만들지 않는다.
#
# 사용:
#   python perturb_boxes.py --in a.jsonl --out b.jsonl [--seed 20261003]
import argparse
import json
import random
from pathlib import Path

HERE = Path(__file__).resolve().parent


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--seed", type=int, default=20261003)
    ap.add_argument("--p-keep", type=float, default=0.30,
                    help="편차 없이 원 상자로 둘 비율")
    ap.add_argument("--shift-x", type=float, default=0.12)
    ap.add_argument("--shift-y", type=float, default=0.10)
    ap.add_argument("--scale-lo", type=float, default=0.88)
    ap.add_argument("--scale-hi", type=float, default=1.12)
    a = ap.parse_args()
    rng = random.Random(a.seed)
    n = n_kept = 0
    with Path(a.out).open("w", encoding="utf-8") as f:
        for line in Path(a.inp).read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            r = json.loads(line)
            x0, y0, x1, y1 = r["pred"]
            w, h = x1 - x0, y1 - y0
            if rng.random() < a.p_keep:
                n_kept += 1
            else:
                dx = rng.uniform(-a.shift_x, a.shift_x) * w
                dy = rng.uniform(-a.shift_y, a.shift_y) * h
                sw = rng.uniform(a.scale_lo, a.scale_hi)
                sh = rng.uniform(a.scale_lo, a.scale_hi)
                cx, cy = (x0 + x1) / 2 + dx, (y0 + y1) / 2 + dy
                x0, x1 = cx - w * sw / 2, cx + w * sw / 2
                y0, y1 = cy - h * sh / 2, cy + h * sh / 2
                r["pred"] = [round(v, 2) for v in (x0, y0, x1, y1)]
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
            n += 1
    print(f"{a.out}: {n}개 · 원 상자 유지 {n_kept} · 편차 {n - n_kept}")


if __name__ == "__main__":
    main()
