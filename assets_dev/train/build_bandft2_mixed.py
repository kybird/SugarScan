# 검출기 재학습(개선)용 혼합 COCO — 카드 「새 세대 코퍼스 B2·C2 굽기와
# CRNN 리더 학습」 파생(사람 진단 2026-09-26: 기울어진 장면에서 검출기가
# 앞·뒤 자리 한 자리를 통째로 잘라버린다 — 검출기·리더 양쪽 조정 필요).
#
# 구성:
#   (a) B2 프레임 크롭 1,000장 — GT 는 합성이라 정확(_diag/bandft/B2_det).
#       새 세대 전체 장면 분포(기울기 포함)를 검출기에 가르친다.
#   (b) 실사진 학습셋 107+16장 — bandft_coco(기기 단절 train, GT 사람 라벨,
#       렌더러와 무관해 여전히 유효). 도메인 격차 방지.
# 검증: 실사진 val 16장만 — 합성 val 은 같은 생성기라 의미 없다.
# 학습 시작점: bandft_v1(실사진 파인튜닝 체크포인트) — 저 lr 로 이어붙인다.
#
# 사용: python build_bandft2_mixed.py
import json
import shutil

from pathlib import Path

HERE = __import__("pathlib").Path(__file__).resolve().parent
SRC = [("합성 B2", HERE / "_diag" / "bandft" / "B2_det", "train2017"),
       ("실사진", HERE / "bandft_coco", "train2017")]
VAL = [("실사진 val", HERE / "bandft_coco", "val2017")]
OUT = HERE / "bandft2_mixed"



def load(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


def main() -> int:
    (OUT / "annotations").mkdir(parents=True, exist_ok=True)
    next_im, next_ann = 1, 1
    for split, sources in (("train2017", SRC), ("val2017", VAL)):
        (OUT / split).mkdir(parents=True, exist_ok=True)
        images, anns, cats = [], [], None
        for name, root, sp in sources:
            doc = load(root / "annotations" / f"instances_{sp}.json")
            cats = doc["categories"] if cats is None else cats
            for im in doc["images"]:
                src_im = root / sp / im["file_name"]
                new_name = f"{name.split()[0]}_{im['file_name']}"
                shutil.copy2(src_im, OUT / split / new_name)
                images.append({"id": next_im, "file_name": new_name,
                               "width": im["width"], "height": im["height"]})
                for a in doc["annotations"]:
                    if a["image_id"] != im["id"]:
                        continue
                    anns.append({"id": next_ann, "image_id": next_im,
                                 "category_id": a["category_id"],
                                 "bbox": a["bbox"], "area": a["area"],
                                 "iscrowd": 0})
                    next_ann += 1
                next_im += 1
        (OUT / split).mkdir(exist_ok=True)
        (OUT / "annotations" / f"instances_{split}.json").write_text(
            json.dumps({"images": images, "annotations": anns,
                        "categories": cats}), encoding="utf-8")
        print(f"{split}: {len(images)}장 / {len(anns)}상자")
    print(f"-> {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
