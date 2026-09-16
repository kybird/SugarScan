# lcd_layout 계약 시험 — 영역 모델이 지켜야 하는 것.
#
# 이 시험이 리팩토링의 바닥이다. 합성 결과를 눈으로 보기 전에 여기서 걸린다.
#   python test_lcd_layout.py
import sys

from lcd_layout import (Rect, build_layout, place_in, slot_field,
                        band_quad, BAND_MARGIN,
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
# 계약이 바뀌었다(2026-09-15): 영역을 꽉 채우는 것은 **밴드**(필드+여백)다.
# 필드만 채우면 여백 자리가 안 남아 band_quad 의 clip 이 여백을 깎는다.
_bq_f = band_quad(f, dh)
ok(_bq_f.w >= lay[MID].w * 0.98 or near(_bq_f.h, lay[MID].h, 1.0),
   "밴드가 폭을 꽉 쓰거나 높이에 걸려 멈춘다")
ok(lay[MID].contains(_bq_f), "밴드가 mid 를 벗어나지 않는다")
# 새 계약(2026-09-15): 숫자 높이는 **영역 높이**가 정한다 — 칸 수와 무관하다.
# 실물 액정도 셀 높이는 유리가 정하고 칸 수는 기기 속성이다. 칸이 적으면
# 높이가 아니라 칸 폭이 넓어지거나(비율 한계까지) 필드가 좁아진다.
f2, dh2, _ = slot_field(lay[MID], slots=2, aspect=0.62)
ok(abs(dh2 - dh) <= 1.0, "칸 수가 달라도 숫자 높이는 같다(영역이 정한다)")
# 계약이 바뀌었다(2026-09-15): 폭이 남으면 **자간을 늘려 채운다**. 구판은
# 남는 면을 그냥 뒀는데 그건 "LCD 에 빈 공간 남기는 게 말이 되냐"와 어긋난다.
# 그래서 칸이 적어도 필드는 영역 폭을 쓴다 — 넓어지는 것은 글리프가 아니라
# **칸 사이 간격**이다(숫자 높이는 위에서 확인한 대로 그대로다).
ok(f2.w >= min(f.w, lay[MID].w * 0.9) - 0.5,
   "칸이 적으면 자간이 벌어져 폭을 채운다")
ok(lay[MID].contains(band_quad(f2, dh2)), "칸이 적어도 밴드가 영역 안")
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


print("── 밴드 여백은 규약이 정한다(측정이 아니라) ──")
f4, dh4, _ = slot_field(lay[MID], slots=3, aspect=0.62)
bq = band_quad(f4, dh4)
ok(near(f4.x0 - bq.x0, BAND_MARGIN * dh4), "왼쪽 여백 = margin*digit_h")
ok(near(bq.x1 - f4.x1, BAND_MARGIN * dh4), "오른쪽도 같다")
ok(near(f4.y0 - bq.y0, BAND_MARGIN * dh4), "위도 같다")
ok(near(bq.y1 - f4.y1, BAND_MARGIN * dh4), "아래도 같다")
ok(bq.contains(f4), "밴드가 슬롯 필드를 담는다")

tight = Rect(f4.x0 + 1, f4.y0 + 1, f4.x1 - 1, f4.y1 - 1)   # 유리가 더 좁은 상황
bq2 = band_quad(f4, dh4, clip=tight)
ok(bq2.contains(f4), "유리로 잘라도 내용은 안 자른다")
ok(bq2.x0 >= bq.x0 and bq2.x1 <= bq.x1, "여백만 줄어든다")


print("── 슬롯 필드는 여백 자리까지 남긴다 ──")
f5, dh5, _ = slot_field(lay[MID], slots=3, aspect=0.62)
bq5 = band_quad(f5, dh5)
ok(lay[MID].contains(bq5), "밴드(필드+여백)가 mid 안에 들어간다")
ok(bq5.w >= lay[MID].w * 0.98 or near(bq5.h, lay[MID].h, 1.0),
   "밴드가 mid 폭을 꽉 쓰거나 높이에 걸린다")
ok(near(f5.x0 - bq5.x0, BAND_MARGIN * dh5), "여백이 깎이지 않는다")

print()
if _fail:
    print(f"실패 {len(_fail)}건")
    sys.exit(1)
print("전부 통과")
