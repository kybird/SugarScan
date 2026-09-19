# 밴드 검출망을 **실촬**에서 잰다 — 합성 게이트를 넘긴 뒤의 검증(SPEC §4).
#
# 입력은 **이미 찍힌 전체 혈당기 사진**이다(SPEC §1.1). 자르지 않는다 —
# LCD 쿼드로 잘라서 재면 배포에 없는 오라클을 쓰는 것이다(§7-2). 폐기된
# 계열이 정확히 그 함정에 빠져 같은 체크포인트가 16.6% 에서 78.6% 로 보였다.
#
# 모집단(§4): 사람 밴드 라벨이 있고 **사람 제외 선언**(band_label_excluded.jsonl)
# 에 없는 장. 기기 단절 분할의 id 목록을 쓰지 않는다 — 그 분할은 실촬
# 파인튜닝용이고, 합성만으로 학습한 모델에는 누수가 성립하지 않는다.
#
# 지표: 실촬에는 `digit_box` 가 없다(생성기만 아는 값이다). 그래서 합성 게이트와
# **같은 지표를 쓸 수 없다.** 대신 사람 밴드 라벨을 기준으로 셋을 낸다:
#   검출     conf 이상 상자가 나왔나
#   포함률   사람 밴드 라벨이 예측 상자에 얼마나 드나 (리더에게 중한 축)
#   IoU      참고용. 게이트로 쓰지 않는다(§7-3)
# **이 셋을 합성 합격률과 한 표에 놓지 않는다** — 정답이 다른 물건이다.
#
# 도는 동안 보이게 한다: 한 장마다 결과를 흘려 쓰고, 웹툴 기종 탭이 읽는
# band_quads_pred.jsonl 을 함께 갱신한다(축정렬 상자를 네 귀로 적는다).
import argparse
import json
import time
from collections import defaultdict
from pathlib import Path

import cv2
import numpy as np
import torch

from band_net import BandNet, decode
from train_band import letterbox
from band_exclusions import load_excluded

HERE = Path(__file__).resolve().parent
DATUMO = HERE.parent / "upstream" / "datumo"
BANDS = HERE / "band_boxes.jsonl"
WIDE_IDS = HERE / "_diag" / "wide_all" / "wide_ids.json"
OUT = HERE / "_diag" / "band_real"
OVERLAY = HERE / "band_quads_pred.jsonl"


def rect(quad):
    q = np.asarray(quad, float)
    return [float(q[:, 0].min()), float(q[:, 1].min()),
            float(q[:, 0].max()), float(q[:, 1].max())]


def iou(a, b):
    x0, y0 = max(a[0], b[0]), max(a[1], b[1])
    x1, y1 = min(a[2], b[2]), min(a[3], b[3])
    i = max(0.0, x1 - x0) * max(0.0, y1 - y0)
    u = (a[2]-a[0])*(a[3]-a[1]) + (b[2]-b[0])*(b[3]-b[1]) - i
    return i / u if u > 0 else 0.0


def contain(gt, pred):
    """사람 밴드 라벨이 예측 상자에 드는 넓이 비율."""
    x0, y0 = max(gt[0], pred[0]), max(gt[1], pred[1])
    x1, y1 = min(gt[2], pred[2]), min(gt[3], pred[3])
    i = max(0.0, x1 - x0) * max(0.0, y1 - y0)
    a = (gt[2]-gt[0]) * (gt[3]-gt[1])
    return i / a if a > 0 else 0.0


def population():
    """모집단 — 사람 밴드 라벨 ∩ 이미지 있음 − 사람 제외 선언."""
    ex = set(load_excluded())
    lab = {}
    for line in (DATUMO / "labels.jsonl").read_text(encoding="utf-8").splitlines():
        if line.strip():
            j = json.loads(line)
            lab[j["id"]] = j["image"]
    band = {}
    for line in BANDS.read_text(encoding="utf-8").splitlines():
        if line.strip():
            j = json.loads(line)
            if j.get("quad"):
                band[j["id"]] = rect(j["quad"])
    ids = [i for i in sorted(band) if i in lab and i not in ex]
    return ids, band, lab, len(ex)


def device_boxes(xml_dir):
    """Datacluster VOC 주석에서 **기기 전체 상자**를 읽는다 (stem -> box).

    이 코퍼스에는 밴드 라벨이 없다. 있는 것은 `glucometer` 클래스의 기기 상자
    하나뿐이라 채점의 정답으로는 쓸 수 없다 — 기기는 밴드가 아니다. 대신 두
    가지에 쓴다: (1) 예측이 기기 안에 드는지·기기만 한 크기인지를 재는 **자**,
    (2) 검출 1단계를 사람이 대신해 주는 **크롭**.
    """
    import xml.etree.ElementTree as ET
    out = {}
    for p in sorted(Path(xml_dir).glob("*.xml")):
        try:
            root = ET.parse(p).getroot()
        except ET.ParseError:
            continue
        for ob in root.findall("object"):
            bb = ob.find("bndbox")
            if bb is None:
                continue
            out[p.stem] = [float(bb.findtext(k)) for k in
                           ("xmin", "ymin", "xmax", "ymax")]
            break
    return out


def device_stats(rows, dev):
    """예측을 **기기 상자**에 대고 잰다. 밴드 정답이 아니므로 합격률이 아니다.

    인쇄하는 것:
      예측넓이/기기넓이  1.0 에 가까우면 기기 전체를 문 것이다. 밴드는 기기의
                       일부이므로 제대로 물었다면 1보다 한참 작아야 한다.
      예측∩기기/예측     예측이 기기 안에 든 비율. 낮으면 배경을 물고 있다.
    """
    ar, inb, frac = [], [], []
    for r in rows:
        if not r["det"]:
            continue
        d = dev.get(r["id"].split("/", 1)[-1])
        if d is None:
            continue
        p = r["pred"]
        pa = max(0.0, p[2]-p[0]) * max(0.0, p[3]-p[1])
        da = max(0.0, d[2]-d[0]) * max(0.0, d[3]-d[1])
        if pa <= 0 or da <= 0:
            continue
        ix = max(0.0, min(p[2], d[2]) - max(p[0], d[0]))
        iy = max(0.0, min(p[3], d[3]) - max(p[1], d[1]))
        ar.append(pa / da)
        inb.append(ix * iy / pa)
        # 기기가 **사진에서** 차지하는 선형 비. 촬영 거리의 자다.
        frac.append(np.sqrt(da / max(1.0, r["ow"] * r["oh"])))
    if not ar:
        print("  기기 상자와 짝지은 장이 없다")
        return
    a, b = np.asarray(ar), np.asarray(inb)
    print(f"  기기 상자와 짝지음 n={len(a)}  (**밴드 정답이 아니다 — 합격률 아님**)")
    print(f"    예측넓이/기기넓이   p10={np.percentile(a,10):.2f} "
          f"중앙={np.median(a):.2f} p90={np.percentile(a,90):.2f}")
    print(f"    예측이 기기 안에 든 비율  중앙={np.median(b):.3f}")
    print(f"      절반 이상 기기 밖(배경을 뭄): {int((b < 0.5).sum())}장 "
          f"({100*(b < 0.5).mean():.1f}%)")
    print(f"      90% 이상 기기 안:           {int((b >= 0.9).sum())}장 "
          f"({100*(b >= 0.9).mean():.1f}%)")
    # 촬영 거리로 층을 갈라 본다 — **평균은 못하는 층을 숨긴다.**
    fr = np.asarray(frac)
    q1, q2 = np.percentile(fr, [33.3, 66.7])
    print(f"    촬영 거리별(기기가 사진에서 차지하는 선형 비):")
    for lbl, m in (("가까움", fr >= q2),
                   ("중간  ", (fr >= q1) & (fr < q2)),
                   ("멂    ", fr < q1)):
        if not m.any():
            continue
        print(f"      {lbl} 기기/사진 {fr[m].min():.2f}~{fr[m].max():.2f} "
              f"n={int(m.sum()):<4} 기기안 중앙={np.median(b[m]):.3f} "
              f"· 90%이상 {100*(b[m] >= 0.9).mean():.1f}%")

@torch.no_grad()
def predict_dir(ckpt, photo_dir, prefix, conf=0.25, limit=0, tag=None,
                xml_dir=None, crop=False, crop_pad=0.05, mask_bg=False):
    """정답이 없는 사진 폴더에 예측만 낸다.

    왜 필요한가: 라이선스가 자유로운 코퍼스(Datacluster CC0, 238장)에는 밴드
    라벨이 없다. 점수는 못 내지만 **예측 상자를 눈으로 보는 것**만으로도
    "실촬에서 무엇을 무는가"를 알 수 있다 — 라벨링 238장을 시작하기 전에
    확인할 값싼 정보다.

    같은 jsonl 모양을 쓰되 gt 는 null 이다. 검수 화면이 그걸 보고 정답 상자를
    안 그린다. **점수 칸을 0 으로 채우지 않는다** — 정답이 없는 것과 0점인 것은
    다르다.

    crop=True 면 **기기 상자로 잘라서** 넣는다(2026-09-18 갈림 실험). 검출의
    1단계("프레임의 여러 사각형 중 어느 것인가")를 사람 주석이 대신해 주는
    셈이다. 전체 사진과 크롭의 성적이 갈리면 실패는 1단계에 있고, 갈리지
    않으면 2단계(유리 안에서 밴드를 짚는 일)에 있다.

    **크롭은 배포 경로에 없다**(§1.1 입력은 자르지 않은 전체 사진). 진단용
    오라클이므로 이 수치를 제품 성적으로 인용하지 않는다 — 폐기된 계열이
    정확히 그 함정에 빠졌다(§7-2).

    예측 좌표는 자르기 전 **원본 사진 픽셀**로 되돌린다. 크롭 좌표계로 적으면
    검수 화면이 상자를 엉뚱한 데 그린다([[unnamed-coordinate-frame]]).
    """
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    c = torch.load(ckpt, map_location="cpu", weights_only=False)
    model = BandNet(width=c["width"]).to(dev).eval()
    model.load_state_dict(c["model"])
    size = c["size"]
    name = tag or (f"{prefix}_{Path(ckpt).stem}"
                   + ("_crop" if crop else "")
                   + ("_flatbg" if mask_bg else ""))
    devbox = device_boxes(xml_dir) if xml_dir else {}
    if (crop or mask_bg) and not devbox:
        raise SystemExit("--crop 은 --xml 이 있어야 한다 — 자를 상자가 없다")
    files = sorted(Path(photo_dir).glob("*.jpg"))
    if limit:
        files = files[:limit]
    OUT.mkdir(parents=True, exist_ok=True)
    res_p = OUT / f"{name}.jsonl"
    t0 = time.time()
    n = 0
    out_rows = []
    with res_p.open("w", encoding="utf-8") as f:
        for fp in files:
            img = cv2.imread(str(fp), cv2.IMREAD_GRAYSCALE)
            if img is None:
                continue
            ox = oy = 0          # 크롭 원점. 되돌릴 때 더한다.
            ow, oh = int(img.shape[1]), int(img.shape[0])
            if mask_bg:
                # **배율은 그대로 두고 배경 내용만 없앤다.** 크롭은 배율과
                # 배경을 함께 바꿔서 둘을 가르지 못한다(pad 쓸기로 확인).
                # 기기 상자 바깥을 그 영역의 평균 한 값으로 덮으면 밝기는
                # 유지되고 결·모서리·경쟁 사각형만 사라진다 — 합성이 그리는
                # 단색 판(bg_col)과 같은 상태다. 여기서 성적이 돌아오면
                # 원인은 배율이 아니라 **배경 내용**이다.
                d = devbox.get(fp.stem)
                if d is None:
                    continue
                m = np.zeros(img.shape, np.uint8)
                m[max(0, int(d[1])):int(d[3]), max(0, int(d[0])):int(d[2])] = 1
                if m.sum() == 0 or m.sum() == m.size:
                    continue
                img = np.where(m == 1, img,
                               np.uint8(img[m == 0].mean())).astype(np.uint8)
            if crop:
                d = devbox.get(fp.stem)
                if d is None:
                    continue
                pw, ph = (d[2]-d[0]) * crop_pad, (d[3]-d[1]) * crop_pad
                ox, oy = max(0, int(d[0]-pw)), max(0, int(d[1]-ph))
                x1, y1 = min(ow, int(d[2]+pw)), min(oh, int(d[3]+ph))
                if x1 - ox < 8 or y1 - oy < 8:
                    continue
                img = img[oy:y1, ox:x1]
            lb, r, dx, dy = letterbox(img, size)
            x = torch.from_numpy(lb).float().div_(255.).unsqueeze(0).unsqueeze(0)
            obj, reg = model(x.to(dev))
            b, s = decode(obj.float(), reg.float(), model.stride)
            b = b[0].cpu().numpy()
            sc = float(s[0].cpu())
            p = [(b[0]-dx)/r + ox, (b[1]-dy)/r + oy,
                 (b[2]-dx)/r + ox, (b[3]-dy)/r + oy]
            f.write(json.dumps({
                "id": f"{prefix}/{fp.stem}", "ow": ow,
                "oh": oh, "score": round(sc, 4),
                "det": bool(sc >= conf),
                "pred": [round(v, 1) for v in p],
                "gt": None, "iou": None, "contain": None, "wide": False,
                "crop": [ox, oy] if crop else None,
            }, ensure_ascii=False) + "\n")
            out_rows.append({"id": f"{prefix}/{fp.stem}", "ow": ow, "oh": oh,
                             "det": bool(sc >= conf), "pred": p})
            n += 1
    miss = sum(1 for r in out_rows if not r["det"])
    print(f"{name}: {n}장 예측 · 검출 실패 {miss} -> {res_p}  ({time.time()-t0:.0f}s)")
    print("  입력: " + ("**기기 상자 크롭**(진단용 오라클, 배포에 없다)"
                       if crop else "자르지 않은 전체 사진"))
    print("  **밴드 정답이 없다** — 합격률은 못 낸다. 눈으로 볼 것: /bandreal")
    if devbox:
        device_stats(out_rows, devbox)
    return {"name": name, "n": n, "miss": miss, "contain1": None,
            "iou_med": None}


@torch.no_grad()
def evaluate(ckpt, conf=0.25, limit=0, overlay=True, tag=None):
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    c = torch.load(ckpt, map_location="cpu", weights_only=False)
    model = BandNet(width=c["width"]).to(dev).eval()
    model.load_state_dict(c["model"])
    size = c["size"]
    name = tag or Path(ckpt).stem

    ids, band, lab, n_ex = population()
    if limit:
        ids = ids[:limit]
    wide = set(json.loads(WIDE_IDS.read_text(encoding="utf-8"))) \
        if WIDE_IDS.exists() else set()

    OUT.mkdir(parents=True, exist_ok=True)
    res_p = OUT / f"{name}.jsonl"
    prog_p = OUT / "progress.json"
    ovl = []
    rows = []
    t0 = time.time()
    with res_p.open("w", encoding="utf-8") as f:
        for k, cid in enumerate(ids):
            img = cv2.imread(str(DATUMO / lab[cid]), cv2.IMREAD_GRAYSCALE)
            if img is None:
                continue
            lb, r, dx, dy = letterbox(img, size)
            x = torch.from_numpy(lb).float().div_(255.).unsqueeze(0).unsqueeze(0)
            obj, reg = model(x.to(dev))
            b, s = decode(obj.float(), reg.float(), model.stride)
            b = b[0].cpu().numpy()
            sc = float(s[0].cpu())
            p = [(b[0]-dx)/r, (b[1]-dy)/r, (b[2]-dx)/r, (b[3]-dy)/r]
            det = sc >= conf
            gt = band[cid]
            # 원본 사진 크기를 함께 적는다 — 검수 화면(/bandreal)이 줄인
            # 이미지 위에 상자를 그리려면 원본→표시 비가 필요하다. 이걸 빼면
            # 상자가 통째로 어긋난다(antipatterns/unnamed-coordinate-frame).
            row = {"id": cid, "ow": int(img.shape[1]), "oh": int(img.shape[0]),
                   "score": round(sc, 4), "det": bool(det),
                   "pred": [round(v, 1) for v in p], "gt": [round(v, 1) for v in gt],
                   "iou": round(iou(p, gt), 4) if det else 0.0,
                   "contain": round(contain(gt, p), 4) if det else 0.0,
                   "wide": cid in wide}
            rows.append(row)
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
            f.flush()
            if overlay and det:
                ovl.append({"id": cid, "quad": [[p[0], p[1]], [p[2], p[1]],
                                                [p[2], p[3]], [p[0], p[3]]],
                            "source": "detector", "ckpt": name, "arch": "bandnet",
                            "score": round(sc, 4)})
            if k % 10 == 0 or k == len(ids) - 1:
                hit = [x for x in rows if x["det"]]
                prog_p.write_text(json.dumps({
                    "ckpt": name, "done": len(rows), "total": len(ids),
                    "det": len(hit), "miss": len(rows) - len(hit),
                    "contain_ge_1": sum(1 for x in hit if x["contain"] >= 0.999),
                    "iou_med": round(float(np.median([x["iou"] for x in hit])), 4)
                    if hit else 0.0,
                    "elapsed": round(time.time() - t0, 1),
                }, ensure_ascii=False), encoding="utf-8")
                if overlay and ovl:
                    OVERLAY.write_text(
                        "\n".join(json.dumps(o, ensure_ascii=False) for o in ovl)
                        + "\n", encoding="utf-8")

    if overlay and ovl:
        OVERLAY.write_text("\n".join(json.dumps(o, ensure_ascii=False)
                                     for o in ovl) + "\n", encoding="utf-8")
    return summarize(name, rows, c, n_ex, res_p)


def summarize(name, rows, meta, n_ex, res_p):
    n = len(rows)
    hit = [r for r in rows if r["det"]]
    tall = [r for r in rows if not r["wide"]]
    wide = [r for r in rows if r["wide"]]
    print(f"체크포인트 {name} · 학습장수 {meta['n_images']} · "
          f"{meta['param']/1e6:.3f}M · 스텝 {meta['steps']}")
    print(f"  모집단 실촬 전체사진 n={n} (사람 제외 선언 {n_ex}장 뺌) · "
          f"입력은 자르지 않은 원본")
    print(f"  검출 실패 {n - len(hit)}")
    for lbl, sel in (("전체", rows), ("세로형", tall), ("가로형", wide)):
        if not sel:
            continue
        h = [r for r in sel if r["det"]]
        if not h:
            print(f"    {lbl} n={len(sel)} 전부 검출 실패")
            continue
        cv = np.array([r["contain"] for r in h])
        iv = np.array([r["iou"] for r in h])
        print(f"    {lbl} n={len(sel)} 실패 {len(sel)-len(h)} · "
              f"포함률 1.0 {int((cv >= .999).sum())}장 "
              f"({100*(cv >= .999).sum()/len(sel):.1f}%) "
              f"중앙 {np.median(cv):.4f} · IoU 중앙 {np.median(iv):.4f}")
    print(f"  -> {res_p}")
    cv = np.array([r["contain"] for r in hit]) if hit else np.array([0.0])
    return {"name": name, "n": n, "miss": n - len(hit),
            "contain1": float((cv >= .999).mean()),
            "iou_med": float(np.median([r["iou"] for r in hit])) if hit else 0.0}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ckpt", nargs="+", required=True)
    ap.add_argument("--conf", type=float, default=0.25)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--no-overlay", action="store_true")
    ap.add_argument("--photodir", default=None,
                    help="정답 없는 사진 폴더에 예측만 낸다")
    ap.add_argument("--prefix", default="datacluster",
                    help="--photodir 와 함께. 웹툴이 코퍼스를 가르는 id 앞머리")
    ap.add_argument("--xml", default=None,
                    help="VOC 주석 폴더. 기기 상자를 자로 쓴다(채점 아님)")
    ap.add_argument("--crop", action="store_true",
                    help="기기 상자로 잘라 넣는다 — 진단용 오라클, 배포에 없다")
    ap.add_argument("--crop-pad", type=float, default=0.05)
    ap.add_argument("--mask-bg", action="store_true",
                    help="기기 상자 바깥을 단색으로 덮는다 — 배율은 두고 "
                         "배경 내용만 없애는 갈림 실험. 배포에 없다")
    a = ap.parse_args()
    if a.photodir:
        for c in a.ckpt:
            predict_dir(c, a.photodir, a.prefix, a.conf, a.limit,
                        xml_dir=a.xml, crop=a.crop, crop_pad=a.crop_pad,
                        mask_bg=a.mask_bg)
        return
    out = []
    for c in a.ckpt:
        out.append(evaluate(c, a.conf, a.limit, not a.no_overlay))
        print()
    print(f"{'체크포인트':<18}{'n':>5}{'실패':>6}{'포함률1.0':>11}{'IoU중앙':>9}")
    for s in out:
        print(f"{s['name']:<18}{s['n']:>5}{s['miss']:>6}"
              f"{100*s['contain1']:>10.1f}%{s['iou_med']:>9.4f}")
    print("  **합성 합격률과 한 표에 놓지 않는다** — 정답이 다른 물건이다.")


if __name__ == "__main__":
    main()
