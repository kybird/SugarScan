# G34 1단계 — 장면 성분 배정을 파일로 뽑는다.
#
# 「촬영 장면 성분에 기종을 태깅한다」 카드의 AC #1. 성분 정의는 재분할
# (build_grouped_split.py) 이 쓴 것과 **동일해야 한다** — components_of() 를
# import 해서 쓰고 임계값도 8 로 고정한다. 여기서 다른 값을 쓰면 태그가 분할
# 그룹과 어긋나 이 카드의 목적(미학습 기기·mmol 확보의 정의)이 사라진다.
#
# 산출: _diag/scene_components.json — {component_id: [image_id, ...]}
#   component_id 는 c000~c709, 성분 대표(사전순 최소 id) 순으로 매긴다.
#   재실행해도 같은 배정이 나온다(union-find·정렬 전부 결정적).
# 확인: 성분 710개 · 최대 723장 · 2장 이상 99개 가 재현되지 않으면 exit 2.
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from audit_split_leakage import dhash  # noqa: E402
from build_grouped_split import DATUMO, components_of  # noqa: E402

THRESHOLD = 8  # 재분할이 갈라진 기준. 다른 값을 쓰면 안 된다(카드 Plan 1).


def main() -> int:
    cache = np.load(HERE / "data_cache_v2.npz", allow_pickle=True)
    tr_ids = [str(x) for x in cache["real_train_ids"]]
    ho_ids = [str(x) for x in cache["real_holdout_ids"]]
    all_ids = tr_ids + ho_ids
    print(f"실사진 {len(all_ids)}장 (train {len(tr_ids)} / holdout {len(ho_ids)})",
          flush=True)

    hashes = {}
    for cid in all_ids:
        p = DATUMO / "extracted" / "TILDE" / f"{cid}.jpg"
        h = dhash(p)
        if h is None:
            print(f"불러오기 실패: {cid}", flush=True)
            return 2
        hashes[cid] = h

    comps = components_of(all_ids, hashes, THRESHOLD)
    # 대표(사전순 최소 id) 순으로 정렬해 번호를 매긴다 — 시트·태그의 순서 근거.
    comps.sort(key=lambda c: min(c))
    n = len(comps)
    sizes = [len(c) for c in comps]
    multi = sum(1 for s in sizes if s >= 2)
    biggest = max(sizes)
    print(f"해밍 ≤{THRESHOLD}: 성분 {n}개 · 2장 이상 {multi} · 최대 {biggest}장 "
          f"· 합계 {sum(sizes)}장", flush=True)
    if (n, multi, biggest) != (710, 99, 723):
        print("재분할 감사의 수치(710/99/723)와 다르다 — 여기서 멈춘다.", flush=True)
        return 2

    out = {}
    for k, c in enumerate(comps):
        out[f"c{k:03d}"] = sorted(c)
    dest = HERE / "_diag" / "scene_components.json"
    dest.write_text(json.dumps(out, ensure_ascii=False, indent=1),
                    encoding="utf-8")

    hold = set(ho_ids)
    top = sorted(out.items(), key=lambda kv: -len(kv[1]))[:5]
    for cid, members in top:
        h = sum(1 for m in members if m in hold)
        print(f"  {cid}: {len(members)}장 (holdout {h}) 대표 {members[0]}", flush=True)
    print(f"저장: {dest}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
