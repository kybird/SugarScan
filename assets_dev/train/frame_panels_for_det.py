# 합성 패널을 검출기 프레이밍(LCD 크롭+여백)으로 내보낸다 — 리더 학습
# 상자 생성용(2026-09-24 무인). 코퍼스가 '전체 기기 장면'(사람 선언
# 2026-09-20)으로 바뀐 뒤로 패널 전체를 검출기에 먹이면 분포 밖이다 —
# 배포와 같은 2단 구조(GM 크롭 → 밴드 검출)로 자른다. 여백은 실촬
# 평가와 같은 build_cache_v2.framed_src_rect(BOX_MARGIN 정본).
#
# 산출: <out>/{train2017/*.png, annotations/instances_train2017.json,
# map.jsonl(패널파일→크롭 오프셋·원본 glass)} — infer_synthband 로 예측한
# 뒤 오프셋을 더하면 패널 좌표 상자가 된다(reader_crnn --boxes 규격).
#
# 사용: python frame_panels_for_det.py --set synth_coco/B2 --out _diag/bandft/B2_det
import argparse
import json

import cv2
import numpy as np

HERE = __import__("pathlib").Path(__file__).resolve().parent

from build_cache_v2 import framed_src_rect          # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--set", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    src = HERE / args.set
    out = HERE / args.out
    (out / "train2017").mkdir(parents=True, exist_ok=True)
    (out / "annotations").mkdir(exist_ok=True)

    coco = json.loads((src / "annotations" / "instances_train2017.json")
                      .read_text(encoding="utf-8"))
    gt = {a["image_id"]: a["bbox"] for a in coco["annotations"]}
    maps = []
    images, anns = [], []
    skipped = 0
    for n, im in enumerate(coco["images"], start=1):
        m = None
        for l in (src / "manifest.jsonl").read_text(encoding="utf-8").splitlines():
            if l.strip():
                j = json.loads(l)
                if j["id"] + ".png" == im["file_name"]:
                    m = j
                    break
        if m is None:
            skipped += 1
            continue
        img = cv2.imread(str(src / "train2017" / im["file_name"]))
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        fr = framed_src_rect(gray, np.asarray(m["glass_quad"], float))
        x0, y0 = int(fr[0][0]), int(fr[0][1])
        x1, y1 = int(fr[2][0]), int(fr[2][1])
        crop = img[y0:y1, x0:x1]
        if crop.size == 0 or min(crop.shape[:2]) < 16:
            skipped += 1
            continue
        name = im["file_name"]
        cv2.imwrite(str(out / "train2017" / name), crop)
        bx, by, bw, bh = gt[im["id"]]
        anns.append({"id": len(anns) + 1, "image_id": n,
                     "category_id": coco["categories"][0]["id"],
                     "bbox": [max(0.0, bx - x0), max(0.0, by - y0), bw, bh],
                     "area": bw * bh, "iscrowd": 0})
        images.append({"id": n, "file_name": name,
                       "width": crop.shape[1], "height": crop.shape[0]})
        maps.append({"file_name": name, "dx": x0, "dy": y0})
        if n % 200 == 0:
            print(f".. {n}", flush=True)
    (out / "annotations" / "instances_train2017.json").write_text(
        json.dumps({"images": images, "annotations": anns,
                    "categories": coco["categories"]}), encoding="utf-8")
    (out / "map.jsonl").write_text(
        "\n".join(json.dumps(x) for x in maps) + "\n", encoding="utf-8")
    print(f"프레임 크롭 {len(images)}장 · 스킵 {skipped} -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
