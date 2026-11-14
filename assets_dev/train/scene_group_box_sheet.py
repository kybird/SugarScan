# 장면그룹 세트 검토 시트 — 현 배포 번들 검출기의 상자를 얹어 본다(2026-11-15).
#
# 왜: 설계 §1 완료 기준 "소량을 생성해 현재 번들의 검출 상자를 그린 검토
# 시트를 만든다". 배포 번들(band_detector.onnx)이 음성 장면에서 어디서
# 상자를 만드는지, 양성 밴드를 제대로 담는지를 눈으로 본다.
#
# 사용: python scene_group_box_sheet.py --set <세트루트> --out <png> [--n 12]
#   <세트루트> = build_synth_coco --scene-group 산출 디렉터리(예: .../SGD_VAL)
import argparse
import json
from pathlib import Path

import cv2
import numpy as np
import onnxruntime as ort

from export_deploy_onnx import decode_np, letterbox


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--set", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--n", type=int, default=12)
    args = ap.parse_args()
    root = Path(args.set)
    models = Path(__file__).resolve().parents[2] / "assets" / "models"
    det = ort.InferenceSession(str(models / "band_detector.onnx"),
                               providers=["CPUExecutionProvider"])
    rows = [json.loads(l) for l in
            (root / "manifest.jsonl").read_text(encoding="utf-8").splitlines()
            if l.strip()]
    kinds = ("pos", "neg", "off")
    picks = []
    for kind in kinds:
        picks += [r for r in rows if r["id"].endswith(f"_{kind}")][:args.n]
    tiles = []
    for r in picks:
        p = root / "train2017" / f"{r['id']}.png"
        img = cv2.imread(str(p), cv2.IMREAD_GRAYSCALE)
        if img is None:
            continue
        lb, s_, dx, dy = letterbox(img, 640)
        obj, reg = det.run(None, {"image": lb[None, None].astype(np.float32) / 255})
        box, score = decode_np(obj[0, 0], reg[0], 16)
        b = [(v - off) / s_ for v, off in zip(box, (dx, dy, dx, dy))]
        color = 255 if r["has_band"] else 90
        if score >= 0.25 and (b[2]-b[0])*(b[3]-b[1]) > 0.02*img.shape[0]*img.shape[1]:
            cv2.rectangle(img, (int(b[0]), int(b[1])), (int(b[2]), int(b[3])),
                          color, 3)
        cv2.putText(img, f"{r['id'].rsplit('_',1)[1]} {r.get('distractor_family') or 'plain'}"
                    f" s={score:.2f}", (6, 24), cv2.FONT_HERSHEY_SIMPLEX,
                    0.55, 255, 1, cv2.LINE_AA)
        if r["has_band"] and r.get("box"):
            g = [int(v) for v in r["box"]]
            cv2.rectangle(img, (g[0], g[1]), (g[2], g[3]), 60, 1)
        sc = 260 / max(img.shape)
        img = cv2.resize(img, (int(img.shape[1]*sc), int(img.shape[0]*sc)))
        tiles.append(img)
    th = max(t.shape[0] for t in tiles)
    tw = max(t.shape[1] for t in tiles)
    tiles = [cv2.copyMakeBorder(t, 0, th-t.shape[0], 0, tw-t.shape[1],
                                cv2.BORDER_CONSTANT, value=0) for t in tiles]
    grid = [np.hstack(tiles[i:i+3]) for i in range(0, len(tiles), 3)]
    w = max(g.shape[1] for g in grid)
    grid = [np.pad(g, ((0, 0), (0, w-g.shape[1]))) for g in grid]
    cv2.imwrite(args.out, np.vstack(grid))
    passed = sum(1 for r in picks)  # 상자 그려진 수는 위 루프에서 셈하지 않음
    print(f"검토 시트 {len(tiles)}장 -> {args.out}")


if __name__ == "__main__":
    main()
