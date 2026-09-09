# 가로형 LCD 밴드 라벨링 큐 — 사람이 전수 조사로 센 51장 중 아직 밴드 라벨이
# 없는 것을 골라 순서를 정한다. 산출: wide_band_queue.json
#
# 왜 이 층만 따로 뽑나: 밴드의 세로 위치가 GM 박스 안에서 일정하다는 측정
# (중심 흩어짐 0.069)은 표본 21장이 전부 세로형이라 **가로형에 적용할 근거가
# 없다.** 가로형은 손으로 찍어야 한다. 그리고 검출기가 가로형에서 사람 라벨의
# 65%만 덮으므로(오른쪽 27.5% 결손) 유도 라벨을 쓰면 그 결손을 그대로 물려받는다.
#
# **순서는 리더 학습셋 먼저, hold-out 나중이다.** 중간에 멈춰도 학습 표본부터
# 채워지고 검증셋이 통째로 비지 않는다. 그리고 캐시의 기존 분할을 그대로 써서
# 밴드 검출기 학습/검증 경계가 리더의 것과 어긋나지 않게 한다 — 어긋나면
# 검출기가 본 장으로 리더를 평가하게 되어 성적이 부풀려진다.
import json
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
WIDE = HERE / "_diag" / "wide_all" / "wide_ids.json"
BAND = HERE / "band_boxes.jsonl"
CACHE = HERE / "data_cache_v2.npz"
OUT = HERE / "wide_band_queue.json"


def main() -> int:
    wide = json.loads(WIDE.read_text(encoding="utf-8"))
    done = set()
    if BAND.exists():
        for line in BAND.read_text(encoding="utf-8").splitlines():
            if line.strip():
                done.add(json.loads(line)["id"])

    c = np.load(str(CACHE))
    train = {str(v) for v in c["real_train_ids"]}
    hold = {str(v) for v in c["real_holdout_ids"]}

    rows = []
    for stratum, member in (("가로형·학습", train), ("가로형·검증", hold),
                            ("가로형·분할밖", None)):
        for cid in wide:
            if cid in done:
                continue
            if member is None:
                if cid in train or cid in hold:
                    continue
            elif cid not in member:
                continue
            rows.append({"id": cid, "stratum": stratum,
                         "note": "숫자줄만 감싼다 (단위·날짜·아이콘 제외)"})

    OUT.write_text(json.dumps(rows, ensure_ascii=False, indent=1),
                   encoding="utf-8")
    print(f"가로형 {len(wide)}장 중 이미 라벨된 {len(wide) - len(rows) - 0}장 제외")
    for s in ("가로형·학습", "가로형·검증", "가로형·분할밖"):
        print(f"  {s}: {sum(1 for r in rows if r['stratum'] == s)}")
    print(f"큐: {OUT.name} ({len(rows)}장)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
