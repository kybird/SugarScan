# Roboflow 코퍼스를 **개발용과 봉인 시험용**으로 가른다. 한 번만 돌린다.
#
# 왜(2026-09-19 사람 승인): Datumo(272장)도 Roboflow(1,273장)도 이제 개발
# 평가셋이다 — 내가 반복해서 보면서 조건을 골랐다. 그 위에서 "98% 달성"이라고
# 말해도 근거가 없다. **더 오염되기 전에 절반을 봉인한다.**
#
# 가르는 단위는 장이 아니라 **촬영 묶음**이다. 같은 순간의 버스트나 같은
# 영상의 프레임이 개발과 시험에 나뉘어 들어가면, 시험셋은 사실상 개발셋을
# 다시 보는 것이 된다. 파일명 계열이 넷이라 각각 다르게 묶는다:
#
#   IMG_5665            연번. 10장 묶음으로 자른다(연속 촬영이 한 묶음)
#   IMG20241209132947   타임스탬프. **분 단위**로 자른다
#   WhatsApp ... 3-41-31 PM   같은 시각 표기. 분 단위
#   VID..._mp4-0001     같은 영상의 프레임. 영상 id 하나로 묶는다
#
# 묶음을 이름 해시로 반반 가른다 — 내가 고르지 않는다. 결과는 `rf_split.json`
# 에 박아 두고 **다시 돌리지 않는다**(파일이 있으면 거부한다).
#
# 평가기는 건드리지 않는다. 전량(1,273장)을 그대로 재고, 보고할 때 이 파일로
# 나눠 읽는다 — 기존 결과를 다시 돌릴 필요가 없다.
import argparse
import hashlib
import json
import re
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "rf_split.json"


def group_key(stem):
    """촬영 묶음 키. 버스트·영상 프레임이 갈라지지 않게 한다."""
    s = re.sub(r"\s*\(\d+\)\s*", "", stem)          # (1) (3) 같은 사본 표시
    m = re.match(r"^(VID[_]?\d+)", s)
    if m:                                            # 같은 영상의 프레임
        return "vid:" + m.group(1)
    m = re.match(r"^IMG_(\d+)", s)
    if m:                                            # 연번 — 10장 묶음
        return f"seq:{int(m.group(1)) // 10}"
    m = re.match(r"^IMG(\d{8})(\d{4})", s)           # IMG<날짜><시분>ss
    if m:
        return f"ts:{m.group(1)}{m.group(2)}"
    m = re.match(r"^WhatsApp Image (\d{4}-\d{2}-\d{2}) at (\d+-\d+)", s)
    if m:                                            # 날짜 + 시-분
        return f"wa:{m.group(1)}:{m.group(2)}"
    return "misc:" + s


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true",
                    help="이미 있는 분할을 덮어쓴다. **쓰지 마라** — 봉인이 깨진다")
    a = ap.parse_args()
    if OUT.exists() and not a.force:
        print(f"이미 있다: {OUT}")
        print("**다시 가르지 않는다.** 분할을 바꾸면 봉인이 무의미해진다.")
        return 1

    from eval_band_roboflow import population
    pop = population()
    groups = defaultdict(list)
    for cid in sorted(pop):
        groups[group_key(cid.split("/", 2)[2])].append(cid)

    dev, test = [], []
    for g in sorted(groups):
        # 이름 해시로 가른다 — 성적을 보고 고르지 않는다.
        h = int(hashlib.sha256(g.encode()).hexdigest()[:8], 16)
        (test if h % 2 else dev).extend(groups[g])

    OUT.write_text(json.dumps({
        "note": "봉인 시험셋. test 는 조건 선택에 쓰지 않는다.",
        "frozen": "2026-09-19",
        "n_groups": len(groups),
        "dev": sorted(dev), "test": sorted(test),
    }, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"묶음 {len(groups)}개 · 개발 {len(dev)}장 · **봉인 시험 {len(test)}장**")
    print(f"  -> {OUT}")
    print("  test 로는 **판정만** 한다. 조건 고르기·문턱 정하기에 쓰지 않는다.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
