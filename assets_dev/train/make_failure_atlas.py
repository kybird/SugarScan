# 판독 실패 아틀라스 — 파이프라인 중간 산출물을 케이스 한 건·한 행에 나란히
# 놓아 "어느 단계에서 틀렸는가"를 눈으로 가르는 도구.
#
# 두 동작 모드:
#   (기본) 정적 HTML 컨택트 시트 생성 — 종전 동작 그대로.
#   --serve  검토 서버 — 검출 판정(det)을 브라우저에서 고치고 agent_review.json
#            에 원자적으로 저장한다. 판정 주체(by: agent|human)·확인함(checked)·
#            시각(ts, UTC ISO-8601)을 함께 남겨 다음 분석이 "임 것"과
#            "1차 추정"을 구분하게 한다. 구버전 파일(by 없음)은 agent 로 읽는다.
#   --compare-preds <file>  A/B 비교 모드 — 기준선(--preds)과 후보 예측을 한 행에
#            나란히 놓는다. 새로 틀림(기준선 정답 → 후보 오답) 층을 목록 맨 위에
#            둔다. McNemar p값은 "차이가 있다"만 말하지 무엇이 달라졌는지는
#            말하지 않는다 — 채택 결정은 새로 틀린 장을 눈으로 보고 한다.
#
# 한 행의 구성:
#   (1) 원본(EXIF 표시 좌표계) 위에 GM 예측 쿼드(파랑)·BOX_MARGIN 크롭 박스(마젠타)
#       ·사람 라벨(밴드=노랑, LCD=초록). 원본 해상도 전체판은 행에서 링크로 건다 —
#       축소 렌더로 경계 판단 금지(downscaled-view-as-evidence).
#   (2) 리더에 실제 들어간 320x160 워프
#   (3) CTC 타임스텝별 argmax 문자·확률 띠 (40칸)
#   (4) TTA 변형별 디코드·득표
#   (5) id/GT/예측/득표율/오류 분류 + 쿼드 종횡비·늘림 배율(2.0/(w/h),
#       기준선 정답 분포 p10~p90=2.10~2.90 밖이면 경고) 텍스트
#
# 지키는 규칙:
#   - 대조군 포함: 정답(저득표 우선 + 고득표 시드 표본)을 최소 오답 수만큼 섞는다.
#     실패만 모아 보면 공통 성질이 전부 원인처럼 보인다(2026-09-04 두 번 반증).
#     대조군을 빼는 옵션은 만들지 않는다.
#   - 층 유지: risky → safe → blank → 정답(저득표) → 정답(고득표) 순서로 놓고
#     사전순 섞지 않는다. 중간에 멈춰도 한 층이 통째로 비지 않게.
#     비교 모드는 그 앞에 새로 틀림 층을 하나 더 얹는다(행 구성 자체는 기준선 기준).
#   - 기하·EXIF·디코딩은 eval_reader.py 를 import 해서 쓴다(재구현·복사 금지 —
#     duplicated-geometry-implementation). eval_reader 의 워프가 바뀌면 이 도구는
#     자동으로 새 프레이밍을 보여준다 — 그래서 복사하지 않는다.
#     시작 시 --cache 의 holdout 크롭과 픽셀 등가성을 검사해 --model/--cache 짝이
#     맞는지 증명한다.
#   - 오류 분류는 webtool.py api_failures 의 기준을 그대로: risky(자릿수 보존
#     오독)/safe(자릿수 변동)/blank(무출력)/rejected(득표율 < REJECT_AT=0.778).
#     새로 정의하지 않는다. 값이 갈라지면 webtool 을 정본으로 맞춘다.
#   - 모든 모델·예측·캐시·라벨 입력은 읽기 전용. 이 도구가 쓰는 파일은 산출물
#     디렉터리(_diag/atlas · _diag/atlas_serve)와 agent_review.json(+.bak) 뿐이다.
#
# 실행(워크트리 — 데이터는 메인 트리에서 읽는다):
#   정적: conda run -n sugartrain python make_failure_atlas.py \
#             --data-root D:/Project/sugarScan/assets_dev/train
#   검토: conda run -n sugartrain python make_failure_atlas.py --serve \
#             --data-root D:/Project/sugarScan/assets_dev/train
#   A/B : 위 검토 명령에 --compare-preds reader_preds_letterbox.json \
#             --model reader_model_letterbox --cache data_cache_v2_letterbox.npz
# 메인 트리에서 그대로 돌리면 --data-root 기본값(스크립트 자신의 디렉터리)이 맞다.
import argparse
import json
import os
import subprocess
import threading
import zlib
from collections import Counter
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

import cv2
import numpy as np
import tensorflow as tf

# 기하·EXIF·디코드의 정본. eval_reader 는 tensorflow 를 module level 에서 import
# 하고 main() 안에서만 자기 경로(HERE)의 파일을 읽으므로, 여기서 import 하는 것은
# 부작용이 없다. 모듈 객체도 함께 잡아둔다 — 실행 시점에 그 소스가 TTA 시드로
# crc32 를 쓰는지 확인해 HTML 머리의 재현 주의문을 조건부로 띄운다.
import eval_reader
from eval_reader import (IN_H, IN_W, NUM_CLASSES, TTA_N, TTA_SEED,
                         _decode, _jitter, frame_crop, framed_src_rect,
                         load_gray)

HERE = Path(__file__).resolve().parent
OUT = HERE / "_diag" / "atlas"              # 정적 산출물
SERVE_OUT = HERE / "_diag" / "atlas_serve"  # 검토 서버 산출물(이미지·메타)
BLANK = NUM_CLASSES - 1          # 10. NUM_CLASSES 가 아니다.
REJECT_AT = 0.778                # webtool.py api_failures 와 같은 값(정본: webtool)
N_CONTROL_LOW = 20               # 정답 중 득표 최저 대조군
N_CONTROL_HIGH = 20              # 정답 중 만장일치 대조군(시드 고정 표본)
CONTROL_SEED = 20260905
EQ_CHECK_N = 12                  # npz holdout 크롭과의 픽셀 등가성 검사 표본 수
DET_CLASSES = ("ok", "cut", "wrong_area", "orient", "ambiguous")
# 워프가 가로로 늘리는 배율 = 2.0/(쿼드 w/h). 기준선 정답 분포의 p10~p90.
# 이 밖이면 행에 경고를 붙인다(가로 화면·회전 층이 여기서 잡힌다).
STRETCH_P10, STRETCH_P90 = 2.10, 2.90
OUTCOME_LABEL = {
    "fixed": "고쳐짐", "new_wrong": "새로 틀림", "both_wrong": "둘 다 틀림",
    "both_right": "둘 다 정답", "no_compare": "비교본 없음",
}
OUTCOME_ORDER = ("new_wrong", "fixed", "both_wrong", "both_right", "no_compare")

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


def _by_agree(rs):
    return sorted(rs, key=lambda r: (r["agree"] if r["agree"] is not None
                                     else 9.0, r["id"]))


def select_rows(rows):
    """층을 유지한 선택. risky → safe → blank(오답 전량) → 정답 저득표 → 정답 고득표."""
    wrong = [r for r in rows.values() if r["bucket"] != "exact"]
    exact = [r for r in rows.values() if r["bucket"] == "exact"]
    strat = {"risky": [], "safe": [], "blank": []}
    for r in wrong:
        strat[r["bucket"]].append(r)
    ctrl_low = _by_agree(exact)[:N_CONTROL_LOW]
    high_pool = [r for r in exact if r["agree"] == 1.0]
    rng = np.random.RandomState(CONTROL_SEED)
    picks = rng.permutation(len(high_pool))[:N_CONTROL_HIGH]
    ctrl_high = sorted((high_pool[i] for i in picks), key=lambda r: r["id"])
    sel = (_by_agree(strat["risky"]) + _by_agree(strat["safe"])
           + _by_agree(strat["blank"]) + ctrl_low + ctrl_high)
    for r in sel:
        r["stratum"] = ("wrong_" + r["bucket"] if r["bucket"] != "exact"
                        else ("ctrl_low" if r in ctrl_low else "ctrl_high"))
    return sel


def select_rows_compare(rows, crows):
    """A/B 비교 모드의 선택. 행 구성(층·대조군)은 기준선(rows) 기준이되,
    새로 틀림(기준선 정답 → 후보 오답)을 전량 뽑아 맨 위 층에 얹는다.

    새로 틀림이 이 모드의 존재 이유다 — 대조군 40건 표본 안에 우연히 들지
    않은 새 오답은 표본 밖에 있으므로 전량을 별도 층으로 노출한다. 기준선
    대조군에 뽑혔던 행이 새로 틀림이면 위 층으로 옮긴다(같은 행이 두 번
    나오는 것보다 낫다 — 편집 대상이 id 라 중복 행은 판정을 갈라놓는다).
    층 안 정렬은 다른 층과 같은 "득표율 오름차순"을 이 층의 오답(후보) 득표에
    적용한다.
    """
    base = select_rows(rows)
    nw_ids = {r["id"] for r in rows.values()
              if r["bucket"] == "exact" and r["id"] in crows
              and crows[r["id"]]["bucket"] != "exact"}
    new_wrong = sorted(
        (rows[i] for i in nw_ids),
        key=lambda r: (crows[r["id"]]["agree"]
                       if crows[r["id"]]["agree"] is not None else 9.0,
                       r["id"]))
    for r in new_wrong:
        r["stratum"] = "new_wrong"
    base = [r for r in base if r["id"] not in nw_ids]
    return new_wrong + base


def outcome_of(base_row, comp):
    """기준선·후보의 정오를 4분류(+비교본 없음)로 묶는다. 기준선 기준 이름."""
    if comp is None:
        return "no_compare"
    bw = base_row["bucket"] != "exact"
    cw = comp["bucket"] != "exact"
    if bw and not cw:
        return "fixed"
    if not bw and cw:
        return "new_wrong"
    if bw and cw:
        return "both_wrong"
    return "both_right"


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


def eval_seed_is_crc32() -> bool:
    """eval_reader 의 TTA 시드가 이미 crc32 인가 — 실행 시점에 소스로 확인한다.

    G29 가 hash(cid) → zlib.crc32 로 바꾼 뒤에는 이 도구의 재현 TTA 표가 곧
    공식 집계와 같은 시드를 쓰므로, "TTA 표는 재현이고 공식 득표율이 정본"
    주의문이 필요 없다. 문구를 지우지 말고 조건부로 띄우라는 지시의 구현.
    """
    src = Path(eval_reader.__file__).read_text(encoding="utf-8")
    return any("RandomState" in ln and "crc32" in ln
               for ln in src.splitlines())


# ===== agent_review.json 저장 — 판정 주체 구분이 이 도구의 핵심 규약 =====
# {id: {"det": "cut", "note": "...", "by": "agent"|"human",
#       "checked": true|false, "ts": "<ISO8601 UTC>"}}
# "_meta" 키(1차 판정의 근거 설명)는 사람 판정과 무관하므로 그대로 보존한다.

def review_load(path: Path):
    if not path.exists():
        return {}
    d = json.loads(path.read_text(encoding="utf-8"))
    for k, v in d.items():
        if k == "_meta" or not isinstance(v, dict):
            continue
        # 구버전 파일에는 by 가 없다 — 없으면 agent 로 읽는다(첫 저장 때 정착).
        v.setdefault("by", "agent")
        v.setdefault("checked", False)
        v.setdefault("note", "")
    return d


def review_save_atomic(path: Path, review: dict):
    """임시 파일 + os.replace 원자적 저장. 첫 저장 전에 원본을 .bak 로 한 번."""
    bak = path.with_name(path.name + ".bak")
    if path.exists() and not bak.exists():
        bak.write_bytes(path.read_bytes())
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(review, ensure_ascii=False, indent=1),
                   encoding="utf-8")
    os.replace(tmp, path)


class ReviewStore:
    """검토 서버용 저장소. 서버가 스레드형이므로 읽기·쓰기 전부 잠근다."""

    def __init__(self, path: Path, known_ids):
        self.path = Path(path)
        self.known = set(known_ids)
        self.lock = threading.Lock()
        self.review = review_load(self.path)

    def get(self):
        with self.lock:
            return self.review

    def apply(self, rid, det, note, checked):
        with self.lock:
            if rid not in self.known:
                raise ValueError(f"모르는 id: {rid}")
            if det is not None and det not in DET_CLASSES:
                raise ValueError(f"모르는 det 클래스: {det}")
            if len(note) > 1000:
                raise ValueError("메모가 너무 길다(1000자)")
            rec = {}
            if det:
                rec["det"] = det
            rec.update(note=note, by="human", checked=bool(checked),
                       ts=datetime.now(timezone.utc).isoformat(
                           timespec="seconds"))
            self.review[rid] = rec
            review_save_atomic(self.path, self.review)
            return dict(rec)


BUCKET_LABEL = {
    "risky": "위험(자릿수 보존 오독)",
    "safe": "안전(자릿수 변동)",
    "blank": "무출력",
    "exact": "정답",
}

BASE_CSS = """
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
select{background:#1b2024;color:#d8dde2;border:1px solid #2a3138;
       border-radius:4px;padding:2px 4px}
.row{border:1px solid #2a3138;border-radius:8px;margin:14px 0;padding:10px;
     background:#181c20}
.row.cur{outline:2px solid #6fb3e0}
.row.head{display:flex;gap:10px;flex-wrap:wrap;align-items:baseline}
.row.head .id{font-family:Consolas,monospace;font-weight:600;font-size:15px}
.badge{padding:1px 8px;border-radius:10px;font-size:12px;font-weight:600}
.b-risky{background:#5c1a1a;color:#ff9c9c}.b-safe{background:#4a3a10;color:#ffd97a}
.b-blank{background:#333a44;color:#aab7c4}.b-exact{background:#153f23;color:#8fe6a8}
.b-det-ok{background:#153f23;color:#8fe6a8}
.b-det-cut{background:#5c1a1a;color:#ff9c9c}.b-det-orient{background:#4a3a10;color:#ffd97a}
.b-det-wrong_area{background:#5c1a5c;color:#e39ce3}.b-det-wide{background:#4a3a10;color:#ffd97a}
.b-det-ambiguous{background:#333a44;color:#aab7c4}.b-det-none{background:#262b31;color:#7d8a96}
.b-out-new_wrong{background:#7a1414;color:#ffb0b0}.b-out-fixed{background:#153f23;color:#8fe6a8}
.b-out-both_wrong{background:#4a2410;color:#ffb97a}.b-out-both_right{background:#1d3450;color:#9cc8f0}
.b-out-no_compare{background:#333a44;color:#aab7c4}
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

NOTES_124 = (
    "<b>주의 1 — CTC 타임스텝은 공간 위치가 아니다.</b> 리더에 BiLSTM 이 "
    "있어 각 타임스텝은 양방향 문맥을 본다. 타임스텝을 이미지 x 좌표에 "
    "겹쳐 읽는 것은 힌트는 되지만 증거가 아니다 — \u201c3번째 타임스텝이 "
    "오른쪽 숫자를 봤다\u201d고 단정하지 말 것.<br>"
    "<b>주의 2 — 축소 렌더로 경계 판단 금지.</b> 행의 원본 패널은 표시용 "
    "축소본이다. \u201c잘렸다\u201d고 말하기 전에 [원본 해상도] 링크로 전체판을 "
    "볼 것. 박스 좌표(원본 픽셀)는 행 텍스트에 있다.<br>"
    "<b>주의 4 — 대조군이 섞여 있다.</b> 하위 정답(stratum=ctrl_*) 행은 "
    "오답과 같은 화면에서 비교하기 위한 정담이다. 정답에도 같은 성질이 "
    "있는지를 재기 전까지 그 성질을 원인으로 말하지 않는다."
)

NOTE_3 = (
    "<b>주의 3 — TTA 변형 표는 재현 실행이다.</b> eval_reader 의 변형 시드는 "
    "hash(cid) 로 프로세스마다 값이 바뀌어(비재현) 이 표는 crc32 시드로 다시 "
    "돈 것이다. 공식 예측·득표율은 행 머리의 것(--preds 파일)이 정본이며 "
    "변형별 표와 다를 수 있다."
)


def _notes_html(seed_crc32):
    if seed_crc32:
        return NOTES_124
    return NOTES_124.replace("주의 4", NOTE_3 + "<br>주의 4")


def _stretch_html(c):
    cls = " class=warn" if c["stretch_out"] else ""
    txt = f"×{c['stretch']}"
    if c["stretch_out"]:
        txt += f"({STRETCH_P10:.2f}~{STRETCH_P90:.2f} 밖)"
    return f"늘림 <b{cls}>{txt}</b>"


def _tta_mismatch_html(c, seed_crc32):
    """TTA 표의 다수결과 공식 예측이 다를 때의 경고.

    시드가 hash(cid)(비재현)인 동안에는 시드 차이가 정상 원인이다. crc32 로
    통일된 뒤에도 다르면 --model 과 --preds/--compare-preds 가 다른 모델이라는
    뜻(짝 불일치) — 조용히 넘기면 안 되는 상태다. 비교 모드에서는 후보 예측이
    살아있는 패널(—model)의 짝이므로 후보 예측과 비교한다.
    """
    if c["tta_majority"] == c["tta_ref"]:
        return ""
    why = ("모델·캐시 짝 불일치 의심" if seed_crc32 else "시드 차이")
    return f" · <span class=warn>공식 예측과 다름({why})</span>"


def build_html(cases, meta, review, seed_crc32):
    """정적 아틀라스 페이지. serve 모드와 같은 행 구성이지만 편집은 없다."""
    compare_mode = meta.get("compare") is not None
    parts = []
    parts.append(f"<!DOCTYPE html><html lang=ko><head><meta charset=utf-8>"
                 f"<title>판독 실패 아틀라스</title><style>{BASE_CSS}</style>"
                 f"</head><body><h1>판독 실패 아틀라스 — 어느 단계에서 틀렸는가"
                 f"</h1>")

    parts.append(
        "<div class=meta>" + html_escape(meta["blurb"]) + "</div>")

    parts.append(
        "<div class=meta legend><b>범례</b> — "
        f"<span><i class=sw style=background:rgb{C_GM[::-1]}></i>GM 예측 쿼드(gmscreen_quads)</span>"
        f"<span><i class=sw style=background:rgb{C_CROP[::-1]}></i>BOX_MARGIN 크롭 박스(리더 입력)</span>"
        f"<span><i class=sw style=background:rgb{C_LCD[::-1]}></i>사람 LCD 라벨(screen_boxes)</span>"
        f"<span><i class=sw style=background:rgb{C_BAND[::-1]}></i>사람 밴드 라벨(band_boxes)</span>"
        "<br><b>읽는 순서</b>: 왼쪽 원본에서 박스가 숫자줄을 감쌌는지 먼저 보고, "
        "가운데 워프가 리더가 실제 본 것이며, 오른쪽 띠·표가 리더의 확신이다."
        "</div>")

    parts.append(f"<div class=meta>{_notes_html(seed_crc32)}</div>")

    outcome_bar = ""
    if compare_mode:
        outcome_bar = (" <b>비교</b> " + "".join(
            f"<label><input type=checkbox name=o value={k} checked>"
            f"{OUTCOME_LABEL[k]}</label>" for k in OUTCOME_ORDER))
    parts.append(
        "<div class=bar><b>필터</b> "
        "<label><input type=checkbox name=b value=risky checked>risky</label>"
        "<label><input type=checkbox name=b value=safe checked>safe</label>"
        "<label><input type=checkbox name=b value=blank checked>blank</label>"
        "<label><input type=checkbox name=b value=exact checked>정답(대조군)</label>"
        f"{outcome_bar}"
        "<label>득표율 ≤ <select id=ag><option value=1.01>전부</option>"
        "<option value=0.778 selected>&lt;0.778(거절선)</option>"
        "<option value=0.556>&lt;0.556</option></select></label>"
        "<label>id <input type=text id=q placeholder=\u201cbatch2/17\u201d></label>"
        "<span id=count class=num></span></div>")

    for c in cases:
        bucket = c["bucket"]
        det = (review or {}).get(c["id"])
        det_badge = ""
        if det:
            mark = ""
            if det.get("by") == "human":
                mark += " ·사람"
            if det.get("checked"):
                mark += " ✓확인"
            det_badge = (f"<span class='badge b-det-{det.get('det') or 'none'}'>"
                         f"검출:{det.get('det') or '미판정'}{mark}</span>")
        cmp_bits = ""
        if compare_mode:
            comp = c.get("compare")
            if comp:
                cmp_bits = (
                    f"<span class='badge b-out-{c['outcome']}'>"
                    f"{OUTCOME_LABEL[c['outcome']]}</span>"
                    f"<span class=num>비교본 <b>{html_escape(comp['pred'] or '(없음)')}</b>"
                    f" · 득표 {comp['agree']}"
                    f" · {BUCKET_LABEL[comp['bucket']]}"
                    f"{' · 거절대상' if comp['rejected'] else ''}</span>")
            else:
                cmp_bits = (f"<span class='badge b-out-no_compare'>"
                            f"{OUTCOME_LABEL['no_compare']}</span>")
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
            f"data-outcome=\"{c.get('outcome') or ''}\" "
            f"data-id=\"{html_escape(c['id'])}\">"
            f"<div class=head><span class=id>{html_escape(c['id'])}</span>"
            f"<span class='badge b-{bucket}'>{BUCKET_LABEL[bucket]}"
            f"{' · 거절대상' if c['rejected'] else ''}</span>{det_badge}"
            f"{cmp_bits}"
            f"<span class=num>GT <b>{html_escape(c['gt'])}</b> → "
            f"예측 <b>{html_escape(c['pred'] or '(없음)')}</b>"
            f" · 공식 득표 {c['agree']}</span>"
            f"<span class=num>{c['img_w']}x{c['img_h']}px"
            f" · 쿼드 종횡비 {c['aspect']}"
            f" · {_stretch_html(c)}"
            f"{' · 가로' if c['wide'] else ''}</span>"
            f"<a href=\"imgs/{c['sid']}_full.jpg\" target=_blank>[원본 해상도]</a>"
            f"</div>"
            f"<div class=cap><span class=mono>GM박스({c['gm_box']}) "
            f"크롭({c['crop_box']}) · {html_escape(c['lab_txt'])}</span></div>"
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
        tally_rows = []
        for name, dec in c["tta_variants"]:
            mark = "■" if dec == c["tta_majority"] else "·"
            tally_rows.append(
                f"<tr><td>{mark} {name}</td><td>{html_escape(dec or '(없음)')}</td></tr>")
        tta_cap = (f"(4) TTA 변형 {len(c['tta_variants'])}개"
                   + ("" if seed_crc32 else "(재현 실행, crc32 시드)"))
        parts.append(
            f"<div><div class=cap>(3) CTC 타임스텝 argmax·확률(기본 크롭, "
            f"붉은 테두리=확률&lt;0.5) → 접기: "
            f"<b class=num>{html_escape(c['collapsed'] or '(없음)')}</b>"
            f" <span class=warn>(raw: "
            f"<span class=num>{html_escape(c['ts_raw'])}</span>)</span></div>"
            f"<div class=ts>{''.join(cells)}</div>"
            f"<div class=cap>{tta_cap} — "
            f"다수결 <b class=num>{html_escape(c['tta_majority'] or '(없음)')}</b>"
            f" 득표 {c['tta_agree']:.3f}{_tta_mismatch_html(c, seed_crc32)}"
            f"</div><table class=tta>{''.join(tally_rows)}</table></div>")

        parts.append("</div></div>")

    parts.append(
        "<script>"
        "var boxes=[...document.querySelectorAll('input[name=b]')],"
        "outs=[...document.querySelectorAll('input[name=o]')],"
        "ag=document.getElementById('ag'),q=document.getElementById('q');"
        "function f(){var n=0;"
        "var on=new Set(boxes.filter(b=>b.checked).map(b=>b.value));"
        "var onO=outs.length?new Set(outs.filter(o=>o.checked).map(o=>o.value)):null;"
        "var qa=q.value.trim();"
        "document.querySelectorAll('.row[data-bucket]').forEach(function(r){"
        "var ok=on.has(r.dataset.bucket)"
        "&&(!onO||onO.has(r.dataset.outcome||'no_compare'))"
        "&&parseFloat(r.dataset.agree)<parseFloat(ag.value)"
        "&&(!qa||r.dataset.id.includes(qa));"
        "r.style.display=ok?'':'none';if(ok)n++;});"
        "document.getElementById('count').textContent=' '+n+'건 표시';}"
        "boxes.forEach(b=>b.onchange=f);outs.forEach(o=>o.onchange=f);"
        "ag.onchange=f;q.oninput=f;f();"
        "</script></body></html>")

    return "".join(parts)


# ===== 검토 서버 페이지 =====
# JS 는 파이썬 문자열 연결이 아니라 아래 템플릿의 __플레이스홀더__ 치환으로
# 조립한다 — 인용 부호 이스케이프가 한 겹이면 서로 꼬인다(실제로 겪었다).
# JS 안 문자열은 작은따옴표, HTML 속성은 큰따옴표로 통일한다.

SERVE_JS = """
var COMPARE=__COMPARE__;
var SEEDCRC=__SEEDCRC__;
var DETS=['ok','cut','wrong_area','orient','ambiguous'];
var BUK={risky:'위험(자릿수 보존 오독)',safe:'안전(자릿수 변동)',
         blank:'무출력',exact:'정답'};
var OUTK={fixed:'고쳐짐',new_wrong:'새로 틀림',both_wrong:'둘 다 틀림',
          both_right:'둘 다 정답',no_compare:'비교본 없음'};
var CASES=[],REVIEW={},byId={},ELS=new Map(),VIS=[],cur=-1;
var pend=null,pendT=null;
function $(id){return document.getElementById(id);}
function esc(s){return String(s).replace(/&/g,'&amp;')
 .replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');}

function badges(c){var rv=REVIEW[c.id]||{};var h='';
 h+='<span class="badge b-'+c.bucket+'">'+BUK[c.bucket]
  +(c.rejected?' · 거절대상':'')+'</span>';
 if(rv.det)h+='<span class="badge b-det-'+rv.det+'">검출:'+rv.det+'</span>';
 else h+='<span class="badge b-det-none">검출:미판정</span>';
 if(COMPARE)h+='<span class="badge b-out-'+(c.outcome||'no_compare')+'">'
  +OUTK[c.outcome||'no_compare']+'</span>';
 return h;}
function nums(c){
 var s='<span class=num>GT <b>'+esc(c.gt)+'</b> → 예측 <b>'
  +esc(c.pred||'(없음)')+'</b> · 공식 득표 '+c.agree+'</span>';
 if(COMPARE&&c.compare){s+=' <span class=num>비교본 <b>'
  +esc(c.compare.pred||'(없음)')+'</b> · 득표 '+c.compare.agree
  +' · '+BUK[c.compare.bucket]
  +(c.compare.rejected?' · 거절대상':'')+'</span>';}
 var st=c.stretch_out?' class=warn':'';
 s+='<span class=num>'+c.img_w+'x'+c.img_h+'px · 쿼드 종횡비 '+c.aspect
  +' · 늘림 <b'+st+'>×'+c.stretch
  +(c.stretch_out?'(2.10~2.90 밖)':'')+'</b>'+(c.wide?' · 가로':'')+'</span>';
 s+='<a href="/imgs/'+c.sid+'_full.jpg" target="_blank">[원본 해상도]</a>';
 return s;}
function controls(c){var rv=REVIEW[c.id]||{};
 var opts='<option value="">(미판정)</option>'+DETS.map(function(d){
  return '<option value="'+d+'"'+(rv.det===d?' selected':'')+'>'+d
   +'</option>';}).join('');
 var bt=rv.by||'agent';
 if(rv.ts)bt+=' · '+rv.ts.slice(11,19)+'Z';
 return '<select class="det" title="검출 판정 (단축키 1~5, 0=미판정)">'
  +opts+'</select>'
  +'<input class="note" type="text" maxlength="1000" value="'
  +esc(rv.note||'')+'" placeholder="메모 한 줄" title="Enter 로 저장">'
  +'<label class="chk"><input type="checkbox" class="chkbox"'
  +(rv.checked?' checked':'')+'>확인함</label>'
  +'<span class="by">'+esc(bt)+'</span>';}

function rowEl(c){var el=document.createElement('div');
 el.className='row';el.dataset.id=c.id;el.dataset.bucket=c.bucket;
 el.dataset.outcome=c.outcome||'';
 el.addEventListener('click',function(){var i=VIS.indexOf(c.id);
  if(i>=0)cur=i;});
 var cells='';
 for(var i=0;i<c.timesteps.length;i++){var t=c.timesteps[i];
  var ch=(t[0]===10)?'.':t[0];
  var al=(0.25+0.75*Math.min(t[1],1)).toFixed(2);
  cells+='<div class="c'+(t[1]<0.5?' low':'')+'" title="t='+i
   +' p='+t[1].toFixed(3)+'" style="background:rgba(96,211,148,'+al
   +')">'+ch+'<small>'+t[1].toFixed(2)+'</small></div>';}
 var tr='';
 for(var j=0;j<c.tta_variants.length;j++){
  var nm=c.tta_variants[j][0],d=c.tta_variants[j][1];
  tr+='<tr><td>'+(d===c.tta_majority?'■ ':'· ')+esc(nm)+'</td><td>'
   +esc(d||'(없음)')+'</td></tr>';}
 var warn='';
 if(c.tta_majority!==c.tta_ref){warn=' · <span class="warn">'
  +(SEEDCRC?'공식 예측과 다름(모델·캐시 짝 불일치 의심)'
           :'공식 예측과 다름(시드 차이)')+'</span>';}
 el.innerHTML='<div class="head"><span class="id">'+esc(c.id)+'</span>'
  +badges(c)+nums(c)+controls(c)+'</div>'
  +'<div class="cap"><span class="mono">GM박스('+c.gm_box+') 크롭('
  +c.crop_box+') · '+esc(c.lab_txt)+'</span></div>'
  +'<div class="panels">'
  +'<div><div class="cap">(1) 원본(EXIF 표시 좌표계) + 박스들</div>'
  +'<a href="/imgs/'+c.sid+'_full.jpg" target="_blank">'
  +'<img loading="lazy" src="/imgs/'+c.sid+'_ov.jpg"></a></div>'
  +'<div><div class="cap">(2) 리더 입력 320x160 (2배 최근접 확대)</div>'
  +'<img loading="lazy" src="/imgs/'+c.sid+'_warp2x.png"></div>'
  +'<div><div class="cap">(3) CTC 타임스텝 argmax·확률 → 접기: '
  +'<b class="num">'+esc(c.collapsed||'(없음)')+'</b></div>'
  +'<div class="ts">'+cells+'</div>'
  +'<div class="cap">(4) TTA '+c.tta_variants.length+'개'
  +(SEEDCRC?'':'(재현 실행, crc32 시드)')+' — 다수결 <b class="num">'
  +esc(c.tta_majority||'(없음)')+'</b> 득표 '+c.tta_agree+warn
  +'</div><table class="tta">'+tr+'</table></div>'
  +'</div>';
 hookRow(el,c.id);return el;}

// ===== 저장 =====
function fire(){if(pend){var f=pend;pend=null;clearTimeout(pendT);f();}}
function schedule(f){fire();pend=f;pendT=setTimeout(fire,800);}
function hookRow(el,id){
 var sel=el.querySelector('.det'),note=el.querySelector('.note'),
     cb=el.querySelector('.chkbox');
 // webtool 에서 실제로 당한 버그: select 를 고르면 포커스가 select 에 남아
 // 단축키가 전부 죽는다. 변경 저장 후 반드시 포커스를 본문으로 되돌린다.
 sel.addEventListener('change',function(){fire();
  save(id,sel.value||null,note.value,cb.checked);sel.blur();});
 cb.addEventListener('change',function(){fire();
  save(id,sel.value||null,note.value,cb.checked);cb.blur();});
 note.addEventListener('input',function(){
  schedule(function(){save(id,sel.value||null,note.value,cb.checked);});});
 note.addEventListener('keydown',function(e){if(e.key==='Enter'){fire();
  save(id,sel.value||null,note.value,cb.checked);note.blur();}});}
function save(id,det,note,checked){
 fetch('/api/review',{method:'POST',
  headers:{'Content-Type':'application/json'},
  body:JSON.stringify({id:id,det:det,note:note,checked:checked})})
 .then(function(r){return r.json();})
 .then(function(j){if(j.error){setSave('저장 실패: '+j.error,true);return;}
  REVIEW[id]=j.rec;refreshRow(id);progress();
  setSave('저장됨 '+new Date().toLocaleTimeString());})
 .catch(function(e){setSave('저장 실패: '+e,true);});}
function refreshRow(id){var el=ELS.get(id);if(!el)return;var c=byId[id];
 el.querySelector('.head').innerHTML='<span class="id">'+esc(id)+'</span>'
  +badges(c)+nums(c)+controls(c);
 hookRow(el,id);}
function setSave(msg,bad){var s=$('save');s.textContent=msg;
 s.style.color=bad?'#ff9c9c':'#8fe6a8';}
function progress(){var n=0;CASES.forEach(function(c){
 if((REVIEW[c.id]||{}).checked)n++;});
 $('prog').textContent='확인 '+n+'/'+CASES.length;}

// ===== 필터·정렬 =====
function vals(n){return Array.prototype.slice.call(
 document.querySelectorAll(n)).filter(function(i){return i.checked;})
 .map(function(i){return i.value;});}
function ensure(c){if(!ELS.has(c.id))ELS.set(c.id,rowEl(c));
 return ELS.get(c.id);}
function apply(){fire();
 var onB=new Set(vals('input[name=b]'));
 var onD=new Set(vals('input[name=d]'));
 var oo=document.querySelectorAll('input[name=o]');
 var onO=oo.length?new Set(vals('input[name=o]')):null;
 var onlyU=$('unc').checked;
 var ag=parseFloat($('ag').value),qa=$('q').value.trim();
 var list=CASES.filter(function(c){var rv=REVIEW[c.id]||{};
  var d=rv.det||'none';
  if(!onB.has(c.bucket))return false;
  if(!onD.has(d))return false;
  if(onO&&!onO.has(c.outcome||'no_compare'))return false;
  if(onlyU&&rv.checked)return false;
  if(!(parseFloat(c.agree)<ag))return false;
  if(qa&&!c.id.includes(qa))return false;
  return true;});
 var s=$('sort').value;
 if(s==='agree')list=list.slice().sort(function(a,b){
  return a.agree-b.agree||(a.id<b.id?-1:1);});
 else if(s==='aspect')list=list.slice().sort(function(a,b){
  return a.aspect-b.aspect;});
 else if(s==='aspect_d')list=list.slice().sort(function(a,b){
  return b.aspect-a.aspect;});
 var box=$('rows');list.forEach(function(c){box.appendChild(ensure(c));});
 var vis=new Set(list.map(function(c){return c.id;}));
 ELS.forEach(function(el,iid){el.style.display=vis.has(iid)?'':'none';});
 VIS=list.map(function(c){return c.id;});
 if(cur>=VIS.length)cur=VIS.length-1;
 $('count').textContent=' '+list.length+'건 표시';}

// ===== 단축키 =====
function curId(){return VIS.length?VIS[Math.max(0,cur)]:null;}
function move(d){if(!VIS.length)return;
 cur=Math.max(0,Math.min(VIS.length-1,cur+d));
 var el=ELS.get(VIS[cur]);if(el){el.scrollIntoView({block:'center'});
  el.classList.add('cur');
  setTimeout(function(){el.classList.remove('cur');},700);}}
function quickDet(d){var id=curId();if(!id)return;
 var el=ELS.get(id);if(!el)return;var sel=el.querySelector('.det');
 sel.value=d;sel.dispatchEvent(new Event('change'));}
function quickChk(){var id=curId();if(!id)return;
 var el=ELS.get(id);if(!el)return;var cb=el.querySelector('.chkbox');
 cb.checked=!cb.checked;cb.dispatchEvent(new Event('change'));}
document.addEventListener('keydown',function(e){var t=e.target;
 if(t&&(t.tagName==='INPUT'||t.tagName==='SELECT'||t.tagName==='TEXTAREA')){
  if(e.key==='Escape')t.blur();return;}
 if(e.key==='j'||e.key==='J'){move(1);e.preventDefault();}
 else if(e.key==='k'||e.key==='K'){move(-1);e.preventDefault();}
 else if(e.key>='1'&&e.key<='5'){quickDet(DETS[+e.key-1]);}
 else if(e.key==='0'){quickDet('');}
 else if(e.key==='x'||e.key==='X'){quickChk();}});

// ===== 초기화 =====
fetch('/api/cases').then(function(r){return r.json();})
 .then(function(d){CASES=d.cases;
  CASES.forEach(function(c){byId[c.id]=c;});
  $('blurb').textContent=d.blurb;
  return fetch('/api/review').then(function(r){return r.json();});})
 .then(function(rv){REVIEW=rv||{};
  var box=$('rows');
  CASES.forEach(function(c){box.appendChild(ensure(c));});
  Array.prototype.slice.call(document.querySelectorAll(
   '.bar input,.bar select')).forEach(function(i){
   i.addEventListener('change',function(){apply();
    if(i.tagName==='SELECT')i.blur();});
   if(i.type==='text')i.addEventListener('input',apply);});
  progress();apply();setSave('준비됨');})
 .catch(function(e){document.body.insertAdjacentHTML('afterbegin',
  '<div class="meta" style="color:#ff9c9c">로드 실패: '+e+'</div>');});
"""


def build_serve_html(meta, review, seed_crc32):
    """브라우저에서 판정을 고치는 검토 UI. 데이터는 /api/cases·/api/review 로."""
    compare_mode = meta.get("compare") is not None
    det_meta = (review or {}).get("_meta", {}).get("det_classes", {})
    det_legend = " · ".join(
        f"{k}={html_escape(v)}" for k, v in det_meta.items()) or (
        "ok=검출 정상 · cut=잘림 · wrong_area=엉뚱한 영역 · orient=방향 · "
        "ambiguous=귀인 불가")
    outcome_bar = ""
    if compare_mode:
        outcome_bar = ("<b>비교</b> " + "".join(
            f"<label><input type=checkbox name=o value={k} checked>"
            f"{OUTCOME_LABEL[k]}</label>" for k in OUTCOME_ORDER))
    det_checks = "".join(
        f"<label><input type=checkbox name=d value={k} checked>{k}</label>"
        for k in DET_CLASSES)
    extra_css = (
        ".row .det{max-width:130px}\n"
        ".row .note{background:#1b2024;color:#d8dde2;"
        "border:1px solid #2a3138;border-radius:4px;padding:3px 6px;"
        "width:260px}\n"
        ".row .by{color:#8aa0ae;font-size:11px;white-space:nowrap}\n"
        ".row .chk{white-space:nowrap}\n"
        "#save{white-space:nowrap}\n")
    js = (SERVE_JS
          .replace("__COMPARE__", "true" if compare_mode else "false")
          .replace("__SEEDCRC__", "true" if seed_crc32 else "false"))
    return (
        "<!DOCTYPE html><html lang=ko><head><meta charset=utf-8>"
        "<title>판독 실패 아틀라스 — 검토</title>"
        f"<style>{BASE_CSS}{extra_css}</style></head>"
        "<body><h1>판독 실패 아틀라스 — 검토 서버</h1>"
        "<div class=meta id=blurb>불러오는 중…</div>"
        "<div class=meta legend><b>범례</b> — "
        f"<span><i class=sw style=background:rgb{C_GM[::-1]}></i>GM 예측 쿼드</span>"
        f"<span><i class=sw style=background:rgb{C_CROP[::-1]}></i>BOX_MARGIN 크롭 박스(리더 입력)</span>"
        f"<span><i class=sw style=background:rgb{C_LCD[::-1]}></i>사람 LCD 라벨</span>"
        f"<span><i class=sw style=background:rgb{C_BAND[::-1]}></i>사람 밴드 라벨</span>"
        "<br><b>det 판정 클래스</b> — " + det_legend +
        "<br><b>단축키</b> — j/k 다음·이전 행 · 1~5 det 지정(ok cut "
        "wrong_area orient ambiguous) · 0 미판정 · x 확인함 토글. "
        "드롭다운을 고른 뒤에도 단축키는 곧바로 먹는다(포커스를 본문으로 "
        "되돌린다). 편집은 즉시 agent_review.json 에 저장된다."
        "</div>"
        f"<div class=meta>{_notes_html(seed_crc32)}</div>"
        "<div class=bar><b>필터</b> "
        "<label><input type=checkbox name=b value=risky checked>risky</label>"
        "<label><input type=checkbox name=b value=safe checked>safe</label>"
        "<label><input type=checkbox name=b value=blank checked>blank</label>"
        "<label><input type=checkbox name=b value=exact checked>정답(대조군)</label>"
        f"{outcome_bar}"
        "<b>검출 판정</b> " + det_checks +
        "<label><input type=checkbox name=d value=none checked>미판정</label>"
        "<label><input type=checkbox id=unc>미확인만</label>"
        "<label>득표율 ≤ <select id=ag><option value=1.01>전부</option>"
        "<option value=0.778 selected>&lt;0.778(거절선)</option>"
        "<option value=0.556>&lt;0.556</option></select></label>"
        "<label>정렬 <select id=sort><option value=default>기본(층·득표)</option>"
        "<option value=agree>득표율 ↑</option>"
        "<option value=aspect>종횡비 w/h ↑</option>"
        "<option value=aspect_d>종횡비 w/h ↓</option></select></label>"
        "<label>id <input type=text id=q placeholder=\u201cbatch2/17\u201d></label>"
        "<span id=count class=num></span> · <span id=prog class=num></span>"
        " · <span id=save></span></div>"
        "<div id=rows></div>"
        f"<script>{js}</script></body></html>")


class AtlasHandler(BaseHTTPRequestHandler):
    # 검토 서버. 상태(케이스 JSON·페이지 HTML·리뷰 저장소)는 서버 시작 전에
    # 클래스 속성으로 묶는다 — 요청 처리 중 무거운 계산은 없다.
    state = None

    def log_message(self, fmt, *args):
        pass

    def _send(self, code, body: bytes, ctype: str):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")  # 옛 HTML 캐시 방지
        self.end_headers()
        self.wfile.write(body)

    def _json(self, obj, code=200):
        self._send(code, json.dumps(obj, ensure_ascii=False).encode("utf-8"),
                   "application/json; charset=utf-8")

    def do_GET(self):
        u = urlparse(self.path)
        st = self.state
        if u.path in ("/", "/index.html"):
            self._send(200, st.page.encode("utf-8"),
                       "text/html; charset=utf-8")
            return
        if u.path == "/api/cases":
            self._send(200, st.cases_json.encode("utf-8"),
                       "application/json; charset=utf-8")
            return
        if u.path == "/api/review":
            self._json(st.store.get())
            return
        if u.path.startswith("/imgs/"):
            name = u.path[len("/imgs/"):]
            # 데이터 루트 밖 경로 차단 — 이름에 경로 성분 자체를 허용하지 않는다.
            if not name or "/" in name or "\\" in name or ".." in name:
                self._send(403, b"forbidden", "text/plain")
                return
            p = (st.imgs_dir / name).resolve()
            try:
                p.relative_to(st.imgs_dir.resolve())
            except ValueError:
                self._send(403, b"forbidden", "text/plain")
                return
            if not p.is_file():
                self._send(404, b"not found", "text/plain")
                return
            ctype = ("image/png" if p.suffix == ".png"
                     else "image/jpeg" if p.suffix == ".jpg"
                     else "application/octet-stream")
            self._send(200, p.read_bytes(), ctype)
            return
        self._send(404, b"not found", "text/plain")

    def do_POST(self):
        u = urlparse(self.path)
        if u.path != "/api/review":
            self._json({"error": "unknown api"}, 404)
            return
        try:
            ln = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(ln) or b"{}")
        except Exception as e:
            self._json({"error": f"bad body: {e}"}, 400)
            return
        rid = body.get("id")
        if not isinstance(rid, str):
            self._json({"error": "id 없음"}, 400)
            return
        det = body.get("det")
        note = body.get("note", "")
        if not isinstance(note, str):
            self._json({"error": "note 는 문자열"}, 400)
            return
        try:
            rec = self.state.store.apply(rid, det, note,
                                         bool(body.get("checked", False)))
        except ValueError as e:
            self._json({"error": str(e)}, 400)
            return
        self._json({"ok": True, "rec": rec})


def build_cases(root: Path, args, out_dir: Path):
    """공통 파이프라인: 입력 로드 → 행 선택 → 렌더·추론 → 메타.
    정적 생성과 검토 서버가 같은 결과를 보게 하는 단일 경로다.
    """
    datumo = root.parent / "upstream" / "datumo"
    images = datumo / "extracted" / "TILDE"

    def rp(name):  # 데이터 루트 상대 이름 → 절대경로(절대경로 입력은 그대로)
        p = Path(name)
        return p if p.is_absolute() else root / p

    # ===== 입력 (모델·캐시·라벨 전부 읽기 전용) =====
    preds = json.loads(rp(args.preds).read_text(encoding="utf-8"))
    compare_preds = None
    if args.compare_preds:
        compare_preds = json.loads(
            rp(args.compare_preds).read_text(encoding="utf-8"))
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

    crows = classify(compare_preds, readings, corrections) \
        if compare_preds is not None else None

    # ===== 선택 + 모델 =====
    sel = select_rows_compare(rows, crows) if crows else select_rows(rows)
    n_new_wrong = sum(1 for r in sel if r["stratum"] == "new_wrong")
    print(f"선택 {len(sel)}건 = 오답 {counts['risky'] + counts['safe'] + counts['blank']}"
          f" + 대조군 {N_CONTROL_LOW + N_CONTROL_HIGH}"
          + (f" · 새로 틀림 층 {n_new_wrong}건(대조군에 뽑혔던 행은 이 층으로 "
             f"옮겨진다)" if crows else ""))

    model = tf.keras.models.load_model(str(rp(args.model)))
    logits_model = tf.keras.Model(model.get_layer("img").input,
                                  model.get_layer("logits").output)

    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "imgs").mkdir(exist_ok=True)

    # ===== 등가성 검사: 이 도구의 워프 == 지정한 캐시의 holdout 크롭 =====
    # --model 과 --cache 는 반드시 같은 쪽(같은 프레이밍)으로 짝지어야 한다.
    # 짝이 어긋나면 여기서 죽는다 — 거짓 통과보다 즉시 실패가 안전하다.
    cache = np.load(str(rp(args.cache)))
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
                f"등가성 검사 실패: {c['id']} — 이 도구의 크롭이 {args.cache} 의 "
                "holdout 크롭과 다르다. --model 과 --cache 가 같은 프레이밍 짝인지 "
                "확인할 것(eval_reader 기하가 바뀌었다면 캐시도 그 짝으로 지정).")
        eq_done += 1
    print(f"등가성 검사 통과 {eq_done}/{EQ_CHECK_N} "
          f"({args.cache} holdout 크롭과 픽셀 일치)")
    if eq_done == 0:
        raise SystemExit("등가성 검사를 한 건도 못 했다 — holdout 교집합이 없다")

    # ===== 케이스별 렌더 + 추론 =====
    cases = []
    for c in sel:
        cid = c["id"]
        sid = cid.replace("/", "__")
        p = images / f"{cid}.jpg"
        g = load_gray(p)
        if g is None:
            print(f"경고: {cid} 디코드 실패 — 행 생략")
            continue
        quad = quads[cid]
        crop_rect = framed_src_rect(g, quad)
        q = np.asarray(quad, dtype=np.float64)
        qw = q[:, 0].max() - q[:, 0].min()
        qh = q[:, 1].max() - q[:, 1].min()
        aspect = round(qw / max(qh, 1e-6), 2)
        stretch = round(2.0 / max(aspect, 1e-6), 2)
        stretch_out = not (STRETCH_P10 <= stretch <= STRETCH_P90)

        vis = draw_overlay(g, quad, crop_rect,
                           [(lcd_labels.get(cid), C_LCD),
                            (band_labels.get(cid), C_BAND)])
        cv2.imwrite(str(out_dir / "imgs" / f"{sid}_full.jpg"), vis,
                    [cv2.IMWRITE_JPEG_QUALITY, 88])
        scale = 1000.0 / vis.shape[0]
        if scale < 1.0:
            ov = cv2.resize(vis, None, fx=scale, fy=scale,
                            interpolation=cv2.INTER_AREA)
        else:
            ov = vis
        cv2.imwrite(str(out_dir / "imgs" / f"{sid}_ov.jpg"), ov,
                    [cv2.IMWRITE_JPEG_QUALITY, 85])

        rect = frame_crop(g, quad)
        cv2.imwrite(str(out_dir / "imgs" / f"{sid}_warp.png"), rect)
        warp2x = cv2.resize(rect, (IN_W * 2, IN_H * 2),
                            interpolation=cv2.INTER_NEAREST)
        cv2.imwrite(str(out_dir / "imgs" / f"{sid}_warp2x.png"), warp2x)

        lcd_m = side_metrics(quad, lcd_labels[cid]) if cid in lcd_labels else None
        lab_bits = []
        if lcd_m:
            lab_bits.append(
                f"LCD라벨 있음 IoU {lcd_m['iou']} recall {lcd_m['label_recall']} "
                f"잘림(L{lcd_m['cut_left_px']}/R{lcd_m['cut_right_px']}/"
                f"T{lcd_m['cut_top_px']}/B{lcd_m['cut_bottom_px']}px)")
        else:
            lab_bits.append("LCD라벨 없음")
        if cid in band_labels:
            lab_bits.append("밴드라벨 있음")

        c.update(sid=sid, img_w=g.shape[1], img_h=g.shape[0],
                 aspect=aspect, stretch=stretch, stretch_out=stretch_out,
                 wide=aspect > 1.5,
                 gm_box=",".join(str(int(round(v))) for v in (
                     q[:, 0].min(), q[:, 1].min(), q[:, 0].max(), q[:, 1].max())),
                 crop_box=",".join(str(int(round(v))) for v in (
                     crop_rect[:, 0].min(), crop_rect[:, 1].min(),
                     crop_rect[:, 0].max(), crop_rect[:, 1].max())),
                 lcd_label=lcd_labels.get(cid), band_label=band_labels.get(cid),
                 lcd_metrics=lcd_m,
                 lab_txt=" · ".join(lab_bits),
                 _rect=rect)
        cases.append(c)

    # ===== 일괄 추론: 기본 크롭 logits + TTA 변형 =====
    base = np.asarray([c["_rect"] for c in cases], dtype=np.float32)[..., None]
    base_logits = logits_model.predict(base, batch_size=128, verbose=0)

    all_var, owner = [], []
    for i, c in enumerate(cases):
        # eval_reader 가 아직 hash(cid)(프로세스마다 바뀜)로 시드를 뽑는다면 이
        # 표는 같은 분포의 지터를 재현 실행으로 보여주는 것(crc32 고정)이다.
        # crc32 로 통일된 뒤에는 곧 공식 집계와 같은 시드가 된다.
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
        am_row = np.array([a for a, _ in c["timesteps"]])
        c["ts_raw"], c["collapsed"] = greedy_with_collapse(am_row)
        # TTA 표와 비교할 공식 예측(비교 모드에선 후보 예측 — 살아있는 패널은
        # --model 이고 그 짝은 후보 예측 파일이다).
        ref = c["pred"]
        if crows is not None:
            comp = crows.get(c["id"])
            c["compare"] = ({"pred": comp["pred"], "agree": comp["agree"],
                             "bucket": comp["bucket"],
                             "rejected": comp["rejected"]}
                            if comp else None)
            c["outcome"] = outcome_of(c, comp)
            if comp:
                ref = comp["pred"]
        else:
            c["compare"], c["outcome"] = None, None
        c["tta_ref"] = ref
        del c["_rect"]

    # ===== 메타 =====
    commit = subprocess.run(
        ["git", "-C", str(HERE), "rev-parse", "--short", "HEAD"],
        capture_output=True, text=True).stdout.strip()

    def src_info(p: Path):
        return {"file": p.name,
                "mtime": datetime.fromtimestamp(p.stat().st_mtime).isoformat(
                    timespec="minutes")}

    files = {name: src_info(p) for name, p in (
        ("gmscreen_quads.jsonl", root / "gmscreen_quads.jsonl"),
        ("preds", rp(args.preds)), ("cache", rp(args.cache)))}
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

    seed_crc32 = eval_seed_is_crc32()
    cmp_meta = None
    if crows is not None:
        totals = Counter(outcome_of(r, crows.get(i))
                         for i, r in rows.items())
        cmp_meta = {
            "path": str(rp(args.compare_preds)),
            # holdout 전체 기준 4분류 — McNemar 표의 눈으로 볼 버전.
            "totals": {k: totals.get(k, 0) for k in OUTCOME_ORDER},
            "selected": dict(Counter(
                c["outcome"] for c in cases if c["outcome"])),
        }

    blurb = (
        f"생성 {datetime.now().isoformat(timespec='minutes')} · 워크트리 커밋 {commit}\n"
        f"data-root(읽기 전용): {root}\n"
        f"검출기 예측: gmscreen_quads.jsonl({len(quads)}행) — ft3/ft4/oriented 아님(정본)\n"
        f"리더 모델: {args.model} · 기준선 예측: {args.preds}"
        f"(hold-out {len(rows)}건) · 캐시: {args.cache}\n"
        f"분류(REJECT_AT={REJECT_AT}, webtool 기준): "
        f"risky {counts['risky']} / safe {counts['safe']} / blank {counts['blank']} "
        f"/ exact {counts['exact']} / 거절대상 {n_rej}\n"
        + (f"A/B 비교: {args.preds} vs {args.compare_preds} — "
           f"고쳐짐 {cmp_meta['totals']['fixed']}"
           f" / 새로 틀림 {cmp_meta['totals']['new_wrong']}"
           f" / 둘 다 틀림 {cmp_meta['totals']['both_wrong']}"
           f" / 둘 다 정답 {cmp_meta['totals']['both_right']}"
           f" / 비교본 없음 {cmp_meta['totals']['no_compare']}"
           f" (hold-out 전체)\n" if cmp_meta else "")
        + f"TTA 시드: "
        f"{'crc32(재현성 확보)' if seed_crc32 else 'hash(cid) — 비재현. TTA 표는 crc32 재현이고 공식 득표율이 정본'}\n"
        f"참고 — GM 검출 없음(labels 중 쿼드 없음): {len(gm_miss)}건 {gm_miss[:8]}\n"
        f"층 순서: " + ("새로 틀림(후보 득표 오름차순) → " if crows is not None else "")
        + f"risky → safe → blank → ctrl_low(정답·저득표 {N_CONTROL_LOW}) "
        f"→ ctrl_high(정답·만장일치 표본 {N_CONTROL_HIGH}) · 사전순 섞기 없음\n"
        f"등가성: eval_reader 기하로 만든 크롭 {eq_done}건이 {args.cache} "
        f"holdout 크롭과 픽셀 일치")

    meta = {"blurb": blurb, "files": files, "q3": q3,
            "preds": str(rp(args.preds)), "model": str(rp(args.model)),
            "cache": str(rp(args.cache)), "compare": cmp_meta,
            "seed_crc32": seed_crc32,
            "strata": Counter(c["stratum"] for c in cases),
            "wide_wrong": sum(1 for c in cases
                              if c["bucket"] != "exact" and c["wide"]),
            "wide_all_selected": sum(1 for c in cases if c["wide"]),
            "stretch_out_selected": sum(1 for c in cases if c["stretch_out"]),
            "lcd_label_overlap": {
                "wrong_with_lcd_label": sum(
                    1 for c in cases
                    if c["bucket"] != "exact" and c["lcd_label"]),
                "ctrl_with_lcd_label": sum(
                    1 for c in cases
                    if c["bucket"] == "exact" and c["lcd_label"])}}
    return cases, meta


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-root", default=str(HERE),
                    help="gitignored 데이터가 있는 assets_dev/train 절대경로. "
                         "워크트리에서는 메인 트리 것을 지정한다.")
    ap.add_argument("--review", default=None,
                    help="agent_review.json — 정적 모드에서는 판정 뱃지 입력. "
                         "--serve 에서는 저장 대상 경로가 되고, 생략하면 "
                         "_diag/atlas/agent_review.json 을 쓴다.")
    ap.add_argument("--serve", action="store_true",
                    help="검토 서버 — 브라우저에서 판정을 고치고 저장한다.")
    ap.add_argument("--port", type=int, default=8790)
    ap.add_argument("--model", default="reader_model",
                    help="리더 모델 디렉터리(데이터 루트 상대 또는 절대경로).")
    ap.add_argument("--preds", default="reader_preds.json",
                    help="기준선 예측 {id: [pred, gt, agree]} (데이터 루트 상대).")
    ap.add_argument("--cache", default="data_cache_v2.npz",
                    help="등가성 검사에 쓸 학습 캐시. --model 과 같은 "
                         "프레이밍 짝이어야 한다.")
    ap.add_argument("--compare-preds", default=None,
                    help="A/B 비교 모드 — 후보 예측 파일. 행 구성은 기준선"
                         "(--preds) 기준이고 새로 틀림 층을 맨 위에 둔다.")
    args = ap.parse_args()
    root = Path(args.data_root).resolve()

    out_dir = SERVE_OUT if args.serve else OUT
    cases, meta = build_cases(root, args, out_dir)
    (out_dir / "atlas_meta.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=1, default=str),
        encoding="utf-8")

    if not args.serve:
        review = review_load(Path(args.review)) if args.review else None
        (OUT / "index.html").write_text(
            build_html(cases, meta, review, meta["seed_crc32"]),
            encoding="utf-8")
        print(f"saved {OUT / 'index.html'} · 행 {len(cases)} · "
              f"이미지 {len(cases) * 4}장")
        return 0

    review_path = Path(args.review) if args.review else OUT / "agent_review.json"
    store = ReviewStore(review_path, {c["id"] for c in cases})
    state = type("State", (), {})()
    state.store = store
    state.imgs_dir = SERVE_OUT / "imgs"
    state.page = build_serve_html(meta, store.get(), meta["seed_crc32"])
    slim = [{k: v for k, v in c.items()
             if k not in ("lcd_label", "band_label", "lcd_metrics")}
            for c in cases]
    state.cases_json = json.dumps(
        {"blurb": meta["blurb"], "cases": slim},
        ensure_ascii=False, default=str)
    AtlasHandler.state = state
    srv = ThreadingHTTPServer(("127.0.0.1", args.port), AtlasHandler)
    print(f"검토 서버: http://127.0.0.1:{args.port}/  (Ctrl+C 중지)")
    print(f"판정 저장: {review_path} (첫 저장 전에 .bak 을 한 번 남긴다)")
    print(meta["blurb"])
    srv.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
