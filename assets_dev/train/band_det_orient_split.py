# 밴드 검출 게이트 결과를 세로형/가로형으로 갈라 본다.
#
# 배경(2026-09-13~14): 가로형 기기는 전체 성적에 46/276 밖에 안 들어가서
# 전체 median 으로는 가로형이 좋아졌는지 나빠졌는지 보이지 않는다. 합성기
# 재정비의 목표가 가로형이었으므로 그 층을 따로 인쇄해야 한다.
#
# 층을 가르는 기준은 **사람이 그린 GM 화면 쿼드의 종횡비**다(gm_quads 로더 —
# 사람 라벨 우선). 검출기 출력으로 가르면 모델 예측을 실측이라 부르는
# 안티패턴을 다시 밟는다(doc/wiki/antipatterns/prediction-used-as-ground-truth).
#
# 입력: eval_band_detector.py gate 가 남기는
#       _diag/<tag>/gate_results.jsonl   (기본 tag = 체크포인트 파일명 어간)
#
# 사용:
#   python eval_band_detector.py gate --ckpt band_det_n40k.pt
#   python band_det_orient_split.py band_det_n40k [band_det_v0 ...]
import json
import sys
from pathlib import Path

import numpy as np

from gm_quads import load_gm_quads

HERE = Path(__file__).resolve().parent
AR_LANDSCAPE = 1.0          # 화면 폭/높이 > 1 이면 가로형


def _aspect(q):
    w = q[:, 0].max() - q[:, 0].min()
    h = q[:, 1].max() - q[:, 1].min()
    return w / max(1.0, h)


def split(tag, quads):
    f = HERE / "_diag" / tag / "gate_results.jsonl"
    if not f.exists():
        return None
    port, land, miss = [], [], 0
    for line in open(f, encoding="utf-8"):
        r = json.loads(line)
        q = quads.get(r["id"])
        if q is None:
            miss += 1
            continue
        (land if _aspect(q) > AR_LANDSCAPE else port).append(r["iou_det"])
    return port, land, miss


def main():
    tags = sys.argv[1:]
    if not tags:
        tags = sorted(p.name for p in (HERE / "_diag").iterdir()
                      if (p / "gate_results.jsonl").exists())
    quads, st = load_gm_quads()
    print(f"GM 쿼드 출처 — 사람 {st['human']} · 검출기 {st['detector']}")
    print(f"{'tag':<20} {'전체':>14} {'세로형':>14} {'가로형':>14}")
    for tag in tags:
        r = split(tag, quads)
        if r is None:
            print(f"{tag:<20}  (gate_results.jsonl 없음)")
            continue
        port, land, miss = r
        allv = port + land
        def cell(v):
            return f"{np.median(v):.3f}({len(v):3d})" if v else "     -     "
        note = f"  쿼드없음 {miss}" if miss else ""
        print(f"{tag:<20} {cell(allv):>14} {cell(port):>14} {cell(land):>14}{note}")


if __name__ == "__main__":
    raise SystemExit(main())
