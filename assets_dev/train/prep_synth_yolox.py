# 세트 A 를 YOLOX 학습용 train/val 분할로 펼친다.
#
# build_synth_coco.py 가 굽는 세트는 분할이 없다(세트 자체가 분할이다 —
# A 검출기 학습 · B 리더 학습 · C 끝단 평가). YOLOX 는 학습 중 mAP 를 재려고
# val 분할을 요구하므로, A 안에서만 잘라 쓴다. B·C 는 건드리지 않는다 —
# 거기서 잘라 오면 검출기가 리더·평가 세트를 보게 된다.
#
# 산출: <out>/{annotations/{instances_train2017.json,instances_val2017.json},
#              train2017/, val2017/}
import argparse
import json
import random
import shutil
from pathlib import Path

HERE = Path(__file__).resolve().parent

SPLIT_SEED = 20260919   # A 를 굽는 시드(20260916)와 다르다 — 분할은 별개 축이다
VAL_N = 100


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", default=str(HERE / "synth_coco" / "A"))
    ap.add_argument("--out", default=str(HERE / "synth_coco" / "A_yolox"))
    ap.add_argument("--val-n", type=int, default=VAL_N)
    args = ap.parse_args()

    src, out = Path(args.src), Path(args.out)
    coco = json.loads((src / "annotations" / "instances_train2017.json")
                      .read_text(encoding="utf-8"))
    by_img = {a["image_id"]: a for a in coco["annotations"]}
    assert len(by_img) == len(coco["annotations"]), "image_id 가 유일하지 않다"

    idx = list(range(len(coco["images"])))
    random.Random(SPLIT_SEED).shuffle(idx)
    val_idx = set(idx[:args.val_n])

    if out.exists():
        shutil.rmtree(out)
    (out / "annotations").mkdir(parents=True)
    (out / "train2017").mkdir()
    (out / "val2017").mkdir()

    splits = {}
    for split, keep in (("train", False), ("val", True)):
        imgs, anns = [], []
        for i, im in enumerate(coco["images"]):
            if (i in val_idx) != keep:
                continue
            imgs.append(im)
            anns.append(by_img[im["id"]])
            shutil.copy2(src / "train2017" / im["file_name"],
                         out / f"{split}2017" / im["file_name"])
        obj = {"info": dict(coco["info"], split=split, split_seed=SPLIT_SEED),
               "licenses": [], "categories": coco["categories"],
               "images": imgs, "annotations": anns}
        p = out / "annotations" / f"instances_{split}2017.json"
        p.write_text(json.dumps(obj), encoding="utf-8")
        splits[split] = len(imgs)
        assert len(imgs) == len(anns)
        print(f"{split}: {len(imgs)}장 / {len(anns)}상자 -> {p}")

    assert splits["train"] + splits["val"] == len(coco["images"])
    print(f"분할 시드 {SPLIT_SEED} · 합계 {sum(splits.values())} "
          f"= 원본 {len(coco['images'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
