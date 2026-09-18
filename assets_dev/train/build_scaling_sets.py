# 규모 곡선 — 방향별 장수만 바꾼 여섯 세트와 그 exp 를 만든다(2026-09-17 사람 지시).
#
# 물음: **세로형·가로형이 각각 몇 장이면 되는가.**
#   N = 100 · 200 · 400 · 800 · 1600 · 3200  (방향별. 학습 장수는 2N)
#
# 설계에서 갈라야 했던 두 가지 ─────────────────────────────────────────
#
# 1) **스텝을 고정하고 장수만 바꾼다.** 지금까지 모든 런은 max_epoch=25 고정이라
#    200장 세트는 313 스텝, 6,400장 세트는 10,000 스텝을 받는다 — 32배 차이다.
#    그대로 여섯을 돌리면 작은 쪽이 못 하는 이유가 '장이 적어서'인지 '스텝이
#    적어서'인지 못 가른다. 이미 한 번 겪었다: P00(200장)이 212장 중 207장
#    검출 실패했고 "200장은 너무 적다"고 보고했는데, 그 런의 스텝은 313이었다.
#    그래서 여기서는 예산을 **v2 와 같은 7,350 스텝**으로 고정하고
#    max_epoch·warmup_epochs·no_aug_epochs 를 세트 크기에 반비례로 조정해
#    **스케줄 모양까지 스텝 단위로 같게** 맞춘다.
#
#    참고로 no_aug_epochs 는 YOLOX 기본값 15 라, 기존 25에폭 런들은 뒤 15에폭을
#    mosaic/mixup 없이 돌았다(전체의 59.8%). 그 비율을 그대로 옮긴다.
#
# 2) **한 번 굽고 중첩 부분집합으로 자른다.** 여섯을 각각 다른 시드로 구우면
#    인접 점의 차이에 시드 잡음이 섞여 곡선의 기울기를 못 믿는다. 100 ⊂ 200 ⊂
#    400 ⊂ … 이면 늘어난 장이 곧 차이다.
#
# 이미지는 **복사하지 않는다.** 한 디렉터리(train2017)에 모아 두고 세트마다
# 주석 파일만 다르게 쓴다 — 여섯 벌을 복사하면 같은 그림이 12,600장 쌓인다.
# val 은 여섯 세트가 **공유**한다(방향별 200장). YOLOX 의 best_ckpt 선택이
# 같은 자 위에서 이뤄져야 체크포인트끼리 비교가 성립한다.
import argparse
import json
import os
import shutil
from pathlib import Path

HERE = Path(__file__).resolve().parent

# 가로형은 기기 프로파일로 가른다. 익명 풀(generic_v1)의 가로 캔버스가 아니라
# **가로형 기기**가 이 축의 대상이다 — synth_panel.EXCLUDE_WIDE_PROFILES 주석 참조.
WIDE_PROFILES = {"onetouch_ultramini", "wide_unknown"}

STEPS = [100, 200, 400, 800, 1600, 3200]
VAL_PER_ORIENT = 200
PICK_SEED = 20260926        # 굽는 시드(20260925)와 다르다 — 고르기는 별개 축이다

# v2(synthband_v2_a2)의 실제 스케줄에서 옮겨 온 예산. n_train 4,700 · 배치 16
# -> 293 스텝/에폭, 25에폭 = 7,350 스텝. warmup 2에폭 = 586 스텝.
# no_aug 15에폭 = 4,395 스텝(58.6%... 정확히는 4395/7350 = 0.598).
BUDGET_ITERS = 7350
WARMUP_ITERS = 586
NOAUG_ITERS = 4395
BATCH = 16
# 에포크당 스텝 수를 여섯 런에서 통일한다 — **YOLOX 는 no_aug 구간에 들어가면
# eval_interval 을 무시하고 매 에포크 평가한다**(trainer.py after_epoch).
# 처음에는 max_epoch 를 세트 크기에 반비례로 키웠는데(200장 -> 612에폭), 그러자
# 366번의 no_aug 에포크가 각각 400장짜리 평가를 끌고 다녔다 — 실측 32초/에포크,
# 런 하나가 3시간 15분이고 체크포인트가 17MB x 366 = 6GB 였다. 학습은 에포크당
# 12스텝인데 평가가 시간을 다 먹었다.
# 그래서 작은 세트의 주석을 K번 반복해 에포크 길이를 맞춘다(K = 6400 / 2N).
# 여섯 런의 max_epoch·warmup·no_aug·평가 횟수가 전부 같아지고, 달라지는 것은
# **서로 다른 이미지 수** 하나뿐이다 — 재려던 바로 그것이다.
ITERS_PER_EPOCH = (2 * STEPS[-1]) // BATCH     # 400
EPOCH_ENTRIES = ITERS_PER_EPOCH * BATCH        # 6400

EXP_TMPL = '''"""합성 밴드 검출기 — 규모 곡선 N={n} (방향별 {n}장, 학습 {ntr}장).

build_scaling_sets.py 가 생성했다. **손으로 고치지 마라** — 여섯 개의 스케줄이
서로 맞물려 있어서 하나만 고치면 곡선이 깨진다.

시작점 규칙은 yolox_synthband_exp.py 머리말이 정본이다(COCO 사전학습,
gmscreen 금지). 여섯 세트가 다른 것은 **학습 장수 하나뿐**이다 —
스텝 예산 {budget} 은 여섯이 모두 같고 v2 와도 같다.

    서로 다른 이미지 {ntr}장 x 반복 {rep} = 에포크당 {ent}개 항목
    **여섯 exp 의 아래 값은 전부 같다.** 다른 것은 위 줄의 '서로 다른 이미지'뿐.
    스텝/에폭 {ipe}  ·  max_epoch {me}  ·  warmup {we}  ·  no_aug {nae}
    -> 실제 스텝 {actual} (목표 {budget})

eval_interval {ev} = max_epoch/5 이고 save_history_ckpt 가 기본 True 라
epoch_N_ckpt.pth 가 **스텝 비율 0.2·0.4·0.6·0.8·1.0 지점**에 떨어진다.
여섯 런의 스냅샷이 같은 스텝 비율에 있으므로 '데이터 고정·스텝 변화' 축을
규모 곡선 안에서 같이 읽을 수 있다 — 가장 큰 세트가 예산 끝에서 아직
오르고 있으면 곡선의 꼭대기가 과소평가된 것이고, 예산을 다시 잡아야 한다.

    python D:/tmp/YOLOX/tools/train.py \
        -f D:/Project/sugarScan/assets_dev/train/{fname} \
        -d 1 -b 16 --fp16 -expn scale_{n:04d} \
        -c D:/Project/sugarScan/assets_dev/train/weights/yolox_nano.pth
"""
from yolox_synthband_exp import Exp as BaseSynthbandExp


class Exp(BaseSynthbandExp):
    def __init__(self):
        super().__init__()
        self.data_dir = r"{data_dir}"
        self.train_ann = "{train_ann}"
        self.val_ann = "instances_val2017.json"
        self.exp_name = "scale_{n:04d}"
        # 스텝 고정 — 아래 넷은 build_scaling_sets.py 가 계산한 값이다.
        self.max_epoch = {me}
        self.warmup_epochs = {we}
        self.no_aug_epochs = {nae}
        self.eval_interval = {ev}
'''


def link(src, dst):
    """하드링크. 같은 볼륨이라 바이트가 늘지 않는다. 실패하면 복사로 떨어진다."""
    if dst.exists():
        return
    try:
        os.link(src, dst)
    except OSError:
        shutil.copy2(src, dst)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", default=str(HERE / "synth_coco" / "S"))
    ap.add_argument("--out", default=str(HERE / "synth_coco" / "S_scale"))
    args = ap.parse_args()
    src, out = Path(args.src), Path(args.out)

    coco = json.loads((src / "annotations" / "instances_train2017.json")
                      .read_text(encoding="utf-8"))
    by_img = {a["image_id"]: a for a in coco["annotations"]}
    assert len(by_img) == len(coco["annotations"]), "image_id 가 유일하지 않다"

    prof = {}
    for line in (src / "manifest.jsonl").read_text(encoding="utf-8").splitlines():
        if line.strip():
            m = json.loads(line)
            prof[f"{m['id']}.png"] = m["profile"]

    wide, tall = [], []
    for im in coco["images"]:
        p = prof.get(im["file_name"])
        assert p is not None, f"매니페스트에 없다: {im['file_name']}"
        (wide if p in WIDE_PROFILES else tall).append(im)

    import random
    rng = random.Random(PICK_SEED)
    rng.shuffle(wide)
    rng.shuffle(tall)
    need = STEPS[-1] + VAL_PER_ORIENT
    print(f"모 코퍼스 {src.name}: 가로형 {len(wide)}장 · 세로형 {len(tall)}장 "
          f"(방향별 필요 {need})")
    for name, pool in (("가로형", wide), ("세로형", tall)):
        assert len(pool) >= need, (
            f"{name}이 {len(pool)}장뿐이다 — {need}장이 필요하다. "
            f"모 코퍼스를 더 크게 굽거나 비중을 올려라")

    val = wide[:VAL_PER_ORIENT] + tall[:VAL_PER_ORIENT]
    wide_tr, tall_tr = wide[VAL_PER_ORIENT:], tall[VAL_PER_ORIENT:]

    if out.exists():
        shutil.rmtree(out)
    (out / "annotations").mkdir(parents=True)
    (out / "train2017").mkdir()
    (out / "val2017").mkdir()

    # 학습 이미지는 가장 큰 세트가 쓰는 만큼만 링크한다.
    for im in wide_tr[:STEPS[-1]] + tall_tr[:STEPS[-1]]:
        link(src / "train2017" / im["file_name"], out / "train2017" / im["file_name"])
    for im in val:
        link(src / "train2017" / im["file_name"], out / "val2017" / im["file_name"])

    def write(split_file, imgs, extra):
        obj = {"info": dict(coco["info"], **extra), "licenses": [],
               "categories": coco["categories"], "images": imgs,
               "annotations": [by_img[im["id"]] for im in imgs]}
        (out / "annotations" / split_file).write_text(json.dumps(obj),
                                                      encoding="utf-8")

    write("instances_val2017.json", val,
          dict(split="val", shared_across=STEPS, pick_seed=PICK_SEED,
               per_orientation=VAL_PER_ORIENT))
    print(f"공통 val: {len(val)}장 (방향별 {VAL_PER_ORIENT})")

    ipe = ITERS_PER_EPOCH
    me = max(1, round(BUDGET_ITERS / ipe))
    we = max(1, round(WARMUP_ITERS / ipe))
    nae = min(max(1, round(NOAUG_ITERS / ipe)), me - 1)
    ev = max(1, me // 5)
    print(f"\n공통 스케줄 — 스텝/에폭 {ipe} · max_epoch {me} · warmup {we} · no_aug {nae} · eval {ev} · 실제 스텝 {ipe*me}")
    print(f"\n{'N':>6}{'서로다른장':>11}{'반복':>6}{'에포크항목':>11}")
    for n in STEPS:
        imgs = wide_tr[:n] + tall_tr[:n]
        ntr = len(imgs)
        k = EPOCH_ENTRIES // ntr
        assert k * ntr == EPOCH_ENTRIES, f"N={n} 이 {EPOCH_ENTRIES} 를 못 채운다"
        # 반복본은 **id 만 새로 준다.** file_name 은 같아 디스크가 늘지 않고,
        # COCODataset 은 id 로 색인하므로 k 개의 표본으로 보인다. 같은 그림이
        # 한 에포크에 k번 나오지만 mosaic·회전·색은 매번 새로 뽑힌다.
        rimgs, ranns = [], []
        for t in range(k):
            off = t * 10_000_000
            for im in imgs:
                a = by_img[im["id"]]
                rimgs.append(dict(im, id=im["id"] + off))
                ranns.append(dict(a, id=a["id"] + off,
                                  image_id=a["image_id"] + off))
        ann = f"instances_train_{n:04d}.json"
        obj = {"info": dict(coco["info"], split="train", n_per_orientation=n,
                            pick_seed=PICK_SEED, nested=True, repeat=k,
                            distinct_images=ntr),
               "licenses": [], "categories": coco["categories"],
               "images": rimgs, "annotations": ranns}
        (out / "annotations" / ann).write_text(json.dumps(obj), encoding="utf-8")
        fname = f"yolox_scale_{n:04d}_exp.py"
        (HERE / fname).write_text(EXP_TMPL.format(
            n=n, ntr=ntr, rep=k, ent=EPOCH_ENTRIES, ipe=ipe, me=me, we=we,
            nae=nae, ev=ev, actual=ipe * me, budget=BUDGET_ITERS, fname=fname,
            data_dir=str(out), train_ann=ann), encoding="utf-8")
        print(f"{n:>6}{ntr:>11}{k:>6}{len(rimgs):>11}")

    print(f"\n주석 -> {out / 'annotations'}   이미지는 하드링크(중복 없음)")
    print("중첩 확인: 작은 세트의 장은 큰 세트에 전부 들어 있다(같은 셔플의 앞부분)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
