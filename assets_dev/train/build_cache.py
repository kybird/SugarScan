# 전체 데이터셋을 .npz 캐시로 구축 — 디코딩 일회성, 이후 학습은 즉시 로딩.
# 산출: assets_dev/train/data_cache.npz
#   synth_images: (N, 160, 320) uint8
#   synth_labels: (N,) 문자열 리스트
#   real_images: (M, 160, 320) uint8
#   real_labels: (M,) 문자열 리스트
import json
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
DATUMO = HERE.parent / "upstream" / "datumo"
SYNTH_DIR = HERE / "synth_screens" / "images"
IN_H, IN_W = 160, 320


def load_synth():
    labels = json.loads(
        (HERE / "synth_screens" / "labels_1.json").read_text(encoding="utf-8"))
    for seed in (2, 3):
        f = HERE / "synth_screens" / f"labels_{seed}.json"
        if f.exists():
            labels.update(json.loads(f.read_text(encoding="utf-8")))
    keys = sorted(labels.keys())
    X = np.zeros((len(keys), IN_H, IN_W), dtype=np.uint8)
    strs = []
    kept = 0
    for i, k in enumerate(keys):
        p = SYNTH_DIR / f"{k}.png"
        img = cv2.imread(str(p), cv2.IMREAD_GRAYSCALE)
        if img is None:
            strs.append("")
            continue
        X[kept] = cv2.resize(img, (IN_W, IN_H),
                             interpolation=cv2.INTER_AREA)
        strs.append(labels[k])
        kept += 1
    return X[:kept], strs[:kept]


def load_real():
    quads = {}
    for l in (HERE / "gmscreen_quads.jsonl").read_text(encoding="utf-8").splitlines():
        if l.strip():
            j = json.loads(l)
            quads[j["id"]] = j["quad"]
    readings = {}
    for l in (DATUMO / "labels.jsonl").read_text(encoding="utf-8").splitlines():
        if l.strip():
            j = json.loads(l)
            readings[j["id"]] = j["reading"]
    corrections = {}
    corr = HERE / "gt_corrections.jsonl"
    if corr.exists():
        for l in corr.read_text(encoding="utf-8").splitlines():
            if l.strip():
                j = json.loads(l)
                corrections[j["id"]] = j["corrected"]

    labeled = read_jsonl_local(HERE / "labeled.jsonl")
    X_list, strs, ids = [], [], []
    for cid in sorted(labeled):
        j = labeled[cid]
        if j.get("source") != "human" or j.get("quad") is None:
            continue
        if cid not in quads:
            continue
        p = DATUMO / "extracted" / "TILDE" / f"{cid}.jpg"
        if not p.exists():
            continue
        try:
            with Image.open(p) as pil:
                pil.load()
                g = cv2.cvtColor(
                    np.asarray(pil.convert("RGB")), cv2.COLOR_RGB2GRAY)
        except Exception:
            continue
        src = np.array(
            [[q[0][0], q[0][1]] for q in [j["quad"][0]]] +
            [[j["quad"][1][0], j["quad"][1][1]],
             [j["quad"][2][0], j["quad"][2][1]],
             [j["quad"][3][0], j["quad"][3][1]]], dtype=np.float32)
        dst = np.array(
            [[0, 0], [IN_W - 1, 0], [IN_W - 1, IN_H - 1], [0, IN_H - 1]],
            dtype=np.float32)
        rect = cv2.warpPerspective(
            g, cv2.getPerspectiveTransform(src, dst), (IN_W, IN_H))
        X_list.append(rect)
        val = corrections.get(cid, str(readings.get(cid, "")))
        strs.append(val)
        ids.append(cid)
    return np.asarray(X_list, dtype=np.uint8), strs, ids


def read_jsonl_local(p):
    if not p.exists():
        return {}
    out = {}
    for l in p.read_text(encoding="utf-8").splitlines():
        if l.strip():
            j = json.loads(l)
            out[j["id"]] = j
    return out


def main() -> int:
    synth_x, synth_s = load_synth()
    real_x, real_s, real_ids = load_real()
    np.savez_compressed(
        str(HERE / "data_cache.npz"),
        synth_images=synth_x, synth_labels=np.array(synth_s),
        real_images=real_x, real_labels=np.array(real_s),
        real_ids=np.array(real_ids),
    )
    print(f"캐시: 합성 {len(synth_x)} + 실사진 {len(real_x)} = {len(synth_x)+len(real_x)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
