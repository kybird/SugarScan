# 물리 패널 재구성 카드 — 실측 기준선 스크립트 (2026-09-12).
#
# 세 축을 직접 잰다(보고서 수치는 남이 쓴 것을 옮기지 않는다 — 원본을 본다):
#   1) 종횡비 — GM 박스(물리 패널) w/h 분포. 표시 좌표계(oriented) 기준.
#      raw 좌표계는 EXIF 미적용이라 83.5% 가 세로 회전 상태 → w/h 뒤집힘.
#   2) 밴드 기하 — 사람 밴드 라벨(97장, 읽기 전용)과 GM 쿼드를 id 조인해
#      밴드가 패널에서 차지하는 폭·높이 비율과 위치를 잰다. 세로/가로 패널별로.
#   3) 밀도 — 숫자 영역(밴드) 밖 Canny 엣지 밀도. 실사진 GM 크롭 vs 합성 패널을
#      같은 자로: 긴 변 896 리사이즈 → (3,3) 블러 → Canny(50,150) →
#      밴드 bbox 밖 픽셀 중 엣지 픽셀 비율.
#
# 사용:
#   conda run -n sugartrain python measure_panel_stats.py aspect
#   conda run -n sugartrain python measure_panel_stats.py band
#   conda run -n sugartrain python measure_panel_stats.py density --limit 97
#   conda run -n sugartrain python measure_panel_stats.py synth-density \
#       --images <dir> --manifest <jsonl>
import argparse
import json
from collections import defaultdict
import sys
from pathlib import Path

import cv2
import numpy as np

HERE = Path(__file__).resolve().parent

# GM 쿼드는 사람 라벨 우선이다(gm_quads.load_gm_quads, 2026-09-13).
# 구판은 검출기 출력(gmscreen_quads_oriented)만 봤고 그걸 실측이라
# 불렀다 — 사람이 그린 화면 상자 411행이 따로 있었는데 측정 경로
# 어디도 쓰지 않았다.
from gm_quads import quad_rows  # noqa: E402
UPSTREAM = HERE.parent / "upstream" / "datumo"
QUADS_ORIENTED = HERE / "gmscreen_quads_oriented.jsonl"   # 읽기 전용 사본(보고서에 md5 기록)
BAND_BOXES = HERE / "band_boxes.jsonl"                    # git 추적, 읽기 전용
LONG_SIDE = 896        # 카드 AC#7 — 패널 긴 변


def _load_jsonl(p):
    rows = []
    with open(p, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def _rect_of(quad):
    q = np.asarray(quad, np.float64)
    return q[:, 0].min(), q[:, 1].min(), q[:, 0].max(), q[:, 1].max()


def collect_aspect():
    """GM 쿼드(표시 좌표계) w/h 전체 목록 — cmd_aspect 와 정본 기준선 생성기
    (make_real_baseline.py)가 같은 코드를 쓴다. 자가 갈리면 두 수치는 비교
    대상이 아니다(2026-09-12 밀도 사고)."""
    ratios = []
    for r in quad_rows():
        x0, y0, x1, y1 = _rect_of(r["quad"])
        ratios.append((x1 - x0) / max(1.0, y1 - y0))
    return ratios


def cmd_aspect():
    a = np.asarray(collect_aspect())
    pct = lambda q: float(np.percentile(a, q))
    print(f"n={len(a)}  분모={vs}"
          + ("  (유리 쿼드 — 배율 불변, 실사진 GM 쿼드와 같은 물건)"
             if vs == "glass" else "  (캔버스 — 배율 난수가 들어간 뒤로는"
             " 실사진과 맞대면 안 된다)"))
    print(f"w/h median={np.median(a):.3f} p10={pct(10):.3f} p90={pct(90):.3f} "
          f"p5={pct(5):.3f} p95={pct(95):.3f}")
    print(f"portrait(w/h<1)={np.mean(a < 1.0) * 100:.1f}%  "
          f"wide(w/h>1)={np.mean(a > 1.0) * 100:.1f}%  "
          f"very-wide(w/h>2)={np.mean(a > 2.0) * 100:.1f}%")
    # 히스토그램(0.1 간격) — 렌더 샘플러 설계용 원본 분포
    hist, edges = np.histogram(a, bins=np.arange(0.0, 3.05, 0.1))
    for h, e in zip(hist, edges):
        if h:
            print(f"  [{e:.1f},{e + 0.1:.1f}) {h:5d} {'#' * int(h / 10)}")


def collect_band():
    """밴드 기하 원본 — (joined, total, stats, pos). cmd_band 와 정본 기준선
    생성기가 같은 코드를 쓴다."""
    quads = {r["id"]: r for r in quad_rows()}
    bands = _load_jsonl(BAND_BOXES)
    joined = 0
    stats = {"portrait": [], "wide": []}
    pos = {"portrait": [], "wide": []}
    for b in bands:
        g = quads.get(b["id"])
        if g is None:
            continue
        joined += 1
        gx0, gy0, gx1, gy1 = _rect_of(g["quad"])
        bx0, by0, bx1, by1 = _rect_of(b["quad"])
        gw, gh = gx1 - gx0, gy1 - gy0
        bw, bh = bx1 - bx0, by1 - by0
        key = "portrait" if gw / gh < 1.0 else "wide"
        stats[key].append((bw / gw, bh / gh))
        pos[key].append(((bx0 + bx1) / 2 - gx0) / gw)   # 밴드 중심 x (패널 좌 frac)
        pos[key].append(0)                                # 자리 표시(아래에서 y 따로)
        pos[key][-1] = ((by0 + by1) / 2 - gy0) / gh
    return joined, len(bands), stats, pos


def cmd_band():
    joined, total, stats, pos = collect_band()
    print(f"join={joined}/{total}")
    _report_band(stats, pos)


def _report_band(stats, pos):
    """밴드 기하 출력 — 실사진(cmd_band)과 합성(cmd_synth_band)이 이 한 코드로
    찍는다. 자가 갈리면 두 수치는 비교 대상이 아니다(2026-09-12 밀도 사고)."""
    for key in ("portrait", "wide"):
        if not stats[key]:
            print(f"{key}: 표본 없음")
            continue
        a = np.asarray(stats[key])
        n = len(a)
        cx = np.asarray(pos[key][0::2])
        cy = np.asarray(pos[key][1::2])
        p = lambda arr, q: float(np.percentile(arr, q))
        print(f"{key} n={n}")
        print(f"  band_w/panel_w median={np.median(a[:, 0]):.3f} "
              f"[p10={p(a[:, 0], 10):.3f} p90={p(a[:, 0], 90):.3f}]")
        print(f"  band_h/panel_h median={np.median(a[:, 1]):.3f} "
              f"[p10={p(a[:, 1], 10):.3f} p90={p(a[:, 1], 90):.3f}]")
        print(f"  band_cx median={np.median(cx):.3f} [p10={p(cx, 10):.3f} "
              f"p90={p(cx, 90):.3f}]")
        print(f"  band_cy median={np.median(cy):.3f} [p10={p(cy, 10):.3f} "
              f"p90={p(cy, 90):.3f}]")


def cmd_shortcut(fit_manifest, test_manifest, by="orient"):
    """**숫자를 보지 않는 오라클**을 합성 게이트에 걸어 본다.

    묻는 것: 우리 게이트가 "숫자 필드를 찾았다"를 재고 있는가, 아니면
    "유리 쿼드를 고정 비율로 줄였다"만으로도 넘어가는가.

    왜 이 자가 필요한가(2026-09-18 사람 지적 "학습이 모양을 보고 배우는 게
    아니라 비율을 보고 배우냐"): 합성에서 정답 상자가 유리 쿼드의 거의 고정된
    아핀 축소라면, 모델은 밴드의 **모양**(숫자 글리프의 범위)을 배우지 않고
    유리 모서리를 찾아 비율만 곱하는 **지름길**을 배울 수 있다. 유리 모서리는
    생성기가 베젤 홈·하이라이트까지 그려 넣은 가장 강한 모서리다. 지름길은
    합성에서는 정답이지만 실촬에서는 기기 외곽으로 옮겨 붙는다.

    방법: fit 세트에서 방향별로 (band/glass) 비율의 **중앙값 하나**를 뽑는다.
    파라미터는 방향당 4개(cx, cy, w비, h비)뿐이고 픽셀은 한 장도 보지 않는다.
    test 세트의 glass_quad 에 그 비율을 곱해 상자를 내고, 학습된 모델과
    **같은 게이트**(digit_box 가 예측 상자에 100% 드는 장의 비율)로 잰다.

    읽는 법: 이 오라클 점수가 모델 점수에 근접하면 게이트는 모양을 재고 있지
    않다 — 지름길이 통과에 충분하다는 뜻이다. 낮게 나오면 모델은 유리만으로는
    낼 수 없는 무언가를 배운 것이다.
    """
    def rows(p):
        return [json.loads(l) for l in Path(p).read_text(encoding="utf-8")
                .splitlines() if l.strip()]

    def gbox(r):
        g = np.asarray(r["glass_quad"], np.float64)
        return (g[:, 0].min(), g[:, 1].min(), g[:, 0].max(), g[:, 1].max())

    def orient(r):
        x0, y0, x1, y1 = gbox(r)
        o = "wide" if (x1 - x0) >= (y1 - y0) else "portrait"
        # by=profile: 기기를 알아본 뒤 그 기기의 배치를 외우는 지름길을 잰다.
        # 방향만으로 쓰는 것보다 강하지만, 실촬에서는 프로파일 목록에 없는
        # 기기 앞에서 무너진다 — 어느 쪽이 통과를 설명하는지 갈라야 한다.
        return f'{r.get("profile", "?")}|{o}' if by == "profile" else o

    fit = defaultdict(list)
    for r in rows(fit_manifest):
        x0, y0, x1, y1 = gbox(r)
        W, H = x1 - x0, y1 - y0
        b = [float(v) for v in r["box"]]
        fit[orient(r)].append((((b[0] + b[2]) / 2 - x0) / W,
                               ((b[1] + b[3]) / 2 - y0) / H,
                               (b[2] - b[0]) / W, (b[3] - b[1]) / H))
    par = {k: np.median(np.asarray(v), axis=0) for k, v in fit.items()}
    print(f"기준={by}  파라미터 {4 * len(par)}개 · 픽셀 0장")
    print(f"fit  {Path(fit_manifest).parent.name}  n={sum(len(v) for v in fit.values())}")
    if len(par) <= 4:
        for k, p in sorted(par.items()):
            print(f"  {k:<9} cx={p[0]:.3f} cy={p[1]:.3f} "
                  f"w비={p[2]:.3f} h비={p[3]:.3f}")

    te = rows(test_manifest)
    per = defaultdict(lambda: [0, 0])
    ok = n = 0
    for r in te:
        if "digit_box" not in r:
            continue
        x0, y0, x1, y1 = gbox(r)
        W, H = x1 - x0, y1 - y0
        k = orient(r)
        if k not in par:      # fit 에 없는 조합은 채점에서 뺀다
            continue
        cx, cy, wr, hr = par[k]
        px, py = x0 + cx * W, y0 + cy * H
        pw, ph = wr * W / 2, hr * H / 2
        p = (px - pw, py - ph, px + pw, py + ph)
        d = [float(v) for v in r["digit_box"]]
        hit = d[0] >= p[0] and d[1] >= p[1] and d[2] <= p[2] and d[3] <= p[3]
        n += 1
        ok += hit
        s = per[r.get("profile", "?")]
        s[0] += hit
        s[1] += 1
    print(f"test {Path(test_manifest).parent.name}  n={n}")
    print(f"  **유리 비율 오라클({by}) 합격률 {100.0 * ok / n:.2f}%**  "
          f"(게이트: digit_box 100% 포함, eval_band.py 와 같은 정의)")
    worst = sorted(per.items(), key=lambda kv: kv[1][0] / kv[1][1])[:5]
    print("  프로파일 최저 5:")
    for name, (h, t) in worst:
        print(f"    {name:<22} {100.0 * h / t:5.1f}%  ({h}/{t})")


def cmd_synth_band(manifest, vs="canvas"):
    """합성 패널의 종횡비·밴드 기하.

    **분모를 고르는 것이 이 자의 핵심이다.**

      vs=canvas  패널 = 이미지 전체. 구판의 유일한 모드였다. 합성이 패널만
                 꽉 채워 렌더하던 시절에는 이게 실사진의 GM 패널과 얼추
                 대응했다. **2026-09-17 촬영 배율 난수(CAM_ZOOM_RANGE)가
                 들어간 뒤로는 대응하지 않는다** — 캔버스에 배경 여백이
                 들어가서 band_w/canvas_w 가 줌만큼 작아진다. 이 모드로
                 실사진과 맞대면 없는 격차를 만들어 낸다.

      vs=glass   패널 = 유리 쿼드(manifest glass_quad). **배율에 불변**이고
                 실사진 쪽 분모인 GM 화면 쿼드와 같은 물건이다
                 (collect_band 가 quad_rows 의 화면 쿼드를 쓴다).
                 합성과 실촬의 밴드 라벨 **규약**을 맞댈 때는 이쪽을 쓴다.

    방향 분류도 같은 분모로 한다 — 캔버스 종횡비로 가르고 유리로 재면
    두 좌표계가 섞인다.
    """
    rows = _load_jsonl(manifest)
    stats = {"portrait": [], "wide": []}
    pos = {"portrait": [], "wide": []}
    asp = []
    for r in rows:
        bx0, by0, bx1, by1 = (float(v) for v in r["box"])
        if vs == "glass":
            if "glass_quad" not in r:
                raise SystemExit("매니페스트에 glass_quad 가 없다 — "
                                 "구판 코퍼스라면 --vs canvas 로 재라")
            g = np.asarray(r["glass_quad"], np.float64)
            gx0, gy0 = g[:, 0].min(), g[:, 1].min()
            gx1, gy1 = g[:, 0].max(), g[:, 1].max()
        else:
            gx0, gy0, gx1, gy1 = 0.0, 0.0, float(r["w"]), float(r["h"])
        W, H = gx1 - gx0, gy1 - gy0
        asp.append(W / H)
        key = "portrait" if W / H < 1.0 else "wide"
        stats[key].append(((bx1 - bx0) / W, (by1 - by0) / H))
        pos[key].append(((bx0 + bx1) / 2 - gx0) / W)
        pos[key].append(((by0 + by1) / 2 - gy0) / H)
    a = np.asarray(asp)
    print(f"n={len(a)}")
    print(f"w/h median={np.median(a):.3f} p10={np.percentile(a, 10):.3f} "
          f"p90={np.percentile(a, 90):.3f}")
    print(f"portrait(w/h<1)={np.mean(a < 1.0) * 100:.1f}%  "
          f"wide(w/h>1)={np.mean(a > 1.0) * 100:.1f}%  "
          f"very-wide(w/h>2)={np.mean(a > 2.0) * 100:.1f}%")
    _report_band(stats, pos)


def _crop_by_rect(img, rect, long_side=LONG_SIDE):
    x0, y0, x1, y1 = rect
    x0, y0 = max(0, int(round(x0))), max(0, int(round(y0)))
    x1, y1 = min(img.shape[1], int(round(x1))), min(img.shape[0], int(round(y1)))
    if x1 - x0 < 8 or y1 - y0 < 8:
        return None
    crop = img[y0:y1, x0:x1]
    s = long_side / max(crop.shape)
    return cv2.resize(crop, (max(8, int(round(crop.shape[1] * s))),
                             max(8, int(round(crop.shape[0] * s)))),
                      interpolation=cv2.INTER_AREA)


def edge_density_outside(gray, band_rect_frac, exclude_frame=0.0):
    """gray: 긴 변 896 정규화 크롭. band_rect_frac: (x0,y0,x1,y1) 를 0~1 비율로.
    exclude_frame>0 이면 양변에서 그 비율만큼 외곽 프레임을 마스크에서 뺀다 —
    베젤 테두리 엣지가 content 밀도를 대신하지 못하게(2026-09-12 파일럿에서
    테두리만으로 3.2% 가 나와 floor 가 허위 통과한 뒤 정정)."""
    H, W = gray.shape
    b = cv2.GaussianBlur(gray, (3, 3), 0)
    e = cv2.Canny(b, 50, 150)
    m = np.ones((H, W), bool)
    x0, y0, x1, y1 = band_rect_frac
    m[int(y0 * H):int(np.ceil(y1 * H)), int(x0 * W):int(np.ceil(x1 * W))] = False
    if exclude_frame > 0:
        mx, my = int(exclude_frame * W), int(exclude_frame * H)
        m[:my, :] = False
        m[H - my:, :] = False
        m[:, :mx] = False
        m[:, W - mx:] = False
    if m.sum() < 100:
        return None
    return float((e > 0)[m].mean())


def collect_density(limit=0, frame_exc=0.0):
    """실사진 GM 크롭 밴드 밖 엣지 밀도값 목록 — cmd_density 와 정본 기준선
    생성기가 같은 코드를 쓴다. synth_panel.REAL_DENSITY 가 이 값을 재표본한다."""
    quads = {r["id"]: r for r in quad_rows()}
    bands = _load_jsonl(BAND_BOXES)
    vals = []
    roots = [UPSTREAM / "extracted" / "TILDE"]
    for b in bands[:limit] if limit else bands:
        g = quads.get(b["id"])
        if g is None:
            continue
        rel = None
        for root in roots:
            p = root / (b["id"].replace("/", "\\") + ".jpg")
            p2 = root / (b["id"].replace("/", "/") + ".jpg")
            if p.exists():
                rel = p
                break
            if p2.exists():
                rel = p2
                break
        if rel is None:
            continue
        img = cv2.imread(str(rel), cv2.IMREAD_GRAYSCALE)
        if img is None:
            continue
        gx = _rect_of(g["quad"])
        crop = _crop_by_rect(img, gx)
        if crop is None:
            continue
        # 밴드 rect 를 크롭 좌표계 비율로
        bx = _rect_of(b["quad"])
        gw, gh = gx[2] - gx[0], gx[3] - gx[1]
        frac = ((bx[0] - gx[0]) / gw, (bx[1] - gx[1]) / gh,
                (bx[2] - gx[0]) / gw, (bx[3] - gx[1]) / gh)
        d = edge_density_outside(crop, frac, exclude_frame=frame_exc)
        if d is not None:
            vals.append(d)
    return vals


def cmd_density(limit, frame_exc):
    a = np.asarray(collect_density(limit, frame_exc))
    print(f"n={len(a)} frame_exc={frame_exc}")
    print(f"density median={np.median(a):.4f} p10={np.percentile(a, 10):.4f} "
          f"p90={np.percentile(a, 90):.4f} min={a.min():.4f} max={a.max():.4f}")


def cmd_synth_density(images_dir, manifest, frame_exc):
    imgs = Path(images_dir)
    rows = _load_jsonl(manifest)
    vals = []
    for r in rows:
        p = imgs / (r["id"] + ".png")
        if not p.exists():
            continue
        gray = cv2.imread(str(p), cv2.IMREAD_GRAYSCALE)
        q = np.asarray(r["quad"], np.float64)
        x0, y0 = q[:, 0].min(), q[:, 1].min()
        x1, y1 = q[:, 0].max(), q[:, 1].max()
        H, W = gray.shape
        frac = (x0 / W, y0 / H, x1 / W, y1 / H)
        d = edge_density_outside(gray, frac, exclude_frame=frame_exc)
        if d is not None:
            vals.append(d)
    a = np.asarray(vals)
    print(f"n={len(a)} frame_exc={frame_exc}")
    print(f"density median={np.median(a):.4f} p10={np.percentile(a, 10):.4f} "
          f"p90={np.percentile(a, 90):.4f} min={a.min():.4f} max={a.max():.4f}")



def cmd_coco(path, limit=0):
    """COCO 주석 세트에서 **상자가 장면을 얼마나 차지하는가**를 잰다.

    왜 이 축인가(2026-09-17 사람 지적: "확대축소도 필요할거같더라"): 합성기의 zoom 은 난수가 아니라 쿼드가
    캔버스를 넘칠 때만 내려가는 사다리다. 기본이 1.0 이라 유리가 늘 캔버스를
    꽉 채운다 — 즉 **피사체 크기가 거의 고정**이다. 실촬은 그렇지 않다.

    두 축을 인쇄한다:
      넓이비   상자 넓이 / 이미지 넓이.  '얼마나 크게 찍혔나'
      선형비   sqrt(넓이비).  배율은 선형으로 생각하는 편이 낫다
                (넓이 4배 = 배율 2배)
      종횡비   상자 w/h

    **모집단을 반드시 함께 읽을 것.** 세트마다 상자가 가리키는 물건이 다르면
    절대값을 맞대면 안 된다([[comparison-across-different-denominators]]).

    **실촬 수치가 필요하면 cmd_band_frame(band-frame)을 쓴다.** 이 자에
    Roboflow COCO 를 먹이지 마라 — CC BY 4.0 귀속 의무로 배제된 데이터셋이고
    (docs/LICENSES.md §1.1), 2026-09-17 에 내가 그걸로 합성 설계값을 정했다가
    사람이 잡았다.
    """
    j = json.loads(Path(path).read_text(encoding="utf-8"))
    wh = {im["id"]: (im["width"], im["height"]) for im in j["images"]}
    frac, asp = [], []
    for an in j["annotations"]:
        W, H = wh[an["image_id"]]
        w, h = an["bbox"][2], an["bbox"][3]
        if w <= 0 or h <= 0 or W <= 0 or H <= 0:
            continue
        frac.append((w * h) / (W * H))
        asp.append(w / h)
        if limit and len(frac) >= limit:
            break
    f = np.asarray(frac)
    lin = np.sqrt(f)
    a = np.asarray(asp)
    print(f"모집단 {path}  n={len(f)}")
    for name, v in (("넓이비", f), ("선형비", lin), ("종횡비", a)):
        print(f"  {name:<6} p10={np.percentile(v,10):.4f} "
              f"중앙={np.median(v):.4f} p90={np.percentile(v,90):.4f} "
              f"최소={v.min():.4f} 최대={v.max():.4f}")
    print(f"  선형비 퍼짐 p90/p10 = {np.percentile(lin,90)/np.percentile(lin,10):.2f}배"
          f"  (최대/최소 {lin.max()/lin.min():.2f}배)")
    print("  주의: 상자가 가리키는 물건이 세트마다 다르다. 절대값이 아니라"
          " 세트 안의 퍼짐을 본다.")



def cmd_band_frame(limit=0):
    """**우리 코퍼스**에서 밴드·LCD 가 사진 전체에서 차지하는 비율.

    모집단은 평가 모집단과 같다 — 사람 밴드 라벨 + LCD 쿼드가 둘 다 있고
    사람 제외 선언(band_label_excluded.jsonl)에 없는 장. 즉 검출기를 채점하는
    바로 그 장들이다. 다른 모집단에서 잰 값을 여기에 섞지 않는다.

    **Roboflow 데이터셋을 쓰지 않는다.** CC BY 4.0 귀속 의무 때문에 이 계열
    작업에서 배제하기로 한 결정이 있다(docs/LICENSES.md §1.1, doc/raw/2026-09-17).
    2026-09-17 에 내가 그걸 어기고 Roboflow COCO 로 촬영 배율 폭을 정했다가
    사람이 잡았다 — 배제한 데이터셋이 생성기 설계값으로 되돌아온 셈이었다.

    인쇄하는 것:
      LCD/사진   LCD 쿼드 외접상자 넓이 / 사진 넓이
      밴드/사진  사람 밴드 라벨 외접상자 넓이 / 사진 넓이
      선형비는 sqrt(넓이비). 배율은 선형으로 생각하는 편이 낫다.
    """
    from band_exclusions import load_excluded
    ex = set(load_excluded())
    lab = {}
    for line in (UPSTREAM / "labels.jsonl").read_text(encoding="utf-8").splitlines():
        if line.strip():
            j = json.loads(line)
            lab[j["id"]] = j["image"]
    gm = {r["id"]: r for r in quad_rows()}
    bands = {}
    for line in BAND_BOXES.read_text(encoding="utf-8").splitlines():
        if line.strip():
            j = json.loads(line)
            if j.get("quad"):
                bands[j["id"]] = j["quad"]

    ids = [i for i in sorted(bands) if i in gm and i in lab and i not in ex]
    if limit:
        ids = ids[:limit]
    wide = set(json.loads((HERE / "_diag" / "wide_all" / "wide_ids.json")
                          .read_text(encoding="utf-8")))

    def box(q):
        a = np.asarray(q, float)
        return (a[:, 0].max() - a[:, 0].min()) * (a[:, 1].max() - a[:, 1].min())

    rows = []
    for cid in ids:
        im = cv2.imread(str(UPSTREAM / lab[cid]))
        if im is None:
            continue
        area = im.shape[0] * im.shape[1]
        rows.append((cid, box(gm[cid]["quad"]) / area, box(bands[cid]) / area))
    print(f"모집단: 사람 밴드 라벨 + LCD 쿼드, 사람 제외 뺌  n={len(rows)} "
          f"(가로형 {sum(1 for r in rows if r[0] in wide)})")
    print(f"  제외 선언으로 뺀 장 {len(ex)} · 사진은 **전체 혈당기 사진**이다")
    for name, k in (("LCD/사진", 1), ("밴드/사진", 2)):
        for grp, sel in (("전체", rows),
                         ("세로형", [r for r in rows if r[0] not in wide]),
                         ("가로형", [r for r in rows if r[0] in wide])):
            if not sel:
                continue
            v = np.asarray([r[k] for r in sel])
            lin = np.sqrt(v)
            print(f"  {name:<9} {grp:<4} n={len(sel):<4} "
                  f"넓이 중앙={np.median(v):.4f}  선형 p10={np.percentile(lin,10):.3f} "
                  f"중앙={np.median(lin):.3f} p90={np.percentile(lin,90):.3f} "
                  f"| 선형 퍼짐 p90/p10={np.percentile(lin,90)/np.percentile(lin,10):.2f}배")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["aspect", "band", "density", "synth-density",
                                    "synth-band", "coco", "band-frame",
                                    "shortcut"])
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--frame-exc", type=float, default=0.0)
    ap.add_argument("--images")
    ap.add_argument("--manifest")
    ap.add_argument("--coco", help="instances_*.json 경로")
    ap.add_argument("--fit", help="shortcut: 비율을 뽑을 매니페스트")
    ap.add_argument("--by", default="orient", choices=("orient", "profile"),
                    help="shortcut: 비율을 방향별로 뽑나 기기별로 뽑나")
    ap.add_argument("--vs", default="canvas", choices=("canvas", "glass"),
                    help="synth-band 의 분모. 실사진과 맞댈 때는 glass")
    a = ap.parse_args()
    if a.cmd == "aspect":
        cmd_aspect()
    elif a.cmd == "band":
        cmd_band()
    elif a.cmd == "density":
        cmd_density(a.limit, a.frame_exc)
    elif a.cmd == "band-frame":
        cmd_band_frame(a.limit)
    elif a.cmd == "coco":
        if not a.coco:
            print("--coco 가 필요하다", file=sys.stderr)
            return 2
        cmd_coco(a.coco, a.limit)
    elif a.cmd == "shortcut":
        if not (a.manifest and a.fit):
            print("--fit 과 --manifest 가 필요하다", file=sys.stderr)
            return 2
        cmd_shortcut(a.fit, a.manifest, a.by)
    elif a.cmd == "synth-band":
        if not a.manifest:
            print("--manifest 가 필요하다", file=sys.stderr)
            return 2
        cmd_synth_band(a.manifest, a.vs)
    else:
        if not (a.images and a.manifest):
            print("--images 와 --manifest 가 필요하다", file=sys.stderr)
            return 2
        cmd_synth_density(a.images, a.manifest, a.frame_exc)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
