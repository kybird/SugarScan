# GM 검출기 파인튜닝 데이터셋 구축 — 기존 Roboflow 957장 + 신규 LCD 라벨 211장.
# 산출: assets_dev/train/gmscreen_ft/{annotations,train2017,val2017}
# 관례: 좌표 정본 = 표시(EXIF 적용) 픽셀. 학습 로더(cv2)가 EXIF 를 구우므로
# 원본 JPEG 을 그대로 복사하고 박스는 표시 좌표계(COCO bbox)로 쓴다.
import json
import random
import shutil
from pathlib import Path

from PIL import Image, ImageOps

HERE = Path(__file__).resolve().parent
SRC = HERE / "gmscreen"          # 기존 Roboflow COCO 데이터셋
TILDE = HERE.parent / "upstream" / "datumo" / "extracted" / "TILDE"
DST = HERE / "gmscreen_ft"

VAL_HOLDOUT = 21                 # 신규 라벨 중 검증용
SEED = 123


def coco_header():
    return {
        "info": {"description": "gmscreen finetune (Roboflow + Datumo LCD labels)",
                 "version": "1"},
        "licenses": [],
        "categories": [{"id": 1, "name": "lcd_screen", "supercategory": "none"}],
        "images": [],
        "annotations": [],
    }


def main() -> int:
    if DST.exists():
        shutil.rmtree(DST)
    (DST / "annotations").mkdir(parents=True)
    (DST / "train2017").mkdir()
    (DST / "val2017").mkdir()

    # ===== 기존 데이터 그대로 이식 =====
    for split in ("train2017", "val2017"):
        for p in (SRC / split).iterdir():
            if p.is_file():
                shutil.copy2(p, DST / split / p.name)

    train = json.loads((SRC / "annotations" / "instances_train2017.json").read_text())
    val = json.loads((SRC / "annotations" / "instances_val2017.json").read_text())
    next_img_id = max(im["id"] for im in train["images"] + val["images"]) + 1
    next_ann_id = max(a["id"] for a in train["annotations"] + val["annotations"]) + 1
    print(f"기존: train {len(train['images'])} / val {len(val['images'])}"
          f" (next ids {next_img_id}/{next_ann_id})")

    # ===== 신규 LCD 라벨 =====
    rows = []
    for l in (HERE / "screen_boxes.jsonl").read_text(encoding="utf-8").splitlines():
        if l.strip():
            j = json.loads(l)
            if j.get("source") == "human" and j.get("quad"):
                rows.append(j)
    rng = random.Random(SEED)
    rng.shuffle(rows)
    val_rows = rows[:VAL_HOLDOUT]
    tr_rows = rows[VAL_HOLDOUT:]
    print(f"신규: train {len(tr_rows)} / val {len(val_rows)} (총 {len(rows)})")

    def add_new(rows_, split, anns):
        nonlocal next_img_id, next_ann_id
        for r in rows_:
            cid = r["id"]
            src_img = TILDE / f"{cid}.jpg"
            fname = f"datumo__{cid.replace('/', '__')}.jpg"
            shutil.copy2(src_img, DST / split / fname)
            with Image.open(src_img) as im:
                w, h = ImageOps.exif_transpose(im).size   # 표시 좌표계 치수
            xs = [p[0] for p in r["quad"]]
            ys = [p[1] for p in r["quad"]]
            x0, y0 = min(xs), min(ys)
            bw, bh = max(xs) - x0, max(ys) - y0
            anns["images"].append({"id": next_img_id, "file_name": fname,
                                   "width": w, "height": h})
            anns["annotations"].append({
                "id": next_ann_id, "image_id": next_img_id,
                "category_id": 1, "bbox": [x0, y0, bw, bh],
                "area": bw * bh, "iscrowd": 0, "segmentation": [],
            })
            next_img_id += 1
            next_ann_id += 1

    add_new(tr_rows, "train2017", train)
    add_new(val_rows, "val2017", val)

    for name, obj in (("train", train), ("val", val)):
        out = DST / "annotations" / f"instances_{name}2017.json"
        out.write_text(json.dumps(obj))
        print(f"{name}: {len(obj['images'])}장 / {len(obj['annotations'])}박스 → {out.name}")

    # ===== 무결성 =====
    for name, obj, split in (("train", train, "train2017"), ("val", val, "val2017")):
        for im in obj["images"]:
            assert (DST / split / im["file_name"]).exists(), im["file_name"]
        for a in obj["annotations"]:
            x, y, w, h = a["bbox"]
            assert w > 8 and h > 8, (a["id"], w, h)
    print("무결성 통과")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
