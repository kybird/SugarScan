# TB(절차적 배경)에 T 와 **같은 장 목록**의 부분집합 주석을 만든다.
#
# 단계 1은 `instances_curve_07998.json`(방향별 7,998장 중첩 부분집합)으로
# 학습했다. 단계 2의 두 조건이 같은 예산에서 비교되려면 개입군도 **같은
# 장들**을 써야 한다. TB 는 T 와 시드가 같아 파일명이 일대일 대응하므로
# (panel_20261001_i), T 쪽 주석의 file_name 목록을 그대로 옮기면 된다.
#
# 부분집합을 TB 에서 새로 추첨하면 장 목록이 달라져 "배경만 바꾼 비교"가
# 아니게 된다. 같은 시드로 구웠다는 사실을 여기서 실제로 써먹는 것이다.
#
# 자가검사: 옮긴 뒤 두 주석의 file_name 집합과 상자가 **완전히 일치**하는지
# 본다. 상자가 다르면 배경 합성이 기하를 건드린 것이다 — 그 경우 학습을
# 걸지 않는다(check_bg_parity.py 와 같은 취지의 두 번째 그물).
import argparse
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", default=str(HERE / "synth_coco" / "T"))
    ap.add_argument("--dst", default=str(HERE / "synth_coco" / "TB"))
    ap.add_argument("--ann", default="instances_curve_07998.json")
    ap.add_argument("--axis", default="bg", choices=["bg", "scene"],
                    help="비교의 불변량. bg=상자까지 같아야 한다 / "
                         "scene=상자는 움직여도 된다(그것이 개입이다)")
    ap.add_argument("--ar-tol", type=float, default=0.01,
                    help="scene 축에서 밴드 종횡비 중앙값이 어긋나도 되는 폭")
    a = ap.parse_args()

    src = Path(a.src) / "annotations" / a.ann
    dstdir = Path(a.dst) / "annotations"
    full = json.loads((dstdir / "instances_train2017.json")
                      .read_text(encoding="utf-8"))
    sub = json.loads(src.read_text(encoding="utf-8"))

    want = {im["file_name"] for im in sub["images"]}
    by_name = {im["file_name"]: im for im in full["images"]}
    missing = want - set(by_name)
    if missing:
        raise SystemExit(f"TB 에 없는 장 {len(missing)}개 — 시드가 다른가? "
                         f"예: {sorted(missing)[:3]}")

    keep_ids = {by_name[n]["id"] for n in want}
    out = dict(full)
    out["images"] = [im for im in full["images"] if im["id"] in keep_ids]
    out["annotations"] = [an for an in full["annotations"]
                          if an["image_id"] in keep_ids]

    # 상자가 두 코퍼스에서 같은가 — 배경이 기하를 건드리지 않았다는 확인.
    sb = {im["file_name"]: an["bbox"] for im in sub["images"]
          for an in sub["annotations"] if an["image_id"] == im["id"]} \
        if len(sub["images"]) < 200 else None
    if sb is None:
        sbi = {im["id"]: im["file_name"] for im in sub["images"]}
        sb = {sbi[an["image_id"]]: an["bbox"] for an in sub["annotations"]
              if an["image_id"] in sbi}
    tbi = {im["id"]: im["file_name"] for im in out["images"]}
    tb = {tbi[an["image_id"]]: an["bbox"] for an in out["annotations"]
          if an["image_id"] in tbi}
    diff = [n for n in sb if n in tb
            and max(abs(x - y) for x, y in zip(sb[n], tb[n])) > 1e-6]
    print(f"장 {len(out['images'])} · 주석 {len(out['annotations'])}")
    print(f"  T 와 파일명 일치 {len(want & set(by_name))}/{len(want)}")
    print(f"  상자가 다른 장 {len(diff)}")

    if a.axis == "bg":
        # 배경만 바꾸는 축 — 상자가 움직였다면 배경 합성이 기하를 건드린 것이다.
        if diff:
            raise SystemExit("**상자가 다르다 — 배경이 기하를 건드렸다.** "
                             f"예: {diff[:3]}. 학습을 걸지 않는다.")
        note = "**통과** — 같은 장, 같은 상자, 배경만 다르다."
    else:
        # 장면 축 — **상자가 움직이는 것이 개입 자체**다. 그래서 상자 동일성은
        # 불변량이 될 수 없다. 대신 두 가지를 본다:
        #   1) 파일명 1:1  같은 기기·자세·값을 쓴다는 보장(시드가 같다).
        #   2) 밴드 종횡비 분포 보존  장면을 바꿔도 밴드의 **모양**은 같아야
        #      한다. 여기가 어긋나면 워프가 달라진 것이고 그러면 "장면만
        #      바꿨다"가 아니다.
        # 2026-09-20 Claude 선언. 근거는 BAND_EXP_PLAN §18.1·§18.8.
        def ar(d):
            return [ (b[2] / b[3]) for b in d.values() if b[3] > 0 ]
        import statistics
        a1, a2 = ar(sb), ar(tb)
        m1 = statistics.median(a1) if a1 else 0.0
        m2 = statistics.median(a2) if a2 else 0.0
        rel = abs(m2 - m1) / m1 if m1 else 1.0
        print(f"  밴드 종횡비 중앙  원본 {m1:.4f} · 대상 {m2:.4f} "
              f"· 어긋남 {rel:.2%} (허용 {a.ar_tol:.0%})")
        if rel > a.ar_tol:
            raise SystemExit("**밴드 모양이 달라졌다 — 장면만 바꾼 것이 "
                             "아니다.** 학습을 걸지 않는다.")
        moved = 100.0 * len(diff) / max(1, len(tb))
        print(f"  상자가 움직인 장 {moved:.1f}% — 장면 축에서는 **이것이 개입**이다")
        if not diff:
            raise SystemExit("**상자가 하나도 안 움직였다 — 장면이 안 바뀌었다.** "
                             "TD 가 TC 와 같은 것을 굽지 않았는지 볼 것.")
        note = "**통과** — 같은 장(같은 기기·자세·값), 밴드 모양 보존, 장면만 다르다."

    p = dstdir / a.ann
    p.write_text(json.dumps(out, ensure_ascii=False), encoding="utf-8")
    print(f"  -> {p}")
    print("  " + note)


if __name__ == "__main__":
    raise SystemExit(main())
