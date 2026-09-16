# 프로파일 덮어쓰기 — 웹툴 에디터의 저장소.
#
# 배경(2026-09-15): 프로파일을 한 기기씩 눈으로 고치는 작업이 반복되면서,
# 값 하나 바꿀 때마다 사람이 지적하고 내가 코드를 고치고 다시 굽는 왕복이
# 생겼다. 사람 요청: "프로파일링 에디터 만들자. 각 요소를 넣고 조절할 수
# 있게."
#
# 에디터가 `synth_profiles.py` 를 다시 쓰지 않는다. 코드를 기계가 고치면
# 주석·근거가 날아가고, 무엇이 사람 판단이고 무엇이 생성물인지 구분이
# 사라진다. 대신 **덮어쓰기만 JSON 에 쌓고** 불러올 때 합친다.
#
#   synth_profiles.py   근거와 주석이 있는 정본(사람이 손으로 쓴다)
#   synth_overrides.json 에디터가 만든 덮어쓰기(기계가 쓴다)
#
# 값이 굳으면 사람이 정본으로 옮기고 덮어쓰기에서 지운다 — 그때 근거를
# 주석으로 적는다.
#
# 구조:
#   {"<profile id>": {"profile": {...}, "regions": {...}}}
# profile 은 PROFILES 항목에, regions 는 REGIONS 항목에 얹는다. 둘 다
# **얕은 병합**이다 — 요소 하나(unit 등)를 통째로 갈아끼운다. 부분 병합은
# 무엇이 덮였는지 읽기 어려워진다.
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
PATH = HERE / "synth_overrides.json"


def load():
    if not PATH.exists():
        return {}
    try:
        return json.loads(PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}


def save(data):
    PATH.write_text(json.dumps(data, ensure_ascii=False, indent=1),
                    encoding="utf-8")


def _merge(base, ov):
    out = dict(base)
    for k, v in (ov or {}).items():
        if v is None:            # None 은 '이 키를 지운다'
            out.pop(k, None)
        else:
            out[k] = v
    return out


def apply_to(profiles, regions, data=None):
    """PROFILES 리스트와 REGIONS dict 에 덮어쓰기를 제자리로 얹는다.

    반환: 얹힌 프로파일 수. 아무것도 없으면 0 이고 원본은 손대지 않는다.
    """
    data = load() if data is None else data
    if not data:
        return 0
    n = 0
    for p in profiles:
        ov = (data.get(p.get("id")) or {}).get("profile")
        if not ov:
            continue
        merged = _merge(p, ov)
        p.clear()
        p.update(merged)
        n += 1
    for pid, ov in data.items():
        rg = (ov or {}).get("regions")
        if rg:
            regions[pid] = _merge(regions.get(pid, {}), rg)
    return n
