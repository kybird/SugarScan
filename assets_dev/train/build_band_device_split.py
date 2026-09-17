# 밴드 라벨 코퍼스의 기기 단절 분할 — 검출기 파인튜닝용.
#
# 카드 「실사진 밴드 라벨로 검출기 파인튜닝 — 기기 단절 분할」 AC#1·#2·#6·#7.
#
# 규칙을 다시 짜지 않는다. build_device_split.py 에서 기기 정체성(device_key)·
# 고정 시드·홀드아웃 목표/상한·단일 기기 독점 가드를 **그대로 import** 한다.
# 같은 규칙을 두 군데 쓰면 한쪽만 고쳐져 리더와 검출기가 다른 분할을 쓰게 된다.
# 바뀌는 것은 모집단뿐이다 — 리더는 캐시 풀, 여기는 band_boxes.jsonl.
#
# 읽기 전용 입력: band_boxes.jsonl · device_labels.jsonl. 둘 다 사람 노동이고
# 이 스크립트는 한 글자도 쓰지 않는다.
#
# 사용:
#   python build_band_device_split.py
import argparse
import json
from collections import Counter
from pathlib import Path

import numpy as np

from build_device_split import (HOLD_MAX, HOLD_TARGET, SEED, SHARE_CAP,
                                device_key, display)

HERE = Path(__file__).resolve().parent
BANDS = HERE / "band_boxes.jsonl"
DEVICES = HERE / "device_labels.jsonl"

# 카드 AC#2 가 이름을 댄, 지금 약한 기기들. 한쪽에 몰리면 시드를 바꾸지 않고
# 그 사실을 보고한다(카드 문구 그대로).
WEAK = ["OneTouch UltraMini", "On Call Extra", "KOOKMIN Check", "GluNEO plus"]


def load_jsonl(p):
    out = {}
    for line in Path(p).read_text(encoding="utf-8").splitlines():
        if line.strip():
            r = json.loads(line)
            out[r["id"]] = r
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(HERE / "_diag" / "band_device_split"))
    args = ap.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    bands = {k: v for k, v in load_jsonl(BANDS).items() if v.get("quad")}
    devs = load_jsonl(DEVICES)
    joined = sorted(k for k in bands if k in devs)
    print(f"밴드 라벨 {len(bands)}장 · 기기 라벨 {len(devs)}장 "
          f"· 조인 {len(joined)}장 (기기 라벨 없는 밴드 "
          f"{len(set(bands) - set(devs))}장)")

    groups = {}
    for cid in joined:
        groups.setdefault(device_key(devs[cid]), []).append(cid)
    order = sorted(groups)
    total = len(joined)
    print(f"기기 {len(order)}종 · 최대 {max(len(v) for v in groups.values())}장 "
          f"· 1장뿐인 기기 {sum(1 for v in groups.values() if len(v) == 1)}종")

    # build_device_split 과 같은 담기 — 고정 시드 순열, 기기 통째로, 상한 가드.
    perm = np.random.RandomState(SEED).permutation(len(order))
    hold_keys, n_hold = [], 0
    for k in perm:
        key = order[int(k)]
        if n_hold >= HOLD_TARGET * total:
            break
        if n_hold + len(groups[key]) > HOLD_MAX * total:
            continue
        hold_keys.append(key)
        n_hold += len(groups[key])
    hold_ids = [i for k in hold_keys for i in groups[k]]
    train_ids = [i for i in joined if i not in set(hold_ids)]
    ratio = len(hold_ids) / total
    print(f"\n분할(시드 {SEED}): train {len(train_ids)}장 / "
          f"holdout {len(hold_ids)}장 ({100 * ratio:.1f}%) · "
          f"기기 train {len(order) - len(hold_keys)}종 / holdout {len(hold_keys)}종")

    # ── 검증 ────────────────────────────────────────────────────────────
    hd = {device_key(devs[i]) for i in hold_ids}
    td = {device_key(devs[i]) for i in train_ids}
    cross = hd & td
    print(f"  교차 기기: {len(cross)}종 {'OK' if not cross else sorted(cross)}")
    assert not cross, "기기가 양쪽에 걸쳤다"
    if hold_ids:
        top = Counter(device_key(devs[i]) for i in hold_ids).most_common(1)[0]
        share = top[1] / len(hold_ids)
        print(f"  홀드아웃 단일 기기 최대 비중: {display(top[0])} "
              f"{top[1]}장 {100 * share:.1f}% (상한 {100 * SHARE_CAP:.0f}%) "
              f"{'OK' if share <= SHARE_CAP else 'FAIL'}")

    # AC#2 — 가로형/세로형이 양쪽에 다 있는가, 약한 기기가 몰렸는가.
    wide_ids = set(json.loads((HERE / "_diag" / "wide_all" / "wide_ids.json")
                              .read_text(encoding="utf-8")))
    w_tr = sum(1 for i in train_ids if i in wide_ids)
    w_ho = sum(1 for i in hold_ids if i in wide_ids)
    print(f"\n가로형 사진: train {w_tr}장 / holdout {w_ho}장 "
          f"(밴드 라벨과 가로 목록의 교집합 {w_tr + w_ho}장)")
    wide_devs = Counter(display(device_key(devs[i]))
                        for i in joined if i in wide_ids)
    print(f"  가로형 밴드 라벨이 붙은 기기는 {len(wide_devs)}종뿐이다: "
          + " · ".join(f"{k} {v}장" for k, v in wide_devs.most_common()))
    print("  기기 단절 분할이라 이 기기들이 통째로 한쪽에 간다 — 홀드아웃에 "
          "가로형을 넣으려면 둘 중 하나를 홀드아웃으로 보내야 하고, 그건 "
          "시드가 아니라 규칙을 바꾸는 일이다.")
    # 기기명 대조는 공백·구분자를 지우고 한다. display() 는 "OneTouch / UltraMini"
    # 처럼 슬래시를 넣으므로 "OneTouch UltraMini" 로 찾으면 못 찾는다 —
    # 2026-09-17 에 실제로 "밴드 라벨 코퍼스에 없음" 으로 잘못 보고했다.
    def squash(s):
        return "".join(ch for ch in s.lower() if ch.isalnum())

    print("약한 기기 배치 (시드를 바꾸지 않는다 — 몰리면 사실대로 적는다):")
    for name in WEAK:
        keys = [k for k in order if squash(name) in squash(display(k))]
        if not keys:
            print(f"  {name:<22} 밴드 라벨 코퍼스에 없음")
            continue
        for k in keys:
            side = "holdout" if k in set(hold_keys) else "train"
            print(f"  {display(k):<22} {len(groups[k]):>3}장 -> {side}")

    # AC#6 — 잘린 장은 따로 센다. 자를 새로 만들지 않고
    # band_det_clip_split.inside_frac() 을 그대로 부른다.
    from band_det_clip_split import inside_frac
    ins = inside_frac()
    CLIP_THRESH = 0.95          # band_det_clip_split 의 기본값과 같다
    clip_all = {i for i, v in ins.items() if v < CLIP_THRESH}
    c_tr = [i for i in train_ids if i in clip_all]
    c_ho = [i for i in hold_ids if i in clip_all]
    n_meas_tr = sum(1 for i in train_ids if i in ins)
    n_meas_ho = sum(1 for i in hold_ids if i in ins)
    print(f"\n잘린 장(사람 밴드 라벨이 GM 크롭 안에 {CLIP_THRESH} 미만, AC#6):")
    print(f"  train   {len(c_tr)}/{n_meas_tr}장 "
          f"({100 * len(c_tr) / max(1, n_meas_tr):.1f}%)")
    print(f"  holdout {len(c_ho)}/{n_meas_ho}장 "
          f"({100 * len(c_ho) / max(1, n_meas_ho):.1f}%)")
    print("  하드 실링이라 파인튜닝으로 안 고쳐진다 — 게이트를 낼 때 이 장들은 "
          "따로 빼서 같이 적는다.")

    # AC#7 — 학습에 쓸 사진 id 목록을 산출물로 남긴다.
    payload = {
        "seed": SEED, "rule": "build_device_split.device_key (brand+model+variant)",
        "population": "band_boxes.jsonl(quad 있음) ∩ device_labels.jsonl",
        "n_total": total, "n_train": len(train_ids), "n_holdout": len(hold_ids),
        "holdout_devices": [display(k) for k in sorted(hold_keys)],
        "train_devices": [display(k) for k in sorted(td)],
        "train_ids": train_ids, "holdout_ids": hold_ids,
        "clipped_train": c_tr, "clipped_holdout": c_ho,
        "clip_thresh": CLIP_THRESH,
        "warning": "train_ids 에 있는 사진은 이후 어떤 평가에도 쓰면 안 된다.",
    }
    p = out / "band_device_split.json"
    p.write_text(json.dumps(payload, ensure_ascii=False, indent=2),
                 encoding="utf-8")
    print(f"\n-> {p}")
    print("   train_ids 에 있는 사진은 이후 어떤 평가에도 쓰면 안 된다(AC#7).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
