# 이전-장 프레임으로 저장된 라벨 복구 (2026-09-02 사고)
#
# 사고 내용: 라벨러(webtool.html)가 캐시 히트로 장을 넘길 때 lb.ow/lb.oh 를
# 갱신하지 않아, 박스가 **직전 장의 표시 크기** 프레임 안에서 저장됐다.
# 저장 좌표는 "표시(EXIF 적용) 이미지의 원본 픽셀"이 정본이므로, 파손된 행은
#
#     올바른 좌표 = 저장된 좌표 × (이 장의 표시 크기 / 직전 장의 표시 크기)
#
# 로 정확히 되돌릴 수 있다. 두 크기 모두 파일에서 직접 잴 수 있고, 라벨러의
# 장 순서(LCD 모드: 모델 예측 없는 장 먼저, 그다음 id 오름차순)는 결정적이라
# "직전 장"이 유일하게 정해진다.
#
# 안전장치: --apply 없이 돌리면 아무것도 쓰지 않고 계산만 보여 준다.
# 되돌린 결과가 이미지 경계 안에 들어오지 않으면 그 행은 손대지 않는다.
#
#   conda run -n sugartrain python repair_prevframe_labels.py
#   conda run -n sugartrain python repair_prevframe_labels.py --apply
import json
import shutil
import sys
import time
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
IMAGES = (HERE / ".." / "upstream" / "datumo" / "extracted" / "TILDE").resolve()
LCD_FILE = HERE / "screen_boxes.jsonl"
GM_QUADS = HERE / "gmscreen_quads_oriented.jsonl"
READINGS = (HERE / ".." / "upstream" / "datumo" / "labels.jsonl").resolve()


def oriented_size(cid):
    with Image.open(IMAGES / f"{cid}.jpg") as im:
        w, h = im.size
        if im.getexif().get(274) in (5, 6, 7, 8):
            w, h = h, w
    return w, h


def lcd_order():
    """라벨러 LCD 모드의 장 순서를 그대로 재현한다(webtool.html loadMode)."""
    preds = set()
    if GM_QUADS.exists():
        for line in GM_QUADS.read_text(encoding="utf-8").splitlines():
            if line.strip():
                preds.add(json.loads(line)["id"])
    ids = []
    for line in READINGS.read_text(encoding="utf-8").splitlines():
        if line.strip():
            ids.append(json.loads(line)["id"])
    ids.sort()
    ids.sort(key=lambda i: (1 if i in preds else 0, i))
    return ids


def main(argv):
    apply = "--apply" in argv
    order = lcd_order()
    pos = {cid: i for i, cid in enumerate(order)}
    rows = []
    for line in LCD_FILE.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))

    fixed, kept = 0, 0
    for r in rows:
        cid = r["id"]
        if not r.get("quad"):
            kept += 1
            continue
        ow, oh = oriented_size(cid)
        xs = [p[0] for p in r["quad"]]
        ys = [p[1] for p in r["quad"]]
        inside = (min(xs) >= -2 and min(ys) >= -2
                  and max(xs) <= ow + 2 and max(ys) <= oh + 2)
        if r.get("ow") is not None:
            kept += 1
            print(f"[skip] {cid}: 프레임 기록 있음({r['ow']}x{r['oh']}) — 신버전 저장분")
            continue
        i = pos.get(cid)
        if i is None or i == 0:
            # 첫 장은 앞 장이 없어 프레임이 밀릴 수 없다 — 그대로 두고 출처만 기록
            r["ow"], r["oh"] = ow, oh
            kept += 1
            print(f"[keep] {cid}: 첫 장 — 원본 유지, 프레임 {ow}x{oh} 기록")
            continue
        pw, ph = oriented_size(order[i - 1])
        sx, sy = ow / pw, oh / ph
        nq = [[p[0] * sx, p[1] * sy] for p in r["quad"]]
        nxs = [p[0] for p in nq]
        nys = [p[1] for p in nq]
        n_inside = (min(nxs) >= -2 and min(nys) >= -2
                    and max(nxs) <= ow + 2 and max(nys) <= oh + 2)
        tag = f"{cid}: 표시 {ow}x{oh}, 직전 장 {order[i-1]} {pw}x{ph}, 배율 {sx:.4f}"
        if abs(sx - 1) < 1e-6 and abs(sy - 1) < 1e-6:
            r["ow"], r["oh"] = ow, oh
            kept += 1
            print(f"[keep] {tag} — 크기가 같아 밀림이 드러나지 않는다(수정 불가·불필요)")
            continue
        if not n_inside:
            kept += 1
            print(f"[WARN] {tag} — 되돌린 결과가 경계를 벗어난다. 손대지 않음. 재라벨 필요")
            continue
        print(f"[fix ] {tag}")
        print(f"        {[round(v) for v in (min(xs), min(ys), max(xs), max(ys))]}"
              f" -> {[round(v) for v in (min(nxs), min(nys), max(nxs), max(nys))]}"
              f" (기존 경계내={inside})")
        r["quad"] = nq
        r["ow"], r["oh"] = ow, oh
        r["repaired"] = "prevframe-20260902"
        fixed += 1

    print(f"\n수정 {fixed}건 · 유지 {kept}건")
    if not apply:
        print("--apply 를 붙여야 실제로 기록한다 (지금은 계산만 했다)")
        return 0
    bak = LCD_FILE.with_name(
        f"screen_boxes_before_repair_{time.strftime('%Y%m%d_%H%M%S')}.jsonl")
    shutil.copy2(LCD_FILE, bak)
    tmp = LCD_FILE.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    tmp.replace(LCD_FILE)
    print(f"기록 완료. 백업: {bak.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
