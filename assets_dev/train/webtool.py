# SugarScan 라벨링·학습 모니터 웹 서버 — 표준 라이브러리만 사용(의존성 0).
#
# 실행:  conda run -n sugartrain python webtool.py   (포트 8777)
# 브라우저: http://127.0.0.1:8777/
#
# 제공:
#   /                       라벨러+모니터 SPA (webtool.html)
#   /api/meta               이미지 id 목록·GT·라벨 현황
#   /api/image?id=&w=       리사이즈 JPEG (디스크 캐시)
#   /api/labels?mode=       band(band_boxes.jsonl) | lcd(screen_boxes.jsonl)
#   POST /api/label         {mode,id,quad,source} 저장
#   POST /api/gtfix         {id,corrected} GT 교정 기록
#   /api/quads?kind=        모델 예측 사전표시용 (band=datumo_quads, gm=gmscreen_quads)
#   /api/trainlog           ctc_train_gpu.log loss 궤적
#   /api/preds_holdout      reader_preds.json (평가 완료 시)
import base64
import hashlib
import json
import os
import re
import subprocess
import sys
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse, parse_qs

import cv2
import numpy as np
from PIL import Image, ImageOps

HERE = Path(__file__).resolve().parent
DATUMO = HERE.parent / "upstream" / "datumo"
IMAGES = DATUMO / "extracted" / "TILDE"
CACHE = HERE / "cache"
# 밴드 라벨은 **새 파일에 쌓는다.** 옛 `labeled.jsonl` 358장 중 300장이
# 프레임 검증(`ow`/`oh`, 2026-09-02) 이전에 저장돼 좌표를 신뢰할 수 없다 —
# 그 크롭으로 읽히면 14.6%(GM 화면 크롭은 96.6%). 같은 파일에 이어 쓰면 옛
# 라벨이 "라벨 있음"으로 떠서 **깨진 박스가 프리필**되고, 사람이 그걸 그대로
# 승인하기 쉽다(시범 79장 중 10장이 여기 걸린다).
# LCD 라벨도 같은 이유로 `screen_boxes.jsonl` 을 새로 팠다 — 그 선례를 따른다.
BAND_FILE = HERE / "band_boxes.jsonl"
BAND_LEGACY = HERE / "labeled.jsonl"   # 보존만. 읽지도 쓰지도 않는다.
LCD_FILE = HERE / "screen_boxes.jsonl"
GT_FIX = HERE / "gt_corrections.jsonl"
BAND_QUADS = HERE / "datumo_quads_v2.jsonl"  # v2 밴드 모델 예측(도메인 AP50 98.4)
GM_QUADS = HERE / "gmscreen_quads_oriented.jsonl"  # 표시(oriented) 좌표계 변환본 — 라벨러 힌트 전용
TRAIN_LOG = HERE / "ctc_train_gpu.log"
RESUME_STATE = HERE / "checkpoints_v2" / "resume_state.json"
HOLDOUT = HERE / "reader_preds.json"
HTML = HERE / "webtool.html"
PID_FILE = HERE / "train_pid.json"
DETACHED = 0x00000008 | 0x00000200  # DETACHED_PROCESS | NEW_PROCESS_GROUP

# 표시(EXIF 적용) 이미지 좌표계가 이 도구의 유일한 좌표 정본이다.
# 라벨 저장은 "클라이언트가 그린 프레임 크기(ow/oh)"를 함께 받아 서버가
# 실측 크기와 대조한 뒤에만 기록한다 — 낡은 JS 가 살아 있는 탭에서 온
# 어긋난 좌표가 파일에 닿지 못하게 막는 마지막 방어선.
# TTA 득표율이 이 아래면 '거절 대상'으로 표시한다. **잠정값이다** —
# 실제 임계값은 사람이 정한다(0.778 에서 오독 0.27%·미인식 5.3%,
# 0.889 에서 0.09%·7.7%. 게이트는 오독 ≤0.2%·미인식 ≤5%).
REJECT_AT = 0.778

FRAME_TOL = 1        # 표시 크기 허용 오차(px) — 반올림 외에는 허용하지 않는다
BOUNDS_TOL = 2.0     # 경계 초과 허용치(px)

ROUTES = {}


def route(path):
    def deco(fn):
        ROUTES[path] = fn
        return fn
    return deco


def read_jsonl(p: Path):
    if not p.exists():
        return {}
    out = {}
    for l in p.read_text(encoding="utf-8").splitlines():
        if l.strip():
            j = json.loads(l)
            out[j["id"]] = j
    return out


def write_jsonl(p: Path, rows: dict):
    tmp = p.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        for j in rows.values():
            f.write(json.dumps(j, ensure_ascii=False) + "\n")
    tmp.replace(p)


def load_readings():
    rows = read_jsonl(DATUMO / "labels.jsonl")
    return {k: v["reading"] for k, v in rows.items()}


def load_corrections():
    out = {}
    if GT_FIX.exists():
        for l in GT_FIX.read_text(encoding="utf-8").splitlines():
            if l.strip():
                j = json.loads(l)
                out[j["id"]] = j["corrected"]
    return out


@route("/api/meta")
def api_meta(qs):
    readings = load_readings()
    corrections = load_corrections()
    band = read_jsonl(BAND_FILE)
    lcd = read_jsonl(LCD_FILE)
    ids = sorted(readings)
    items = []
    for cid in ids:
        s = str(corrections.get(cid, readings[cid]))
        items.append({
            "id": cid,
            "gt": s,
            "fixed": cid in corrections,
            "band": "quad" in band.get(cid, {}) or band.get(cid, {}).get("source") == "skipped",
            "lcd": "quad" in lcd.get(cid, {}) or lcd.get(cid, {}).get("source") == "skipped",
        })
    return {"items": items,
            "band_count": sum(1 for i in items if i["band"]),
            "lcd_count": sum(1 for i in items if i["lcd"])}


@route("/api/labels")
def api_labels(qs):
    mode = qs.get("mode", ["band"])[0]
    p = BAND_FILE if mode == "band" else LCD_FILE
    rows = read_jsonl(p)
    out = {}
    for cid, j in rows.items():
        out[cid] = {"quad": j.get("quad"), "source": j.get("source")}
    return {"labels": out}


@route("/api/quads")
def api_quads(qs):
    kind = qs.get("kind", ["band"])[0]
    p = BAND_QUADS if kind == "band" else GM_QUADS
    out = {}
    if p.exists():
        for l in p.read_text(encoding="utf-8").splitlines():
            if l.strip():
                j = json.loads(l)
                out[j["id"]] = j["quad"]
    return {"quads": out}


@route("/api/trainlog")
def api_trainlog(qs):
    losses, phase = parse_trainlog()
    return {"losses": losses, "phase": phase, "epoch": len(losses)}


def parse_trainlog():
    losses = []
    phase = "대기"
    if TRAIN_LOG.exists():
        raw = TRAIN_LOG.read_text(encoding="utf-8", errors="ignore")
        raw = re.sub(r"\x1b\[[0-9;]*m", "", raw)
        # val_loss 까지 삼키지 않게 단어 경로 차단
        for m in re.finditer(r"(?<![A-Za-z_])loss: ([0-9.]+)", raw):
            losses.append(float(m.group(1)))
        if "== real finetune ==" in raw:
            phase = "파인튜닝"
        elif losses:
            phase = "사전학습"
    return losses, phase


def train_pid():
    if not PID_FILE.exists():
        return None
    try:
        return json.loads(PID_FILE.read_text(encoding="utf-8")).get("pid")
    except Exception:
        return None


def pid_alive(pid):
    if not pid:
        return False
    out = subprocess.run(["tasklist", "/FI", f"PID eq {pid}"],
                         capture_output=True, text=True).stdout
    return str(pid) in out


def resume_point():
    """이어서 돌릴 지점. 학습이 끝까지 가면 스크립트가 지운다."""
    if not RESUME_STATE.exists():
        return None
    try:
        return json.loads(RESUME_STATE.read_text(encoding="utf-8"))
    except Exception:
        return None


@route("/api/train/status")
def api_train_status(qs):
    pid = train_pid()
    alive = pid_alive(pid)
    fresh = False
    if TRAIN_LOG.exists():
        fresh = (time.time() - TRAIN_LOG.stat().st_mtime) < 180
    losses, phase = parse_trainlog()
    # 에폭 수를 로그의 `loss:` 개수로 세면 재개할 때마다 누적돼 부풀려진다.
    # 재개 지점이 있으면 그쪽이 정본이다.
    rp = resume_point()
    epoch = rp["next_epoch"] if rp else len(losses)
    return {"managed_pid": pid, "managed_alive": alive,
            "log_fresh": fresh, "losses": losses[-300:],
            "epoch": epoch, "phase": phase, "resume": rp}


@route("/api/logtail")
def api_logtail(qs):
    n = int(qs.get("lines", ["50"])[0])
    if not TRAIN_LOG.exists():
        return {"text": "(로그 없음)"}
    lines = TRAIN_LOG.read_text(encoding="utf-8", errors="ignore").splitlines()
    return {"text": "\n".join(lines[-n:])}


@route("/api/preds_holdout")
def api_preds_holdout(qs):
    if not HOLDOUT.exists():
        return {"preds": None}
    return {"preds": json.loads(HOLDOUT.read_text(encoding="utf-8"))}


@route("/api/failures")
def api_failures(qs):
    # 실패 모아보기(라벨러 큐 필터용):
    #   gm_miss    — GM 검출기가 쿼드를 못 낸 장(gmscreen_quads 기준)
    #   reader_miss — CTC 판독이 GT 와 다른 장(reader_preds 기준, eval 대상만)
    readings = load_readings()
    corrections = load_corrections()
    gm_ids = set(read_jsonl(GM_QUADS))
    all_ids = set(readings)
    gm_miss = sorted(all_ids - gm_ids)
    # 판독 실패를 **성격별로 가른다.** 한 덩어리로 두면 쓸모가 적다 —
    # 이 앱에서 위험한 것은 "값을 냈는데 틀린 것"이지 "못 읽은 것"이 아니다.
    #   risky   자릿수가 GT 와 같은데 틀림 → 값이 그럴듯해 범위 검증기·프레임
    #           합의를 통과한다. **실제로 위험한 유일한 부류다.**
    #   safe    자릿수가 달라짐(늘거나 줄거나) → 범위 밖으로 걸러진다
    #   blank   아무것도 못 냄
    reader_miss, reader_risky, reader_safe, reader_blank = [], [], [], []
    reader_rejected = []
    reader_note = {}
    if HOLDOUT.exists():
        preds = json.loads(HOLDOUT.read_text(encoding="utf-8"))
        for cid, v in preds.items():
            gt = str(corrections.get(cid, readings.get(cid, v[1] if len(v) > 1 else v[0])))
            pred = str(v[0])
            if pred == gt:
                continue
            reader_miss.append(cid)
            if not pred:
                kind, bucket = "무출력", reader_blank
            elif len(pred) == len(gt):
                kind, bucket = "위험(자릿수 보존)", reader_risky
            else:
                kind, bucket = "안전(자릿수 변동)", reader_safe
            bucket.append(cid)
            # 득표율(TTA 다수결의 지지도)이 있으면 함께 보여준다 — 이 값이 낮으면
            # 거절 대상이라 실제 앱에서는 사용자에게 값이 가지 않는다.
            ag = v[2] if len(v) > 2 else None
            tail = f" · 득표 {ag:.2f}{' → 거절대상' if ag < REJECT_AT else ''}"                 if ag is not None else ""
            reader_note[cid] = f"{kind} · {gt} -> {pred or '(없음)'}{tail}"
        # 득표율이 낮아 거절될 장 — 정답·오답 무관. 실제 앱에서 값이 안 나가는 쪽이다.
        if any(len(v) > 2 for v in preds.values()):
            for cid, v in preds.items():
                if len(v) > 2 and v[2] < REJECT_AT:
                    reader_rejected.append(cid)
                    if cid not in reader_note:
                        reader_note[cid] = (f"거절대상(득표 {v[2]:.2f}) · "
                                            f"판독 {v[0]} · GT {v[1]}")
        for b in (reader_miss, reader_risky, reader_safe, reader_blank,
                  reader_rejected):
            b.sort()
    # band_pilot — make_band_pilot.py 가 만든 시범 라벨링 작업 목록.
    # 사람이 "어느 장을 라벨링할지" 고르지 않아도 되게 미리 층화해 둔 것이다
    # (가로 화면 / 위험군 오독 / 대조군). 없으면 빈 목록.
    def _queue(fname):
        ids, note = [], {}
        p = HERE / fname
        if p.exists():
            try:
                for r in json.loads(p.read_text(encoding="utf-8")):
                    ids.append(r["id"])
                    note[r["id"]] = f"{r['stratum']} · {r['note']}"
            except Exception:
                return [], {}
        return ids, note

    pilot, pilot_note = _queue("band_pilot.json")
    lcdfix, lcdfix_note = _queue("lcd_fix_queue.json")
    # 가로형 밴드 — make_wide_band_queue.py. 학습셋 먼저, 검증 나중 순서다.
    wideband, wideband_note = _queue("wide_band_queue.json")
    # 테스트 holdout — 라벨링하면 개선을 잴 데가 없어진다. 큐에서 빼는 것으로는
    # 부족하고(전체 큐로 들어올 수 있다) 화면에 경고를 띄운다.
    hold, _ = _queue("lcd_fix_holdout.json")
    return {"gm_miss": gm_miss, "reader_miss": reader_miss,
            "reader_risky": reader_risky, "reader_safe": reader_safe,
            "reader_blank": reader_blank, "reader_rejected": reader_rejected,
            "reader_note": reader_note,
            "band_pilot": pilot, "band_pilot_note": pilot_note,
            "lcd_fix": lcdfix, "lcd_fix_note": lcdfix_note,
            "wide_band": wideband, "wide_band_note": wideband_note,
            "lcd_holdout": hold}


CACHE.mkdir(exist_ok=True)


_OSIZE_MEMO = {}


def _oriented_size(p: Path):
    """EXIF 회전이 적용된 표시 크기(헤더만 읽음). cv2.imread와 달리 PIL은
    EXIF를 무시하므로 orientation 5~8은 가로세로를 바꿔준다.
    장당 수백 번 불리므로 (경로, mtime, 크기) 키로 메모이즈한다."""
    try:
        st = p.stat()
    except OSError:
        raise
    key = (str(p), st.st_mtime_ns, st.st_size)
    hit = _OSIZE_MEMO.get(key)
    if hit:
        return hit
    with Image.open(p) as pil:
        w, h = pil.size
        if pil.getexif().get(274) in (5, 6, 7, 8):
            w, h = h, w
    if len(_OSIZE_MEMO) > 8000:
        _OSIZE_MEMO.clear()
    _OSIZE_MEMO[key] = (w, h)
    return w, h


@route("/api/image")
def api_image(qs):
    cid = qs.get("id", [""])[0]
    w = int(qs.get("w", ["1600"])[0])
    # id 는 하위폴더 포함 경로명(glucose_batch1/1) — .. 만 차단
    if not cid or ".." in cid or cid.startswith("/"):
        return {"error": "bad id"}
    src = IMAGES / f"{cid}.jpg"
    if not src.exists():
        return {"error": "not found"}
    # 박스 좌표계는 EXIF 적용(표시) 이미지 기준 — 라벨러·검수·캐시 전부 동일 관례
    ow, oh = _oriented_size(src)
    cache = CACHE / f"{cid.replace('/', '__')}_{w}.jpg"
    # 디스크 캐시 자가치유: 예전 파이프라인(EXIF 무시 등)이 남긴 캐시는
    # 종횡비가 표시 크기와 어긋난다. 그 상태로 서빙하면 캔버스가 이미지를
    # 늘려 그려 라벨 좌표가 통째로 틀어지므로 발견 즉시 다시 만든다.
    if cache.exists():
        try:
            with Image.open(cache) as ci:
                cw, ch = ci.size
            if ch <= 0 or abs((cw / ch) - (ow / oh)) > 0.01 * (ow / oh):
                cache.unlink()
        except Exception:
            cache.unlink(missing_ok=True)
    if not cache.exists():
        try:
            with Image.open(src) as pil:
                pil.load()
                pil = ImageOps.exif_transpose(pil)
        except Exception as e:
            return {"error": f"decode fail: {e}"}
        if pil.width != ow or pil.height != oh:
            # exif_transpose 결과와 헤더 계산이 갈리면 좌표 정본이 무너진다.
            return {"error": f"orientation 불일치: transpose {pil.size} vs 헤더 {(ow, oh)}"}
        if pil.width > w:
            pil = pil.resize((w, int(round(pil.height * w / pil.width))),
                             Image.BILINEAR)
        pil.convert("RGB").save(str(cache), "JPEG", quality=88)
    return {"url": "/cache/" + cache.name, "ow": ow, "oh": oh,
            "frame": f"{cid}@{ow}x{oh}"}


# ===== 펼치기(원근 펴기) 검수 — 라벨 박스 안에서 유리 쿼드를 찾아 워프 =====

def _load_gray(cid):
    src = IMAGES / f"{cid}.jpg"
    if not src.exists():
        return None
    with Image.open(src) as pil:
        pil.load()
        pil = ImageOps.exif_transpose(pil)  # 라벨 좌표계(표시 이미지)와 정합
        return cv2.cvtColor(np.asarray(pil.convert("RGB")), cv2.COLOR_RGB2GRAY)


def _order_quad(q):
    """4점을 TL,TR,BR,BL 시계순서로 재정렬 — 중심각 정렬이라 강한 기울기에서도
    사각형이 꼬이지 않는다(min/max 방식은 45° 부근에서 순서가 뒤집혀 워프가 접힘)."""
    ctr = q.mean(axis=0)
    ang = np.arctan2(q[:, 1] - ctr[1], q[:, 0] - ctr[0])
    q = q[np.argsort(-ang)]
    s = q[:, 0] + q[:, 1]
    q = np.roll(q, -int(np.argmin(s)), axis=0)
    if q[1, 1] > q[3, 1]:
        q = q[[0, 3, 2, 1]]
    return q.astype(np.float32)


def _refine_corners(c, quad):
    """approx 쿼드의 각 모서리를 윤곽점 두 변의 직선 교점으로 정밀화.
    픽셀 스냅 오차数px가 긴 변에서 수도~십도 회전 오차로 커지는 것을 억제."""
    pts = c.reshape(-1, 2).astype(np.float32)
    out = quad.copy()
    edges = []
    for i in range(4):
        a, b = quad[i], quad[(i + 1) % 4]
        ab = b - a
        L = float(np.linalg.norm(ab))
        if L < 1e-3:
            edges.append(None)
            continue
        da = np.linalg.norm(pts - a, axis=1)
        db = np.linalg.norm(pts - b, axis=1)
        t = np.clip(((pts - a) @ ab) / (L * L), 0, 1)
        dist = np.linalg.norm(pts - (a + t[:, None] * ab), axis=1)
        m = (da > 0.12 * L) & (db > 0.12 * L) & (dist < 0.22 * L)
        edges.append(pts[m] if int(m.sum()) >= 8 else None)
    for i in range(4):
        e_prev, e_this = edges[(i - 1) % 4], edges[i]
        if e_prev is None or e_this is None:
            continue
        l1 = cv2.fitLine(e_prev, cv2.DIST_L2, 0, 0.01, 0.01).flatten()
        l2 = cv2.fitLine(e_this, cv2.DIST_L2, 0, 0.01, 0.01).flatten()
        v1 = np.array([l1[0], l1[1]], np.float32)
        p1 = np.array([l1[2], l1[3]], np.float32)
        v2 = np.array([l2[0], l2[1]], np.float32)
        p2 = np.array([l2[2], l2[3]], np.float32)
        A = np.array([v1, -v2]).T
        if abs(float(np.linalg.det(A))) < 1e-4:
            continue
        tt = np.linalg.solve(A, p1 - p2)
        inter = p1 + v1 * tt[0]
        if np.linalg.norm(inter - quad[i]) < 0.3 * float(
                np.linalg.norm(quad[(i + 1) % 4] - quad[(i - 1) % 4])):
            out[i] = inter
    return out


def _find_glass_quad(g, box):
    """박스 내부에서 LCD 유리 사각형 탐색 → 원본 좌표 TL,TR,BR,BL. 실패 시 None.
    반사광으로 마스크가 갈라지는 걸 대비해 close 커널을 단계별로 시험."""
    H, W = g.shape
    x0, y0, x1, y1 = box
    mx = int((x1 - x0) * 0.06) + 2
    my = int((y1 - y0) * 0.06) + 2
    cx0, cy0 = max(0, x0 - mx), max(0, y0 - my)
    cx1, cy1 = min(W, x1 + mx), min(H, y1 + my)
    if cx1 - cx0 < 24 or cy1 - cy0 < 24:
        return None
    crop = g[cy0:cy1, cx0:cx1]
    scale = 800.0 / max(crop.shape)
    es = min(1.0, scale)  # 실제 적용 배율(scale≥1이면 리사이즈 안 함)
    cs = (cv2.resize(crop, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
          if scale < 1.0 else crop)
    blur = cv2.GaussianBlur(cs, (5, 5), 0)
    _, mpos = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    area_s = float(cs.shape[0] * cs.shape[1])
    ch, cw = cs.shape
    best, best_score = None, 0.0
    for ksz in (9, 17, 29):  # 클수록 반사광 갈라짐을 메운다
        for m in (mpos, cv2.bitwise_not(mpos)):  # 양극성 모두 시험(반전형 화면)
            m2 = cv2.morphologyEx(m, cv2.MORPH_CLOSE,
                                  np.ones((ksz, ksz), np.uint8))
            n, lab, stats, _ = cv2.connectedComponentsWithStats(m2, 8)
            for k in range(1, n):
                x, y, w, h, a = stats[k]
                if a < area_s * 0.15 or a > area_s * 0.98:
                    continue
                ccx, ccy = x + w / 2.0, y + h / 2.0
                if not (cw * 0.15 < ccx < cw * 0.85 and ch * 0.15 < ccy < ch * 0.85):
                    continue
                fill = a / float(w * h)
                if fill < 0.55:
                    continue
                score = a * fill
                if score > best_score:
                    best_score = score
                    best = (lab == k).astype(np.uint8)
    if best is None:
        return None
    cnts, _ = cv2.findContours(best, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not cnts:
        return None
    c = max(cnts, key=cv2.contourArea)
    # box_area 도 작업스케일로 환산 — 원본 좌표계와 섞으면 정상 쿼드가 전부 기각됨
    box_area = float((x1 - x0) * (y1 - y0)) * es * es
    for eps in (0.02, 0.035, 0.05, 0.07):
        ap = cv2.approxPolyDP(c, eps * cv2.arcLength(c, True), True)
        if len(ap) != 4 or not cv2.isContourConvex(ap):
            continue
        qa = float(cv2.contourArea(ap))
        if qa < box_area * 0.35 or qa > box_area * 1.5:
            continue
        quad = ap.reshape(4, 2).astype(np.float32)
        quad = _refine_corners(c, quad)
        quad = quad / es
        quad[:, 0] += cx0
        quad[:, 1] += cy0
        return _order_quad(quad)
    return None


def _warp_quad(g, quad, max_side=640):
    tl, tr, br, bl = quad
    w = max(float(np.linalg.norm(tr - tl)), float(np.linalg.norm(br - bl)))
    h = max(float(np.linalg.norm(tr - br)), float(np.linalg.norm(tl - bl)))
    s = min(1.0, max_side / max(w, h, 1.0))
    Wc = max(32, int(round(w * s)))
    Hc = max(32, int(round(h * s)))
    M = cv2.getPerspectiveTransform(
        quad.astype(np.float32),
        np.array([[0, 0], [Wc - 1, 0], [Wc - 1, Hc - 1], [0, Hc - 1]],
                 dtype=np.float32))
    return cv2.warpPerspective(g, M, (Wc, Hc))


def _auto_upright(img):
    """펼친 rect를 0/90/180/270 중 가장 '바로 선' 방향으로 회전.
    판정 근거(7세그 관례): 숫자는 세로로 길고 한 행에 나란히 늘어서고,
    큰 숫자 줄은 작은 시간 줄보다 위에 있다. 0↔180·90↔270 중 형상만으로
    안 갈리는 건 큰-작은 줄 위치 선호로 대부분 결정, 나머지는 사람/판독기 몫."""
    best, best_k, best_score = img, 0, -1e9
    for k in (0, 90, 180, 270):
        r = img if k == 0 else np.rot90(img, k // 90).copy()
        s = 400.0 / max(r.shape)
        rs = (cv2.resize(r, None, fx=s, fy=s, interpolation=cv2.INTER_AREA)
              if s < 1.0 else r)
        _, mb = cv2.threshold(rs, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        if mb.mean() > 127:  # 잉크 = 면적 작은 쪽
            mb = cv2.bitwise_not(mb)
        n, lab, stats, cen = cv2.connectedComponentsWithStats(mb, 8)
        H, W = rs.shape
        tall, big_y, small_y = [], [], []
        for k2 in range(1, n):
            x, y, w, h, a = stats[k2]
            if a < H * W * 0.004 or h < H * 0.10:
                continue
            ar = h / max(w, 1.0)
            if 1.05 <= ar <= 4.5:
                tall.append(cen[k2])
                (big_y if a >= H * W * 0.015 else small_y).append(cen[k2][1])
        row_bonus = 0.0
        if len(tall) >= 2:
            yy = [p[1] for p in tall]
            xx = [p[0] for p in tall]
            row_bonus = (np.std(xx) - np.std(yy)) / max(H, 1)
        prior = 0
        if big_y and small_y:
            prior = 1 if (np.mean(big_y) < np.mean(small_y)) else -1
        score = len(tall) + 2.0 * row_bonus + 0.7 * prior
        if score > best_score:
            best, best_k, best_score = r, k, score
    return np.ascontiguousarray(best), best_k


@route("/api/rect")
def api_rect(qs):
    cid = qs.get("id", [""])[0]
    if ".." in cid or cid.startswith("/"):
        return {"error": "bad id"}
    mode = qs.get("mode", ["lcd"])[0]
    src_file = BAND_FILE if mode == "band" else LCD_FILE
    stored = read_jsonl(src_file).get(cid)
    chosen = stored.get("upright") if stored else None
    qparam = qs.get("q", [None])[0]
    if qparam:  # 저장 전 편집 중인 박스로 바로 검수
        v = [float(t) for t in qparam.split(",")]
        x0, y0, x1, y1 = v
    elif stored and stored.get("quad"):
        q = np.array(stored["quad"], dtype=np.float64)
        x0, y0 = float(q[:, 0].min()), float(q[:, 1].min())
        x1, y1 = float(q[:, 0].max()), float(q[:, 1].max())
    else:
        return {"error": "라벨 없는 장 — 박스를 그린 뒤 E(또는 Space로 저장)"}
    g = _load_gray(cid)
    if g is None:
        return {"error": "이미지 없음"}
    H, W = g.shape
    oob = x0 < 0 or y0 < 0 or x1 > W - 1 or y1 > H - 1
    bx0, by0 = int(max(0, x0)), int(max(0, y0))
    bx1, by1 = int(min(W - 1, x1)), int(min(H - 1, y1))
    if bx1 - bx0 < 16 or by1 - by0 < 16:
        return {"error": "박스가 이미지 밖 — 라벨 좌표 파손"}
    # 왼쪽: 현재 방식(박스 스트레치 2:1) / 오른쪽: 유리 쿼드 펼치기
    now = cv2.resize(g[by0:by1, bx0:bx1], (480, 240),
                     interpolation=cv2.INTER_AREA)
    quad = _find_glass_quad(g, (bx0, by0, bx1, by1))
    quad_ok = quad is not None
    auto_k = 0
    if quad_ok:
        unw = _warp_quad(g, quad, max_side=640)
        _, auto_k = _auto_upright(unw)
        # 상하 부호(0↔180·90↔270)는 형상만으론 기기마다 틀려 자동 단정 불가(실측)
        # → 검수용으로 4방향을 나란히 제시하고 사람이 고른다
        cells = []
        for kk in range(4):
            r = np.ascontiguousarray(unw if kk == 0 else np.rot90(unw, kk))
            sc = 230.0 / r.shape[0]
            cell = cv2.resize(r, (max(1, int(r.shape[1] * sc)), 230),
                              interpolation=cv2.INTER_AREA)
            cv2.putText(cell, f"{kk * 90}", (6, 26),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 255), 2,
                        cv2.LINE_AA)
            cells.append(cell)
        wl = max(cells[0].shape[1], cells[2].shape[1])
        wr = max(cells[1].shape[1], cells[3].shape[1])
        grid = np.full((466, wl + wr + 6, 3), 40, np.uint8)
        pos = []
        for idx, cell in enumerate(cells):
            rr, cc = divmod(idx, 2)
            x = 0 if cc == 0 else wl + 6
            y = rr * 236
            pos.append((x, y))
            grid[y:y + 230, x:x + cell.shape[1]] = \
                cv2.cvtColor(cell, cv2.COLOR_GRAY2BGR)
        if chosen is not None:
            ci = int(chosen) // 90
            cx, cy = pos[ci]
            cv2.rectangle(grid, (cx - 2, cy - 2),
                          (cx + cells[ci].shape[1] + 2, cy + 232),
                          (90, 255, 130), 5)
    else:
        unw = _warp_quad(g, np.array([[bx0, by0], [bx1, by0],
                                      [bx1, by1], [bx0, by1]], np.float32))
        grid = cv2.cvtColor(unw, cv2.COLOR_GRAY2BGR)

    # 좌측 상: 원본 박스 크롭(종횡비 유지) + 검출 쿼드 오버레이 — 신뢰 가능한 기준면
    src = g[by0:by1, bx0:bx1]
    sh, sw = src.shape
    sc = min(480.0 / sw, 240.0 / sh)
    sr = cv2.resize(src, (max(1, int(sw * sc)), max(1, int(sh * sc))),
                    interpolation=cv2.INTER_AREA)
    srcp = np.full((240, 480), 40, np.uint8)
    oxp, oyp = (480 - sr.shape[1]) // 2, (240 - sr.shape[0]) // 2
    srcp[oyp:oyp + sr.shape[0], oxp:oxp + sr.shape[1]] = sr
    srcp = cv2.cvtColor(srcp, cv2.COLOR_GRAY2BGR)
    if quad_ok:
        pts = (quad - np.array([bx0, by0], np.float32)) * sc
        pts = pts.astype(np.int32) + np.array([oxp, oyp], np.int32)
        cv2.polylines(srcp, [pts], True, (90, 255, 130), 2)
    if stored and stored.get("quad"):  # 저장 라벨 청색선 — 그린 박스와 즉시 비교
        sq = np.array(stored["quad"], np.float32)
        spts = ((sq - np.array([bx0, by0], np.float32)) * sc).astype(np.int32)
        spts += np.array([oxp, oyp], np.int32)
        cv2.polylines(srcp, [spts], True, (255, 170, 60), 2)
    cv2.putText(srcp, "SRC: label box (no warp) + quad", (6, 16),
                cv2.FONT_HERSHEY_SIMPLEX, 0.45, (90, 200, 255), 1, cv2.LINE_AA)
    # 좌측 하: 현재 방식(2:1 스트레치)
    nowp = cv2.cvtColor(now, cv2.COLOR_GRAY2BGR)
    cv2.putText(nowp, "NOW: stretch 2:1", (6, 16),
                cv2.FONT_HERSHEY_SIMPLEX, 0.45, (90, 200, 255), 1, cv2.LINE_AA)
    left = np.full((488, 480, 3), 22, np.uint8)
    left[0:240] = srcp
    left[248:488] = nowp
    tw = max(660, 480 + 12 + grid.shape[1])
    th = 30 + max(488, grid.shape[0])
    strip = np.full((th, tw, 3), 22, np.uint8)
    strip[30:30 + 488, 6:486] = left
    strip[30:30 + grid.shape[0], 492:492 + grid.shape[1]] = grid
    cap = "UNWARP 4-way (auto %ddeg)" % auto_k if quad_ok \
        else "QUAD FAIL -> box aspect"
    if chosen is not None:
        cap += "  chosen %ddeg" % chosen
    if oob:
        cap += "  + BOX OVERFLOW!"
    cv2.putText(strip, cap, (6, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5,
                (90, 200, 255), 1, cv2.LINE_AA)
    ok, buf = cv2.imencode(".jpg", strip, [cv2.IMWRITE_JPEG_QUALITY, 90])
    return {"img": "data:image/jpeg;base64," + base64.b64encode(buf).decode(),
            "quad_ok": quad_ok, "oob": oob, "upright_k": auto_k,
            "chosen": chosen,
            "quad": quad.tolist() if quad_ok else None}


def _verify_frame(cid, quad, body):
    """​저장 요청의 좌표계를 서버가 검증한다.

    라벨 좌표는 '표시(EXIF 적용) 이미지의 원본 픽셀'이 정본이다. 클라이언트가
    그때 실제로 그렸던 프레임 크기(ow/oh)를 함께 보내게 하고, 서버가 파일에서
    직접 재는 크기와 대조한다. 어긋나면 저장하지 않는다 — 브라우저에 난은 JS 가
    살아 있어도 파일은 오염되지 않는다(2026-09-02 사고: 프레임이 한 장
    밀려 이전 장 크기로 저장되어 3건이 파손됐다).

    반환: (에러문자열 또는 None, ow, oh)
    """
    src = IMAGES / f"{cid}.jpg"
    if not src.exists():
        return f"원본 이미지 없음: {cid}", 0, 0
    try:
        ow, oh = _oriented_size(src)
    except Exception as e:
        return f"크기 판독 실패: {e}", 0, 0
    cow, coh = body.get("ow"), body.get("oh")
    if not isinstance(cow, (int, float)) or not isinstance(coh, (int, float)):
        return ("좌표계 정보(ow/oh) 없이 저장 요청 — 낡은 탭이다. "
                "Ctrl+Shift+R 로 새로고침할 것", ow, oh)
    if abs(cow - ow) > FRAME_TOL or abs(coh - oh) > FRAME_TOL:
        return (f"좌표계 불일치 — 브라우저는 {cow:.0f}x{coh:.0f} 프레임으로 그렸는데 "
                f"{cid} 의 실제 표시 크기는 {ow}x{oh} 다. 저장 거부(이 상태로 "
                f"저장하면 박스가 {ow / max(cow, 1):.3f}배 어긋난다). "
                "Ctrl+Shift+R 후 다시 그릴 것", ow, oh)
    xs = [float(pt[0]) for pt in quad]
    ys = [float(pt[1]) for pt in quad]
    if min(xs) < -BOUNDS_TOL or min(ys) < -BOUNDS_TOL or \
       max(xs) > ow + BOUNDS_TOL or max(ys) > oh + BOUNDS_TOL:
        return (f"박스가 이미지 밖 — x {min(xs):.0f}~{max(xs):.0f}, "
                f"y {min(ys):.0f}~{max(ys):.0f} vs {ow}x{oh}", ow, oh)
    if max(xs) - min(xs) < 8 or max(ys) - min(ys) < 8:
        return "박스가 너무 작다(8px 미만) — 오조작으로 보고 거부", ow, oh
    return None, ow, oh


def _build_stamp():
    """webtool.html 의 지문. 브라우저가 난은 JS 를 돌리고 있는지 UI 가
    스스로 알아채게 하는 값 — '고쳤는데 왜 그대로냐'의 절반은 이것이었다."""
    try:
        st = HTML.stat()
        h = hashlib.sha1(HTML.read_bytes()).hexdigest()[:8]
        return {"sha": h, "mtime": int(st.st_mtime), "bytes": st.st_size}
    except OSError:
        return {"sha": "?", "mtime": 0, "bytes": 0}


@route("/api/build")
def api_build(qs):
    return _build_stamp()


@route("/api/selftest")
def api_selftest(qs):
    """좌표 파이프라인 전수 점검 — 저장된 라벨 전부를 원본 파일과 대조한다.
    라벨러에서 버튼 한 번으로 부르는 것이 목적이라 무거운 디코드는 하지 않고
    헤더만 읽는다."""
    report = {"build": _build_stamp(), "modes": {}}
    for mode, path in (("band", BAND_FILE), ("lcd", LCD_FILE)):
        rows = read_jsonl(path)
        checked = ok = skipped = legacy = 0
        problems = []
        for cid, r in rows.items():
            if not r.get("quad"):
                skipped += 1
                continue
            checked += 1
            src = IMAGES / f"{cid}.jpg"
            if not src.exists():
                problems.append({"id": cid, "why": "원본 없음"})
                continue
            ow, oh = _oriented_size(src)
            xs = [p[0] for p in r["quad"]]
            ys = [p[1] for p in r["quad"]]
            bad = []
            if min(xs) < -BOUNDS_TOL or min(ys) < -BOUNDS_TOL or \
               max(xs) > ow + BOUNDS_TOL or max(ys) > oh + BOUNDS_TOL:
                bad.append("경계 초과")
            rec = r.get("ow")
            if rec is None:
                # 구버전 저장분은 프레임 기록이 없어 "검증 불가"일 뿐 결함이 아니다.
                # 문제로 세면 매번 수백 건이 떠서 자가검증이 무의미해진다.
                legacy += 1
            elif abs(rec - ow) > FRAME_TOL or abs(r.get("oh", 0) - oh) > FRAME_TOL:
                bad.append(f"기록 프레임 {rec}x{r.get('oh')} != 실제 {ow}x{oh}")
            if bad:
                problems.append({"id": cid, "why": " / ".join(bad),
                                 "size": [ow, oh],
                                 "box": [round(min(xs)), round(min(ys)),
                                         round(max(xs)), round(max(ys))]})
            else:
                ok += 1
        report["modes"][mode] = {"rows": len(rows), "checked": checked,
                                 "skipped": skipped, "ok": ok,
                                 "legacy": legacy,
                                 "problems": problems[:50],
                                 "problem_count": len(problems)}
    cache_bad = []
    files = sorted(CACHE.glob("*.jpg"))
    for c in files:
        stem = c.stem
        if "_" not in stem:
            continue
        cid = stem.rsplit("_", 1)[0].replace("__", "/")
        src = IMAGES / f"{cid}.jpg"
        if not src.exists():
            continue
        try:
            ow, oh = _oriented_size(src)
            with Image.open(c) as ci:
                cw, ch = ci.size
        except Exception as e:
            cache_bad.append({"file": c.name, "why": str(e)})
            continue
        if abs((cw / ch) - (ow / oh)) > 0.01 * (ow / oh):
            cache_bad.append({"file": c.name, "cache": [cw, ch],
                              "oriented": [ow, oh]})
    report["cache_bad"] = cache_bad
    report["cache_files"] = len(files)
    return report


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass  # 요청 로그 조용히 (콘솔에 학습 로그만)

    def _send(self, code, body: bytes, ctype: str):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _json(self, obj, code=200):
        self._send(code, json.dumps(obj, ensure_ascii=False).encode("utf-8"),
                   "application/json; charset=utf-8")

    def do_GET(self):
        u = urlparse(self.path)
        qs = parse_qs(u.query)
        if u.path == "/" or u.path == "/index.html":
            if HTML.exists():
                self._send(200, HTML.read_bytes(), "text/html; charset=utf-8")
            else:
                self._send(404, "webtool.html 없음 — 서버 옆에 만들 것".encode(), "text/plain")
            return
        if u.path.startswith("/api/"):
            fn = ROUTES.get(u.path)
            if fn is None:
                self._json({"error": "unknown api"}, 404)
                return
            try:
                self._json(fn(qs))
            except Exception as e:
                self._json({"error": str(e)}, 500)
            return
        if u.path.startswith("/img/"):
            rel = u.path[len("/img/"):]
            p = (HERE / rel).resolve()
            try:
                p.relative_to(HERE.resolve())
            except ValueError:
                self._send(403, b"forbidden", "text/plain")
                return
            if p.exists():
                ctype = "image/png" if p.suffix == ".png" else "image/jpeg"
                self._send(200, p.read_bytes(), ctype)
            else:
                self._send(404, b"not found", "text/plain")
            return
        if u.path.startswith("/cache/"):
            p = CACHE / Path(u.path).name
            if p.exists():
                self._send(200, p.read_bytes(), "image/jpeg")
            else:
                self._send(404, b"", "image/jpeg")
            return
        self._send(404, b"not found", "text/plain")

    def _train_pid(self):
        pf = HERE / "train_pid.json"
        if not pf.exists():
            return None
        try:
            return json.loads(pf.read_text(encoding="utf-8")).get("pid")
        except Exception:
            return None

    def _pid_alive(self, pid):
        if not pid:
            return False
        out = subprocess.run(["tasklist", "/FI", f"PID eq {pid}"],
                             capture_output=True, text=True).stdout
        return str(pid) in out

    def do_POST(self):
        u = urlparse(self.path)
        ln = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(ln) or b"{}")
        if u.path == "/api/label":
            mode = body.get("mode", "band")
            p = BAND_FILE if mode == "band" else LCD_FILE
            rows = read_jsonl(p)
            cid = body.get("id", "")
            src = body.get("source", "human")
            if not cid or ".." in cid or cid.startswith("/"):
                self._json({"error": "bad id"}, 400)
                return
            if src == "skipped":
                rows[cid] = {"id": cid, "quad": None, "source": "skipped"}
            else:
                quad = body.get("quad")
                if not quad or len(quad) != 4:
                    self._json({"error": "bad quad"}, 400)
                    return
                err, ow, oh = _verify_frame(cid, quad, body)
                if err:
                    self._json({"error": err}, 409)
                    return
                row = {"id": cid, "quad": quad, "source": "human",
                       "ow": ow, "oh": oh}
                uk = body.get("upright_k")
                if uk in (0, 90, 180, 270):
                    row["upright"] = int(uk)
                prev = rows.get(cid) or {}
                if prev.get("upright") is not None and "upright" not in row:
                    row["upright"] = prev["upright"]
                rows[cid] = row
            write_jsonl(p, rows)
            self._json({"ok": True})
            return
        if u.path == "/api/gtfix":
            cid = body.get("id", "")
            if body.get("revert"):
                rows = {}
                if GT_FIX.exists():
                    for l in GT_FIX.read_text(encoding="utf-8").splitlines():
                        if l.strip():
                            j = json.loads(l)
                            rows[j["id"]] = j
                rec = rows.pop(cid, None)
                write_jsonl(GT_FIX, rows)
                readings = load_readings()
                self._json({"ok": True,
                            "gt": str(readings.get(cid, "")),
                            "removed": bool(rec)})
                return
            corrected = str(body.get("corrected", "")).strip()
            readings = load_readings()
            orig = readings.get(cid)
            if not cid or not corrected:
                self._json({"error": "bad body"}, 400)
                return
            rows = {}
            if GT_FIX.exists():
                for l in GT_FIX.read_text(encoding="utf-8").splitlines():
                    if l.strip():
                        j = json.loads(l)
                        rows[j["id"]] = j
            rows[cid] = {"id": cid, "original": orig, "corrected": corrected}
            write_jsonl(GT_FIX, rows)
            self._json({"ok": True})
            return
        if u.path == "/api/train/start":
            if self._pid_alive(self._train_pid()):
                self._json({"ok": False, "error": "이미 실행 중"})
                return
            if TRAIN_LOG.exists() and (time.time() - TRAIN_LOG.stat().st_mtime) < 120:
                self._json({"ok": False,
                            "error": "다른 학습이 방금까지 로그를 기록 중 — 잠시 후 시도"})
                return
            mode = body.get("mode", "fresh")
            if mode not in ("fresh", "resume", "ft"):
                self._json({"ok": False, "error": f"모르는 모드: {mode}"})
                return
            if mode == "resume" and not RESUME_STATE.exists():
                self._json({"ok": False,
                            "error": "이어서 돌릴 지점이 없다 — 처음부터 시작할 것"})
                return
            logf = open(TRAIN_LOG, "ab")  # 모니터가 같은 파일을 읽는다
            env = dict(os.environ, PYTHONUNBUFFERED="1")
            proc = subprocess.Popen(
                [sys.executable, str(HERE / "ctc_reader_v2.py"), mode],
                stdout=logf, stderr=subprocess.STDOUT,
                creationflags=DETACHED, env=env, cwd=str(HERE))
            (HERE / "train_pid.json").write_text(
                json.dumps({"pid": proc.pid}), encoding="utf-8")
            self._json({"ok": True, "pid": proc.pid, "mode": mode})
            return
        if u.path == "/api/train/stop":
            pid = self._train_pid()
            if pid and self._pid_alive(pid):
                subprocess.run(["taskkill", "/PID", str(pid), "/F"],
                               capture_output=True)
            self._json({"ok": True})
            return
        self._json({"error": "unknown api"}, 404)


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    port = 8777
    if argv:  # webtool.py 8778 — 돌아가는 인스턴스를 죽이지 않고 검증용으로 띄운다
        try:
            port = int(argv[0])
        except ValueError:
            print(f"포트 값이 이상하다: {argv[0]}")
            return 2
    srv = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    print(f"webtool: http://127.0.0.1:{port}/  (Ctrl+C 중지)")
    srv.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
