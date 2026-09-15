# 밴드 라벨에서 뺄 장 — 사람 선언의 단일 출처.
#
# 규칙(사람 판정 2026-09-14): 사진이 숫자칸 영역을 잘라 먹었으면 제외한다.
# **빈칸이라도 잘리면 제외**다. 세 자리가 다 보이더라도 숫자칸이 프레임에
# 걸렸으면 그 장은 규약대로 라벨할 수 없고, 검출기는 맞게 내고도 점수를 잃는다.
#
# 측정으로 고르지 않는다. 화면 쿼드가 사진 가장자리에 닿는 장은 19장이지만,
# 그중 실제로 숫자칸이 잘린 것과 가로형이라 원래 꽉 차는 것은 사람이 봐야
# 갈린다. 실제로 내가 기하로 2489 를 '오탐'이라 판정했다가 사람이 뒤집었다 —
# 세 자리가 다 보인다는 것과 숫자칸이 온전하다는 것은 다른 말이었다.
# (doc/wiki/patterns/declare-what-the-human-knows)
#
# 사용:
#   from band_exclusions import load_excluded, drop
#   ex = load_excluded()                  # {id: reason}
#   rows = drop(rows, key=lambda r: r["id"])
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
FILE = HERE / "band_label_excluded.jsonl"


def load_excluded():
    """id -> reason. 파일이 없으면 빈 dict."""
    out = {}
    if FILE.exists():
        for line in open(FILE, encoding="utf-8"):
            line = line.strip()
            if line:
                r = json.loads(line)
                out[r["id"]] = r.get("reason", "")
    return out


def drop(rows, key=lambda r: r["id"], report=True, where=""):
    """제외 목록에 있는 행을 뺀다. 뺀 수를 인쇄한다 — 분모가 조용히 바뀌면
    이전 수치와 나란히 인용됐을 때 아무도 눈치채지 못한다."""
    ex = load_excluded()
    if not ex:
        return list(rows)
    keep = [r for r in rows if key(r) not in ex]
    n = len(rows) - len(keep) if hasattr(rows, "__len__") else None
    if report and n:
        tag = f"[{where}] " if where else ""
        print(f"{tag}사람 선언 제외 {n}장 (남은 {len(keep)}) — "
              + ", ".join(f"{k}({v})" for k, v in ex.items()))
    return keep


if __name__ == "__main__":
    ex = load_excluded()
    print(f"밴드 라벨 제외 {len(ex)}장")
    for k, v in ex.items():
        print(f"  {k:<24} {v}")
