# 순수 리더 오류 35장 — 분류별 검수판(2026-10-06).
# 사람 지시: "리더기 오류의 이미지들 한개식 분석해서 합성기에 반영할수있게 해줄래"
# reader_err35_analysis.json 의 분류(세그소실/세그잔상/자릿수삽입/크롭절단)대로
# 행을 나눠 한 판에 놓는다. 사람이 분류를 눈으로 검증하는 용도.
# cv2.putText 는 한글이 깨진다 — PIL+malgun 만 쓴다([[cv2-putText-no-hangul]]).
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
EACH = HERE / "reader_err_each"
FONT = ImageFont.truetype("C:/Windows/Fonts/malgun.ttf", 15)
FONT_S = ImageFont.truetype("C:/Windows/Fonts/malgun.ttf", 13)

an = json.loads((HERE / "reader_err35_analysis.json").read_text(encoding="utf-8"))
rows = [
    ("세그 소실 (반사·그림자·미세약화로 활성 세그가 죽음)", "seg_loss"),
    ("세그 잔상 (꺼진 세그가 희미하게 보여 다른 숫자로)", "seg_gain"),
    ("자릿수 삽입 (빈 슬롯 잔상·간격 노치를 숫자로 환각)", "digit_insert"),
    ("크롭 절단 (검출 상자 — 리더 순수 오류 아님)", "crop"),
]
def cls_of(r):
    c = r["class"]
    if c.startswith("seg_loss") or c.startswith("digit_loss"):
        return "seg_loss"  # 끝자리 전체 소실(#2)은 세그 소실의 극단
    if c.startswith("seg_gain"):
        return "seg_gain"
    if "crop" in c:
        return "crop"
    return "digit_insert"

TILE_W = 300  # 크롭 원본 폭(×2 확대분)을 이 폭으로 축소
TH = 96
HDR = 30
LBL = 22
COLS = 6

groups = {k: [r for r in an["per_image"] if cls_of(r) == k] for _, k in rows}
H = sum(HDR + ((len(v) + COLS - 1) // COLS) * (TH + LBL) for _, v in groups.items())
sheet = Image.new("RGB", (COLS * TILE_W, H), (18, 18, 18))
d = ImageDraw.Draw(sheet)
y = 0
for title, key in rows:
    v = groups[key]
    d.rectangle([0, y, sheet.width, y + HDR - 4], fill=(40, 40, 48))
    d.text((10, y + 6), f"{title}  —  {len(v)}장", font=FONT, fill=(240, 240, 240))
    y += HDR
    for i, r in enumerate(v):
        cx, cy = (i % COLS) * TILE_W, y + (i // COLS) * (TH + LBL)
        p = EACH / f"{r['n']:02d}_{r['id']}.png"
        im = Image.open(p).convert("RGB")
        h = int(im.height * TILE_W / im.width)
        im = im.resize((TILE_W, min(h, TH)), Image.LANCZOS)
        sheet.paste(im, (cx + 2, cy + 2))
        d.text((cx + 6, cy + TH + 4),
               f"#{r['n']} {r['id']}  {r['gt']}→{r['pred']}",
               font=FONT_S, fill=(255, 220, 120))
    y += ((len(v) + COLS - 1) // COLS) * (TH + LBL)
out = HERE / "reader_err35_sheet.png"
sheet.save(out)
print(f"{out}  {sheet.width}x{sheet.height}")
for t, k in rows:
    print(f"  {t}: {len(groups[k])}장  #{','.join(str(r['n']) for r in groups[k])}")
