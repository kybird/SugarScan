# holdout 예측 오류 분석 — 4개 레버(렌더러 실화면화/실데이터/모델확대/시간줄 마스킹)
# 방향 결정용 수치 근거. 학습·추론 없음, json/npz 읽기만.
# 산출: 콘솔 리포트 (predictions_breakdown.txt 에도 저장)
import json
import math
from collections import Counter
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
PREDS = HERE / "reader_preds.json"
LABELS = HERE / ".." / ".." / "assets_dev" / "upstream" / "datumo" / "labels.jsonl"
CACHE = HERE / "data_cache_v2.npz"
QUADS = HERE / "gmscreen_quads.jsonl"
OUT = HERE / "predictions_breakdown.txt"

lines = []


def say(s=""):
    print(s)
    lines.append(s)


# ---- 1. 데이터 적재 ----
preds = json.loads(PREADS.read_text(encoding="utf-8")) if (PREADS := PREDS).exists() else {}
meta = {}
for ln in LABELS.read_text(encoding="utf-8").splitlines():
    if not ln.strip():
        continue
    d = json.loads(ln)
    meta[d["id"]] = (int(d["reading"]), str(d.get("display_time", "")))

say(f"== holdout 예측 분석 (reader_preds.json {len(preds)}행) ==")

rows = []  # (id, gt, pred, time)
miss_gt = 0
for cid, (p, g_art) in preds.items():
    if cid not in meta:
        continue
    gt, t = meta[cid]
    rows.append((cid, str(gt), p, t))
say(f"labels.jsonl 매칭: {len(rows)}행 (미매칭 {len(preds) - len(rows)})")

n = len(rows)
exact = sum(1 for _, g, p, _ in rows if p == g)
say(f"exact: {exact}/{n} = {100 * exact / max(n, 1):.1f}%")

# ---- 2. 오류 유형 분해 ----
empty = [(c, g, p, t) for c, g, p, t in rows if p == ""]
lenmis = [(c, g, p, t) for c, g, p, t in rows if p != g and len(p) != len(g)]
sub_only = [(c, g, p, t) for c, g, p, t in rows
            if p != g and len(p) < len(g) and g.endswith(p) and p]
say("")
say(f"빈 예측(아무것도 디코드 못함): {len(empty)} ({100 * len(empty) / n:.1f}%)")
say(f"길이 불일치 오류: {len(lenmis)} ({100 * len(lenmis) / n:.1f}%)")
say(f"  └ 길이짧은 접미 오류(GT 접두=예측, 자리 탈락): {len(sub_only)}")
samediff = [(c, g, p, t) for c, g, p, t in rows if p != g and len(p) == len(g)]
say(f"같은 길이 오류(글자 혼동): {len(samediff)} ({100 * len(samediff) / n:.1f}%)")

# ---- 3. '1'·'0' 쏠림 정량 ----
say("")
say("== 예측 숫자 분포 vs GT 숫자 분포 ==")
pred_dig = Counter()
gt_dig = Counter()
for _, g, p, _ in rows:
    gt_dig.update(g)
    pred_dig.update(p)
order = "0123456789"
say("숫자 | 예측빈도 | GT빈도 | 예측/GT비율")
for d in order:
    pd_, gd = pred_dig.get(d, 0), gt_dig.get(d, 0)
    ratio = (pd_ / pd_total * 100) if (pd_total := sum(pred_dig.values())) else 0
    gr = gd / max(1, sum(gt_dig.values())) * 100
    say(f"  {d} | {pd_:4d} ({ratio:4.1f}%) | {gd:4d} ({gr:4.1f}%) | {pd_ / max(1, gd):.2f}x")

only01_pred = sum(1 for _, g, p, _ in rows if p and set(p) <= {"0", "1"})
only01_gt = sum(1 for _, g, p, _ in rows if set(g) <= {"0", "1"})
one_pred = sum(1 for _, g, p, _ in rows if "1" in p)
one_gt = sum(1 for _, g, p, _ in rows if "1" in g)
say(f"예측이 0/1만으로 구성: {only01_pred}/{n} ({100 * only01_pred / n:.1f}%) — GT는 {only01_gt}/{n}")
say(f"'1' 포함 예측: {one_pred}/{n} ({100 * one_pred / n:.1f}%) — GT는 {one_gt}/{n} ({100 * one_gt / n:.1f}%)")

# 첫 글자 분포 (시간 줄 '1X:XX' 가설 — 시간 첫 글자는 0~2, 특히 1이 많음)
first_pred = Counter(p[0] for _, g, p, _ in rows if p)
first_gt = Counter(g[0] for _, g, p, _ in rows)
say("첫 글자 | 예측 | GT")
for d in order:
    say(f"  {d} | {first_pred.get(d, 0):4d} | {first_gt.get(d, 0):4d}")

# ---- 4. 시간 줄 간섭 검증: 예측이 display_time 자릿수의 부분문자열? ----
say("")
say("== 시간 줄 간섭 검증 (예측 = 화면 시각 HHMM의 부분문자열?) ==")
def time_digits(t):
    ds = "".join(ch for ch in t if ch.isdigit())
    return ds[:4] if len(ds) >= 4 else ds  # HHMM

tm_hit_all, tm_hit_miss = 0, 0
miss_n = 0
tm_examples = []
for c, g, p, t in rows:
    td = time_digits(t)
    hit = bool(p) and len(p) >= 2 and p in td
    if hit:
        tm_hit_all += 1
    if p != g:
        miss_n += 1
        if hit:
            tm_hit_miss += 1
            if len(tm_examples) < 12:
                tm_examples.append((c, g, p, t, td))
say(f"오류 {miss_n}건 중 예측이 시각(HHMM) 부분문자열: {tm_hit_miss}건 "
    f"({100 * tm_hit_miss / max(1, miss_n):.1f}%)")
for c, g, p, t, td in tm_examples:
    say(f"  {c}: GT {g:>4} pred {p!r}  시각 {t[:8]} (digits {td})")

# 시각별 시(hour) 대역과 오류 상관 — 오전 10~12시(1X) 사진이 오류가 많나?
say("")
say("== 시(hour) 대역별 정확도 ==")
band = {}
for c, g, p, t in rows:
    td = time_digits(t)
    h = td[:2] if len(td) >= 2 else "??"
    b = h if h in ("10", "11", "12") else ("0" + h[0] if h.startswith("0") else "기타")
    e = band.setdefault(b, [0, 0])
    e[0] += 1
    e[1] += (p == g)
for b in sorted(band):
    tot, ok = band[b]
    say(f"  hour {b:>2}: {ok}/{tot} = {100 * ok / tot:.1f}%")

# ---- 5. GT 길이별 정확도 ----
say("")
say("== GT 자릿수별 정확도 ==")
bylen = {}
for c, g, p, t in rows:
    e = bylen.setdefault(len(g), [0, 0])
    e[0] += 1
    e[1] += (p == g)
for L in sorted(bylen):
    tot, ok = bylen[L]
    say(f"  {L}자리: {ok}/{tot} = {100 * ok / tot:.1f}%")

# ---- 6. GM 쿼드 기하 — 렌더러 실화면화(±90/180·와이드) 근거 ----
say("")
say("== gmscreen_quads.jsonl 기하 (2,007 검출분) ==")
angles, aspects = [], []
qline_fail = 0
for ln in QUADS.read_text(encoding="utf-8").splitlines():
    try:
        d = json.loads(ln)
        q = d["quad"]
    except Exception:
        qline_fail += 1
        continue
    (x0, y0), (x1, y1) = q[0], q[1]
    (x3, y3) = q[3]
    ang = math.degrees(math.atan2(y1 - y0, x1 - x0))  # 상변 방향
    h1 = math.hypot(x3 - x0, y3 - y0)
    w1 = math.hypot(x1 - x0, y1 - y0)
    if w1 < 5 or h1 < 5:
        continue
    angles.append(ang)
    aspects.append(w1 / h1)
angles_a = np.abs(np.array(angles))
# 상변이 세로(±60~120°) = 기기가 눕혀 찍힘 → 워프 rect에서 숫자가 90° 회전으로 등장
vert = np.sum((angles_a > 60) & (angles_a < 120))
flat = np.sum(angles_a <= 30)
flat180 = np.sum(angles_a >= 150)
asp = np.array(aspects)
wide = np.sum(asp > 3.0)
tall = np.sum(asp < 0.8)
say(f"상변 수평(±30°): {flat} / 상변 수평-뒤집힘(150°+): {flat180} / "
    f"상변 세로(60~120°, 숫자 90° 회전 등장): {vert} / 전체 {len(angles)}")
say(f"  → 세로 상변 비율 {100 * vert / len(angles):.1f}%")
say(f"종횡비: wide(>3.0) {wide} ({100 * wide / len(asp):.1f}%) / "
    f"tall(<0.8) {tall} ({100 * tall / len(asp):.1f}%) / "
    f"중앙값 {np.median(asp):.2f} / p90 {np.percentile(asp, 90):.2f}")

# holdout 903에 한정하면? (캐시 id와 교집합)
cache = np.load(str(CACHE))
hold_ids = [str(x) for x in cache["real_holdout_ids"]]
hold_set = set(hold_ids)
va, vv, vt = [], 0, 0
for ln in QUADS.read_text(encoding="utf-8").splitlines():
    try:
        d = json.loads(ln)
        if d.get("id") not in hold_set:
            continue
        q = d["quad"]
        ang = abs(math.degrees(math.atan2(q[1][1] - q[0][1], q[1][0] - q[0][0])))
        w1 = math.hypot(q[1][0] - q[0][0], q[1][1] - q[0][1])
        h1 = math.hypot(q[3][0] - q[0][0], q[3][1] - q[0][1])
        if w1 < 5 or h1 < 5:
            continue
        va.append(w1 / h1)
        if 60 < ang < 120:
            vv += 1
        vt += 1
    except Exception:
        pass
if vt:
    say(f"holdout 903 한정: 세로 상변 {vv}/{vt} = {100 * vv / vt:.1f}%")
    asp2 = np.array(va)
    say(f"holdout 종횡비 중앙값 {np.median(asp2):.2f} · wide(>3) {np.sum(asp2 > 3)} ({100 * np.mean(asp2 > 3):.1f}%)")

# 캐시 실사진 rect 자체의 잉크 방향은 몽타주(diag_holdout_sheet.png)로 눈확인 별도.

say("")
say("== 샘플 오류 20건 ==")
shown = 0
for c, g, p, t in rows:
    if p != g and shown < 20:
        say(f"  {c}: GT {g:>4} pred {p!r}  시각 {t[:8]}")
        shown += 1

OUT.write_text("\n".join(lines), encoding="utf-8")
say("")
say(f"저장: {OUT}")
