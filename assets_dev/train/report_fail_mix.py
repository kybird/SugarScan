# 부 지표 — **실패의 구성**. 전체 포함률이 같아도 구성이 다를 수 있다.
#
# 앞선 회차에서 이 표를 즉석으로 냈다. CLAUDE.md "수치를 인용하기 전에" 규칙이
# 즉석 스크립트의 값을 금지하므로 자를 여기에 고정한다.
#
# 분류는 **배포 상자**(build_cache_v2.BOX_MARGIN 적용)와 **숫자 칸**
# (사람 밴드 라벨에서 lcd_layout.BAND_MARGIN 규약으로 역산)의 관계로 한다:
#   통과   숫자 칸을 사방으로 담았다
#   일부만 겹치기는 하는데 한 변 이상이 모자라다 (잘림)
#   딴 데  숫자 칸과 **겹치지 않는다** (버튼·로고 등 다른 곳을 잡았다)
#   미검출 상자가 안 나왔다
#
# "딴 데"가 이 회차의 표적이다. 1~2% 구간이라 시드 8개로는 잘 안 갈린다 —
# 그래서 **시드를 무작위변수로 넣은 붓스트랩 구간**을 함께 낸다. 시드 하나의
# 값을 설계 상수로 쓰다가 데인 적이 있다(2026-09-20 §16).
import argparse
import json
from pathlib import Path

import numpy as np

from lcd_layout import BAND_MARGIN
from build_cache_v2 import BOX_MARGIN

HERE = Path(__file__).resolve().parent
K = BAND_MARGIN / (1.0 + 2.0 * BAND_MARGIN)
CLASSES = ("통과", "일부만", "딴 데", "미검출")
PFX = "roboflow_"


def rows(p):
    p = Path(p)
    if not p.exists():
        return []
    return [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines()
            if l.strip()]


def load_foreign(p):
    """이물 태그 {id: tag} — 사람 전용 파일(rf_foreign_tags.jsonl)을 읽는다.

    헤더(_meta 행)는 규약이므로 무시한다. 이 도구는 태그를 **읽기만** 한다 —
    태그 값을 만드는 것은 사람 몫이다(카드 '로보플로우 이물층 태그 규약').
    """
    if not p or not Path(p).exists():
        return {}
    out = {}
    for l in Path(p).read_text(encoding="utf-8").splitlines():
        if not l.strip():
            continue
        j = json.loads(l)
        if "_meta" in j:
            continue
        if "id" in j and "tag" in j:
            out[j["id"]] = j["tag"]
    return out


def digit_cell(g):
    m = (g[3] - g[1]) * K
    return [g[0] + m, g[1] + m, g[2] - m, g[3] - m]


def pad(q):
    w, h = q[2] - q[0], q[3] - q[1]
    ml, mr, mt, mb = BOX_MARGIN
    return [q[0] - w * ml, q[1] - h * mt, q[2] + w * mr, q[3] + h * mb]


def classify(r):
    """한 장을 CLASSES 중 하나로."""
    if not r.get("det"):
        return "미검출"
    if not r.get("gt"):
        return None
    d = digit_cell(r["gt"])
    e = pad(r["pred"])
    if e[0] <= d[0] and e[1] <= d[1] and e[2] >= d[2] and e[3] >= d[3]:
        return "통과"
    ix = min(e[2], d[2]) - max(e[0], d[0])
    iy = min(e[3], d[3]) - max(e[1], d[1])
    return "일부만" if (ix > 0 and iy > 0) else "딴 데"


def per_seed(paths, keep, drop=frozenset(), gt_override=None):
    """시드마다 {장 id: 분류}. drop 은 이물 태그 장(제외 표용).

    gt_override({id: [x0,y0,x1,y1]})를 주면 그 장의 정답을 그 값으로 바꿔
    채점한다 — 사람이 그린 우리 규약 라벨(rf_band_boxes.jsonl)로 READING 과
    나란히 채점하기 위한 것(§20.5 '규약 차이 vs 모델 결함')."""
    out = []
    for p in paths:
        rs = rows(p)
        if not rs:
            continue
        m = {}
        for r in rs:
            if keep is not None and r["id"] not in keep:
                continue
            if r["id"] in drop:
                continue
            if gt_override is not None and r["id"] in gt_override:
                r = dict(r, gt=gt_override[r["id"]])
            c = classify(r)
            if c:
                m[r["id"]] = c
        if m:
            out.append(m)
    return out


def share(seeds, cls):
    """시드별 해당 분류 비율(%) 배열."""
    return np.array([100.0 * sum(v == cls for v in m.values()) / len(m)
                     for m in seeds])


def boot_diff(a_seeds, b_seeds, cls, n=4000, rng=None):
    """b - a 차이의 붓스트랩 구간. **시드와 장을 둘 다 다시 뽑는다.**

    시드 하나짜리 차이를 구간 없이 인용하지 않기 위한 장치다. 장은 두 팔에
    공통인 id 집합에서 같은 표본을 쓴다(짝 유지) — 팔마다 다른 장을 뽑으면
    코퍼스 변동이 개입 효과로 둔갑한다.
    """
    rng = rng or np.random.default_rng(12345)
    ids = sorted(set(a_seeds[0]) & set(b_seeds[0]))
    ids = np.array(ids, dtype=object)
    na, nb = len(a_seeds), len(b_seeds)
    out = np.empty(n)
    for k in range(n):
        pick = rng.integers(0, len(ids), len(ids))
        sub = ids[pick]
        sa = rng.integers(0, na, na)
        sb = rng.integers(0, nb, nb)
        fa = np.mean([100.0 * np.mean([a_seeds[i][x] == cls for x in sub])
                      for i in sa])
        fb = np.mean([100.0 * np.mean([b_seeds[i][x] == cls for x in sub])
                      for i in sb])
        out[k] = fb - fa
    return out



def anatomy(name, ss_paths, keep):
    """**일부만**으로 떨어진 장들의 해부 — 어느 변이 얼마나 모자란가.

    처방이 갈리기 때문에 변을 나눈다(diag_band_sides.py 와 같은 취지지만
    저기는 밴드 라벨 기준이고 여기는 **숫자 칸** 기준이다 — 주 지표와 같은
    자를 써야 실패를 설명한 것이 된다).

    부호 규약: +면 배포 상자가 숫자 칸보다 **넓다**(여유), -면 모자란다.
    정규화는 숫자 칸의 해당 변 길이로 한다.
    """
    S = {"왼": [], "위": [], "오른": [], "아래": []}
    nshort, worst, arear = [], [], []
    for p in ss_paths:
        for r in rows(p):
            if keep is not None and r["id"] not in keep:
                continue
            if classify(r) != "일부만":
                continue
            d = digit_cell(r["gt"])
            e = pad(r["pred"])
            dw = max(1.0, d[2] - d[0]); dh = max(1.0, d[3] - d[1])
            v = {"왼": (d[0] - e[0]) / dw, "위": (d[1] - e[1]) / dh,
                 "오른": (e[2] - d[2]) / dw, "아래": (e[3] - d[3]) / dh}
            for k in S:
                S[k].append(v[k])
            nshort.append(sum(1 for x in v.values() if x < 0))
            worst.append(min(v.values()))
            arear.append(r.get("area_ratio", float("nan")))
    if not nshort:
        print(f"  [{name}] 일부만 없음")
        return
    print(f"  [{name}] n={len(nshort)}")
    cells = "".join(f"{np.median(S[k]):>+9.3f}" for k in ("왼", "위", "오른", "아래"))
    print(f"    변별 여유(중앙){cells}")
    frac = {k: 100.0 * np.mean(np.asarray(S[k]) < 0) for k in S}
    cells = "".join(f"{frac[k]:>8.0f}%" for k in ("왼", "위", "오른", "아래"))
    print(f"    그 변이 모자란 비율{cells}")
    print(f"    모자란 변 수 평균 {np.mean(nshort):.2f}개 · "
          f"최악 변 중앙 {np.median(worst):+.3f} · p90 {np.percentile(worst, 10):+.3f}")
    print(f"    이 장들의 면적비 중앙 {np.nanmedian(arear):.2f}")



def sweep(name, paths, keep, grows, tau):
    """**추론 때 배포 상자를 더 부풀리면** 얼마나 회수되고 면적은 얼마를 무는가.

    학습을 다시 걸기 전에 먼저 본다. 회수 폭이 작으면 --grow 로 학습을 다시
    굽는 5시간이 헛돈이고, 크면 얼마를 걸어야 하는지 눈금이 나온다.
    부풀림은 build_cache_v2.BOX_MARGIN 을 **얹은 뒤**에 사방으로 더한다 —
    배포 경로가 실제로 그 순서이기 때문이다. 단위는 상자 높이 비율로
    train_band.py --grow 와 맞춘다.
    """
    print(f"  [{name}]")
    print(f"    {'부풀림':<8}{'담음':>9}{'∧면적<=' + str(tau):>12}{'면적비 중앙':>12}")
    for g in grows:
        dep, gate, ars = [], [], []
        for p2 in paths:
            for r in rows(p2):
                if keep is not None and r["id"] not in keep:
                    continue
                if not r.get("det") or not r.get("gt"):
                    dep.append(False); gate.append(False)
                    continue
                d = digit_cell(r["gt"])
                e = pad(r["pred"])
                m = (e[3] - e[1]) * g
                e = [e[0] - m, e[1] - m, e[2] + m, e[3] + m]
                ga = max(1.0, (r["gt"][2]-r["gt"][0]) * (r["gt"][3]-r["gt"][1]))
                ar = max(0.0, e[2]-e[0]) * max(0.0, e[3]-e[1]) / ga
                ok = (e[0] <= d[0] and e[1] <= d[1]
                      and e[2] >= d[2] and e[3] >= d[3])
                dep.append(ok); gate.append(ok and ar <= tau); ars.append(ar)
        print(f"    {g:<8.2f}{100*np.mean(dep):>8.1f}%{100*np.mean(gate):>11.1f}%"
              f"{np.median(ars):>12.2f}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--arms", default="aunder:_diag/fix2,atone:_diag/tone",
                    help="이름:디렉터리 쉼표 구분. 첫 팔이 대조군이다")
    ap.add_argument("--seeds", default="0,1,2,3,4,5,6,7")
    ap.add_argument("--split", default="dev", choices=["dev", "test", "all"])
    ap.add_argument("--corpus", default="roboflow", choices=["roboflow", "datumo"],
                    help="datumo 는 라벨 주체가 다르다 — 절대값을 맞대지 말 것")
    ap.add_argument("--boot", type=int, default=4000)
    ap.add_argument("--sweep", default="",
                    help="추론 부풀림 스윕, 예: 0,0.05,0.1,0.15,0.2,0.3")
    ap.add_argument("--tau", type=float, default=2.0)
    ap.add_argument("--foreign", default="rf_foreign_tags.jsonl",
                    help="이물 태그 파일(사람 전용, 헤더에 규약). 태그된 장이 "
                         "모집단에 있으면 이물 포함/제외 두 표를 나란히 낸다. "
                         "'' 로 끈다.")
    ap.add_argument("--gt", default="reading", choices=["reading", "rfband"],
                    help="rfband: 사람이 그린 우리 규약 라벨(rf_band_boxes.jsonl)"
                         "이 있는 장으로 측정을 좁히고, 같은 장에서 READING "
                         "기준과 우리 규약 기준을 나란히 낸다(§20.5).")
    ap.add_argument("--stratum", default="", choices=["", "rand", "fail"],
                    help="rf_label_queue.json 의 층으로 좁힌다(rand=실패 제외 "
                         "무작위, fail='일부만' 2시드 이상 실패장). 층 편향을 "
                         "분해할 때 쓴다 — rand 성적은 dev 전체 대표가 아니다.")
    ap.add_argument("--anatomy", action="store_true",
                    help="일부만으로 떨어진 장의 변별 해부를 함께 낸다")
    a = ap.parse_args()
    seeds = [int(x) for x in a.seeds.split(",")]
    global PFX
    PFX = "roboflow_" if a.corpus == "roboflow" else ""

    keep = None
    sp = HERE / "rf_split.json"
    if a.corpus == "datumo":
        a.split = "all"   # rf_split 은 Roboflow 전용이다
    if a.split != "all" and sp.exists():
        keep = set(json.loads(sp.read_text(encoding="utf-8"))[a.split])

    # 이물 태그(사람이 채운 것만). 도구는 읽기 전용이다.
    foreign = load_foreign((HERE / a.foreign) if a.foreign else "")

    # 우리 규약 사람 라벨 — §20.5 '규약 차이 vs 모델 결함' 병렬 채점용.
    ours = {}
    if a.gt == "rfband":
        fb = HERE / "rf_band_boxes.jsonl"
        for l in rows(fb):
            if "id" in l and l.get("quad"):
                q = l["quad"]
                ours[l["id"]] = [q[0][0], q[0][1], q[2][0], q[2][1]]
        if not ours:
            raise SystemExit("rf_band_boxes.jsonl 에 상자 라벨이 없다")
        keep = (set(ours) if keep is None else keep & set(ours))
    if a.stratum:
        q = json.loads((HERE / "rf_label_queue.json").read_text(
            encoding="utf-8"))["items"]
        ids = {i["id"] for i in q if i["stratum"] == a.stratum}
        keep = ids if keep is None else keep & ids

    label = {"dev": "Roboflow 개발 586",
             "test": "Roboflow 봉인 시험 687",
             "all": ("Datumo 272" if a.corpus == "datumo"
                     else "Roboflow 전량")}[a.split]
    print(f"실패 구성 — {label} · 배포 상자 대 숫자 칸")
    if foreign:
        from collections import Counter
        print(f"  이물 태그 {len(foreign)}건 "
              f"({', '.join(f'{k} {v}' for k, v in sorted(Counter(foreign.values()).items()))}) "
              f"— 포함/제외 두 표를 나란히 낸다")
    print(f"  {'':<18}" + "".join(f"{c:>10}" for c in CLASSES) + f"{'n':>7}{'시드':>6}")

    def arm_row(name, ss):
        cells = ""
        for c in CLASSES:
            v = share(ss, c)
            cells += f"{v.mean():>7.2f}±{v.std(ddof=1) if len(v) > 1 else 0:<2.1f}"
        print(f"  {name:<18}{cells}{len(ss[0]):>7}{len(ss):>6}")

    arms = []
    for spec in a.arms.split(","):
        name, d = spec.split(":")
        paths = [HERE / d / (PFX + f"{name}_s{s}.jsonl") for s in seeds]
        ss = per_seed(paths, keep)
        if not ss:
            print(f"  [{name}] 결과 없음")
            continue
        arms.append((name, ss))
        arm_row(name, ss)
        if ours:
            # §20.5 병렬 채점 — 같은 장·같은 시드, 정답만 우리 규약으로.
            ss_o = per_seed(paths, keep, gt_override=ours)
            arm_row(name + " gt=우리규약", ss_o)
            arms.append((name + "/ours", ss_o))
        # 이물 제외 표 — 태그된 장을 뺀 같은 자. 게이트 수치가 이물 때문에
        # 실제보다 나쁘게 왜곡되는지를 이 표에서 가른다(카드 AC#2).
        ssx = per_seed(paths, keep, drop=set(foreign)) if foreign else []
        if ssx and ssx[0].keys() != ss[0].keys():
            arm_row(name + "ˣ이물제외", ssx)

    if a.anatomy:
        print()
        print("  **일부만**의 해부 — +면 배포 상자가 숫자 칸보다 넓다")
        for spec in a.arms.split(","):
            nm, dd = spec.split(":")
            anatomy(nm,
                    [HERE / dd / (PFX + f"{nm}_s{s}.jsonl") for s in seeds],
                    keep)

    if a.sweep:
        print()
        print("  추론 부풀림 스윕 — 학습을 다시 걸기 전에 본다")
        gs = [float(x) for x in a.sweep.split(",")]
        for spec in a.arms.split(","):
            nm, dd = spec.split(":")
            sweep(nm, [HERE / dd / (PFX + f"{nm}_s{s}.jsonl") for s in seeds],
                  keep, gs, a.tau)

    if len(arms) < 2:
        return
    base = arms[0]
    print(f"\n  차이 (기준 {base[0]}) — 붓스트랩 {a.boot}회, **시드와 장을 함께 재추첨**")
    for name, ss in arms[1:]:
        print(f"  [{name}]")
        for c in CLASSES:
            d = boot_diff(base[1], ss, c, a.boot)
            lo, hi = np.percentile(d, [2.5, 97.5])
            sig = "" if lo <= 0 <= hi else "  *"
            print(f"    {c:<8}{d.mean():>+7.2f}pt  95% [{lo:+.2f}, {hi:+.2f}]{sig}")
    print("\n  * = 구간이 0 을 지나지 않음. 표시가 없으면 **유의하지 않음**이다 —")
    print("  평균이 움직였어도 그렇게 적는다.")


if __name__ == "__main__":
    main()
