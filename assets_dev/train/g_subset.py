# Gmaster 8,000장에서 중첩 부분집합 세트를 자른다 — 스케일 곡선용.
#
# 사람 결정(2026-10-03 밤): 매 점 새 시드로 굽지 않는다 — 인접 점의 차이에
# 시드 잡음이 섞여 곡선 기울기를 못 믿는다(2026-09-17 S 세트 설계와 같은
# 결정). Gmaster 하나(시드 20261120)를 한 번 굽고 1,000·2,000·4,000·
# 8,000을 **앞에서 순서대로** 중첩 자른다. 학습은 점마다 from scratch.
#
# 사용:
#   python g_subset.py --n 1000   # synth_coco/G1000 (Gmaster 앞 1,000장)
#   python g_subset.py --n 2000
import argparse
import json
import shutil
from pathlib import Path

HERE = Path(__file__).resolve().parent
MASTER = HERE / "synth_coco" / "Gmaster"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, required=True)
    a = ap.parse_args()
    out = HERE / "synth_coco" / f"G{a.n}"
    if out.exists():
        shutil.rmtree(out)
    (out / "train2017").mkdir(parents=True)
    (out / "annotations").mkdir(exist_ok=True)

    coco = json.loads((MASTER / "annotations" / "instances_train2017.json")
                      .read_text(encoding="utf-8"))
    want = coco["images"][:a.n]
    keep = {im["id"] for im in want}
    anns = [x for x in coco["annotations"] if x["image_id"] in keep]
    for im in want:
        shutil.copy2(MASTER / "train2017" / im["file_name"],
                     out / "train2017" / im["file_name"])
    (out / "annotations" / "instances_train2017.json").write_text(
        json.dumps({"images": want, "annotations": anns,
                    "categories": coco["categories"]}), encoding="utf-8")
    with (out / "manifest.jsonl").open("w", encoding="utf-8") as f:
        rows = (MASTER / "manifest.jsonl").read_text(encoding="utf-8").splitlines()
        names = {im["file_name"] for im in want}
        for line in rows:
            if line.strip():
                j = json.loads(line)
                if f"{j['id']}.png" in names:
                    f.write(line + "\n")
    print(f"G{a.n}: {len(want)} 이미지 · {len(anns)} 상자 (Gmaster 중첩)")


if __name__ == "__main__":
    main()
