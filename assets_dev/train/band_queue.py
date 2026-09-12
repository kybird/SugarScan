# 숫자 밴드 라벨링 큐와 진행 계측. 라벨 파일은 읽기만 한다 — 한 줄도 쓰지 않는다.
#
#   verify    band_boxes.jsonl 좌표 프레임 검증(AC#1)
#   build     기기별 번갈아 뽑는 씨앗 큐 생성(AC#2) → band_seed_queue.json
#   progress  진행 계측 한 명령(AC#3)
#
# 좌표 정본은 **표시 이미지**(EXIF 적용)다. eval_reader.load_gray 를 쓴다 —
# PIL 로 그냥 열면 EXIF 를 무시해 원본의 83.5%(orientation=6)가 옆으로 눕는다.
# 그 한 줄 차이로 완전일치가 14.7% ↔ 90.7% 로 갈렸다(load_gray docstring).
import argparse
import json
import random
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

from eval_reader import load_gray  # EXIF 규약 — 저장소 통일 로더. 재구현 금지

HERE = Path(__file__).resolve().parent
UPSTREAM = HERE.parent / "upstream" / "datumo"
ROOT = UPSTREAM / "extracted" / "TILDE"
BAND_BOXES = HERE / "band_boxes.jsonl"
DEVICE_LABELS = HERE / "device_labels.jsonl"
QUADS = HERE / "gmscreen_quads.jsonl"
OUT = HERE / "band_seed_queue.json"
SEED = 20260911  # 기기 단절 분할과 같은 고정 시드 — 큐가 실행마다 바뀌면 진행이 무의미하다


def _rows(p):
    for line in Path(p).read_text(encoding="utf-8").splitlines():
        if line.strip():
            yield json.loads(line)


def _device_key(r):
    return (r.get("brand", "").strip(), r.get("model", "").strip(),
            r.get("variant", "").strip())


def _device_name(k):
    return " / ".join(p for p in k if p) or "(무명)"


def _img_path(cid):
    return ROOT / (cid + ".jpg")


def cmd_verify(limit):
    rows = list(_rows(BAND_BOXES))
    if limit:
        rows = rows[:limit]
    bad = defaultdict(list)
    checked = 0
    for r in rows:
        cid = r["id"]
        q = np.asarray(r["quad"], float)
        if q.shape != (4, 2):
            bad["quad 가 4x2 가 아니다"].append(cid)
            continue
        ow, oh = r.get("ow"), r.get("oh")
        if not ow or not oh:
            bad["ow/oh 가 없다"].append(cid)
            continue
        p = _img_path(cid)
        if not p.exists():
            bad["원본 파일이 없다"].append(cid)
            continue
        g = load_gray(p)
        if g is None:
            bad["디코드 실패"].append(cid)
            continue
        h, w = g.shape
        checked += 1
        if (w, h) != (ow, oh):
            bad[f"ow/oh 가 표시 해상도와 다르다"].append(f"{cid} 라벨 {ow}x{oh} 실제 {w}x{h}")
        if q[:, 0].min() < -1 or q[:, 1].min() < -1 or \
           q[:, 0].max() > ow + 1 or q[:, 1].max() > oh + 1:
            bad["quad 가 이미지 밖으로 나간다"].append(cid)
        if q[:, 0].ptp() < 4 or q[:, 1].ptp() < 4:
            bad["quad 가 퇴화했다(너비/높이 4px 미만)"].append(cid)

    print(f"검사 {checked}/{len(rows)}장 (band_boxes.jsonl)")
    if not bad:
        print("통과 — 좌표 프레임 위반 0건")
        return 0
    for k, v in bad.items():
        print(f"  {k}: {len(v)}건")
        for x in v[:8]:
            print(f"      {x}")
        if len(v) > 8:
            print(f"      … 외 {len(v) - 8}건")
    return 1


def _labeled_ids():
    return {r["id"] for r in _rows(BAND_BOXES)}


def _by_device():
    """기기키 -> 그 기기의 사진 id 목록(gmscreen quad 가 있는 것만)."""
    have_quad = {r["id"] for r in _rows(QUADS)}
    g = defaultdict(list)
    for r in _rows(DEVICE_LABELS):
        if r["id"] in have_quad:
            g[_device_key(r)].append(r["id"])
    return g


def cmd_build(per_device):
    labeled = _labeled_ids()
    groups = _by_device()
    rng = random.Random(SEED)

    # 기기당 목표를 채울 만큼만, 이미 라벨된 장수를 빼고 뽑는다.
    picks = {}
    for k, ids in groups.items():
        done = [i for i in ids if i in labeled]
        rest = sorted(i for i in ids if i not in labeled)
        rng.shuffle(rest)
        need = max(0, per_device - len(done))
        picks[k] = rest[:need]

    # 번갈아 뽑기 — 중간에 멈춰도 기기 다양성이 유지되게(AC#2).
    # 라벨이 적은 기기부터 돈다. 같은 라운드 안의 순서는 기기명 정렬(결정적).
    order = sorted(groups, key=lambda k: (len([i for i in groups[k] if i in labeled]),
                                          _device_name(k)))
    queue = []
    for rnd in range(per_device):
        for k in order:
            if rnd < len(picks[k]):
                queue.append({
                    "id": picks[k][rnd],
                    "stratum": "band-seed",
                    "device": _device_name(k),
                    "note": f"{_device_name(k)} · 기기당 {per_device}장 목표 · "
                            f"{rnd + 1}/{len(picks[k])}",
                })
    OUT.write_text(json.dumps(queue, ensure_ascii=False, indent=1),
                   encoding="utf-8")
    print(f"기기 {len(groups)}종 · 이미 라벨 {len(labeled)}장")
    print(f"큐 {len(queue)}장 → {OUT.name}  (기기당 목표 {per_device})")
    covered = len({q['device'] for q in queue})
    print(f"큐가 덮는 기기 {covered}종. 앞 {min(len(queue), covered)}장만 해도 "
          f"{covered}종이 한 장씩 채워진다")
    return 0


def cmd_progress(per_device):
    labeled = _labeled_ids()
    groups = _by_device()
    in_corpus = {r["id"] for r in _rows(DEVICE_LABELS)}
    have_quad = {r["id"] for r in _rows(QUADS)}
    total_photos = sum(len(v) for v in groups.values())
    done_by = {k: len([i for i in v if i in labeled]) for k, v in groups.items()}
    n_done = sum(done_by.values())
    target = sum(min(per_device, len(v)) for k, v in groups.items())
    print(f"완료 {n_done}장 / 목표 {target}장 (기기당 {per_device}) · "
          f"남은 {max(0, target - n_done)}장")
    print(f"전체 사진 {total_photos}장 · 기기 {len(groups)}종 · "
          f"목표 달성 기기 {sum(1 for k, c in done_by.items() if c >= min(per_device, len(groups[k])))}종")
    # 집계 밖 밴드 라벨 — 성격이 둘이고 대응도 다르다(2026-09-12 확인).
    #  (가) 코퍼스 밖 18장: device_labels(2494장)와 scene_components 는 같은
    #       집합인데 이 18장은 양쪽 모두에 없다. 옛 더 큰 풀에서 만들어진
    #       밴드 라벨이다. 기종 탭은 성분 단위로 돌아 닿을 수 없다 —
    #       기기 라벨 대상이 아니다. 할 일 없음.
    #  (나) 코퍼스 안인데 GM quad 없음 3장: GM 검출 실패다. 라벨로 못 고친다.
    #       카드「GM 검출 추론 전처리 … 레터박스」의 표적이다.
    out_of_corpus = sorted(i for i in labeled
                           if i not in {x for v in groups.values() for x in v}
                           and i not in in_corpus)
    no_quad = sorted(i for i in labeled if i in in_corpus and i not in have_quad)
    if out_of_corpus:
        print("\n코퍼스 밖 밴드 라벨 %d장 — 기기 라벨 대상이 아니다"
              " (성분에 없어 기종 탭이 닿지 않는다). 할 일 없음"
              % len(out_of_corpus))
    if no_quad:
        print(f"GM quad 없는 밴드 라벨 {len(no_quad)}장 — GM 검출 실패다. "
              f"라벨로 못 고친다. 레터박스 카드 표적: {', '.join(no_quad)}")
    print(f"\n{'완료':>4} {'목표':>4} {'보유':>4}  기기")
    for k in sorted(groups, key=lambda k: (done_by[k], _device_name(k))):
        t = min(per_device, len(groups[k]))
        print(f"{done_by[k]:4d} {t:4d} {len(groups[k]):4d}  {_device_name(k)}")
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=("verify", "build", "progress"))
    ap.add_argument("--per-device", type=int, default=4,
                    help="기기당 목표 라벨 장수(build·progress)")
    ap.add_argument("--limit", type=int, default=0, help="verify 표본 제한")
    a = ap.parse_args()
    if a.cmd == "verify":
        return cmd_verify(a.limit)
    if a.cmd == "build":
        return cmd_build(a.per_device)
    return cmd_progress(a.per_device)


if __name__ == "__main__":
    raise SystemExit(main())
