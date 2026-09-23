# 세트-C 끝단 보고 자 — review-arbiter 판정(2026-09-22 무인)의 시행 계약.
#
# 조인: 검출 상자 jsonl(_diag/tone2te/ve_*.jsonl — det·pass·area_ratio) ×
# 리더 덤프(_diag/reader_dump/VE_*.jsonl — ok). 분모는 VE 1,000 전량(미검출=실패).
#
# 분해(서로 소, 합=1000):
#   성공        ok ∧ det        — 끝단(값 완전일치)
#   미검출      ¬det
#   잘림·비포함 det ∧ ¬pass ∧ ¬ok
#   담고도 오독 pass ∧ ¬ok
# 게이트(사전 결정 — 결과를 보고 고치지 않는다):
#   tone2te 상자 s0~3 × 리더 B 의 성공 **최저 시드** ≥ 950/1000
#   유효조건: 같은 실행의 B_gt 성공 ≥ 980/1000
#   배포 스택(atone × B)은 게이트 밖 참조 수치로 기록한다.
import json
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
BOX = HERE / "_diag" / "tone2te"
RD = HERE / "_diag" / "reader_dump"


def load(p):
    return {r["file_name"]: r for r in
            (json.loads(l) for l in
             Path(p).read_text(encoding="utf-8").splitlines() if l.strip())}


def row(name, boxes, readers):
    """boxes: 상자원 이름(상자 jsonl 접두), readers: 리더 덤프 상자원 이름."""
    bx = load(BOX / f"ve_{boxes}.jsonl")
    rd = load(RD / f"VE_B_{readers}.jsonl")
    files = sorted(bx)
    assert set(files) == set(rd), f"짝 불일치: {boxes} × {readers}"
    ok = np.array([rd[f]["ok"] for f in files])
    det = np.array([bx[f]["det"] for f in files])
    pas = np.array([bx[f]["pass"] for f in files])
    ar = {f: bx[f]["area_ratio"] for f in files}
    succ = ok & det
    miss = ~det
    cut = det & ~pas & ~ok
    hold = pas & ~ok
    assert succ.sum() + miss.sum() + cut.sum() + hold.sum() == len(files)

    cut_ar = [ar[f] for f, k in zip(files, cut) if k]
    hold_ar = [ar[f] for f, k in zip(files, hold) if k]

    def fmt(v):
        return f"{np.percentile(v, 50):.1f}/{np.percentile(v, 90):.1f}" if v else "  -  "

    print(f"  {name:<18} 성공 {succ.sum():4d} ({100*succ.mean():5.2f}%)  "
          f"미검출 {miss.sum():3d}  잘림 {cut.sum():3d}  담고도오독 {hold.sum():3d}  "
          f"잘림과대 {fmt(cut_ar)}  담기과대 {fmt(hold_ar)}")
    return int(succ.sum())


def main() -> int:
    print("세트-C 끝단 — VE 1,000 · 리더 B 팔 · 분모 전량(미검출=실패)")
    rows = {}
    print("[배포 스택 참조 — atone 상자]")
    rows[f"atone_s0"] = row("atone_s0", "atone_s0", "pred")
    for s in (1, 2, 3):
        rows[f"atone_s{s}"] = row(f"atone_s{s}", f"atone_s{s}", f"atone_s{s}")
    print("[게이트 차량 — tone2te 상자]")
    for s in (0, 1, 2, 3):
        rows[f"tone2te_s{s}"] = row(f"tone2te_s{s}", f"tone2te_s{s}",
                                    f"tone2te_s{s}")
    print("[유효조건 — GT 상자(검출기 없음, 천장)]")
    rd = load(RD / "VE_B_gt.jsonl")
    ok_n = sum(r["ok"] for r in rd.values())
    print(f"  B_gt              성공 {ok_n:4d} ({100*ok_n/len(rd):.2f}%)  "
          f"오독 {len(rd)-ok_n}")
    rows["gt"] = ok_n

    # 재현성 검문 — §28.2 의 값이 안 나오면 조인이 틀린 것이다.
    assert rows["atone_s0"] == 856, f"atone_s0 성공 {rows['atone_s0']} != 856"
    assert rows["tone2te_s0"] == 969, f"tone2te_s0 성공 {rows['tone2te_s0']} != 969"
    assert rows["gt"] == 989, f"B_gt 성공 {rows['gt']} != 989"

    te = [rows[f"tone2te_s{s}"] for s in range(4)]
    gate = min(te) >= 950
    valid = rows["gt"] >= 980
    print(f"\n[게이트] tone2te×B 최저 시드 성공 {min(te)}/1000 "
          f"(4시드 {te}) — 기준 ≥950")
    print(f"[유효조건] B_gt {rows['gt']}/1000 — 기준 ≥980: "
          f"{'충족' if valid else '미충족'}")
    print(f"판정: {'PASS' if gate and valid else 'FAIL'}")
    print("\n면책: 표본은 합성(VE)이다 — 실사진 성적이 아니며 일반화 주장이 아니다. "
          "tone2te 는 배포 팔이 아니다(§28.4 실사진 회귀). 배포 스택(atone×B) "
          "끝단은 다음 마일스톤 인계 수치다.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
