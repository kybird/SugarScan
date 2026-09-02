# EXIF 미적용(저장) 좌표계로 저장된 band 라벨 복구
#
# 사고 내용: 예전 라벨러는 /api/image 를 cv2(EXIF 적용)로, 검수·rect 를
# PIL(EXIF 무시)로 읽어 좌표계가 갈렸다. 그 시기에 저장된 일부 행은 박스가
# **회전 전(저장) 이미지** 좌표로 남았다. orientation=6(시계방향 90도로
# 표시) 기준으로 저장 좌표 (xs, ys) 는 표시 좌표에서
#
#     x_d = (Hs - 1) - ys,   y_d = xs        (Hs = 저장 이미지 높이)
#
# 가 된다. 스케일이 아니라 회전이므로 배율 보정으로는 절대 맞출 수 없다 —
# repair_prevframe_labels.py 와 원인도 해법도 다른 별개의 사고다.
#
# 탐지 기준은 "표시 좌표계에서 경계를 벗어나고, 회전 보정하면 경계 안에 들어옴".
# 두 조건을 모두 만족하는 행만 건드린다.
#
#   conda run -n sugartrain python repair_unrotated_band_labels.py
#   conda run -n sugartrain python repair_unrotated_band_labels.py --apply
import json
import shutil
import sys
import time
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
IMAGES = (HERE / ".." / "upstream" / "datumo" / "extracted" / "TILDE").resolve()
TARGETS = {"band": HERE / "labeled.jsonl", "lcd": HERE / "screen_boxes.jsonl"}
TOL = 2.0


def sizes(cid):
    """(저장 크기, 표시 크기, orientation)."""
    with Image.open(IMAGES / f"{cid}.jpg") as im:
        ws, hs = im.size
        ori = im.getexif().get(274)
    w, h = (hs, ws) if ori in (5, 6, 7, 8) else (ws, hs)
    return (ws, hs), (w, h), ori


def unrotate(quad, stored, ori):
    """저장(회전 전) 좌표 → 표시 좌표. 지원하지 않는 ori 는 None."""
    ws, hs = stored
    if ori == 6:     # 시계방향 90도 회전해야 바로 선다
        return [[(hs - 1) - p[1], p[0]] for p in quad]
    if ori == 8:     # 반시계 90도
        return [[p[1], (ws - 1) - p[0]] for p in quad]
    if ori == 3:     # 180도
        return [[(ws - 1) - p[0], (hs - 1) - p[1]] for p in quad]
    return None


def inside(quad, w, h):
    xs = [p[0] for p in quad]
    ys = [p[1] for p in quad]
    return (min(xs) >= -TOL and min(ys) >= -TOL
            and max(xs) <= w + TOL and max(ys) <= h + TOL)


def box(quad):
    xs = [p[0] for p in quad]
    ys = [p[1] for p in quad]
    return [round(min(xs)), round(min(ys)), round(max(xs)), round(max(ys))]


def main(argv):
    apply = "--apply" in argv
    total_fixed = 0
    for mode, path in TARGETS.items():
        if not path.exists():
            continue
        rows = [json.loads(l) for l in
                path.read_text(encoding="utf-8").splitlines() if l.strip()]
        fixed = 0
        for r in rows:
            q = r.get("quad")
            if not q:
                continue
            cid = r["id"]
            if not (IMAGES / f"{cid}.jpg").exists():
                continue
            stored, (w, h), ori = sizes(cid)
            if inside(q, w, h):
                continue                      # 표시 좌표계에서 멀쩡하다
            nq = unrotate(q, stored, ori)
            if nq is None:
                print(f"[WARN] {mode} {cid}: 경계 초과인데 ori={ori} 라 "
                      f"회전 가설로 설명 못 함 — 재라벨 필요 {box(q)} vs {w}x{h}")
                continue
            if not inside(nq, w, h):
                print(f"[WARN] {mode} {cid}: 회전 보정해도 경계 밖 — 재라벨 필요")
                continue
            print(f"[fix ] {mode} {cid} ori={ori} 저장 {stored[0]}x{stored[1]} "
                  f"표시 {w}x{h}: {box(q)} -> {box(nq)}")
            r["quad"] = nq
            r["ow"], r["oh"] = w, h
            r["repaired"] = "unrotated-20260902"
            fixed += 1
        print(f"{mode}: {len(rows)}행 중 {fixed}건 수정")
        total_fixed += fixed
        if apply and fixed:
            bak = path.with_name(f"{path.stem}_before_unrotate_"
                                 f"{time.strftime('%Y%m%d_%H%M%S')}.jsonl")
            shutil.copy2(path, bak)
            tmp = path.with_suffix(".tmp")
            with open(tmp, "w", encoding="utf-8") as f:
                for r in rows:
                    f.write(json.dumps(r, ensure_ascii=False) + "\n")
            tmp.replace(path)
            print(f"  기록 완료. 백업: {bak.name}")
    if not apply:
        print("\n--apply 를 붙여야 실제로 기록한다 (지금은 계산만 했다)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
