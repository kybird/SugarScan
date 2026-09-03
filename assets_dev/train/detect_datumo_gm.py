# torch(YOLOX evaluator와 동일 전처리: 416 스트레치+BGR)로 Datumo 전량 추론.
import json
import sys
from pathlib import Path

import cv2
import numpy as np
import torch
from PIL import Image, ImageOps

sys.path.insert(0, "D:/tmp/YOLOX")
from yolox.exp import get_exp  # noqa: E402
from yolox.utils import postprocess  # noqa: E402

HERE = Path(__file__).resolve().parent
LABELS = HERE.parent / "upstream" / "datumo" / "labels.jsonl"
DATUMO = HERE.parent / "upstream" / "datumo"
OUT = HERE / "gmscreen_quads.jsonl"
CONF = 0.25


def _load_bgr(p: Path):
    # 단일 로더: PIL + exif_transpose. cv2.imread(EXIF 적용) 와 PIL 폴백(EXIF 무시)
    # 이 갈라져 출력 좌표계가 섞이던 것을 표시(EXIF 적용) 좌표계 하나로 통일한다.
    # 채널 순서는 기존 cv2.imread 경로와 같은 BGR 로 내놓는다(모델 입력 불변).
    with Image.open(p) as pil:
        pil.load()
        pil = ImageOps.exif_transpose(pil)
        return cv2.cvtColor(np.asarray(pil.convert("RGB")), cv2.COLOR_RGB2BGR)


def main() -> int:
    exp = get_exp("D:/tmp/YOLOX/reading_exp.py", "reading")
    model = exp.get_model()
    ckpt = torch.load(HERE / "yolox_out" / "gmscreen" / "latest_ckpt.pth", map_location="cpu")
    model.load_state_dict(ckpt["model"])
    model.eval().cuda()

    rows = [
        json.loads(l)
        for l in LABELS.read_text(encoding="utf-8").splitlines()
        if l.strip()
    ]
    n_ok = 0
    with open(OUT, "w", encoding="utf-8") as out:
        for k, row in enumerate(rows):
            p = DATUMO / row["image"]
            try:
                img0 = _load_bgr(p)
            except Exception:
                continue
            sh, sw = img0.shape[:2]
            img = cv2.resize(img0, (416, 416))
            x = torch.from_numpy(img[..., ::-1].copy()).permute(2, 0, 1)[None].float().cuda()
            with torch.no_grad():
                out_t = model(x)
                dets = postprocess(out_t, 1, CONF, 0.45)[0]
            if dets is None or len(dets) == 0:
                continue
            d = dets[0].cpu().numpy()
            sx, sy = sw / 416.0, sh / 416.0
            x0, y0, x1, y1 = float(d[0]) * sx, float(d[1]) * sy, float(d[2]) * sx, float(d[3]) * sy
            x0, x1 = sorted((max(0.0, min(sw, x0)), max(0.0, min(sw, x1))))
            y0, y1 = sorted((max(0.0, min(sh, y0)), max(0.0, min(sh, y1))))
            if x1 - x0 < 8 or y1 - y0 < 8:
                continue
            out.write(json.dumps({
                "id": row["id"],
                "quad": [[x0, y0], [x1, y0], [x1, y1], [x0, y1]],
                "score": round(float(d[4]), 3),
            }, ensure_ascii=False) + chr(10))
            n_ok += 1
            if (k + 1) % 200 == 0:
                print(f"... {k + 1} (det {n_ok})", flush=True)
    print(f"done: {n_ok}/{len(rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
