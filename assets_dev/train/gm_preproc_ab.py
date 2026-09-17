# GM 검출 전처리 A/B — 여러 쿼드 출력을 같은 잣대로 나란히 놓는다.
#
# 잣대는 **사람이 그린 화면 라벨**(screen_boxes.jsonl, 411행, source=human)이다.
# 검출기 출력끼리만 비교하면 "달라졌다"는 알 수 있어도 "나아졌다"는 모른다.
#
#   경고(docs/DONE.md GM ft3 승격 절): 이 대조 표본은 모델의 학습 데이터와
#   겹친다. 셋 중 무엇을 쓸지 고르는 데는 충분하지만 **검출기 성능 수치로
#   인용하지 말 것.**
#
# 층은 하나만 쓴다 — 가로 화면(_diag/wide_all/wide_ids.json, 51장). 이 작업의
# 동기가 거기다. 가로 화면의 '접힘/미검출' 판정은 diag_wide_gm.py 가 이미
# 자를 갖고 있으므로 여기서 다시 정의하지 않고 그 스크립트를 따로 부른다.
#
# 사용:
#   python gm_preproc_ab.py --arm 운영=gmscreen_quads.jsonl \
#       --arm stretch=_diag/preproc_ab/stretch.jsonl \
#       --arm letterbox=_diag/preproc_ab/letterbox.jsonl \
#       --arm yolox=_diag/preproc_ab/yolox.jsonl \
#       --targets glucose_batch1/1046,glucose_batch1/1826,glucose_batch1/2198
import argparse
import json
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
LABELS = HERE.parent / "upstream" / "datumo" / "labels.jsonl"
HUMAN = HERE / "screen_boxes.jsonl"
WIDE = HERE / "_diag" / "wide_all" / "wide_ids.json"
# 사진이 회전돼 화면이 세로로 보이는 장. diag_wide_gm.py 와 같은 집합을 쓴다.
ROTATED = {"glucose_batch1/1564", "glucose_batch1/1565"}


def rect(quad):
    q = np.asarray(quad, float)
    return [q[:, 0].min(), q[:, 1].min(), q[:, 0].max(), q[:, 1].max()]


def iou(a, b):
    x0, y0 = max(a[0], b[0]), max(a[1], b[1])
    x1, y1 = min(a[2], b[2]), min(a[3], b[3])
    inter = max(0.0, x1 - x0) * max(0.0, y1 - y0)
    ua = ((a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter)
    return inter / ua if ua > 0 else 0.0


def load_quads(p):
    out = {}
    for l in Path(p).read_text(encoding="utf-8").splitlines():
        if l.strip():
            j = json.loads(l)
            out[j["id"]] = rect(j["quad"])
    return out


def load_human():
    out = {}
    for l in HUMAN.read_text(encoding="utf-8").splitlines():
        if l.strip():
            j = json.loads(l)
            if j.get("source") == "human" and j.get("quad"):
                out[j["id"]] = rect(j["quad"])
    return out


def table(name, arms, ids, human, corpus_n):
    print(f"\n── {name} (대조 라벨 n={len(ids)}) " + "─" * 30)
    print(f"{'팔':<12}{'검출/전체':>14}{'IoU중앙':>9}{'>=0.9':>8}"
          f"{'>=0.75':>8}{'<0.3':>7}{'넓이비중앙':>11}")
    for label, q in arms.items():
        have = [i for i in ids if i in q]
        v = np.array([iou(q[i], human[i]) for i in have]) if have else np.zeros(0)
        ar = np.array([((q[i][2] - q[i][0]) * (q[i][3] - q[i][1])) /
                       ((human[i][2] - human[i][0]) * (human[i][3] - human[i][1]))
                       for i in have]) if have else np.zeros(0)
        det = f"{len(have)}/{len(ids)}"
        if len(v) == 0:
            print(f"{label:<12}{det:>14}{'-':>9}{'-':>8}{'-':>8}{'-':>7}{'-':>11}")
            continue
        print(f"{label:<12}{det:>14}{np.median(v):>9.3f}"
              f"{100*(v >= .9).mean():>7.1f}%{100*(v >= .75).mean():>7.1f}%"
              f"{100*(v < .3).mean():>6.1f}%{np.median(ar):>11.3f}")
    print(f"  전량 검출률 (코퍼스 {corpus_n}장): " + " · ".join(
        f"{k} {len(v)}/{corpus_n} ({100*len(v)/corpus_n:.1f}%)"
        for k, v in arms.items()))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm", action="append", required=True,
                    help="이름=경로.jsonl 을 여러 번")
    ap.add_argument("--targets", default="",
                    help="장 단위로 볼 id 목록(쉼표)")
    ap.add_argument("--wide-detail", action="store_true",
                    help="가로 층을 diag_wide_gm 의 판정으로 장 단위 비교")
    args = ap.parse_args()

    arms = {}
    for spec in args.arm:
        name, _, path = spec.partition("=")
        arms[name] = load_quads(path)
    human = load_human()
    corpus_n = sum(1 for l in LABELS.read_text(encoding="utf-8").splitlines()
                   if l.strip())
    wide = set(json.loads(WIDE.read_text(encoding="utf-8"))) - ROTATED

    print(f"사람 화면 라벨 {len(human)}장 (screen_boxes.jsonl, source=human)")
    print("주의: 이 대조 표본은 모델 학습 데이터와 겹친다 — 팔 사이 선택에는"
          " 쓰되 검출기 성능 수치로 인용하지 말 것(docs/DONE.md GM ft3 승격 절).")

    all_ids = sorted(human)
    table("전체", arms, all_ids, human, corpus_n)
    w = sorted(i for i in all_ids if i in wide)
    table(f"가로 화면 층 (wide_all {len(wide)}장 중 사람 라벨 있는 것)",
          arms, w, human, corpus_n)
    p = sorted(i for i in all_ids if i not in wide)
    table("세로 화면 층", arms, p, human, corpus_n)

    if args.wide_detail:
        # 판정 규칙은 diag_wide_gm 에 하나만 둔다 — 여기서 다시 쓰지 않는다.
        import diag_wide_gm as W
        raw = {name: {j["id"]: j for j in
                      (json.loads(l) for l in Path(p).read_text(
                          encoding="utf-8").splitlines() if l.strip())}
               for name, p in ((s.partition("=")[0], s.partition("=")[2])
                               for s in args.arm)}
        cls = {}
        for name, q in raw.items():
            rows, ok, miss, fold = W.classify(q)
            cls[name] = dict((i, why) for i, why, _, _ in rows)
            print(f"\n[{name}] 가로 {ok+miss+fold}장: OK {ok} · 미검출 {miss} "
                  f"· 접힘 {fold} → GM 실패 {miss+fold}")
        # 개수(문턱 넘김)가 아니라 w/h 자체의 분포도 같이 낸다. 문턱 세기는
        # 연속량의 이동을 통째로 삼킨다 — 두 숫자를 나란히 놓아야 보인다.
        print(f"\n  가로 층 w/h 분포(검출된 장만, 문턱 무관):")
        for name, q in raw.items():
            rows, *_ = W.classify(q)
            ar = np.array([a for _, _, _, a in rows if a is not None])
            print(f"    {name:<12} n={len(ar):<4} p25={np.percentile(ar,25):.2f}"
                  f" p50={np.median(ar):.2f} p75={np.percentile(ar,75):.2f}"
                  f" · w/h>=1.2 {int((ar>=1.2).sum())}장")

        names = list(cls)
        changed = [i for i in W.horiz_ids()
                   if len({cls[n][i].split()[0] for n in names}) > 1]
        print(f"\n── 가로 층 장 단위 — 판정 부류가 갈린 {len(changed)}장 "
              + "─" * 20)
        print(f"{'id':<24}" + "".join(f"{n:<20}" for n in names))
        for i in changed:
            print(f"{i:<24}" + "".join(f"{cls[n][i]:<20}" for n in names))
        print("  접힘 w/h 값 자체는 좋아졌는데 1.2 문턱을 못 넘어 개수가 안 "
              "움직이는 장이 많다. 개수만 보면 '변화 없음'으로 읽힌다.")

    if args.targets:
        tg = [t.strip() for t in args.targets.split(",") if t.strip()]
        print(f"\n── 장 단위 ({len(tg)}장) " + "─" * 40)
        print(f"{'id':<26}" + "".join(f"{k:>22}" for k in arms))
        for t in tg:
            cells = []
            for k, q in arms.items():
                if t not in q:
                    cells.append("미검출")
                elif t in human:
                    cells.append(f"IoU {iou(q[t], human[t]):.3f}")
                else:
                    b = q[t]
                    cells.append(f"검출 w/h {(b[2]-b[0])/(b[3]-b[1]):.2f}")
            print(f"{t:<26}" + "".join(f"{c:>22}" for c in cells))
        print("  (사람 화면 라벨이 없는 장은 IoU 대신 상자 종횡비를 적는다)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
