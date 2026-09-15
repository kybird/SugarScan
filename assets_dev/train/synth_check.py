# 합성 코퍼스 불변식 검사 — 리팩토링의 안전망.
#
# 배경(2026-09-15): 밴드 쿼드·요소 배치를 고치는 동안 "고쳤습니다" 라고 보고한
# 뒤에 사람이 화면에서 결함을 찾아내는 일이 여러 번 반복됐다. 잘못된 앵커,
# 내용을 자르는 클램프, 예약만 하고 안 쓴 자리, 자리를 다투는 두 요소 —
# 전부 눈으로 찾아야 했다.
#
# 그래서 불변식을 코드로 박는다. 리팩토링은 **이 검사를 통과하는 것**으로
# 정의한다. 사람이 같은 것을 두 번 지적하지 않아도 되게.
#
# 검사하는 것:
#   1 band-contains-slots   밴드 쿼드가 숫자 슬롯 필드를 통째로 담는다
#   2 band-digits-only      밴드 쿼드 안에 숫자 아닌 요소가 없다
#   3 no-overlap            요소끼리 겹치지 않는다
#   4 inside-glass          모든 요소가 유리 안에 있다
#   5 slot-stable           같은 기기는 같은 자리에 같은 요소가 온다
#   6 glass-filled          유리에 크게 빈 면이 남지 않는다
#
# 5 는 '자리'를 유리를 3x3 으로 나눈 칸으로 본다. 같은 기기에서 어떤 요소가
# 장마다 다른 칸에 나타나면 위반이다 — green_doctor 좌상단을 M 과 삼각형이
# 다퉈 장마다 다른 것이 떴던 결함이 이걸로 잡힌다.
#
# 6 은 액정 설계 원칙이다(사람 지침 2026-09-15: "LCD 에 빈 공간 남기는 게
# 말이 되냐"). 유리를 격자로 나눠 어떤 요소도 닿지 않는 칸의 비율을 센다.
#
# 사용:
#   python synth_check.py synth_fix_1200
#   python synth_check.py synth_fix_1200 --verbose      위반 장 id 를 찍는다
#   python synth_check.py synth_fix_1200 --json out.json  기준선으로 떠 둔다
import argparse
import json
from collections import defaultdict
from pathlib import Path

import numpy as np

BAND_EL = "band"
# 밴드 줄에 있어도 숫자가 아닌 것 — 밴드 쿼드에 들어오면 안 된다.
NON_DIGIT = ("unit", "mem", "meal", "arrow", "meter_arrow", "glulabel",
             "time", "daterow", "dotrow_above", "dotrow_below", "avgrow")
# 자리가 움직이는 것이 설계인 요소 — 5번 검사에서 면제한다.
#   band         값 자릿수에 따라 폭이 달라진다
#   meter_arrow  미터기 지시자다. 세로 위치가 곧 값이다(accuchek_instant,
#                실측 34장: v100 하단 ~ v159+ 상단 포화). 고정되면 오히려 틀린다.
MOVES_BY_DESIGN = {"band", "meter_arrow"}
# 자리 고정을 요구하지 않는 프로파일 — 한 기기가 아니라 여러 기기를 뭉뚱그린
# 풀이다. 고정하면 실물에 없는 기기 하나를 가르치게 된다.
POOL_PROFILES = {"generic_v1"}
GRID = 3            # 자리 안정성: 유리를 GRID x GRID 칸으로
FILL_GRID = 6       # 빈 면: 유리를 FILL_GRID x FILL_GRID 칸으로


def _rect_of(q):
    q = np.asarray(q, float)
    return q[:, 0].min(), q[:, 1].min(), q[:, 0].max(), q[:, 1].max()


def _contains(outer, inner, tol=0.5):
    ox0, oy0, ox1, oy1 = outer
    ix0, iy0, ix1, iy1 = inner
    return (ox0 <= ix0 + tol and oy0 <= iy0 + tol
            and ox1 >= ix1 - tol and oy1 >= iy1 - tol)


def _center_in(outer, r):
    ox0, oy0, ox1, oy1 = outer
    cx, cy = (r[0] + r[2]) / 2.0, (r[1] + r[3]) / 2.0
    return ox0 <= cx <= ox1 and oy0 <= cy <= oy1


def _overlap(a, b):
    return not (a[2] <= b[0] or b[2] <= a[0] or a[3] <= b[1] or b[3] <= a[1])


def _cell(glass, r, n):
    gx0, gy0, gx1, gy1 = glass
    gw, gh = max(1e-6, gx1 - gx0), max(1e-6, gy1 - gy0)
    cx, cy = (r[0] + r[2]) / 2.0, (r[1] + r[3]) / 2.0
    i = min(n - 1, max(0, int((cx - gx0) / gw * n)))
    j = min(n - 1, max(0, int((cy - gy0) / gh * n)))
    return j * n + i


def check(rows, verbose=False):
    fail = defaultdict(list)
    slots = defaultdict(lambda: defaultdict(set))   # profile -> element -> cells
    empty_frac = defaultdict(list)

    for r in rows:
        rid = r["id"]
        # rects 는 워프 전 패널 좌표다. 같은 좌표계인 quad_panel 로 비교한다 —
        # 워프 후 quad 와 섞으면 기울어진 장에서 허위 위반이 난다.
        quad = _rect_of(r.get("quad_panel") or r["quad"])
        # 유리도 워프 전 좌표가 필요하다. glass_quad 는 워프 후라 못 쓴다 —
        # 대신 패널 좌표의 유리 사각형을 manifest 에 넣기 전까지는 캔버스로
        # 대신한다(캔버스 밖으로 나간 요소만 잡는다. 유리 밖 검사는 약해진다).
        glass = (0.0, 0.0, float(r["w"] - 1), float(r["h"] - 1))
        rects = r.get("rects") or []
        band = [x for x in rects if x[4] == BAND_EL]

        # 1 밴드가 슬롯 필드를 담는가 — manifest 의 band rect 는 '보이는 숫자'
        #   라 빈 앞칸을 뺀 것이다. 그래서 담김만 본다(왼쪽 여유는 정상).
        for b in band:
            if not _contains(quad, b[:4]):
                fail["1 band-contains-slots"].append(rid)
                break

        # 2 밴드 안에 숫자 아닌 것이 없는가
        for x in rects:
            if x[4] in NON_DIGIT and _center_in(quad, x[:4]):
                fail["2 band-digits-only"].append(f"{rid}:{x[4]}")

        # 3 요소끼리 겹치는가
        for i in range(len(rects)):
            for j in range(i + 1, len(rects)):
                if _overlap(rects[i][:4], rects[j][:4]):
                    fail["3 no-overlap"].append(
                        f"{rid}:{rects[i][4]}x{rects[j][4]}")

        if glass is None:
            continue

        # 4 유리 안에 있는가
        for x in rects:
            if not _contains(glass, x[:4], tol=1.5):
                fail["4 inside-glass"].append(f"{rid}:{x[4]}")

        # 5 자리 안정성 — 나중에 프로파일별로 합산
        for x in rects:
            slots[r["profile"]][x[4]].add(_cell(glass, x[:4], GRID))

        # 6 빈 면 — 어떤 요소도 닿지 않는 칸의 비율
        gx0, gy0, gx1, gy1 = glass
        cw = (gx1 - gx0) / FILL_GRID
        ch = (gy1 - gy0) / FILL_GRID
        touched = set()
        for x in rects:
            i0 = max(0, min(FILL_GRID - 1, int((x[0] - gx0) / max(cw, 1e-6))))
            i1 = max(0, min(FILL_GRID - 1, int((x[2] - gx0) / max(cw, 1e-6))))
            j0 = max(0, min(FILL_GRID - 1, int((x[1] - gy0) / max(ch, 1e-6))))
            j1 = max(0, min(FILL_GRID - 1, int((x[3] - gy0) / max(ch, 1e-6))))
            for j in range(j0, j1 + 1):
                for i in range(i0, i1 + 1):
                    touched.add(j * FILL_GRID + i)
        empty_frac[r["profile"]].append(
            1.0 - len(touched) / float(FILL_GRID * FILL_GRID))

    # 5 집계: 한 요소가 두 칸 이상에 나타나면 자리가 흔들린 것
    unstable = []
    for pid, els in sorted(slots.items()):
        if pid in POOL_PROFILES:
            continue
        for el, cells in sorted(els.items()):
            if el in MOVES_BY_DESIGN:
                continue
            if len(cells) > 1:
                unstable.append(f"{pid}:{el} -> {sorted(cells)}")
    if unstable:
        fail["5 slot-stable"] = unstable

    return fail, empty_frac


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("corpus")
    ap.add_argument("--verbose", action="store_true")
    ap.add_argument("--json", default=None, help="결과를 기준선으로 저장")
    args = ap.parse_args()

    d = Path(args.corpus)
    rows = [json.loads(l) for l in
            (d / "manifest.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    fail, empty = check(rows, args.verbose)

    print(f"{d.name}  n={len(rows)}")
    print("── 불변식 ─────────────────────────────────")
    names = ["1 band-contains-slots", "2 band-digits-only", "3 no-overlap",
             "4 inside-glass", "5 slot-stable"]
    total = 0
    for k in names:
        v = fail.get(k, [])
        total += len(v)
        mark = "OK " if not v else "FAIL"
        print(f"  [{mark}] {k:<24} {len(v)}")
        if v and args.verbose:
            for s in v[:12]:
                print(f"           {s}")
            if len(v) > 12:
                print(f"           ... 외 {len(v) - 12}")

    print("── 유리 빈 면 (요소가 닿지 않는 칸 비율, 6x6) ──")
    allv = [x for vs in empty.values() for x in vs]
    print(f"  전체 median {np.median(allv):.3f}")
    for pid, vs in sorted(empty.items(), key=lambda kv: -np.median(kv[1])):
        print(f"    {pid:<24} {np.median(vs):.3f}")

    if args.json:
        Path(args.json).write_text(json.dumps(
            {"corpus": d.name, "n": len(rows),
             "fail": {k: len(v) for k, v in fail.items()},
             "empty_median": float(np.median(allv)),
             "empty_by_profile": {k: float(np.median(v))
                                  for k, v in empty.items()}},
            ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"\n기준선 저장: {args.json}")
    return 0 if total == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
