# G30 — bandcrop 캐시 검증. 다섯 가지를 증명하고 끝난다.
#
# 1. 분할 동일성: data_cache_v2_bandcrop.npz 의 real_train_ids/real_holdout_ids 가
#    기존 data_cache_v2.npz 와 **순서까지** 같아야 한다. 분할이 달라지면 두 모델이
#    다른 hold-out 을 보게 되어 A/B 비교가 무효다.
# 2. 합성 항등성: 합성 경로는 크롭 대상이 아니므로 기존 캐시와 픽셀 완전일치.
# 3. 가로형 항등성: w/h > 1.2 (마진 전 원본 GM 박스) 장은 크롭하지 않으므로
#    기존 캐시와 픽셀 완전일치 — 이것이 "크롭 안 한 경로가 기준선과 같다"의
#    기하 증명이다.
# 4. 세로형 전체 크롭됨: 세로형은 전부(회전 제외) 기존 캐시와 픽셀 불일치여야
#    한다. 하나라도 우연히 같으면 크롭이 실제로 안 들어간 것이다.
# 5. 학습/추론 프레이밍 등가: 캐시의 real 이미지 몇 장을 추론 경로
#    (eval_reader.load_gray → frame_crop(bandcrop=True))로 다시 만들어
#    픽셀 완전일치를 본다. 어긋나면 학습과 추론이 다른 규약을 쓰고 있는 것이다.
# 부수. band_rotation id 는 원본 박스 그대로(픽셀 일치), 형태 판정 집계,
#       wide_ids.json(사람 라벨) 과 규칙 판정의 교차검증.
#
# 사용: python g30_check_cache.py [--data-root DIR]
# 읽기만 한다. 아무것도 쓰지 않는다.
import argparse
import json
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--data-root", type=Path, default=None,
                    help="데이터 루트(기본: 스크립트 폴더)")
    args = ap.parse_args()
    data = args.data_root if args.data_root else HERE

    old = np.load(str(data / "data_cache_v2.npz"))
    bc = np.load(str(data / "data_cache_v2_bandcrop.npz"))

    quads = {}
    for l in (data / "gmscreen_quads.jsonl").read_text(encoding="utf-8").splitlines():
        if l.strip():
            j = json.loads(l)
            quads[j["id"]] = j["quad"]
    rotated = set()
    for l in (data / "band_rotation.jsonl").read_text(encoding="utf-8").splitlines():
        if l.strip():
            rotated.add(json.loads(l)["id"])

    def form(cid):
        """규칙 판정: rotated / wide(크롭 안 함) / tall(크롭)."""
        if cid in rotated:
            return "rotated"
        q = np.asarray(quads[cid], dtype=np.float64)
        w = q[:, 0].max() - q[:, 0].min()
        h = q[:, 1].max() - q[:, 1].min()
        return "wide" if w > 1.2 * h else "tall"

    ok = True

    # 1. 분할 동일성
    for key in ("real_train_ids", "real_holdout_ids"):
        a, b = old[key], bc[key]
        same_order = np.array_equal(a, b)
        same_set = set(map(str, a)) == set(map(str, b))
        print(f"[{'OK' if same_order and same_set else 'FAIL'}] {key}: "
              f"{len(a)} vs {len(b)}, 순서일치={same_order}, 집합일치={same_set}")
        ok &= same_order and same_set
    for key in ("synth_train_images", "synth_val_images",
                "real_train_images", "real_holdout_images"):
        good = old[key].shape == bc[key].shape
        print(f"[{'OK' if good else 'FAIL'}] {key} shape "
              f"{old[key].shape} vs {bc[key].shape}")
        ok &= good

    # 2. 합성 항등성(표본 500)
    rng = np.random.RandomState(0)
    idx = rng.permutation(len(bc["synth_train_images"]))[:500]
    d = np.abs(old["synth_train_images"][idx].astype(np.int16)
               - bc["synth_train_images"][idx].astype(np.int16))
    ident = int((d == 0).all(axis=(1, 2)).sum())
    print(f"[{'OK' if ident == len(idx) else 'FAIL'}] 합성 항등: "
          f"{ident}/{len(idx)} 픽셀 완전일치 (크롭 대상이 아니므로 항등이어야 한다)")
    ok &= ident == len(idx)

    # 3+4. 가로형·회전 항등 / 세로형 전체 불일치 (train+holdout 전수)
    tally = {"wide": [0, 0], "tall": [0, 0], "rotated": [0, 0]}  # [일치, 불일치]
    for split in ("train", "holdout"):
        ids = [str(v) for v in bc[f"real_{split}_ids"]]
        pos = {c: i for i, c in enumerate(ids)}
        oi = {str(v): i for i, v in enumerate(old[f"real_{split}_ids"])}
        imgs_o, imgs_b = old[f"real_{split}_images"], bc[f"real_{split}_images"]
        for cid in ids:
            f = form(cid)
            same = np.array_equal(imgs_o[oi[cid]], imgs_b[pos[cid]])
            tally[f][0 if same else 1] += 1
    wide_ok = tally["wide"][1] == 0 and tally["wide"][0] > 0
    rot_ok = tally["rotated"][1] == 0
    tall_ok = tally["tall"][0] == 0 and tally["tall"][1] > 0
    print(f"[{'OK' if wide_ok else 'FAIL'}] 가로형 항등: {tally['wide'][0]}장 "
          f"전부 픽셀 일치 (불일치 {tally['wide'][1]}) — 크롭 안 한 경로 검증")
    ok &= wide_ok
    print(f"[{'OK' if rot_ok else 'FAIL'}] 회전 제외 항등: {tally['rotated'][0]}장 "
          f"전부 픽셀 일치 (불일치 {tally['rotated'][1]})")
    ok &= rot_ok
    print(f"[{'OK' if tall_ok else 'FAIL'}] 세로형 크롭됨: {tally['tall'][1]}장 "
          f"전부 픽셀 불일치 (우연히 일치 {tally['tall'][0]})")
    ok &= tall_ok
    n_all = sum(v[0] + v[1] for v in tally.values())
    print(f"  형태 집계(실사진 {n_all}장): "
          f"세로형(크롭) {tally['tall'][1]} · 가로형 {tally['wide'][0]} · "
          f"회전 제외 {tally['rotated'][0]}")

    # 부수. wide_ids.json(사람 라벨 가로형) 교차검증 — 규칙이 가로형으로
    # 판정했는지. 1564 는 rotated 라 예외가 정상.
    wide_json = set(json.loads(
        (data / "_diag" / "wide_all" / "wide_ids.json").read_text(encoding="utf-8")))
    in_pool = set()
    for split in ("train", "holdout"):
        in_pool |= {str(v) for v in bc[f"real_{split}_ids"]}
    inter = wide_json & in_pool
    mism = sorted(c for c in inter if form(c) not in ("wide", "rotated"))
    print(f"[{'OK' if not mism else 'FAIL'}] wide_ids.json 교차검증: "
          f"풀 내 {len(inter)}장 중 규칙-가로형 아님 {len(mism)} {mism}")
    ok &= not mism

    # 5. 학습/추론 프레이밍 등가 — 세로형 6·가로형 4·회전(있으면) 표본
    from eval_reader import frame_crop, load_gray  # noqa: E402
    ids_h = [str(v) for v in bc["real_holdout_ids"]]
    pos_h = {c: i for i, c in enumerate(ids_h)}
    want = {"tall": 6, "wide": 4, "rotated": 4}
    picks = {f: [] for f in want}
    for cid in rng.permutation(ids_h):
        f = form(cid)
        if len(picks[f]) < want[f]:
            picks[f].append(cid)
    matched = 0
    total = 0
    for f, lst in picks.items():
        for cid in lst:
            g = load_gray(data.parent / "upstream" / "datumo" / "extracted"
                          / "TILDE" / f"{cid}.jpg")
            if g is None:
                continue
            total += 1
            again = frame_crop(g, quads[cid], cid, True, rotated)
            if np.array_equal(again, bc["real_holdout_images"][pos_h[cid]]):
                matched += 1
            else:
                print(f"  픽셀 불일치({f}): {cid}")
    print(f"[{'OK' if matched == total and total >= 10 else 'FAIL'}] "
          f"학습/추론 bandcrop 프레이밍 등가: {matched}/{total} 픽셀 완전일치")
    ok &= matched == total and total >= 10

    print("RESULT:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
