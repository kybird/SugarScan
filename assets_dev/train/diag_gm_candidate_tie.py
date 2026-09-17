# GM 검출 후보가 근접 동점인지 본다 — 왜 그 장이 전처리에 흔들렸는가.
#
# 배경(2026-09-17): 전처리 A/B 에서 glucose_batch1/1826 의 IoU 가 letterbox
# 0.526 -> yolox 0.039 로 무너졌다. 처음엔 채널 순서(RGB/BGR) 탓으로 보고했다.
# 틀렸다. 그 장의 두 입력은 픽셀 평균 3.4/255 밖에 안 다르고(거의 무채색이라
# R<->B 를 바꿔도 안 변한다), 진짜 원인은 **후보 두 개가 0.3% 차이로 붙어
# 있고 그 둘이 기하적으로 정반대**라는 것이었다 — 하나는 기기 전체, 하나는
# 작은 조각. 입력이 조금만 흔들려도 순위가 뒤집힌다.
#
# 그래서 "전처리가 나쁘다" 가 아니라 "이 장에서 검출기가 못 정한다" 가 답이다.
# 이 스크립트가 그 구별을 낸다:
#   - 두 전처리의 입력 픽셀 차이 (작으면 전처리 탓이 아니다)
#   - 상위 후보들의 점수와 상자 (붙어 있으면 동전 던지기다)
#   - 상위 두 후보의 넓이비 (정반대면 top-1 을 그냥 믿으면 안 된다)
#
# 사용:
#   python diag_gm_candidate_tie.py --ids glucose_batch1/1826,glucose_batch1/1598
import argparse
import json
import sys
from pathlib import Path

import numpy as np
import torch

sys.path.insert(0, "D:/tmp/YOLOX")
from yolox.exp import get_exp  # noqa: E402
from yolox.utils import postprocess  # noqa: E402

import detect_datumo_gm as D  # _load_bgr · _prep 를 그대로 쓴다  # noqa: E402

HERE = Path(__file__).resolve().parent
DATUMO = HERE.parent / "upstream" / "datumo"
CKPT = HERE / "yolox_out" / "gmscreen_ft3" / "best_ckpt_np1.pth"
TIE_REL = 0.05      # 상위 두 후보 점수가 이 비율 안이면 '근접 동점'


# ── 공용 부품 — GM 검출 후보 뽑기 ────────────────────────────────────────
# diag_ft3_miss5.py 가 이 둘을 부른다. 같은 추론 경로를 두 파일이 각자 짜면
# 한쪽만 고쳐져 두 진단이 다른 말을 한다([[duplicated-geometry-implementation]]).
# 실제로 2026-09-17 에 그렇게 만들었다가 합쳤다.

def load_model(ckpt=None):
    exp = get_exp("D:/tmp/YOLOX/reading_exp.py", "reading")
    model = exp.get_model()
    model.load_state_dict(
        torch.load(str(ckpt or CKPT), map_location="cpu")["model"])
    return model.eval().cuda()


def candidates(model, img0, imgsz, mode, conf):
    """(점수 내림차순 [(점수, [x0,y0,x1,y1])], 되돌리는 배율) — 원본 좌표계.

    전처리는 detect_datumo_gm._prep 하나만 쓴다. 여기서 다시 짜지 않는다.
    """
    arr, (sx, sy) = D._prep(img0, imgsz, mode)
    x = torch.from_numpy(arr).permute(2, 0, 1)[None].float().cuda()
    with torch.no_grad():
        det = postprocess(model(x), 1, conf, 0.45)[0]
    if det is None or len(det) == 0:
        return [], (sx, sy)
    o = det.cpu().numpy()
    sc = o[:, 4] * o[:, 5]
    out = [(float(sc[k]),
            [float(o[k][0]) * sx, float(o[k][1]) * sy,
             float(o[k][2]) * sx, float(o[k][3]) * sy])
           for k in np.argsort(sc)[::-1]]
    return out, (sx, sy)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ids", required=True, help="쉼표로 구분한 사진 id")
    ap.add_argument("--ckpt", default=str(CKPT))
    ap.add_argument("--imgsz", type=int, default=416)
    ap.add_argument("--modes", default="letterbox,yolox")
    args = ap.parse_args()

    rows = {}
    for l in (DATUMO / "labels.jsonl").read_text(encoding="utf-8").splitlines():
        if l.strip():
            j = json.loads(l)
            rows[j["id"]] = j["image"]

    model = load_model(args.ckpt)
    modes = [m.strip() for m in args.modes.split(",") if m.strip()]
    print(f"체크포인트 {Path(args.ckpt).name} · imgsz {args.imgsz} · 전처리 {modes}")

    for gid in [g.strip() for g in args.ids.split(",") if g.strip()]:
        img0 = D._load_bgr(DATUMO / rows[gid])
        print(f"\n── {gid} ({img0.shape[1]}x{img0.shape[0]}) " + "─" * 24)

        prepped = {m: D._prep(img0, args.imgsz, m) for m in modes}
        if len(modes) == 2:
            a = prepped[modes[0]][0].astype(np.float32)
            b = prepped[modes[1]][0].astype(np.float32)
            diff = np.abs(a - b)
            print(f"  두 입력 픽셀차: 평균 {diff.mean():.2f} · max {diff.max():.0f}"
                  f"  (0~255)")
            # 무채색이면 채널 순서가 바뀌어도 픽셀이 안 변한다.
            bgr = img0.astype(np.float32)
            print(f"  화면 밖 포함 |R-B| 평균: {np.mean(np.abs(bgr[:, :, 2] - bgr[:, :, 0])):.1f}"
                  f"  (작으면 무채색 — 채널 순서 탓을 하기 어렵다)")

        for m in modes:
            cands, _ = candidates(model, img0, args.imgsz, m, 0.10)
            if not cands:
                print(f"  {m:<10} 후보 없음(conf 0.10)")
                continue
            print(f"  {m}:")
            areas = []
            for sc_, bx in cands[:3]:
                w_, h_ = bx[2] - bx[0], bx[3] - bx[1]
                areas.append(w_ * h_)
                print(f"     점수 {sc_:.4f}  상자 {w_:7.0f}x{h_:<7.0f}"
                      f" at ({bx[0]:.0f},{bx[1]:.0f})")
            if len(cands) >= 2:
                s1, s2 = cands[0][0], cands[1][0]
                rel = (s1 - s2) / max(s1, 1e-9)
                ar = max(areas[0], areas[1]) / max(min(areas[0], areas[1]), 1e-9)
                flag = "근접 동점" if rel <= TIE_REL else "명확한 1위"
                print(f"     -> 1·2위 점수차 {100 * rel:.1f}% ({flag}) · "
                      f"넓이비 {ar:.1f}배")
                if rel <= TIE_REL and ar >= 3:
                    print("     -> 붙어 있는데 기하가 정반대다. top-1 을 그냥 "
                          "믿으면 입력이 조금만 흔들려도 상자가 뒤집힌다.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
