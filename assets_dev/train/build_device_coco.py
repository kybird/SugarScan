"""Build a NEW whole-device corpus; never overwrite existing data.

python build_device_coco.py --name Train --count 16000 --seed 20261001 \
  --reference-ann synth_coco/TB/annotations/instances_curve_07998.json
python build_device_coco.py --name Val --count 1000 --seed 20261002
"""
import argparse
import json
from pathlib import Path

import cv2

from build_synth_coco import build_set, box_sheet


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="synth_device_fit")
    ap.add_argument("--name", required=True)
    ap.add_argument("--count", type=int, required=True)
    ap.add_argument("--seed", type=int, required=True)
    ap.add_argument("--scene", choices=("panel", "device", "mixed"), default="mixed")
    ap.add_argument("--reference-ann")
    a = ap.parse_args()
    if Path(a.name).name != a.name or a.name in (".", ".."):
        ap.error("name must be one directory component")
    root = Path(a.out).resolve()
    if (root/a.name).exists():
        ap.error("output already exists; choose a new name (never overwrite)")
    cv2.setNumThreads(1)
    root.mkdir(parents=True, exist_ok=True)
    coco = build_set(a.name, a.count, a.seed, root, .5, "procedural", a.scene)
    if a.reference_ann:
        reference = json.loads(Path(a.reference_ann).read_text(encoding="utf-8"))
        names = {r["file_name"] for r in reference["images"]}
        coco["images"] = [r for r in coco["images"] if r["file_name"] in names]
        if {r["file_name"] for r in coco["images"]} != names:
            raise ValueError("reference image names not reproduced")
        ids = {r["id"] for r in coco["images"]}
        coco["annotations"] = [r for r in coco["annotations"] if r["image_id"] in ids]
        (root/a.name/"annotations"/"instances_matched.json").write_text(
            json.dumps(coco), encoding="utf-8")
    (root/a.name/"build_config.json").write_text(json.dumps(vars(a), indent=2), encoding="utf-8")
    # Full annotation order matches manifest order; subset sheets would not.
    full = json.loads((root/a.name/"annotations"/"instances_train2017.json").read_text())
    box_sheet(root/a.name, full, root/f"{a.name}_preview.png", n=15)


if __name__ == "__main__":
    main()
