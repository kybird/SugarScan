# 휴먼 밴드 상자 라벨 전수조사(2026-10-07 사람: "숫자를 감싼 라벨은 하나도없다..
# 이거 전수조사해야겠는데"). 방법: 라벨 쿼드를 리더 입력(144x96)으로 워프해
# 25k 리더로 읽고 GT 값과 비교한다. 상자가 숫자줄을 감싸고 있으면 ~98% 읽힌다.
# 대조군으로 검출기 예측 상자 크롭도 같이 읽는다 — 예측 크롭은 읽히는데
# 라벨 크롭이 안 읽히면 라벨이 틀린 것.
import json
import sys
from pathlib import Path

import cv2
import numpy as np
import torch

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from reader_crnn import CRNN, IN_H, IN_W, NUM_CLASSES, decode_greedy  # noqa: E402

DATUMO = HERE.parent.parent / "upstream" / "datumo"

imgs, gts = {}, {}
for ln in (DATUMO / "labels.jsonl").read_text(encoding="utf-8").splitlines():
    if ln.strip():
        j = json.loads(ln)
        imgs[j["id"].split("/")[-1]] = j["image"]
        gts[j["id"].split("/")[-1]] = str(j["reading"])

labels = [json.loads(l) for l in
          (HERE.parent / "band_boxes.jsonl").read_text(encoding="utf-8").splitlines()
          if l.strip()]
hold = {r["id"]: r for r in
        json.loads((HERE / "det_latest_holdout.json").read_text(encoding="utf-8"))}

dev = "cuda" if torch.cuda.is_available() else "cpu"
ck = torch.load(HERE.parent / "reader_out" / "gen2lad25000_s8k" / "best.pt",
                map_location="cpu", weights_only=False)
reader = CRNN(NUM_CLASSES).to(dev).eval()
reader.load_state_dict(ck["model"])


def read_crop(img, quad):
    src = np.float32(quad)
    dst = np.float32([[0, 0], [IN_W - 1, 0], [IN_W - 1, IN_H - 1], [0, IN_H - 1]])
    M = cv2.getPerspectiveTransform(src, dst)
    crop = cv2.warpPerspective(img, M, (IN_W, IN_H))
    t = torch.from_numpy(crop).float().div_(255.).sub_(0.5).unsqueeze(0).unsqueeze(0)
    with torch.no_grad():
        logits = reader(t.to(dev))
    return decode_greedy(logits[0].cpu().unsqueeze(0))[0]


def read_box(img, b):
    x0, y0 = max(0, int(b[0])), max(0, int(b[1]))
    x1 = min(img.shape[1], int(round(b[2])))
    y1 = min(img.shape[0], int(round(b[3])))
    if x1 - x0 < 4 or y1 - y0 < 4:
        return ""
    crop = cv2.resize(img[y0:y1, x0:x1], (IN_W, IN_H))
    t = torch.from_numpy(crop).float().div_(255.).sub_(0.5).unsqueeze(0).unsqueeze(0)
    with torch.no_grad():
        logits = reader(t.to(dev))
    return decode_greedy(logits[0].cpu().unsqueeze(0))[0]


lab_ok = lab_bad = det_ok = det_bad = 0
bad_rows = []
for r in labels:
    pid = r["id"].split("/")[-1]
    gt = gts.get(pid, "")
    if not gt or not gt.isdigit():
        continue
    img = cv2.imread(str(DATUMO / imgs[pid]), cv2.IMREAD_GRAYSCALE)
    lp = read_crop(img, r["quad"])
    l_ok = (lp == str(int(gt)))
    lab_ok += l_ok
    lab_bad += not l_ok
    d_ok = None
    h = hold.get(pid)
    if h and h["gated"]:
        dp = read_box(img, h["pred"])
        d_ok = (dp == str(int(gt)))
        det_ok += bool(d_ok)
        det_bad += not d_ok
    if not l_ok:
        bad_rows.append(dict(id=pid, gt=gt, label_pred=lp or "(빈)",
                             det_pred=(hold[pid]["pred"] and read_box(
                                 img, hold[pid]["pred"]) or "(검출실패)")
                             if hold.get(pid) else "?"))

n = lab_ok + lab_bad
print(f"라벨 상자 크롭을 리더로 읽은 결과: 정독 {lab_ok}/{n} "
      f"({100*lab_ok/n:.1f}%) · 오독/빈 {lab_bad}")
nd = det_ok + det_bad
print(f"대조군(검출기 예측 상자 크롭):        정독 {det_ok}/{nd} "
      f"({100*det_ok/nd:.1f}%) · 오독/빈 {det_bad}")
print()
print("라벨 크롭 오독 목록 (라벨이 숫자를 안 감쌌거나 리더 한계):")
for r in bad_rows:
    print(f"  #{r['id']}: GT {r['gt']} · 라벨크롭→{r['label_pred']}"
          f" · 검출크롭→{r['det_pred']}")
(HERE / "label_census.json").write_text(
    json.dumps(dict(n=n, label_ok=lab_ok, det_ok=det_ok,
                    bad=bad_rows), ensure_ascii=False, indent=1), encoding="utf-8")
print("\n기록: _diag/label_census.json")
