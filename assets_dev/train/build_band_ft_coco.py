# 실사진 밴드 파인튜닝 COCO 굽기 — 카드 「실사진 밴드 라벨로 검출기
# 파인튜닝 — 기기 단절 분할」 AC#3(2026-09-24 무인, 사람 결정 (가)).
#
# 모집단: 기기 단절 분할(_diag/band_device_split) train 140장 − 사람 제외
# 선언(band_exclusions) − 잘림 14장(hard sealing — 파인튜닝으로 안 고쳐짐,
# AC#6). 검증 16장은 이 안에서 시드 고정으로 떼어 체크포인트 선택에만 쓴다
# — 홀드아웃(119장·28기기)은 파인튜닝 전후 게이트의 정본(AC#4·#5).
#
# 프레이밍은 eval_synthband_real 과 동일: 사람 GM 쿼드 + build_cache_v2.
# framed_src_rect(lcdcrop — 합성 학습 분포에 맞춘 여백). 정답은 사람 밴드
# 라벨(band_boxes.jsonl)을 크롭 좌표로 평행 이동.
#
# categories 는 합성 COCO(prep_synth_yolox 산출)에서 통째로 복사해
# 클래스 id 를 맞춘다. 산출: bandft_coco/{train2017,val2017,annotations}.
#
# 사용: python build_band_ft_coco.py
import json
import random

import cv2
import numpy as np

HERE = __file__ and __import__("pathlib").Path(__file__).resolve().parent
SPLIT = HERE / "_diag" / "band_device_split" / "band_device_split.json"
DATUMO = HERE.parent / "upstream" / "datumo"
BANDS = HERE / "band_boxes.jsonl"
SYNTH_COCO = HERE / "synth_coco" / "A2"
OUT = HERE / "bandft_coco"
VAL_N = 16
SEED = 20260924

from build_cache_v2 import framed_src_rect      # noqa: E402
from gm_quads import quad_rows                  # noqa: E402
from band_exclusions import load_excluded       # noqa: E402


def rect(quad):
    q = np.asarray(quad, float)
    return [q[:, 0].min(), q[:, 1].min(), q[:, 0].max(), q[:, 1].max()]


def main() -> int:
    split = json.loads(SPLIT.read_text(encoding="utf-8"))
    excluded = set(load_excluded())
    clipped = set(split["clipped_train"])
    bands = {}
    for l in BANDS.read_text(encoding="utf-8").splitlines():
        if l.strip():
            j = json.loads(l)
            if j.get("quad"):
                bands[j["id"]] = rect(j["quad"])
    gm = {r["id"]: r for r in quad_rows()}
    labels = {}
    for l in (DATUMO / "labels.jsonl").read_text(encoding="utf-8").splitlines():
        if l.strip():
            j = json.loads(l)
            labels[j["id"]] = j["image"]

    ids = [i for i in split["train_ids"]
           if i not in excluded and i not in clipped]
    rng = random.Random(SEED)
    val_ids = set(rng.sample(sorted(ids), VAL_N))

    cats = json.loads((SYNTH_COCO / "annotations" / "instances_train2017.json")
                      .read_text(encoding="utf-8"))["categories"]
    cat0 = cats[0]["id"]

    out_sets = {"train2017": [], "val2017": []}
    anns = {"train2017": [], "val2017": []}
    (OUT / "train2017").mkdir(parents=True, exist_ok=True)
    (OUT / "val2017").mkdir(parents=True, exist_ok=True)
    skipped = []
    for n, cid in enumerate(sorted(ids)):
        side = "val2017" if cid in val_ids else "train2017"
        if cid not in bands or cid not in gm or cid not in labels:
            skipped.append((cid, "자산 없음")); continue
        img = cv2.imread(str(DATUMO / labels[cid]))
        if img is None:
            skipped.append((cid, "이미지 로드 실패")); continue
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        fr = framed_src_rect(gray, gm[cid]["quad"])
        x0, y0 = int(fr[0][0]), int(fr[0][1])
        x1, y1 = int(fr[2][0]), int(fr[2][1])
        crop = img[y0:y1, x0:x1]
        if crop.size == 0 or min(crop.shape[:2]) < 16:
            skipped.append((cid, "크롭 불가")); continue
        bx0, by0, bx1, by1 = bands[cid]
        bx0, bx1 = bx0 - x0, bx1 - x0
        by0, by1 = by0 - y0, by1 - y0
        bx0 = max(0.0, bx0); by0 = max(0.0, by0)
        bx1 = min(float(crop.shape[1]), bx1); by1 = min(float(crop.shape[0]), by1)
        w, h = bx1 - bx0, by1 - by0
        if w < 2 or h < 2:
            skipped.append((cid, "라벨 크롭 밖")); continue
        fname = cid.replace("/", "__") + ".png"
        cv2.imwrite(str(OUT / side / fname), crop)
        im_id = n + 1
        out_sets[side].append({"id": im_id, "file_name": fname,
                               "width": crop.shape[1], "height": crop.shape[0]})
        anns[side].append({"id": len(anns[side]) + 1, "image_id": im_id,
                           "category_id": cat0,
                           "bbox": [round(bx0, 2), round(by0, 2),
                                    round(w, 2), round(h, 2)],
                           "area": round(w * h, 2), "iscrowd": 0})

    (OUT / "annotations").mkdir(exist_ok=True)
    for side in out_sets:
        doc = {"images": out_sets[side], "annotations": anns[side],
               "categories": cats}
        (OUT / "annotations" / f"instances_{side}.json").write_text(
            json.dumps(doc, ensure_ascii=False), encoding="utf-8")
    print(f"train {len(out_sets['train2017'])}장 / val {len(out_sets['val2017'])}장"
          f" / 스킵 {len(skipped)}장(제외 {len(excluded & set(split['train_ids']))}"
          f" · 잘림 {len(clipped & set(split['train_ids']))} 는 애초에 뺐다)")
    for cid, why in skipped:
        print(f"  스킵 {cid}: {why}")
    print(f"-> {OUT}")
    print("train_ids(전 140−제외−잘림) 는 band_device_split.json 이 정본(AC#7).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
