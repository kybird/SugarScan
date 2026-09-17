# 합성 밴드 검출이 실패한 장을 해부한다 — "왜 이 장만 안 되는가".
#
# 배경(2026-09-17): 세트 B 1000장 중 한 장(panel_20260917_22)만 conf 0.25 를
# 못 넘었다. 처음엔 "딱딱한 그림자가 숫자를 가른다"고 보고했다. **틀렸다.**
#
# 이 스크립트는 그 종류의 오진을 막으려고 세 가지를 순서대로 한다:
#
#   1. 위치인가 신뢰도인가 — 임계를 내려 후보를 뽑고 정답과의 IoU 를 본다.
#      IoU 가 높으면 검출기는 찾은 것이고 확신만 없는 것이다. 둘은 처방이 다르다.
#   2. 무엇이 다른가 — 후보 축(gpc·밀도·전역 대비)마다 **모집단 순위**를 낸다.
#      "이 장은 대비가 낮다" 는 모집단에서 낮아야 뜻이 있다.
#   3. 정말 그 축인가 — 이미지를 절개해 점수가 움직이는지 보고, **같은 절개를
#      성공한 장에도** 걸어 본다. 대조군이 없으면 "절개하니 올랐다"가
#      "그것이 원인이다"로 잘못 읽힌다. 한계 장은 무엇을 해도 크게 움직인다.
#
# 사용:
#   python diag_synthband_miss.py --set synth_coco/B --pred _diag/synthband_v0/B.jsonl
import argparse
import json
import sys
from pathlib import Path

import cv2
import numpy as np
import torch

sys.path.insert(0, "D:/tmp/YOLOX")
from yolox.data.data_augment import ValTransform  # noqa: E402
from yolox.exp import get_exp  # noqa: E402
from yolox.utils import postprocess  # noqa: E402

HERE = Path(__file__).resolve().parent
EXP = str(HERE / "yolox_synthband_exp.py")
CKPT = HERE / "yolox_out" / "synthband_v0" / "best_ckpt.pth"
PROBE = 0.001


def iou(a, b):
    x0, y0 = max(a[0], b[0]), max(a[1], b[1])
    x1, y1 = min(a[2], b[2]), min(a[3], b[3])
    i = max(0.0, x1 - x0) * max(0.0, y1 - y0)
    u = (a[2]-a[0])*(a[3]-a[1]) + (b[2]-b[0])*(b[3]-b[1]) - i
    return i / u if u > 0 else 0.0


def stretch(im):
    g = cv2.cvtColor(im, cv2.COLOR_BGR2GRAY).astype(np.float32)
    p2, p98 = np.percentile(g, 2), np.percentile(g, 98)
    s = np.clip((g - p2) / max(1.0, p98 - p2) * 255, 0, 255).astype(np.uint8)
    return cv2.cvtColor(s, cv2.COLOR_GRAY2BGR)


def flatten(im):
    """큰 가우시안으로 조명을 추정해 나눈다 — 그림자를 지우는 절개."""
    g = cv2.cvtColor(im, cv2.COLOR_BGR2GRAY).astype(np.float32)
    ill = cv2.GaussianBlur(g, (0, 0), 60)
    f = np.clip(g / np.maximum(ill, 1) * ill.mean(), 0, 255).astype(np.uint8)
    return cv2.cvtColor(f, cv2.COLOR_GRAY2BGR)


ABLATIONS = (("stretch", stretch), ("flatten", flatten),
             ("flip", lambda im: cv2.flip(im, 1)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--set", required=True)
    ap.add_argument("--pred", required=True)
    ap.add_argument("--split", default="train2017")
    ap.add_argument("--ckpt", default=str(CKPT))
    ap.add_argument("--controls", type=int, default=4)
    args = ap.parse_args()

    root = Path(args.set)
    rows = [json.loads(l) for l in
            Path(args.pred).read_text(encoding="utf-8").splitlines() if l.strip()]
    mf = {}
    for l in (root / "manifest.jsonl").read_text(encoding="utf-8").splitlines():
        if l.strip():
            j = json.loads(l)
            mf[j["id"]] = j
    miss = [r for r in rows if not r["pred"]]
    hit = [r for r in rows if r["pred"]]
    print(f"모집단 {args.pred} n={len(rows)} · 검출 {len(hit)} · 실패 {len(miss)}")
    if not miss:
        print("실패한 장이 없다 — 해부할 것이 없다")
        return 0

    exp = get_exp(args.ckpt and EXP, None)
    model = exp.get_model().cuda().eval()
    model.load_state_dict(torch.load(args.ckpt, map_location="cpu")["model"])
    pre = ValTransform(legacy=False)

    def candidates(img):
        r = min(exp.test_size[0] / img.shape[0], exp.test_size[1] / img.shape[1])
        t, _ = pre(img, None, exp.test_size)
        with torch.no_grad():
            o = postprocess(model(torch.from_numpy(t).unsqueeze(0).float().cuda()),
                            1, PROBE, 0.45, class_agnostic=True)[0]
        if o is None or not len(o):
            return []
        a = o.cpu().numpy()
        sc = a[:, 4] * a[:, 5]
        return [(float(sc[k]), [float(a[k][q]) / r for q in range(4)])
                for k in np.argsort(sc)[::-1]]

    # ── 2 준비: 모집단 축 ───────────────────────────────────────────────
    def contrast(name):
        g = cv2.imread(str(root / args.split / f"{name}.png"),
                       cv2.IMREAD_GRAYSCALE).astype(np.float32)
        return float(np.percentile(g, 98) - np.percentile(g, 2))

    names = [r["file_name"][:-4] for r in rows]
    axes = {
        "gpc": np.array([mf[n]["glyph_plane_check"] for n in names]),
        "density": np.array([mf[n]["density"] for n in names]),
        "contrast": np.array([contrast(n) for n in names]),
    }
    score = np.array([r["score"] if r["pred"] else 0.0 for r in rows])

    for r in miss:
        name = r["file_name"][:-4]
        i = names.index(name)
        img = cv2.imread(str(root / args.split / r["file_name"]))
        print(f"\n── {name} · 프로파일 {mf[name]['profile']} · "
              f"라벨 {mf[name]['label']} " + "─" * 20)

        # 1. 위치인가 신뢰도인가
        cands = candidates(img)
        print("  [1] 위치인가 신뢰도인가 — 임계 %.3f 후보 상위 3" % PROBE)
        for s, b in cands[:3]:
            print(f"      점수 {s:.4f}  {b[2]-b[0]:4.0f}x{b[3]-b[1]:<4.0f}  "
                  f"정답과 IoU {iou(b, r['gt']):.3f}")
        if cands and iou(cands[0][1], r["gt"]) >= 0.5:
            print("      -> 상자는 맞다. **신뢰도 문제**이지 위치 문제가 아니다.")
        else:
            print("      -> 상자가 어긋났다. 위치 문제다.")

        # 2. 모집단에서 무엇이 다른가
        print("  [2] 모집단 순위 (낮을수록 꼬리)")
        for k, v in axes.items():
            pct = 100.0 * (v < v[i]).mean()
            print(f"      {k:<9} {v[i]:8.4f}  하위 {pct:5.1f}%  "
                  f"| 점수와의 상관 {np.corrcoef(v, score)[0, 1]:+.3f}")
        print("      -> 상관이 0 근처면 그 축은 실패를 설명하지 못한다.")

        # 3. 절개 + 대조군
        base = cands[0][0] if cands else 0.0
        ctrl = sorted(hit, key=lambda x: -x["score"])[:args.controls]
        print(f"  [3] 절개와 대조군 (확신 있는 장 {len(ctrl)}개를 같이 절개한다)")
        print(f"      {'장':<14}{'원본':>8}" +
              "".join(f"{n:>10}" for n, _ in ABLATIONS))
        def line(tag, im0):
            b = candidates(im0)
            b0 = b[0][0] if b else 0.0
            cells = []
            for _, fn in ABLATIONS:
                c = candidates(fn(im0))
                cells.append((c[0][0] if c else 0.0) - b0)
            print(f"      {tag:<14}{b0:>8.4f}" +
                  "".join(f"{d:>+10.4f}" for d in cells))
        line("실패장", img)
        for c in ctrl:
            line("대조 " + c["file_name"].split("_")[-1][:-4],
                 cv2.imread(str(root / args.split / c["file_name"])))
        print("      -> 대조군이 조금 움직이는데 실패장만 크게 움직이면 "
              "**한계 장**이다(원인이 아니라 위치 문제).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
