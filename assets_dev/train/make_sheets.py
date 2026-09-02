# 웹 훈련 탭 검토 카드용 몽타주 2장 생성.
#  finetune_rects_sheet.png — 캐시의 실사진 rect(화면 전체 240장)
#  glyph_sheet.png          — glyph_data 크롭 표본
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent


def sheet(images, cols, cell_w, cell_h, out, bg=(24, 26, 30)):
    rows = (len(images) + cols - 1) // cols
    im = Image.new("RGB", (cols * cell_w, rows * cell_h), bg)
    dr = ImageDraw.Draw(im)
    for i, arr in enumerate(images):
        if arr.ndim == 2:
            pil = Image.fromarray(arr.astype(np.uint8), "L").convert("RGB")
        else:
            pil = Image.fromarray(arr.astype(np.uint8))
        pil = pil.resize((cell_w, cell_h))
        x = (i % cols) * cell_w
        y = (i // cols) * cell_h
        im.paste(pil, (x, y))
        dr.rectangle([x, y, x + cell_w - 1, y + cell_h - 1], outline=(60, 66, 78))
    im.save(str(out))
    print(f"{out.name}: {im.size}")


def main() -> int:
    cache = np.load(str(HERE / "data_cache_v2.npz"))
    real = cache["real_images"]
    idx = np.linspace(0, len(real) - 1, 120).astype(int)
    sheet([real[i] for i in idx], cols=12, cell_w=160, cell_h=80,
          out=HERE / "finetune_rects_sheet.png")

    glyphs = sorted((HERE / "glyph_data").glob("*.png"))
    rng = np.random.RandomState(1)
    pick = [glyphs[i] for i in rng.choice(len(glyphs), min(120, len(glyphs)),
                                          replace=False)]
    sheet([np.asarray(Image.open(p).convert("L")) for p in pick],
          cols=20, cell_w=48, cell_h=64, out=HERE / "glyph_sheet.png")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
