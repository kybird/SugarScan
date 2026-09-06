# 판독 실패 아틀라스 — 파이프라인 중간 산출물을 케이스 한 건·한 행에 나란히
# 놓아 "어느 단계에서 틀렸는가"를 눈으로 가르는 정적 HTML 컨택트 시트 생성기.
#
# 한 행의 구성:
#   (1) 원본(EXIF 표시 좌표계) 위에 GM 예측 쿼드(파랑)·BOX_MARGIN 크롭 박스(마젠타)
#       ·사람 라벨(밴드=노랑, LCD=초록). 원본 해상도 전체판은 행에서 링크로 건다 —
#       축소 렌더로 경계 판단 금지(downscaled-view-as-evidence).
#   (2) 리더에 실제 들어간 320x160 워프
#   (3) CTC 타임스텝별 argmax 문자·확률 띠 (40칸)
#   (4) TTA 변형별 디코드·득표
#   (5) id/GT/예측/득표율/오류 분류 텍스트
#
# 지키는 규칙:
#   - 대조군 포함: 정답(저득표 우선 + 고득표 시드 표본)을 최소 오답 수만큼 섞는다.
#     실패만 모아 보면 공통 성질이 전부 원인처럼 보인다(2026-09-04 두 번 반증).
#   - 층 유지: risky → safe → blank → 정답(저득표) → 정답(고득표) 순서로 놓고
#     사전순 섞지 않는다. 중간에 멈춰도 한 층이 통째로 비지 않게.
#   - 기하·EXIF·디코딩은 eval_reader.py 를 import 해서 쓴다(재구현 금지 —
#     duplicated-geometry-implementation). 시작 시 npz holdout 크롭과 픽셀
#     등가성을 검사해 재사용이 어긋나지 않았음을 증명한다.
#   - 오류 분류는 webtool.py api_failures 의 기준을 그대로: risky(자릿수 보존
#     오독)/safe(자릿수 변동)/blank(무출력)/rejected(득표율 < REJECT_AT=0.778).
#     새로 정의하지 않는다. 값이 갈라지면 webtool 을 정본으로 맞춘다.
#   - 모든 입력은 읽기 전용. 산출물은 이 스크립트 위치의 _diag/atlas/ 만.
#
# 실행(워크트리 — 데이터는 메인 트리에서 읽는다):
#   conda run -n sugartrain python make_failure_atlas.py \
#       --data-root D:/Project/sugarScan/assets_dev/train
# 메인 트리에서 그대로 돌리면 --data-root 기본값(스크립트 자신의 디렉터리)이 맞다.
import argparse
import json
import subprocess
import zlib
from collections import Counter
from datetime import datetime
from pathlib import Path

import cv2
import numpy as np
import tensorflow as tf

# 기하·EXIF·디코드의 정본. eval_reader 는 tensorflow 를 module level 에서 import
# 하고 main() 안에서만 자기 경로(HERE)의 파일을 읽으므로, 여기서 import 하는 것은
# 부작용이 없다.
from eval_reader import (IN_H, IN_W, NUM_CLASSES, TTA_N, TTA_SEED,
                         _decode, _jitter, frame_crop, framed_src_rect,
                         load_gray)

HERE = Path(__file__).resolve().parent
OUT = HERE / "_diag" / "atlas"
BLANK = NUM_CLASSES - 1          # 10. NUM_CLASSES 가 아니다.
REJECT_AT = 0.778                # webtool.py api_failures 와 같은 값(정본: webtool)
N_CONTROL_LOW = 20               # 정답 중 득표 최저 대조군
N_CONTROL_HIGH = 20              # 정답 중 만장일치 대조군(시드 고정 표본)
CONTROL_SEED = 20260905
EQ_CHECK_N = 12                  # npz holdout 크롭과의 픽셀 등가성 검사 표본 수

# 오버레이 색. webtool 관례(파랑=GM 자동 예측, 노랑=사람 라벨)를 따르고,
# 크롭 박스(마젠타)·LCD 라벨(초록)을 더한다.
C_GM, C_CROP, C_BAND, C_LCD = ((255, 90, 30), (255, 0, 255),
                               (0, 230, 230), (0, 255, 60))


def read_jsonl(p: Path):
    out = {}
    if p.exists():
        for l in p.read_text(encoding="utf-8").splitlines():
            if l.strip():
                j = json.loads(l)
                out[j["id"]] = j
    return out


def classify(preds, readings, corrections):
    """webtool.py api_failures 의 분류 기준을 그대로 적용한다.

    gt 체인(corrections → readings → v[1])·blank 우선·자릿수 비교 순서 전부
    webtool 과 같아야 한다. 순서를 바꾸면 blank 가 safe 로 샌다.
    """
    rows = {}
    for cid, v in preds.items():
        gt = str(corrections.get(cid, readings.get(
            cid, v[1] if len(v) > 1 else v[0])))
        pred = str(v[0])
        ag = v[2] if len(v) > 2 else None
        if pred == gt:
            bucket = "exact"
        elif not pred:
            bucket = "blank"
        elif len(pred) == len(gt):
            bucket = "risky"
        else:
            bucket = "safe"
        rows[cid] = {"id": cid, "gt": gt, "pred": pred, "agree": ag,
                     "bucket": bucket,
                     "rejected": ag is not None and ag < REJECT_AT}
    return rows


def select_rows(rows):
    """층을 유지한 선택. risky → safe → blank(오답 전량) → 정답 저득표 → 정답 고득표."""
    def by_agree(rs):
        return sorted(rs, key=lambda r: (r["agree"] if r["agree"] is not None
                                         else 9.0, r["id"]))

    wrong = [r for r in rows.values() if r["bucket"] != "exact"]
    exact = [r for r in rows.values() if r["bucket"] == "exact"]
    strat = {"risky": [], "safe": [], "blank": []}
    for r in wrong:
        strat[r["bucket"]].append(r)
    ctrl_low = by_agree(exact)[:N_CONTROL_LOW]
    high_pool = [r for r in exact if r["agree"] == 1.0]
    rng = np.random.RandomState(CONTROL_SEED)
    picks = rng.permutation(len(high_pool))[:N_CONTROL_HIGH]
    ctrl_high = sorted((high_pool[i] for i in picks), key=lambda r: r["id"])
    sel = (by_agree(strat["risky"]) + by_agree(strat["safe"])
           + by_agree(strat["blank"]) + ctrl_low + ctrl_high)
    for r in sel:
        r["stratum"] = ("wrong_" + r["bucket"] if r["bucket"] != "exact"
                        else ("ctrl_low" if r in ctrl_low else "ctrl_high"))
    return sel


def side_metrics(quad, label):
    """GM 쿼드의 축정렬 박스 vs 사람 라벨 박스 — 검출 품질의 자동 지표.

    사람 라벨이 정본이라는 전제에서, 라벨 박스가 GM 박스 밖으로 나간 폭을
    변마다 잰다(build_cache_v2 의 GM 오차 분석과 같은 관점). 좌표는 전부
    원본(표시) 좌표계 픽셀.
    """
    q = np.asarray(quad, dtype=np.float64)
    lb = np.asarray(label["quad"], dtype=np.float64)

    def aabb(pts):
        return (float(pts[:, 0].min()), float(pts[:, 1].min()),
                float(pts[:, 0].max()), float(pts[:, 1].max()))

    gx0, gy0, gx1, gy1 = aabb(q)
    lx0, ly0, lx1, ly1 = aabb(lb)
    ix0, iy0 = max(gx0, lx0), max(gy0, ly0)
    ix1, iy1 = min(gx1, lx1), min(gy1, ly1)
    inter = max(0.0, ix1 - ix0) * max(0.0, iy1 - iy0)
    larea = max((lx1 - lx0) * (ly1 - ly0), 1e-6)
    garea = max((gx1 - gx0) * (gy1 - gy0), 1e-6)
    return {
        "iou": round(inter / (larea + garea - inter), 3),
        "label_recall": round(inter / larea, 3),   # 라벨 중 GM 박스가 덮은 비율
        "cut_left_px": round(max(0.0, gx0 - lx0), 1),
        "cut_right_px": round(max(0.0, lx1 - gx1), 1),
        "cut_top_px": round(max(0.0, gy0 - ly0), 1),
        "cut_bottom_px": round(max(0.0, ly1 - gy1), 1),
    }


def draw_overlay(gray, quad, crop_rect, labels):
    vis = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
    W = vis.shape[1]
    th = max(3, W // 420)

    def poly(pts, color):
        p = np.round(np.asarray(pts, dtype=np.float32)).astype(np.int32)
        cv2.polylines(vis, [p], True, color, th, cv2.LINE_AA)

    poly(quad, C_GM)         # GM 예측 쿼드
    poly(crop_rect, C_CROP)  # BOX_MARGIN 확장 크롭 박스
    for lab, color in labels:
        if lab is not None:
            poly(lab["quad"], color)
    return vis


def timestep_cells(logits_row):
    """40 타임스텝의 (argmax 클래스, 확률). logits_row: (40, NUM_CLASSES)."""
    m = logits_row.max(axis=-1, keepdims=True)
    e = np.exp(logits_row - m)
    probs = e / e.sum(axis=-1, keepdims=True)
    am = np.argmax(logits_row, axis=-1)
    return [(int(a), float(probs[t, a])) for t, a in enumerate(am)]


def greedy_with_collapse(am_row):
    """CTC 접기(중복 제거·blank 삭제)를 사람이 눈으로 따라갈 수 있게 표시."""
    out, prev = [], -1
    for v in am_row:
        v = int(v)
        out.append("." if v == BLANK else str(v))
        prev = v
    # 접힌 결과는 _decode 와 같은 규칙으로
    decoded = _decode(am_row[None, :])
    return "".join(out), decoded


def html_escape(s):
    return (str(s).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;"))


BUCKET_LABEL = {
    "risky": "위험(자릿수 보존 오독)",
    "safe": "안전(자릿수 변동)",
    "blank": "무출력",
    "exact": "정답",
}


def build_html(cases, meta, review):
    css = """
body{background:#141719;color:#d8dde2;font:13px/1.5 'Segoe UI',sans-serif;
     margin:0;padding:18px}
h1{font-size:18px;margin:0 0 4px}
.meta{color:#8aa0ae;font-size:12px;white-space:pre-wrap;
      background:#1b2024;padding:10px 12px;border-radius:6px}
.legend span{margin-right:14px;white-space:nowrap}
.sw{display:inline-block;width:14px;height:3px;vertical-align:middle;
    margin-right:4px}
.bar{position:sticky;top:0;background:#141719;padding:8px 0;z-index:5;
     border-bottom:1px solid #2a3138}
.bar label{margin-right:12px;white-space:nowrap}
.bar input[type=text]{background:#1b2024;color:#d8dde2;border:1px solid #2a3138;
     border-radius:4px;padding:3px 6px}
.row{border:1px solid #2a3138;border-radius:8px;margin:14px 0;padding:10px;
     background:#181c20}
.row.head{display:flex;gap:10px;flex-wrap:wrap;align-items:baseline}
.row.head .id{font-family:Consolas,monospace;font-weight:600;font-size:15px}
.badge{padding:1px 8px;border-radius:10px;font-size:12px;font-weight:600}
.b-risky{background:#5c1a1a;color:#ff9c9c}.b-safe{background:#4a3a10;color:#ffd97a}
.b-blank{background:#333a44;color:#aab7c4}.b-exact{background:#153f23;color:#8fe6a8}
.b-det-ok{background:#153f23;color:#8fe6a8}
.b-det-cut{background:#5c1a1a;color:#ff9c9c}.b-det-orient{background:#4a3a10;color:#ffd97a}
.b-det-wrong_area{background:#5c1a5c;color:#e39ce3}.b-det-wide{background:#4a3a10;color:#ffd97a}
.b-det-ambiguous{background:#333a44;color:#aab7c4}
.num{font-family:Consolas,monospace}
.panels{display:grid;grid-template-columns:430px 350px minmax(560px,1fr);
        gap:10px;margin-top:8px}
.panels img{width:100%;border-radius:4px;display:block;background:#000}
.cap{color:#8aa0ae;font-size:11px;margin:2px 0 6px}
.ts{display:flex;gap:1px;margin:4px 0}
.ts .c{width:13px;height:40px;border-radius:2px;display:flex;flex-direction:column;
       align-items:center;justify-content:center;font-family:Consolas,monospace;
       font-size:11px;color:#0d1114}
.ts .c small{font-size:8px;color:rgba(13,17,20,.85)}
.ts .c.low{outline:2px solid #ff5252}
table.tta{border-collapse:collapse;font-family:Consolas,monospace;font-size:12px}
table.tta td,table.tta th{border:1px solid #2a3138;padding:2px 7px;text-align:left}
.mono{font-family:Consolas,monospace;white-space:pre-wrap}
.warn{color:#ffb454}
a{color:#6fb3e0}
"""
    parts = []
    parts.append(f"<!DOCTYPE html><html lang=ko><head><meta charset=utf-8>"
                 f"<title>판독 실패 아틀라스</title><style>{css}</style></head>"
                 f"<body><h1>판독 실패 아틀라스 — 어느 단계에서 틀렸는가</h1>")

    m = meta
    parts.append(
        "<div class=meta>" + html_escape(m["blurb"]) + "</div>")

    parts.append(
        "<div class=meta legend><b>범례</b> — "
        f"<span><i class=sw style=background:rgb{C_GM[::-1]}></i>GM 예측 쿼드(gmscreen_quads)</span>"
        f"<span><i class=sw style=background:rgb{C_CROP[::-1]}></i>BOX_MARGIN 크롭 박스(리더 입력)</span>"
        f"<span><i class=sw style=background:rgb{C_LCD[::-1]}></i>사람 LCD 라벨(screen_boxes)</span>"
        f"<span><i class=sw style=background:rgb{C_BAND[::-1]}></i>사람 밴드 라벨(band_boxes)</span>"
        "<br><b>읽는 순서</b>: 왼쪽 원본에서 박스가 숫자줄을 감쌌는지 먼저 보고, "
        "가운데 워프가 리더가 실제 본 것이며, 오른쪽 띠·표가 리더의 확신이다."
        "</div>")

    parts.append(
        "<div class=meta>"
        "<b>주의 1 — CTC 타임스텝은 공간 위치가 아니다.</b> 리더에 BiLSTM 이 "
        "있어 각 타임스텝은 양방향 문맥을 본다. 타임스텝을 이미지 x 좌표에 "
        "겹쳐 읽는 것은 힌트는 되지만 증거가 아니다 — \u201c3번째 타임스텝이 "
        "오른쪽 숫자를 봤다\u201d고 단정하지 말 것.<br>"
        "<b>주의 2 — 축소 렌더로 경계 판단 금지.</b> 행의 원본 패널은 표시용 "
        "축소본이다. \u201c잘렸다\u201d고 말하기 전에 [원본 해상도] 링크로 전체판을 "
        "볼 것. 박스 좌표(원본 픽셀)는 행 텍스트에 있다.<br>"
        "<b>주의 3 — TTA 변형 표는 재현 실행이다.</b> eval_reader 의 변형 시드는 "
        "hash(cid) 로 프로세스마다 값이 바뀌어(비재현) 이 표는 crc32 시드로 다시 "
        "돈 것이다. 공식 예측·득표율은 행 머리의 것(reader_preds.json)이 정본이며 "
        "변형별 표와 다를 수 있다.<br>"
        "<b>주의 4 — 대조군이 섞여 있다.</b> 하위 정답(stratum=ctrl_*) 행은 "
        "오답과 같은 화면에서 비교하기 위한 정담이다. 정답에도 같은 성질이 "
        "있는지를 재기 전까지 그 성질을 원인으로 말하지 않는다."
        "</div>")

    parts.append(
        "<div class=bar><b>필터</b> "
        "<label><input type=checkbox name=b value=risky checked>risky</label>"
        "<label><input type=checkbox name=b value=safe checked>safe</label>"
        "<label><input type=checkbox name=b value=blank checked>blank</label>"
        "<label><input type=checkbox name=b value=exact checked>정답(대조군)</label>"
        "<label>득표율 ≤ <select id=ag><option value=1.01>전부</option>"
        "<option value=0.778 selected>&lt;0.778(거절선)</option>"
        "<option value=0.556>&lt;0.556</option></select></label>"
        "<label>id <input type=text id=q placeholder=\u201cbatch2/17\u201d></label>"
        "<span id=count class=num></span></div>")

    for c in cases:
        bucket = c["bucket"]
        det = (review or {}).get(c["id"])
        det_badge = (f"<span class='badge b-det-{det['det']}'>검출:{det['det']}"
                     f"</span>" if det else "")
        lab_bits = []
        if c["lcd_label"]:
            sm = c["lcd_metrics"]
            lab_bits.append(
                f"LCD라벨 있음 IoU {sm['iou']} recall {sm['label_recall']} "
                f"잘림(L{sm['cut_left_px']}/R{sm['cut_right_px']}/"
                f"T{sm['cut_top_px']}/B{sm['cut_bottom_px']}px)")
        else:
            lab_bits.append("LCD라벨 없음")
        if c["band_label"]:
            lab_bits.append("밴드라벨 있음")
        parts.append(
            f"<div class=row data-bucket={bucket} data-agree={c['agree']} "
            f"data-id=\"{html_escape(c['id'])}\">"
            f"<div class=head><span class=id>{html_escape(c['id'])}</span>"
            f"<span class='badge b-{bucket}'>{BUCKET_LABEL[bucket]}"
            f"{' · 거절대상' if c['rejected'] else ''}</span>{det_badge}"
            f"<span class=num>GT <b>{html_escape(c['gt'])}</b> → "
            f"예측 <b>{html_escape(c['pred'] or '(없음)')}</b>"
            f" · 공식 득표 {c['agree']}</span>"
            f"<span class=num>{c['img_w']}x{c['img_h']}px"
            f" · 쿼드 종횡비 {c['aspect']}"
            f"{' · 가로' if c['wide'] else ''}</span>"
            f"<a href=\"imgs/{c['sid']}_full.jpg\" target=_blank>[원본 해상도]</a>"
            f"</div>"
            f"<div class=cap><span class=mono>GM박스({c['gm_box']}) "
            f"크롭({c['crop_box']}) · {html_escape(' · '.join(lab_bits))}</span></div>"
            f"<div class=panels>")

        # (1) 원본 오버레이(표시용 축소본)
        parts.append(
            f"<div><div class=cap>(1) 원본(EXIF 표시 좌표계) + 박스들</div>"
            f"<a href=\"imgs/{c['sid']}_full.jpg\" target=_blank>"
            f"<img loading=lazy src=\"imgs/{c['sid']}_ov.jpg\"></a></div>")

        # (2) 리더 입력 워프
        parts.append(
            f"<div><div class=cap>(2) 리더 입력 320x160 (아래는 2배 최근접 확대)</div>"
            f"<img loading=lazy src=\"imgs/{c['sid']}_warp2x.png\"></div>")

        # (3) 타임스텝 띠 + (4) TTA 표
        cells = []
        for t, (cls, p) in enumerate(c["timesteps"]):
            ch = "." if cls == BLANK else str(cls)
            alpha = 0.25 + 0.75 * min(p, 1.0)
            low = " low" if p < 0.5 else ""
            cells.append(
                f"<div class='c{low}' title='t={t} p={p:.3f}' "
                f"style=background:rgba(96,211,148,{alpha:.2f})>"
                f"{ch}<small>{p:.2f}</small></div>")
        raw, collapsed = greedy_with_collapse(np.array(
            [a for a, _ in c["timesteps"]]))
        tally_rows = []
        for name, dec in c["tta_variants"]:
            mark = "■" if dec == c["tta_majority"] else "·"
            tally_rows.append(
                f"<tr><td>{mark} {name}</td><td>{html_escape(dec or '(없음)')}</td></tr>")
        parts.append(
            f"<div><div class=cap>(3) CTC 타임스텝 argmax·확률(기본 크롭, "
            f"붉은 테두리=확률&lt;0.5) → 접기: <b class=num>{html_escape(collapsed or '(없음)')}</b>"
            f" <span class=warn>(raw: <span class=num>{html_escape(raw)}</span>)</span></div>"
            f"<div class=ts>{''.join(cells)}</div>"
            f"<div class=cap>(4) TTA 변형 9개(재현 실행, crc32 시드) — "
            f"다수결 <b class=num>{html_escape(c['tta_majority'] or '(없음)')}</b>"
            f" 득표 {c['tta_agree']:.3f}"
            f"{'' if c['tta_majority'] == c['pred'] else ' · <span class=warn>공식 예측과 다름(시드 차이)</span>'}"
            f"</div><table class=tta>{''.join(tally_rows)}</table></div>")

        parts.append("</div></div>")

    parts.append(
        "<script>"
        "var boxes=[...document.querySelectorAll('input[name=b]')],"
        "ag=document.getElementById('ag'),q=document.getElementById('q');"
        "function f(){var n=0;"
        "var on=new Set(boxes.filter(b=>b.checked).map(b=>b.value));"
        "var qa=q.value.trim();"
        "document.querySelectorAll('.row[data-bucket]').forEach(function(r){"
        "var ok=on.has(r.dataset.bucket)"
        "&&parseFloat(r.dataset.agree)<parseFloat(ag.value)"
        "&&(!qa||r.dataset.id.includes(qa));"
        "r.style.display=ok?'':'none';if(ok)n++;});"
        "document.getElementById('count').textContent=' '+n+'건 표시';}"
        "boxes.forEach(b=>b.onchange=f);ag.onchange=f;q.oninput=f;f();"
        "</script></body></html>")

    return "".join(parts)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-root", default=str(HERE),
                    help="gitignored 데이터가 있는 assets_dev/train 절대경로. "
                         "워크트리에서는 메인 트리 것을 지정한다.")
    ap.add_argument("--review", default=None,
                    help="agent_review.json — 눈검 판정 {id: {det, note}} 을 행에 "
                         "뱃지로 심는다(2차 재생성용).")
    args = ap.parse_args()
    root = Path(args.data_root).resolve()
    datumo = root.parent / "upstream" / "datumo"
    images = datumo / "extracted" / "TILDE"

    review = None
    if args.review:
        review = json.loads(Path(args.review).read_text(encoding="utf-8"))

    # ===== 입력 (전부 읽기 전용) =====
    def src_info(p: Path):
        return {"file": p.name, "rows_or_bytes": (
            p.stat().st_size if p.suffix == ".json" else p.stat().st_size),
            "mtime": datetime.fromtimestamp(p.stat().st_mtime).isoformat(
                timespec="minutes")}

    preds = json.loads((root / "reader_preds.json").read_text(encoding="utf-8"))
    quads = {k: v["quad"] for k, v in read_jsonl(root / "gmscreen_quads.jsonl"
                                                 ).items()}
    readings = {k: v["reading"] for k, v in
                read_jsonl(datumo / "labels.jsonl").items()}
    corrections = {k: v["corrected"] for k, v in
                   read_jsonl(root / "gt_corrections.jsonl").items()}
    lcd_labels = read_jsonl(root / "screen_boxes.jsonl")
    band_labels = read_jsonl(root / "band_boxes.jsonl")

    rows = classify(preds, readings, corrections)
    counts = Counter(r["bucket"] for r in rows.values())
    n_rej = sum(1 for r in rows.values() if r["rejected"])
    gm_miss = sorted(set(readings) - set(quads))

    # ===== 선택 + 모델 =====
    sel = select_rows(rows)
    print(f"선택 {len(sel)}건 = 오답 {counts['risky'] + counts['safe'] + counts['blank']}"
          f" + 대조군 {N_CONTROL_LOW + N_CONTROL_HIGH}")

    model = tf.keras.models.load_model(str(root / "reader_model"))
    logits_model = tf.keras.Model(model.get_layer("img").input,
                                  model.get_layer("logits").output)

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "imgs").mkdir(exist_ok=True)

    # ===== 등가성 검사: 이 도구의 워프 == 학습 캐시의 holdout 크롭 =====
    # 기하 재사용이 어긋나지 않았음을 픽셀로 증명한다. 어긋나면 아틀라스 전체가
    # 무효이므로 즉시 죽는다.
    cache = np.load(str(root / "data_cache_v2.npz"))
    hold_ids = {str(v): i for i, v in enumerate(cache["real_holdout_ids"])}
    eq_done = 0
    for c in sel:
        if eq_done >= EQ_CHECK_N:
            break
        if c["id"] not in hold_ids:
            continue
        p = images / f"{c['id']}.jpg"
        g = load_gray(p)
        if g is None:
            continue
        mine = frame_crop(g, quads[c["id"]])
        ref = cache["real_holdout_images"][hold_ids[c["id"]]]
        if not np.array_equal(mine, ref):
            raise SystemExit(
                f"등가성 검사 실패: {c['id']} — 이 도구의 크롭이 학습 캐시와 다르다. "
                "eval_reader 기하 재사용이 깨졌으니 아틀라스를 만들면 안 된다.")
        eq_done += 1
    print(f"등가성 검사 통과 {eq_done}/{EQ_CHECK_N} (npz holdout 크롭과 픽셀 일치)")
    if eq_done == 0:
        raise SystemExit("등가성 검사를 한 건도 못 했다 — holdout 교집합이 없다")

    # ===== 케이스별 렌더 + 추론 =====
    cases, gray_memo = [], {}
    for c in sel:
        cid = c["id"]
        sid = cid.replace("/", "__")
        p = images / f"{cid}.jpg"
        g = load_gray(p)
        if g is None:
            print(f"경고: {cid} 디코드 실패 — 행 생략")
            continue
        gray_memo[cid] = g
        quad = quads[cid]
        crop_rect = framed_src_rect(g, quad)
        q = np.asarray(quad, dtype=np.float64)
        qw = q[:, 0].max() - q[:, 0].min()
        qh = q[:, 1].max() - q[:, 1].min()
        aspect = round(qw / max(qh, 1e-6), 2)

        vis = draw_overlay(g, quad, crop_rect,
                           [(lcd_labels.get(cid), C_LCD),
                            (band_labels.get(cid), C_BAND)])
        cv2.imwrite(str(OUT / "imgs" / f"{sid}_full.jpg"), vis,
                    [cv2.IMWRITE_JPEG_QUALITY, 88])
        scale = 1000.0 / vis.shape[0]
        if scale < 1.0:
            ov = cv2.resize(vis, None, fx=scale, fy=scale,
                            interpolation=cv2.INTER_AREA)
        else:
            ov = vis
        cv2.imwrite(str(OUT / "imgs" / f"{sid}_ov.jpg"), ov,
                    [cv2.IMWRITE_JPEG_QUALITY, 85])

        rect = frame_crop(g, quad)
        cv2.imwrite(str(OUT / "imgs" / f"{sid}_warp.png"), rect)
        warp2x = cv2.resize(rect, (IN_W * 2, IN_H * 2),
                            interpolation=cv2.INTER_NEAREST)
        cv2.imwrite(str(OUT / "imgs" / f"{sid}_warp2x.png"), warp2x)

        c.update(sid=sid, img_w=g.shape[1], img_h=g.shape[0], aspect=aspect,
                 wide=aspect > 1.5,
                 gm_box=",".join(str(int(round(v))) for v in (
                     q[:, 0].min(), q[:, 1].min(), q[:, 0].max(), q[:, 1].max())),
                 crop_box=",".join(str(int(round(v))) for v in (
                     crop_rect[:, 0].min(), crop_rect[:, 1].min(),
                     crop_rect[:, 0].max(), crop_rect[:, 1].max())),
                 lcd_label=lcd_labels.get(cid), band_label=band_labels.get(cid),
                 lcd_metrics=(side_metrics(quad, lcd_labels[cid])
                              if cid in lcd_labels else None),
                 _rect=rect)
        cases.append(c)

    # ===== 일괄 추론: 기본 크롭 logits + TTA 변형 =====
    base = np.asarray([c["_rect"] for c in cases], dtype=np.float32)[..., None]
    base_logits = logits_model.predict(base, batch_size=128, verbose=0)

    all_var, owner = [], []
    for i, c in enumerate(cases):
        # eval_reader 는 hash(cid)(프로세스마다 바뀜)로 시드를 뽑는다. 여기서는
        # 같은 분포의 지터를 재현 실행으로 보여주기만 하므로 crc32 로 고정한다.
        rng = np.random.RandomState(
            TTA_SEED + (zlib.crc32(c["id"].encode()) & 0xFFFF))
        for k in range(TTA_N + 1):
            v = c["_rect"] if k == 0 else _jitter(
                c["_rect"], rng.uniform(0.92, 1.08), rng.uniform(-0.03, 0.03),
                rng.uniform(-0.03, 0.03), rng.uniform(0.85, 1.15))
            all_var.append(v)
            owner.append(i)
    var_logits = logits_model.predict(
        np.asarray(all_var, dtype=np.float32)[..., None], batch_size=128,
        verbose=0)

    per_case = [[] for _ in cases]
    for lg, i in zip(var_logits, owner):
        per_case[i].append(_decode(lg))
    for i, c in enumerate(cases):
        c["timesteps"] = timestep_cells(base_logits[i])
        tally = Counter(per_case[i])
        maj, k = tally.most_common(1)[0]
        c["tta_variants"] = [(("기본" if j == 0 else f"지터{j}"), d)
                             for j, d in enumerate(per_case[i])]
        c["tta_majority"] = maj
        c["tta_agree"] = k / len(per_case[i])
        del c["_rect"]

    # ===== 메타 =====
    commit = subprocess.run(
        ["git", "-C", str(HERE), "rev-parse", "--short", "HEAD"],
        capture_output=True, text=True).stdout.strip()
    files = {name: src_info(root / name) for name in
             ("gmscreen_quads.jsonl", "reader_preds.json", "data_cache_v2.npz")}
    files["screen_boxes.jsonl"] = src_info(
        root / "screen_boxes.jsonl") | {"rows": len(lcd_labels)}
    files["band_boxes.jsonl"] = src_info(
        root / "band_boxes.jsonl") | {"rows": len(band_labels)}
    files["labels.jsonl"] = src_info(datumo / "labels.jsonl") | {
        "rows": len(readings)}

    # Q3 용 전수 집계 — 선택 행이 아니라 holdout 전체에서.
    wrong_ids = [i for i, r in rows.items() if r["bucket"] != "exact"]
    q3 = {
        "holdout_total": len(rows),
        "wrong": len(wrong_ids),
        "wrong_agree_lt_reject": sum(
            1 for i in wrong_ids if rows[i]["agree"] < REJECT_AT),
        "correct_agree_lt_reject": sum(
            1 for r in rows.values()
            if r["bucket"] == "exact" and r["agree"] < REJECT_AT),
        "correct_total": counts["exact"],
    }

    blurb = (
        f"생성 {datetime.now().isoformat(timespec='minutes')} · 워크트리 커밋 {commit}\n"
        f"data-root(읽기 전용): {root}\n"
        f"검출기 예측: gmscreen_quads.jsonl({len(quads)}행) — ft3/ft4/oriented 아님(정본)\n"
        f"리더: reader_model · 평가 정본: reader_preds.json(hold-out {len(rows)}건)\n"
        f"분류(REJECT_AT={REJECT_AT}, webtool 기준): "
        f"risky {counts['risky']} / safe {counts['safe']} / blank {counts['blank']} "
        f"/ exact {counts['exact']} / 거절대상 {n_rej}\n"
        f"참고 — GM 검출 없음(labels 중 쿼드 없음): {len(gm_miss)}건 {gm_miss[:8]}\n"
        f"층 순서: risky → safe → blank → ctrl_low(정답·저득표 {N_CONTROL_LOW}) "
        f"→ ctrl_high(정답·만장일치 표본 {N_CONTROL_HIGH}) · 사전순 섞기 없음\n"
        f"등가성: eval_reader 기하로 만든 크롭 {eq_done}건이 npz holdout 크롭과 픽셀 일치")

    meta = {"blurb": blurb, "files": files, "q3": q3,
            "strata": Counter(c["stratum"] for c in cases),
            "wide_wrong": sum(1 for c in cases
                              if c["bucket"] != "exact" and c["wide"]),
            "wide_all_selected": sum(1 for c in cases if c["wide"]),
            "lcd_label_overlap": {
                "wrong_with_lcd_label": sum(
                    1 for c in cases
                    if c["bucket"] != "exact" and c["lcd_label"]),
                "ctrl_with_lcd_label": sum(
                    1 for c in cases
                    if c["bucket"] == "exact" and c["lcd_label"])}}
    (OUT / "atlas_meta.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=1, default=str),
        encoding="utf-8")

    (OUT / "index.html").write_text(build_html(cases, meta, review),
                                    encoding="utf-8")
    print(f"saved {OUT / 'index.html'} · 행 {len(cases)} · "
          f"이미지 {len(cases) * 4}장")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
