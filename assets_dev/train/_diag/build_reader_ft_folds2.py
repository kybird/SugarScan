# 리더 실촉 K=5 학습 세트 조립 v2 — 리플레이를 세그축 코퍼스(SEGAX)로
# (2026-10-09). 실촉 크롭·폴드는 1차와 동일(crops_manifest 재사용 — holdout
# 동일성이 A/B 짝비교의 전제). 합성 리플레이만 교체: SEGAX 패널을 ftk5_g0.06
# 이 예측한 상자로 자른 크롭 1,200장. 세그축 합성기는 어노테이션 json 을
# 안 쓰므로(images 목록만 필요) boxes jsonl 에서 직접 images 를 만든다.
import json
import random
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
TRAIN = HERE.parent
OUT = HERE / "reader_ft2"
SYNTH_BOXES = HERE / "reader_boxes" / "SEGAX_g006.jsonl"
SYNTH_MANIFEST = TRAIN / "synth_coco" / "SEGAX" / "manifest.jsonl"
# SEGAX generate() 는 images/ 하위에 판을 쓴다(train2017 아님 — 실측)
SYNTH_N = 1200


def build(fold, keep_folds, tag):
    fdir = OUT / tag
    (fdir / "annotations").mkdir(parents=True, exist_ok=True)
    crops = [json.loads(l) for l in
             (HERE / "reader_ft" / "crops_manifest.jsonl").read_text(
                 encoding="utf-8").splitlines() if l.strip()]
    train_rows = [c for c in crops if c["fold"] in keep_folds]
    hold = [c for c in crops if c["fold"] == fold]
    (fdir / "holdout_ids.json").write_text(
        json.dumps([c["id"] for c in hold]), encoding="utf-8")

    rng = random.Random(20261020 + (fold if fold is not None else 99))
    synth = []
    for l in SYNTH_BOXES.read_text(encoding="utf-8").splitlines():
        if l.strip():
            r = json.loads(l)
            if r.get("pred"):
                synth.append(r)
    synth_pick = rng.sample(synth, min(SYNTH_N, len(synth)))

    images, boxes = [], []
    aid = 1
    for c in train_rows:
        fn = "../../../reader_ft/crops/" + c["id"] + ".png"      # reader_ft(1차) 크롭 공유
        images.append(dict(id=aid, file_name=fn))
        boxes.append(dict(file_name=fn, pred=[0, 0, c["w"], c["h"]]))
        aid += 1
    for s in synth_pick:
        # SEGAX generate() 는 images/ 하위에 판을 쓴다(train2017 아님 — 실측)
        fn = "../../../../synth_coco/SEGAX/images/" + s["file_name"]
        images.append(dict(id=aid, file_name=fn))
        boxes.append(dict(file_name=fn, pred=s["pred"]))
        aid += 1
    (fdir / "annotations" / "instances_train2017.json").write_text(
        json.dumps(dict(images=images, annotations=[])), encoding="utf-8")
    (fdir / "boxes_g006.jsonl").write_text(
        "\n".join(json.dumps(b) for b in boxes) + "\n", encoding="utf-8")
    with (fdir / "manifest.jsonl").open("w", encoding="utf-8") as mf:
        for im in images:
            mid = im["file_name"][:-4]
            if im["file_name"].startswith("../../../reader_ft/crops/"):
                label = next(c["label"] for c in train_rows
                             if "../../../reader_ft/crops/" + c["id"] == mid)
            else:
                key = im["file_name"].rsplit("/", 1)[-1][:-4]
                label = SYNTH_LABELS.get(key)
                if not label:
                    continue
            mf.write(json.dumps(dict(id=mid, label=label)) + "\n")
    print(f"{tag}: 실촉 {len(train_rows)} + SEGAX {SYNTH_N} · holdout {len(hold)}")


if __name__ == "__main__":
    SYNTH_LABELS = {}
    for l in SYNTH_MANIFEST.read_text(encoding="utf-8").splitlines():
        if l.strip():
            m = json.loads(l)
            SYNTH_LABELS[m["id"]] = m["label"]
    for f in range(5):
        build(f, {i for i in range(5) if i != f}, f"fold{f}")
    build(None, {0, 1, 2, 3, 4}, "foldall")
