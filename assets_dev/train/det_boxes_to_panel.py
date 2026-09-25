# frame_panels_for_det 크롭 좌표 예측 상자를 패널 좌표로 되돌린다 —
# reader_crnn --boxes 규격({file_name, pred:[x0,y0,x1,y1]} 패널 픽셀).
# 사용: python det_boxes_to_panel.py --infer 예측.jsonl --map map.jsonl --out boxes.jsonl
import argparse
import json

HERE = __import__("pathlib").Path(__file__).resolve().parent


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--infer", required=True)
    ap.add_argument("--map", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    off = {}
    for l in (HERE / args.map).read_text(encoding="utf-8").splitlines():
        if l.strip():
            j = json.loads(l)
            off[j["file_name"]] = (j["dx"], j["dy"])
    n = 0
    with open(HERE / args.out, "w", encoding="utf-8") as f:
        for l in (HERE / args.infer).read_text(encoding="utf-8").splitlines():
            if not l.strip():
                continue
            r = json.loads(l)
            if not r.get("pred"):
                continue
            dx, dy = off[r["file_name"]]
            x0, y0, x1, y1 = r["pred"]
            f.write(json.dumps({"file_name": r["file_name"],
                                "pred": [x0 + dx, y0 + dy,
                                         x1 + dx, y1 + dy],
                                "iou": r.get("iou")}) + "\n")
            n += 1
    print(f"패널 좌표 상자 {n}행 -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
