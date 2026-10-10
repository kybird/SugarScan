# 리더 실촉 파인튜닝 사전작업 — 새 검출기(ftk5_g0.06)로 실촬 전량 크롭 + K=5 폴드
# (2026-10-09 사람: "새로 만든 검출기와 페어로 리더 학습해야하자나" — 배포 동등).
# 배포 게이트와 동일 조건으로 검출 → 크롭을 _diag/reader_ft/crops/<id>.png 로
# 저장하고 manifest(id,label,fold)를 남긴다. 폴드: 값 라벨 보유 2,504장을
# 기기 층화 × 연속 2장 청크 라운드로빈(검출기 파인튜닝 폴드와 같은 골격,
# 모집단은 상자 라벨 346이 아니라 값 라벨 전체).
import json
import sys
from pathlib import Path

import cv2
import torch

HERE = Path(__file__).resolve().parent
TRAIN = HERE.parent
sys.path.insert(0, str(TRAIN))
from band_net import BandNet, decode  # noqa: E402
from train_band import letterbox  # noqa: E402

DATUMO = TRAIN.parent / "upstream" / "datumo"
DET = TRAIN / "band_out" / "tone" / "ftk5_g0.06"
OUT = HERE / "reader_ft"
ROTATED_90 = {"1213", "1226", "1564", "1565", "940", "283", "2411"}


def main():
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    c = torch.load(DET, map_location="cpu", weights_only=False)
    det = BandNet(width=c["width"], stride=c.get("stride", 16)).to(dev).eval()
    det.load_state_dict(c["model"])

    rows = []
    for ln in (DATUMO / "labels.jsonl").read_text(encoding="utf-8").splitlines():
        if not ln.strip():
            continue
        j = json.loads(ln)
        pid = j["id"].split("/")[-1]
        rd = str(j.get("reading", ""))
        if pid in ROTATED_90 or not rd.lstrip("-").isdigit():
            continue
        rows.append((j["id"], pid, rd, j["image"]))

    dev_lab = {}
    for ln in (TRAIN / "device_labels.jsonl").read_text(
            encoding="utf-8").splitlines():
        if ln.strip():
            d = json.loads(ln)
            dev_lab[d["id"].split("/")[-1]] = " ".join(
                x for x in (d.get("brand"), d.get("model"), d.get("variant")) if x)

    def idnum(p):
        try:
            return int(p)
        except ValueError:
            return 0

    rows.sort(key=lambda r: (dev_lab.get(r[1], "?"), idnum(r[1])))
    chunks = [rows[i:i + 2] for i in range(0, len(rows), 2)]
    fold_of = {}
    for ci, ch in enumerate(chunks):
        for r in ch:
            fold_of[r[1]] = ci % 5

    (OUT / "crops").mkdir(parents=True, exist_ok=True)
    man = OUT / "crops_manifest.jsonl"
    n_ok = n_fail = 0
    with man.open("w", encoding="utf-8") as mf, torch.no_grad():
        for k, (cid, pid, rd, imgp) in enumerate(rows):
            img = cv2.imread(str(DATUMO / imgp), cv2.IMREAD_GRAYSCALE)
            if img is None:
                n_fail += 1
                continue
            lb, r, dx, dy = letterbox(img, c["size"])
            x = torch.from_numpy(lb).float().div_(255.).unsqueeze(0).unsqueeze(0)
            obj, reg = det(x.to(dev))
            b, s = decode(obj.float(), reg.float(), det.stride)
            b = b[0].cpu().numpy()
            sc = float(s[0].cpu())
            p = [(b[0]-dx)/r, (b[1]-dy)/r, (b[2]-dx)/r, (b[3]-dy)/r]
            frac = (p[2]-p[0])*(p[3]-p[1]) / max(1., img.shape[1]*img.shape[0])
            if sc < 0.25 or frac < 0.02:
                n_fail += 1
                continue
            x0, y0 = max(0, int(p[0])), max(0, int(p[1]))
            x1 = min(img.shape[1], int(round(p[2])))
            y1 = min(img.shape[0], int(round(p[3])))
            if x1-x0 < 4 or y1-y0 < 4:
                n_fail += 1
                continue
            cv2.imwrite(str(OUT / "crops" / f"{pid}.png"), img[y0:y1, x0:x1])
            mf.write(json.dumps(dict(id=pid, label=str(int(rd)),
                                     fold=fold_of[pid],
                                     w=x1-x0, h=y1-y0)) + "\n")
            n_ok += 1
            if (k+1) % 500 == 0:
                print(f"  {k+1}/{len(rows)} 크롭 {n_ok} · 게이트실패 {n_fail}",
                      flush=True)
    from collections import Counter
    fc = Counter(json.loads(l)["fold"] for l in man.read_text(
        encoding="utf-8").splitlines() if l.strip())
    print(f"크롭 {n_ok}장 · 실패 {n_fail} · 폴드 {dict(sorted(fc.items()))}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
