# synth_panel 코퍼스를 YOLOX 가 읽는 COCO 형식으로 내보낸다.
#
# 산출: <out>/{A,B,C}/{annotations/instances_train2017.json, train2017/*.png,
#                      manifest.jsonl}  +  <out>/seeds.json
#
# 상자는 매니페스트 quad(워프 후 밴드 쿼드, 캔버스 픽셀)의 축정렬 외접 상자
# 하나뿐이다. 쿼드 펴기·기울기 예측은 이 파이프라인에서 쓰지 않는다 — 검출기는
# 축정렬 사각형만 내놓는다.
#
# 세트별로 시드가 다른 것이 요구사항이다. 같은 시드로 구우면 검출기가 외운 장에
# 추론하게 되고, 그러면 리더가 학습 때 본 상자가 배포 때 받는 상자보다 좋다.
# A=검출기 학습 · B=리더 학습(검출기가 처음 보는 장) · C=끝단 평가.
#
# manifest.jsonl 을 세트 안에 같이 남긴다 — COCO 에는 숫자 라벨이 없고
# 리더 학습(B)·끝단 평가(C)가 그 라벨을 필요로 한다.
import argparse
import json
import shutil
from pathlib import Path

import cv2
import numpy as np

import synth_panel

HERE = Path(__file__).resolve().parent

# 세트 이름: (장수, 시드). 시드는 굽는 날짜에서 따 왔고 과거 코퍼스
# (22000·23000·10000·20000·40000·80000 대)와 겹치지 않는다.
SETS = {
    "A": (1000, 20260916),
    "B": (1000, 20260917),
    "C": (300, 20260918),
    # A2 — 검출기 학습을 두껍게 하려고 더 구운 학습 세트(2026-09-17).
    # A 900장 25에폭으로는 한계 장이 남았다(세트 B 1000장 중 1장이 conf 0.25
    # 를 못 넘었고, 그 장은 위치는 맞고 신뢰도만 0.19 였다 —
    # diag_synthband_miss.py). 얇아서인지 보려고 5배로 늘린다.
    # **시드는 A·B·C 어느 것과도 겹치지 않는다** — 겹치면 B 가 검출기가 외운
    # 장이 되어 리더가 배포보다 좋은 상자를 본다.
    "A2": (5000, 20260919),
}

CATEGORY = {"id": 1, "name": "glucose_band", "supercategory": "none"}

MIN_SIDE = 8            # 이보다 작은 상자는 학습에 쓸 수 없다 — 하드 실패시킨다


def quad_to_bbox(quad, w, h):
    """쿼드의 축정렬 외접 상자 → COCO bbox [x, y, w, h]."""
    q = np.asarray(quad, np.float64)
    x0 = float(np.clip(q[:, 0].min(), 0, w - 1))
    y0 = float(np.clip(q[:, 1].min(), 0, h - 1))
    x1 = float(np.clip(q[:, 0].max(), 0, w - 1))
    y1 = float(np.clip(q[:, 1].max(), 0, h - 1))
    return [round(x0, 2), round(y0, 2), round(x1 - x0, 2), round(y1 - y0, 2)]


def build_set(name, count, seed, out_root):
    set_dir = out_root / name
    if set_dir.exists():
        shutil.rmtree(set_dir)
    set_dir.mkdir(parents=True)

    synth_panel.generate(count, seed, set_dir)
    (set_dir / "images").rename(set_dir / "train2017")

    rows = [json.loads(l) for l in
            (set_dir / "manifest.jsonl").read_text(encoding="utf-8").splitlines()
            if l.strip()]
    assert len(rows) == count, f"{name}: 매니페스트 {len(rows)} != 요청 {count}"

    coco = {
        "info": {"description": f"sugarScan synth panels set {name}",
                 "generator": "synth_panel.py via build_synth_coco.py",
                 "set": name, "seed": seed, "count": count},
        "licenses": [],
        "categories": [CATEGORY],
        "images": [],
        "annotations": [],
    }
    for i, r in enumerate(rows):
        fname = f"{r['id']}.png"
        assert (set_dir / "train2017" / fname).exists(), fname
        bbox = quad_to_bbox(r["quad"], r["w"], r["h"])
        assert bbox[2] > MIN_SIDE and bbox[3] > MIN_SIDE, (r["id"], bbox)
        coco["images"].append({"id": i, "file_name": fname,
                               "width": r["w"], "height": r["h"]})
        coco["annotations"].append({
            "id": i, "image_id": i, "category_id": CATEGORY["id"],
            "bbox": bbox, "area": round(bbox[2] * bbox[3], 2),
            "iscrowd": 0, "segmentation": [],
        })

    (set_dir / "annotations").mkdir()
    ann_path = set_dir / "annotations" / "instances_train2017.json"
    ann_path.write_text(json.dumps(coco), encoding="utf-8")

    n_img, n_ann = len(coco["images"]), len(coco["annotations"])
    assert n_img == n_ann, f"{name}: 이미지 {n_img} != 어노테이션 {n_ann}"
    print(f"[{name}] seed={seed}  이미지 {n_img}장 / 상자 {n_ann}개 -> {ann_path}")
    return coco


def box_sheet(set_dir, coco, out_png, n=10, cols=5):
    """상자를 원본에 그려 눈으로 확인하는 판. 초록=COCO bbox, 파랑=원본 quad."""
    rows = [json.loads(l) for l in
            (set_dir / "manifest.jsonl").read_text(encoding="utf-8").splitlines()
            if l.strip()]
    step = max(1, len(rows) // n)
    picks = [(rows[i], coco["annotations"][i]) for i in range(0, len(rows), step)][:n]

    cell_w, cell_h = 420, 520
    tiles = []
    for r, a in picks:
        img = cv2.imread(str(set_dir / "train2017" / f"{r['id']}.png"))
        cv2.polylines(img, [np.asarray(r["quad"], np.int32)], True, (255, 120, 0), 2)
        x, y, w, h = a["bbox"]
        cv2.rectangle(img, (int(x), int(y)), (int(x + w), int(y + h)),
                      (0, 220, 0), 2)
        cv2.putText(img, r["label"], (6, 26), cv2.FONT_HERSHEY_SIMPLEX,
                    0.8, (0, 220, 0), 2)
        s = min(cell_w / img.shape[1], cell_h / img.shape[0])
        img = cv2.resize(img, (int(img.shape[1] * s), int(img.shape[0] * s)))
        pad = np.zeros((cell_h, cell_w, 3), np.uint8)
        pad[:img.shape[0], :img.shape[1]] = img
        tiles.append(pad)

    grid = [np.hstack(tiles[i:i + cols]) for i in range(0, len(tiles), cols)]
    width = max(g.shape[1] for g in grid)
    grid = [np.pad(g, ((0, 0), (0, width - g.shape[1]), (0, 0))) for g in grid]
    cv2.imwrite(str(out_png), np.vstack(grid))
    print(f"      상자 확인판 {len(picks)}장 -> {out_png}")


def verify(out_root, names):
    """구운 결과를 디스크에서 다시 잰다 — 빌드와 독립한 자.

    세트 간 겹침은 파일명이 아니라 픽셀 해시로 본다. 파일명에 시드가 박혀
    있어서 이름 비교는 시드가 달랐다는 사실만 되풀이하고, 장면이 정말 달라
    졌는지는 말해 주지 않는다.
    """
    import hashlib

    ok = True
    hashes = {}
    for name in names:
        d = out_root / name
        ann = d / "annotations" / "instances_train2017.json"
        j = json.loads(ann.read_text(encoding="utf-8"))
        files = sorted(p.name for p in (d / "train2017").iterdir())
        n_img, n_ann = len(j["images"]), len(j["annotations"])

        checks = {
            "annotations/instances_train2017.json 존재": ann.exists(),
            "어노테이션 수 = 이미지 수": n_img == n_ann,
            "train2017/ 파일 수 = 이미지 수": len(files) == n_img,
            "file_name 전부 실재": {i["file_name"] for i in j["images"]} == set(files),
            "image_id 유일": len({a["image_id"] for a in j["annotations"]}) == n_ann,
            "클래스 하나": len(j["categories"]) == 1,
            "상자가 이미지 안": all(
                a["bbox"][0] >= 0 and a["bbox"][1] >= 0
                and a["bbox"][0] + a["bbox"][2] <= im["width"]
                and a["bbox"][1] + a["bbox"][3] <= im["height"]
                for im, a in zip(j["images"], j["annotations"])),
        }
        print(f"[{name}] seed={j['info']['seed']} 이미지 {n_img} / 상자 {n_ann}")
        for k, v in checks.items():
            print(f"      {'OK ' if v else 'FAIL'} {k}")
            ok &= v
        hashes[name] = {hashlib.md5((d / "train2017" / f).read_bytes()).hexdigest()
                        for f in files}

    seeds = json.loads((out_root / "seeds.json").read_text(encoding="utf-8"))["sets"]
    uniq = len({s["seed"] for s in seeds.values()}) == len(seeds)
    print(f"[시드] {'OK ' if uniq else 'FAIL'} seeds.json 의 시드가 서로 다르다: "
          f"{ {k: v['seed'] for k, v in seeds.items()} }")
    ok &= uniq
    for a in names:
        for b in names:
            if a < b:
                n = len(hashes[a] & hashes[b])
                print(f"[겹침] {'OK ' if n == 0 else 'FAIL'} {a}∩{b} 동일 픽셀 {n}장")
                ok &= n == 0
    print("VERIFY PASS" if ok else "VERIFY FAIL")
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(HERE / "synth_coco"))
    ap.add_argument("--sets", default="A,B,C")
    ap.add_argument("--sheet-n", type=int, default=10)
    ap.add_argument("--verify", action="store_true",
                    help="굽지 않고 이미 구운 결과만 검사한다")
    args = ap.parse_args()

    out_root = Path(args.out)
    names = [s.strip() for s in args.sets.split(",") if s.strip()]
    if args.verify:
        return verify(out_root, names)

    out_root.mkdir(parents=True, exist_ok=True)

    seeds = {}
    for name in names:
        count, seed = SETS[name]
        assert seed not in seeds.values(), f"시드 중복: {name}"
        coco = build_set(name, count, seed, out_root)
        seeds[name] = seed
        box_sheet(out_root / name, coco, out_root / f"{name}_boxcheck.png",
                  n=args.sheet_n)

    seed_path = out_root / "seeds.json"
    seed_path.write_text(json.dumps(
        {"sets": {n: {"count": SETS[n][0], "seed": SETS[n][1]} for n in names},
         "note": "세트마다 다른 시드 — B 는 A 로 학습한 검출기가 처음 보는 장이어야 "
                 "리더가 배포와 같은 품질의 상자를 본다."},
        ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"시드 기록 -> {seed_path}: {seeds}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
