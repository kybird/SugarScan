# 코퍼스 크기 곡선용 중첩 부분집합 (2026-09-17 사람 지시).
#
# 물음: **방향별 몇 장이면 되는가.** 모델을 하나로 고정하고 장수만 바꾼다.
#
# 설계에서 지킨 것(접은 규모 곡선 카드에서 건진 교훈):
#   - **한 번 굽고 중첩 부분집합으로 자른다.** 점마다 다른 시드로 구우면 인접
#     점의 차이에 시드 잡음이 섞여 곡선의 기울기를 못 믿는다. 500 ⊂ 1000 ⊂ ...
#     이면 늘어난 장이 곧 차이다.
#   - **방향별 장수를 정확히 맞춘다.** 추첨 비중(50:50)은 이항 잡음이 있으므로
#     세어서 자른다.
#   - 이미지를 복사하지 않는다. 주석만 여러 벌 쓰고 전부 T/train2017 을 가리킨다.
#
# 스텝 고정은 학습 쪽에서 한다 — train_band.py 가 에포크가 아니라 스텝으로
# 돌기 때문에 이미지 반복으로 에포크 길이를 맞출 필요가 없다.
import argparse
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
WIDE_PROFILES = {"onetouch_ultramini", "wide_unknown"}
STEPS = [500, 1000, 2000, 4000, 8000]     # 방향별 장수
PICK_SEED = 20261003                      # 굽는 시드와 다르다 — 고르기는 별개 축


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", default=str(HERE / "synth_coco" / "T"))
    ap.add_argument("--steps", default=",".join(str(s) for s in STEPS))
    args = ap.parse_args()
    src = Path(args.src)
    steps = [int(x) for x in args.steps.split(",")]

    coco = json.loads((src / "annotations" / "instances_train2017.json")
                      .read_text(encoding="utf-8"))
    by_img = {a["image_id"]: a for a in coco["annotations"]}
    prof = {}
    for line in (src / "manifest.jsonl").read_text(encoding="utf-8").splitlines():
        if line.strip():
            m = json.loads(line)
            prof[m["id"] + ".png"] = m["profile"]

    wide, tall = [], []
    for im in coco["images"]:
        p = prof.get(im["file_name"])
        assert p is not None, f"매니페스트에 없다: {im['file_name']}"
        (wide if p in WIDE_PROFILES else tall).append(im)

    import random
    rng = random.Random(PICK_SEED)
    rng.shuffle(wide)
    rng.shuffle(tall)
    need = max(steps)
    print(f"모 코퍼스 {src.name}: 가로형 {len(wide)} · 세로형 {len(tall)} "
          f"(방향별 필요 {need})")
    for name, pool in (("가로형", wide), ("세로형", tall)):
        assert len(pool) >= need, (
            f"{name}이 {len(pool)}장뿐이다 — {need}장이 필요하다")

    prev = None
    print(f"\n{'N(방향별)':>10}{'합계':>8}{'중첩':>8}")
    for n in steps:
        imgs = wide[:n] + tall[:n]
        fs = {im["file_name"] for im in imgs}
        nest = "-" if prev is None else ("OK" if prev <= fs else "깨짐!")
        assert prev is None or prev <= fs, "중첩이 깨졌다"
        obj = {"info": dict(coco["info"], split="train", n_per_orientation=n,
                            pick_seed=PICK_SEED, nested=True),
               "licenses": [], "categories": coco["categories"],
               "images": imgs,
               "annotations": [by_img[im["id"]] for im in imgs]}
        p = src / "annotations" / f"instances_curve_{n:05d}.json"
        p.write_text(json.dumps(obj), encoding="utf-8")
        print(f"{n:>10}{len(imgs):>8}{nest:>8}   -> {p.name}")
        prev = fs
    print("\n이미지는 복사하지 않았다 — 주석이 전부 "
          f"{src.name}/train2017 을 가리킨다")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
