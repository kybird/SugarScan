# torch 로 Datumo 전량 추론.
#
# 2026-09-16 정정: 이 파일 머리말은 오랫동안 "YOLOX evaluator와 동일 전처리:
# 스트레치+BGR" 이라고 적혀 있었는데 **두 군데 다 사실이 아니었다.**
#   기하   YOLOX 의 preproc(data_augment.py:142-155)는 레터박스다 —
#          r = min(비율) 로 비율을 유지하고 남는 자리를 114 회색으로 채운다.
#          ValTransform·TrainTransform 이 둘 다 이걸 부르므로 학습은 레터박스다.
#          그런데 이 파일의 기존 경로는 cv2.resize(img0,(imgsz,imgsz)) 스트레치다.
#   채널   preproc 는 채널을 바꾸지 않고, 학습 로더(coco.py:148)는 cv2.imread 라
#          BGR 이다. 그런데 이 파일의 기존 경로는 img[..., ::-1] 로 RGB 를 넣는다.
# 두 어긋남은 서로 다른 축이라 --preproc 로 갈라 잰다(한 번에 둘을 바꾸면
# 어느 쪽이 움직였는지 알 수 없다):
#   stretch    기존 경로 그대로 — 스트레치 + RGB. 기본값이라 동작이 바뀌지 않는다
#   letterbox  기하만 맞춘다 — 레터박스 + RGB
#   yolox      둘 다 맞춘다 — 레터박스 + BGR. ValTransform 과 같은 그림이다
#
# 인자(선택): --preproc <mode>  위 셋 중 하나(기본 stretch)
#             --ckpt <pth>  체크포인트(기본: 운영 gmscreen/latest_ckpt.pth)
#             --out <jsonl>  출력(기본: 운영 gmscreen_quads.jsonl)
#             --exp <exp.py> exp 파일(기본: reading_exp.py — gmscreen 과 동일 구조)
#             --imgsz <n>    추론 입력 변 크기(기본 416 — 기존 동작 보존).
#                            resize 와 좌표 역산 **두 곳이 같은 값**을 써야 한다.
#                            한쪽만 바꾸면 박스가 조용히 어긋나는데 검출은
#                            성공한 것처럼 보인다.
# 평가 실험은 --out 을 _diag 쪽으로 돌려 운영 쿼드(webtool 힌트·CTC 캐시 원료)를
# 덮어쓰지 않게 한다.
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
CKPT = HERE / "yolox_out" / "gmscreen" / "latest_ckpt.pth"
EXP_FILE = "D:/tmp/YOLOX/reading_exp.py"
CONF = 0.25


def _load_bgr(p: Path):
    # 단일 로더: PIL + exif_transpose. cv2.imread(EXIF 적용) 와 PIL 폴백(EXIF 무시)
    # 이 갈라져 출력 좌표계가 섞이던 것을 표시(EXIF 적용) 좌표계 하나로 통일한다.
    # 채널 순서는 기존 cv2.imread 경로와 같은 BGR 로 내놓는다(모델 입력 불변).
    with Image.open(p) as pil:
        pil.load()
        pil = ImageOps.exif_transpose(pil)
        return cv2.cvtColor(np.asarray(pil.convert("RGB")), cv2.COLOR_RGB2BGR)


def _prep(img0, imgsz, mode):
    """(모델 입력 텐서원본 배열, 되돌리는 배율 (sx, sy)) 를 낸다.

    되돌리는 배율을 여기서 함께 내는 것이 요점이다. 전처리와 역변환이 다른
    함수에 있으면 한쪽만 바꿔도 검출은 성공한 것처럼 보이고 박스만 조용히
    어긋난다(이 파일 머리말의 --imgsz 경고와 같은 함정).
    """
    sh, sw = img0.shape[:2]
    if mode == "stretch":
        img = cv2.resize(img0, (imgsz, imgsz))
        return img[..., ::-1].copy(), (sw / float(imgsz), sh / float(imgsz))
    # 레터박스 — YOLOX preproc 와 같은 식. 기하를 재구현하지 않으려고
    # 같은 계산을 쓴다(r = min 비율, 남는 자리 114).
    r = min(imgsz / sh, imgsz / sw)
    padded = np.ones((imgsz, imgsz, 3), dtype=np.uint8) * 114
    resized = cv2.resize(img0, (int(sw * r), int(sh * r)),
                         interpolation=cv2.INTER_LINEAR).astype(np.uint8)
    padded[:int(sh * r), :int(sw * r)] = resized
    if mode == "letterbox":
        padded = padded[..., ::-1].copy()      # 기하만 맞추고 채널은 기존대로
    return padded, (1.0 / r, 1.0 / r)


def selftest() -> int:
    """yolox 모드가 YOLOX 정본 preproc 와 픽셀까지 같은지 본다.

    "학습과 맞췄다"는 주장은 읽어서가 아니라 대조해서 확인한다. 역변환 배율도
    같이 본다 — 전처리만 맞추고 역변환을 안 고치면 박스가 조용히 어긋난다.
    """
    from yolox.data.data_augment import preproc as ypre
    rng = np.random.RandomState(0)
    ok = True
    for h, w in ((4032, 3024), (3024, 4032), (1000, 1000)):
        img = rng.randint(0, 255, (h, w, 3), dtype=np.uint8)
        a, r = ypre(img, (416, 416))               # 정본: CHW float32
        b, (sx, sy) = _prep(img, 416, "yolox")
        same = np.array_equal(a.transpose(1, 2, 0).astype(np.uint8), b)
        rmatch = abs(1.0 / sx - r) < 1e-9 and abs(1.0 / sy - r) < 1e-9
        print(f"  {h}x{w}: 픽셀 동일 {same} · 역배율 1/sx={1/sx:.6f} == r={r:.6f}"
              f" {rmatch}")
        ok &= same and rmatch
    print("SELFTEST PASS" if ok else "SELFTEST FAIL")
    return 0 if ok else 1


def main() -> int:
    if "--selftest" in sys.argv[1:]:
        return selftest()
    out_path = OUT
    ckpt_path = CKPT
    exp_file = EXP_FILE
    imgsz = 416
    preproc_mode = "stretch"
    limit = None            # 앞의 N 장만 — 체크포인트 출처를 맞춰 볼 때 쓴다
    args = sys.argv[1:]
    for i, a in enumerate(args):
        if a == "--out" and i + 1 < len(args):
            out_path = Path(args[i + 1])
        elif a == "--ckpt" and i + 1 < len(args):
            ckpt_path = Path(args[i + 1])
        elif a == "--exp" and i + 1 < len(args):
            exp_file = args[i + 1]
        elif a == "--imgsz" and i + 1 < len(args):
            imgsz = int(args[i + 1])
        elif a == "--preproc" and i + 1 < len(args):
            preproc_mode = args[i + 1]
        elif a == "--limit" and i + 1 < len(args):
            limit = int(args[i + 1])
    assert preproc_mode in ("stretch", "letterbox", "yolox"), preproc_mode
    if out_path == OUT and preproc_mode != "stretch":
        raise SystemExit(
            "운영 gmscreen_quads.jsonl 에 실험 결과를 쓰지 않는다. "
            "--out 을 _diag 쪽으로 돌려라.")
    print(f"ckpt:    {ckpt_path}")
    print(f"out:     {out_path}")
    print(f"imgsz:   {imgsz}")
    print(f"preproc: {preproc_mode}")

    exp = get_exp(exp_file, "reading")
    model = exp.get_model()
    ckpt = torch.load(ckpt_path, map_location="cpu")
    model.load_state_dict(ckpt["model"])
    model.eval().cuda()

    rows = [
        json.loads(l)
        for l in LABELS.read_text(encoding="utf-8").splitlines()
        if l.strip()
    ]
    if limit:
        rows = rows[:limit]
        print(f"limit:   앞 {len(rows)}장만")
    n_ok = 0
    with open(out_path, "w", encoding="utf-8") as out:
        for k, row in enumerate(rows):
            p = DATUMO / row["image"]
            try:
                img0 = _load_bgr(p)
            except Exception:
                continue
            sh, sw = img0.shape[:2]
            arr, (sx, sy) = _prep(img0, imgsz, preproc_mode)
            x = torch.from_numpy(arr).permute(2, 0, 1)[None].float().cuda()
            with torch.no_grad():
                out_t = model(x)
                dets = postprocess(out_t, 1, CONF, 0.45)[0]
            if dets is None or len(dets) == 0:
                continue
            d = dets[0].cpu().numpy()
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
