# lcd_layout 계약 시험 — 영역 모델이 지켜야 하는 것.
#
# 이 시험이 리팩토링의 바닥이다. 합성 결과를 눈으로 보기 전에 여기서 걸린다.
#   python test_lcd_layout.py
import sys

from lcd_layout import (Rect, build_layout, place_in, slot_field,
                        TOP, MID, BOTTOM, TRACK_R, COLUMN_R)

GLASS = Rect(0, 0, 600, 800)
_fail = []


def ok(cond, msg):
    if cond:
        print(f"  [OK ] {msg}")
    else:
        print(f"  [FAIL] {msg}")
        _fail.append(msg)


def near(a, b, tol=0.51):
    return abs(a - b) <= tol


print("── 영역이 안쪽 면을 빈틈없이 나눈다 ──")
lay = build_layout(GLASS, dict(pad=(0.04, 0.04, 0.05, 0.05),
                               rows=(0.22, 0.52, 0.26)))
ok(near(lay.covered_fraction(), 1.0, 1e-6), "3분할이 안쪽 면을 100% 덮는다")
ok(lay.inner.contains(lay[TOP]) and lay.inner.contains(lay[MID])
   and lay.inner.contains(lay[BOTTOM]), "모든 영역이 안쪽 면 안에 있다")
ok(near(lay[TOP].y1, lay[MID].y0) and near(lay[MID].y1, lay[BOTTOM].y0),
   "영역 사이에 틈이 없다")
ok(near(lay.inner.x0, GLASS.w * 0.04) and near(lay.inner.y0, GLASS.h * 0.05),
   "패딩이 유리 비율로 들어간다")

print("── 트랙을 선언하면 행이 그만큼 좁아진다 ──")
lt = build_layout(GLASS, dict(pad=(0.04, 0.04, 0.05, 0.05),
                              rows=(0.18, 0.56, 0.26), track_right=0.12))
ok(lt.has(TRACK_R), "track-right 영역이 생긴다")
ok(near(lt.covered_fraction(), 1.0, 1e-6), "트랙 포함해도 100% 덮는다")
ok(near(lt[MID].x1, lt[TRACK_R].x0), "mid 오른쪽 끝이 트랙 왼쪽 끝과 붙는다")
ok(lt[MID].w < lay[MID].w, "트랙이 있으면 mid 가 더 좁다")

print("── 가로형: 정보 칼럼 ──")
lw = build_layout(Rect(0, 0, 800, 300),
                  dict(pad=(0.03, 0.03, 0.05, 0.05), column_right=0.42,
                       rows=(0.0, 1.0, 0.0)))
ok(lw.has(COLUMN_R), "column-right 영역이 생긴다")
ok(not lw.has(TOP) and not lw.has(BOTTOM), "0 인 줄은 영역을 만들지 않는다")
ok(near(lw.covered_fraction(), 1.0, 1e-6), "가로형도 100% 덮는다")

print("── 슬롯 필드는 mid 폭을 다 쓴다 ──")
f, dh, pitch = slot_field(lay[MID], slots=3, aspect=0.62)
ok(lay[MID].contains(f), "슬롯 필드가 mid 안에 있다")
ok(f.w >= lay[MID].w * 0.98 or near(dh, lay[MID].h),
   "폭을 꽉 쓰거나 높이에 걸려 멈춘다")
f2, dh2, _ = slot_field(lay[MID], slots=2, aspect=0.62)
ok(dh2 > dh, "칸이 적으면 숫자가 커진다")
tall = build_layout(GLASS, dict(pad=(0.0,) * 4, rows=(0.0, 1.0, 0.0)))
f3, dh3, _ = slot_field(tall[MID], slots=3, aspect=0.62)
ok(near(dh3, tall[MID].h) or dh3 <= tall[MID].h + 0.5,
   "높이를 넘지 않는다")

print("── 배치는 영역을 벗어나지 않는다 ──")
r = place_in(lay[TOP], 60, 20, align="left", valign="top", margin=2)
ok(r is not None and lay[TOP].contains(r), "top-left 배치가 영역 안")
r2 = place_in(lay[TOP], 60, 20, align="right", valign="top", margin=2)
ok(r2 is not None and lay[TOP].contains(r2), "top-right 배치가 영역 안")
ok(r2.x1 > r.x1, "right 정렬이 left 보다 오른쪽")
ok(place_in(lay[TOP], 10_000, 20) is None, "너무 크면 None — 밀어내지 않는다")
ok(place_in(lay[TOP], 60, 10_000) is None, "높이가 넘쳐도 None")

print("── 같은 영역에 둘을 놓으면 비켜 쌓는다 ──")
a = place_in(lay[BOTTOM], 80, 24, align="right", valign="middle", margin=2)
b = place_in(lay[BOTTOM], 80, 24, align="right", valign="middle", margin=2,
             used=(a,))
ok(b is not None and lay[BOTTOM].contains(b), "두 번째도 영역 안")
ok(b.x1 <= a.x0 + 0.5, "두 번째가 첫 번째 왼쪽으로 비킨다")
ok(not (b.x1 > a.x0 and a.x1 > b.x0), "겹치지 않는다")

print("── 영역이 없으면 만들지 않는다 ──")
try:
    build_layout(GLASS, dict(rows=(0.5, 0.0, 0.5)))
    ok(False, "mid 없는 선언은 거부한다")
except ValueError:
    ok(True, "mid 없는 선언은 거부한다")

print()
if _fail:
    print(f"실패 {len(_fail)}건")
    sys.exit(1)
print("전부 통과")
