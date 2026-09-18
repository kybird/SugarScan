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
SYNTH_HTML = HERE / "synth_view.html"   # 합성 코퍼스 열람 — 읽기 전용
PROFEDIT_HTML = HERE / "prof_edit.html"  # 프로파일 에디터 — 덮어쓰기만 쓴다
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
# 밴드 예측 오버레이. 재구축 뒤 새 검출기 산물을 먼저 쓰고, 없으면 옛 v2 파일로
# 떨어진다(그 파일은 재구축 때 사라졌다 — 그래서 오버레이가 빈 채로 돌고 있었다).
# predict_band_quads.py 가 만든다. **예측**이지 라벨이 아니다 — 행마다 source·ckpt.
_BAND_PRED = HERE / "band_quads_pred.jsonl"
BAND_QUADS = _BAND_PRED if _BAND_PRED.exists() else HERE / "datumo_quads_v2.jsonl"
# 라벨러 힌트 전용(점선 제안). 표시(EXIF 적용) 좌표계 — convert_quads_oriented.py
# 의 정정문 참조. **캐시 정본인 gmscreen_quads.jsonl 과 별개다** — 이 파일을
# 바꿔도 data_cache_v2.npz 는 영향받지 않는다(build_cache_v2.py:146 은 정본을 읽는다).
# 2026-09-12: ft3 가 정본으로 승격돼 별도 힌트 파일이 필요 없어졌다.
# gmscreen_quads.jsonl(정본) -> convert_quads_oriented.py -> 이 파일. 한 갈래다.
GM_QUADS = HERE / "gmscreen_quads_oriented.jsonl"
# 폐기된 CTC 리더의 흔적 — 더 이상 어느 화면도 읽지 않는다(2026-09-15).
# reader_preds.json 만 남긴다: 라벨러 큐가 '판독 실패' 필터에 쓴다.
HOLDOUT = HERE / "reader_preds.json"
HTML = HERE / "webtool.html"
DEVICES_HTML = HERE / "devices.html"
DEVICE_TAGS = HERE / "device_tags.jsonl"
# 사진 단위 라벨 — 라벨의 정본. 성분(dhash 연결요소)은 오염될 수 있어서
# "성분 하나에 기기 하나"로는 정답을 적을 수 없는 경우가 실제로 있다.
# device_tags.jsonl 은 여기서 파생되는 성분 요약으로 남는다.
DEVICE_LABELS = HERE / "device_labels.jsonl"
DETACHED = 0x00000008 | 0x00000200  # DETACHED_PROCESS | NEW_PROCESS_GROUP

# ── 밴드 쿼드 검출기 — 지금 실제로 돌리는 학습 (2026-09-15) ────────────────
# 모니터·훈련 탭은 CTC 리더(ctc_train_gpu.log · reader_preds.json)를 가리키고
# 있었다. 그 파이프라인은 2026-09-11 에 폐기됐는데 화면은 8월 31일에 죽은
# 프로세스의 마지막 줄을 "파인튜닝 · 에폭 30" 으로 계속 보여 줬다 — 살아
# 있는 것처럼 읽히고, 표의 성적은 **새 수치와 나란히 놓으면 안 되는 옛 값**
# 이다(CLAUDE.md). 그래서 두 탭이 읽는 곳을 검출기로 옮긴다.
DET_LOG = HERE / "band_det_train.log"       # 훈련 탭 버튼이 쓰는 로그
DET_PID = HERE / "band_det_pid.json"
# 학습은 이 화면 밖에서도 돈다 — band_det_sweep.py 로 터미널에서 띄우면
# 출력이 스윕 로그로 간다. 구판은 DET_LOG 하나만 봐서 "loss 데이터 없음" 을
# 띄웠다(2026-09-16). 화면이 거짓말한 게 아니라 엉뚱한 파일을 본 것이다.
# **가장 최근에 쓰인 로그**를 따라간다.
DET_LOGS = (HERE / "band_det_train.log", HERE / "band_det_sweep.log")
# 오버레이 — 기종 탭이 그리는 예측. predict_band_quads.py 가 채운다.
OVL_LOG = HERE / "band_quads_overlay.log"
OVL_PID = HERE / "band_quads_overlay.pid"
DIAG = HERE / "_diag"


def _det_log():
    live = [p for p in DET_LOGS if p.exists()]
    return max(live, key=lambda p: p.stat().st_mtime) if live else DET_LOG

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


def load_device_tags():
    """device_tags.jsonl — 행 순서가 곧 성분 정렬이므로 list 로 보존한다."""
    rows = []
    if DEVICE_TAGS.exists():
        for l in DEVICE_TAGS.read_text(encoding="utf-8").splitlines():
            if l.strip():
                rows.append(json.loads(l))
    return rows


def save_device_tags(rows):
    tmp = DEVICE_TAGS.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        for j in rows:
            f.write(json.dumps(j, ensure_ascii=False) + "\n")
    tmp.replace(DEVICE_TAGS)


def load_device_labels():
    """사진 id → {brand, model, status}. 없으면 빈 dict."""
    out = {}
    if DEVICE_LABELS.exists():
        for l in DEVICE_LABELS.read_text(encoding="utf-8").splitlines():
            if l.strip():
                j = json.loads(l)
                out[j["id"]] = j
    return out


def backup_device_labels():
    """덮어쓰기 전에 직전 상태를 남긴다.

    사람이 몇 시간 들여 붙인 라벨을 한 번의 잘못된 선택이 통째로 덮을 수 있다
    (실제로 782장이 그렇게 날아갔다). 파일은 작고(수백 KB) 백업은 싸다.
    """
    if not DEVICE_LABELS.exists():
        return
    d = HERE / "_diag" / "device_tags" / "backups"
    d.mkdir(parents=True, exist_ok=True)
    dst = d / ("device_labels_" + time.strftime("%Y%m%d_%H%M%S") + ".jsonl")
    if not dst.exists():
        dst.write_bytes(DEVICE_LABELS.read_bytes())
    keep = sorted(d.glob("device_labels_*.jsonl"))[:-200]
    for old_file in keep:
        old_file.unlink()


def save_device_labels(labels):
    backup_device_labels()
    tmp = DEVICE_LABELS.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        for _id in sorted(labels):
            f.write(json.dumps(labels[_id], ensure_ascii=False) + "\n")
    tmp.replace(DEVICE_LABELS)


def scene_members():
    mp = HERE / "_diag" / "scene_components.json"
    return json.loads(mp.read_text(encoding="utf-8")) if mp.exists() else {}


def resummarize_components(labels):
    """사진 라벨에서 성분 요약을 다시 만든다 — 정본은 언제나 사진 쪽이다.

    한 성분의 사진이 전부 라벨되고 기기가 하나면 identified, 기기가 둘 이상이면
    mixed(성분이 오염됐다는 사실 자체가 결과다), 아직 남았으면 checked=False.
    """
    members = scene_members()
    rows = load_device_tags()
    for r in rows:
        ids = members.get(r["component"], [r["rep"]])
        got = [labels[i] for i in ids if i in labels]
        r["labeled"] = len(got)
        # G34 에이전트가 남긴 원래 추정을 한 번 보관해 둔다. 사람 라벨을 전부
        # 지웠을 때 돌아갈 자리가 없으면 그 추정이 영영 사라진다.
        if "agent_brand" not in r:
            r["agent_brand"] = r.get("brand", "")
            r["agent_model"] = r.get("model", "")
        if not got:
            r["brand"] = r.get("agent_brand", "")
            r["model"] = r.get("agent_model", "")
            r["status"] = ""
            r["checked"] = False
            r["by"] = "agent"
            r["confidence"] = "high" if r["brand"] else "low"
            continue
        devices = {(g.get("brand", ""), g.get("model", ""), g.get("variant", ""))
                   for g in got if g.get("status") == "identified"}
        unknown = any(g.get("status") == "unknown" for g in got)
        r["by"] = "human"
        r["checked"] = len(got) == len(ids)
        if len(devices) > 1:
            r["status"] = "mixed"
            r["brand"] = r["model"] = ""
        elif len(devices) == 1:
            r["status"] = "identified"
            (r["brand"], r["model"], r["variant"]) = list(devices)[0]
        else:
            r["status"] = "unknown" if unknown else ""
            r["brand"] = r["model"] = ""
        r["confidence"] = "high" if r["checked"] else "low"
    save_device_tags(rows)
    return rows


def label_vocab(labels):
    """이미 쓴 (브랜드, 모델) — 사진 수 기준 사용량 순."""
    tally = {}
    for j in labels.values():
        if j.get("status") != "identified":
            continue
        key = (j.get("brand", "").strip(), j.get("model", "").strip(),
               j.get("variant", "").strip())
        if not key[0] and not key[1]:
            continue
        agg = tally.setdefault(key, {"brand": key[0], "model": key[1],
                                     "variant": key[2], "images": 0})
        agg["images"] += 1
    return sorted(tally.values(), key=lambda a: -a["images"])


def device_vocab(rows):
    """이미 쓴 (브랜드, 모델) 목록 — 사용 빈도 순.

    자유 입력만 두면 같은 기기가 CareSens II / Caresens 2 / 케어센스 II 로
    갈려 없는 기종이 생기고, 기기 단절 평가(LODO)가 조용히 무효가 된다.
    그래서 화면의 기본 경로는 '이미 쓴 이름 고르기'이고, 이 목록이 그 원천이다.
    """
    tally = {}
    for r in rows:
        # 사람 라벨이 성분 요약을 덮어쓴 뒤에도 에이전트 추정이 팔레트에서
        # 사라지지 않도록, 보관해 둔 agent_* 를 우선 본다.
        b = (r.get("agent_brand") if "agent_brand" in r else r.get("brand", "")) or ""
        m = (r.get("agent_model") if "agent_brand" in r else r.get("model", "")) or ""
        if not b and not m:
            continue
        key = (b.strip(), m.strip())
        agg = tally.setdefault(key, {"brand": key[0], "model": key[1],
                                     "components": 0, "images": 0})
        agg["components"] += 1
        agg["images"] += int(r.get("size", 0))
    return sorted(tally.values(), key=lambda a: -a["images"])


def palette_vocab(rows, labels):
    """팔레트 = 사진 라벨 사용량 순 + G34 에이전트가 이미 알아낸 기기(0장).

    에이전트 추정을 남기지 않으면, 사람이 첫 라벨을 찍는 순간 팔레트가 그 하나로
    줄어든다. 예측이 지워진 것처럼 보일 뿐 아니라 같은 기기를 매번 다시
    타이핑하게 되어 표기가 갈린다 — 없는 기종이 생기는 바로 그 경로다.
    """
    vocab = label_vocab(labels)
    have = {(v["brand"], v["model"], v.get("variant", "")) for v in vocab}
    for v in device_vocab(rows):
        if (v["brand"], v["model"], "") not in have:
            vocab.append({"brand": v["brand"], "model": v["model"],
                          "variant": "", "images": 0})
    return vocab


@route("/api/devicetags")
def api_devicetags(qs):
    rows = load_device_tags()
    summary = {}
    sp = HERE / "_diag" / "device_tags" / "summary.json"
    if sp.exists():
        summary = json.loads(sp.read_text(encoding="utf-8"))
    # 성분 구성원 — 대표 1장으로는 성분이 순수한지 알 수 없다. 723장짜리
    # 성분도 넘겨 볼 수 있게 전부 넘긴다(2,494개 문자열, 수십 KB).
    members = {}
    mp = HERE / "_diag" / "scene_components.json"
    if mp.exists():
        members = json.loads(mp.read_text(encoding="utf-8"))
    # 같은 기기 후보는 '제안'으로만 쓴다. 임계 9 에서도 11% 가 다른 기기를
    # 섞었다(docs/reports/premerge-device-components.md) — 절대 자동 적용하지 않는다.
    near = {}
    for pair in summary.get("near_pairs", []):
        if pair.get("dist", 99) <= 11:
            near.setdefault(pair["a"], []).append([pair["b"], pair["dist"]])
            near.setdefault(pair["b"], []).append([pair["a"], pair["dist"]])
    for k in near:
        near[k].sort(key=lambda x: x[1])
    labels = load_device_labels()
    vocab = palette_vocab(rows, labels)
    return {"rows": rows,
            "members": members,
            "labels": labels,
            "vocab": vocab,
            "near": near,
            "review_priority": summary.get("review_priority", {})}


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


def _det_pid():
    if not DET_PID.exists():
        return None
    try:
        return json.loads(DET_PID.read_text(encoding="utf-8")).get("pid")
    except Exception:
        return None


def pid_alive(pid):
    if not pid:
        return False
    out = subprocess.run(["tasklist", "/FI", f"PID eq {pid}"],
                         capture_output=True, text=True).stdout
    return str(pid) in out


def parse_det_log(path=None):
    """검출기 학습 로그 -> (에폭별 loss, 머리말, 저장한 체크포인트).

    로그 한 줄의 모양은 train_band_detector.py 가 정한다:
      `epoch  12  train 0.00042  sanity-val 0.00051`
    **이 정규식이 그 형식에 매여 있다** — 학습 스크립트의 print 를 바꾸면
    여기가 조용히 빈 그래프를 그린다.
    """
    rows, head, saved = [], "", []
    path = path or _det_log()
    if not path.exists():
        return rows, head, saved
    raw = path.read_text(encoding="utf-8", errors="ignore")
    # 스윕 로그에는 학습이 여러 번 들어 있다. **마지막 한 번만** 본다 —
    # 전부 모으면 에폭이 누적돼 그래프가 부풀고, 어느 줄이 지금 도는
    # 학습인지 화면에서 가를 수 없다.
    _cut = raw.rfind("train_band_detector.py")
    if _cut > 0:
        raw = raw[_cut:]
    raw = re.sub("\x1b" + r"\[[0-9;]*m", "", raw)
    for m in re.finditer(
            r"epoch\s+(\d+)\s+train\s+([0-9.eE+-]+)\s+sanity-val\s+([0-9.eE+-]+)",
            raw):
        rows.append({"epoch": int(m.group(1)),
                     "train": float(m.group(2)),
                     "val": float(m.group(3))})
    for m in re.finditer(r"saved (\S+)", raw):
        saved.append(m.group(1))
    for ln in raw.splitlines():
        if ln.startswith("train ") and "sanity-val" in ln or ln.startswith("arch="):
            head = (head + " · " if head else "") + ln.strip()
    return rows, head, saved


def _det_run_meta():
    """지금(또는 마지막) 실행이 무엇이었는지 — 코퍼스·에폭·출력 이름."""
    if not DET_PID.exists():
        return {}
    try:
        d = json.loads(DET_PID.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return {k: d.get(k) for k in ("data", "epochs", "out", "arch", "started")}


@route("/api/det/status")
def api_det_status(qs):
    log = _det_log()
    pid = _det_pid()
    alive = pid_alive(pid)
    fresh = log.exists() and (time.time() - log.stat().st_mtime) < 180
    rows, head, saved = parse_det_log(log)
    run = _det_run_meta()
    if not run and rows:
        # 이 화면 밖에서 돈 학습 — 명령줄이 로그에 찍혀 있으므로 거기서 읽는다.
        raw = log.read_text(encoding="utf-8", errors="ignore")
        cut = raw.rfind("train_band_detector.py")
        if cut > 0:
            line = raw[cut:].splitlines()[0]
            tok = line.split()
            for k, key in (("--data", "data"), ("--epochs", "epochs"),
                           ("--out", "out"), ("--limit", "limit")):
                if k in tok:
                    run[key] = tok[tok.index(k) + 1]
            run["epochs"] = int(run.get("epochs") or 0) or None
            run["external"] = log.name
    return {"pid": pid, "alive": alive, "log_fresh": fresh,
            "rows": rows[-400:], "epoch": rows[-1]["epoch"] if rows else 0,
            "head": head, "saved": saved[-6:], "run": run,
            "log": log.name,
            "log_mtime": (log.stat().st_mtime if log.exists() else 0)}


@route("/api/det/logtail")
def api_det_logtail(qs):
    n = int(qs.get("lines", ["60"])[0])
    log = _det_log()
    if not log.exists():
        return {"text": "(로그 없음 — 아직 검출기를 돌린 적이 없다)"}
    lines = log.read_text(encoding="utf-8", errors="ignore").splitlines()
    return {"text": chr(10).join(lines[-n:])}


@route("/api/det/corpora")
def api_det_corpora(qs):
    """학습에 쓸 수 있는 합성 코퍼스 — manifest 줄 수가 곧 장 수다."""
    out = []
    for d in sorted(HERE.glob("synth*")):
        mf = d / "manifest.jsonl"
        if not (d.is_dir() and mf.exists()):
            continue
        n = sum(1 for _ in mf.open(encoding="utf-8", errors="ignore"))
        out.append({"name": d.name, "n": n,
                    "mtime": mf.stat().st_mtime})
    out.sort(key=lambda r: -r["mtime"])
    return {"corpora": out}


def _overlay_ckpt():
    """지금 오버레이가 어느 체크포인트 것인가 — 행마다 박혀 있다."""
    if not _BAND_PRED.exists():
        return None
    try:
        with _BAND_PRED.open(encoding="utf-8") as f:
            for ln in f:
                if ln.strip():
                    return json.loads(ln).get("ckpt")
    except Exception:                                # noqa: BLE001
        return None
    return None


@route("/api/det/overlay")
def api_det_overlay(qs):
    """오버레이 상태 — 어느 체크포인트인지, 지금 다시 뽑는 중인지."""
    pid = None
    if OVL_PID.exists():
        try:
            pid = int(OVL_PID.read_text(encoding="utf-8").strip())
        except (ValueError, OSError):
            pid = None
    # **진행 줄만** 고른다. 로그 마지막 줄을 그대로 쓰면 하필 경고문의 꼬리가
    # 걸려 "오류난 것 같다"로 읽힌다(사람 보고 2026-09-16: tail 이
    # "warnings.warn(" 이었다). 진행은 predict_band_quads.py 가 내는
    # "  250/2511  27s" 모양이다.
    tail = ""
    if OVL_LOG.exists():
        for ln in OVL_LOG.read_text(encoding="utf-8",
                                    errors="ignore").splitlines():
            t = ln.strip()
            if re.match(r"^\d+/\d+\s", t) or "기록 ·" in t:
                tail = t
    return {"ckpt": _overlay_ckpt(), "running": pid_alive(pid), "pid": pid,
            "tail": tail,
            "n": (sum(1 for _ in _BAND_PRED.open(encoding="utf-8"))
                  if _BAND_PRED.exists() else 0)}


@route("/api/det/ckpts")
def api_det_ckpts(qs):
    """체크포인트 — 게이트를 돌린 적이 있으면 그 결과도 함께."""
    out = []
    for f in sorted(HERE.glob("band_det*.pt")):
        g = DIAG / f.stem / "gate_results.jsonl"
        out.append({"name": f.name, "stem": f.stem,
                    "overlay": (f.name == _overlay_ckpt()),
                    "mtime": f.stat().st_mtime,
                    "mb": round(f.stat().st_size / 1e6, 1),
                    "gated": g.exists()})
    out.sort(key=lambda r: -r["mtime"])
    return {"ckpts": out}


def _gate_summary(path):
    """게이트 결과 한 판 요약. **여기서 새 수치를 만들지 않는다** — 파일에
    적힌 장별 값을 그대로 모아 분위수만 낸다. 자는 eval_band_detector.py 다.

    1순위는 포함률(사람 라벨을 다 담았는가), 2순위는 넓이비. IoU 는 옛 판과
    잇대어 보라고 남긴 참고값이라 **합격을 정하지 않는다** — 기울어진 예측을
    축정렬 라벨과 견주는 자라 천장이 있고, 합성 기울기를 넓히면 검출이 좋아져도
    내려간다. [[proxy-metric-moves-against-the-goal]]
    """
    CONTAIN_PASS = 0.999
    rows = []
    with path.open(encoding="utf-8") as f:
        for ln in f:
            ln = ln.strip()
            if ln:
                rows.append(json.loads(ln))
    if not rows:
        return None
    det = np.array([r.get("iou_det", 0.0) for r in rows], float)
    has_con = any("contain" in r for r in rows)
    out = {
        "n": len(rows),
        "iou_p50": round(float(np.median(det)), 3),
        "iou_p10": round(float(np.percentile(det, 10)), 3),
        "legacy": not has_con,
    }
    if has_con:
        con = np.array([r.get("contain", 0.0) for r in rows], float)
        ar = np.array([r.get("area", 0.0) for r in rows], float)
        ok = con >= CONTAIN_PASS
        out.update({
            "pass": int(ok.sum()),
            "pass_pct": round(100.0 * ok.mean(), 1),
            "con_p50": round(float(np.median(con)), 4),
            "con_p10": round(float(np.percentile(con, 10)), 4),
            "con_min": round(float(con.min()), 4),
            "area_p50": round(float(np.median(ar)), 2),
            "area_p90": round(float(np.percentile(ar, 90)), 2),
        })
        edges = {}
        for side in ("top", "bottom", "left", "right"):
            v = np.array([(r.get("edges") or {}).get(side, 0.0) for r in rows],
                         float)
            edges[side] = {"cut": int((v > 0).sum()),
                           "max": round(float(v.max()), 3)}
        out["edges"] = edges
        key = "contain"
    else:
        key = "iou_det"
    per = {}
    for r in rows:
        per.setdefault(r.get("device") or "(미식별)", []).append(r.get(key, 0.0))
    devs = [{"device": k, "n": len(v), "median": round(float(np.median(v)), 3)}
            for k, v in per.items() if len(v) >= 3]
    devs.sort(key=lambda d: d["median"])
    out["devices"] = devs[:8]
    out["worst"] = [r["id"] for r in sorted(rows, key=lambda r: r.get(key, 0.0))[:8]]
    return out


@route("/api/det/gate")
def api_det_gate(qs):
    """게이트 결과들. tag 를 주면 그 한 판만, 없으면 있는 것 전부 요약."""
    tag = qs.get("tag", [""])[0]
    runs = []
    # 폴더 이름으로 고르지 않는다 — `--tag` 를 주면 이름이 뭐든 될 수 있다
    # (contain_r2_40k 가 band_det* 글롭에 안 걸려 표가 비었다, 2026-09-15).
    # **게이트 결과 파일이 있는 폴더**가 곧 한 판이다.
    for d in sorted(p for p in DIAG.iterdir() if p.is_dir()):
        g = d / "gate_results.jsonl"
        if not g.exists():
            continue
        if tag and d.name != tag:
            continue
        try:
            sm = _gate_summary(g)
        except Exception as e:                       # noqa: BLE001
            sm = {"error": f"{type(e).__name__}: {e}"}
        if sm:
            sm["tag"] = d.name
            sm["mtime"] = g.stat().st_mtime
            sm["sheet"] = (d / "gate_worst.png").exists()
            runs.append(sm)
    runs.sort(key=lambda r: -r.get("mtime", 0))
    return {"runs": runs}


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
    # 라벨 감사 — make_label_audit_queue.py. 라벨 안 빈 여백이 큰 순서다.
    audit, audit_note = _queue("label_audit_queue.json")
    # 밴드 씨앗 — band_queue.py build. 기기별로 번갈아 뽑은 순서다(2026-09-12).
    # 기존 밴드 라벨 97장이 세 기기에 몰려 있어(OneTouch UltraMini 30 ·
    # CareSens N 19 · 이름모를 가로형 14) 54종 중 39종이 0장이었다. 이 큐는
    # 0장 기기부터 한 장씩 돈다 — 중간에 멈춰도 기기 다양성이 유지된다.
    seed, seed_note = _queue("band_seed_queue.json")
    # 빈자리 누락 수정 — make_band_slot_queue.py. 2자리 값인데 상자가 두 자리만
    # 감싼 장이다(2026-09-14). 규약은 빈 앞자리까지 넣는 것이고 합성기도 그렇게
    # 그린다 — 그 15장에서 검출기는 맞게 내고도 IoU 0.6 에 갇힌다.
    slotfix, slotfix_note = _queue("band_slot_fix_queue.json")
    # 밴드 라벨 전수 검토 — 같은 스크립트. 자릿수별 중앙에서 벗어난 순이라
    # 중간에 멈춰도 이상한 것은 이미 다 본 상태가 된다.
    review, review_note = _queue("band_review_queue.json")
    # 가로형 밴드 전수 검토 — make_wide_review_queue.py. 그 기기 자신의 중앙값
    # 에서 벗어난 순이다(기기마다 밴드 폭이 다르므로 전체 분포로 재면 정상
    # 기기가 통째로 걸린다). 2026-09-15 밤샘: 세로형은 0.780->0.859 로 올랐는데
    # 가로형만 0.69 에서 안 움직였다 — 라벨을 의심할 차례다.
    wide2, wide2_note = _queue("band_wide_queue.json")
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
            "label_audit": audit, "label_audit_note": audit_note,
            "band_seed": seed, "band_seed_note": seed_note,
            "band_slot_fix": slotfix, "band_slot_fix_note": slotfix_note,
            "band_review": review, "band_review_note": review_note,
            "band_wide": wide2, "band_wide_note": wide2_note,
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


# ===== 합성 코퍼스 열람 (읽기 전용) =====
# 합성에는 사람 라벨이 없다 — 생성기가 밴드 쿼드를 알고 manifest 에 적는다.
# 여기서 보는 것은 '모델이 무엇을 정답으로 보고 배우는가' 그 자체다.
# 라벨링 경로(/api/labels, /api/rect)와 완전히 분리해 둔다: 합성에 사람이
# 손대는 순간 정답의 출처가 둘이 되고, 그러면 무엇으로 배웠는지 알 수 없게 된다.

def _synth_dirs():
    """합성 코퍼스 폴더 — 한 단계 아래까지 본다.

    구판은 `synth_*` 바로 아래만 봤다. 그런데 세트로 나눠 굽는 코퍼스는
    `synth_coco/A` 처럼 한 겹 더 들어간다(2026-09-17 마일스톤). 그러면
    사람이 웹툴에서 그 세트를 아예 못 본다 — 판정을 요구하면서 볼 화면을
    안 준 셈이 된다.
    """
    out = []
    for pat in ("synth_*", "gmscreen*"):
        for d in sorted(HERE.glob(pat)):
            if not d.is_dir():
                continue
            if _corpus_kind(d):
                out.append(d.name)
            for sub in sorted(d.iterdir()):
                if sub.is_dir() and _corpus_kind(sub):
                    out.append(f"{d.name}/{sub.name}")
    return out


def _corpus_kind(d):
    """이 폴더를 열람할 수 있나 — manifest(합성)냐 COCO(실촬)냐.

    합성 코퍼스만 보던 구판은 Roboflow 같은 COCO 데이터셋을 못 띄웠다.
    사람이 "실제 라벨이 어떻게 돼 있는지 보고 싶다"고 했을 때 폴더를 열어
    .jpg 만 보이면 라벨이 없는 것처럼 보인다 — COCO 는 라벨을 annotations/
    한 파일에 몰아 두기 때문이다. 그 오해를 화면에서 푼다.
    """
    if (d / "manifest.jsonl").exists():
        return "manifest"
    if (d / "annotations").is_dir() and any(
            (d / "annotations").glob("instances_*.json")):
        return "coco"
    return None


def _coco_rows(d):
    """COCO 데이터셋을 합성 열람과 같은 행 모양으로 바꾼다.

    상자(bbox)를 네 점 쿼드로 펴서 같은 그리기 코드가 그대로 돌게 한다.
    숫자 라벨은 COCO 에 없으므로 클래스 이름을 대신 보여 준다.
    """
    rows = []
    for ann_f in sorted((d / "annotations").glob("instances_*.json")):
        split = ann_f.stem.replace("instances_", "")
        j = json.loads(ann_f.read_text(encoding="utf-8"))
        cats = {c["id"]: c["name"] for c in j.get("categories", [])}
        by_img = {}
        for a in j.get("annotations", []):
            by_img.setdefault(a["image_id"], []).append(a)
        for im in j.get("images", []):
            anns = by_img.get(im["id"], [])
            if not anns:
                continue
            a = anns[0]
            x, y, w, h = a["bbox"]
            rows.append({
                "id": Path(im["file_name"]).stem,
                "file": im["file_name"], "split": split,
                "profile": f"{d.name}/{split}",
                "label": cats.get(a["category_id"], "?"),
                "w": im["width"], "h": im["height"],
                "quad": [[x, y], [x + w, y], [x + w, y + h], [x, y + h]],
                "rects": [[x, y, x + w, y + h, cats.get(a["category_id"], "?")]],
                "inverted": False, "dropped": [],
                "n_boxes": len(anns),
            })
    return rows


_SYNTH_CACHE = {}


def _synth_rows(name):
    """manifest 를 캐시하되 **파일이 바뀌면 버린다**.

    이름만으로 캐시하던 구판은 같은 이름으로 다시 구우면 옛 쿼드를 계속
    내줬다. 이미지는 디스크에서 새로 읽으니 화면에는 새 그림 위에 옛 상자가
    그려졌다 — 고친 것이 안 보이는 정도가 아니라 **없는 결함이 보인다**
    (사람 확인 2026-09-15). mtime+크기로 무효화한다.
    """
    # 한 겹 아래까지 허용한다. `..` 와 절대경로는 여전히 막는다.
    if ".." in name or name.startswith("/") or name.count("/") > 1:
        return []
    d = HERE / name
    kind = _corpus_kind(d)
    if kind == "coco":
        st = max((f.stat().st_mtime_ns, f.stat().st_size)
                 for f in (d / "annotations").glob("instances_*.json"))
        hit = _SYNTH_CACHE.get(name)
        if hit and hit[0] == st:
            return hit[1]
        rows = _coco_rows(d)
        _SYNTH_CACHE[name] = (st, rows)
        return rows
    m = d / "manifest.jsonl"
    if not m.exists():
        return []
    pred = _synth_pred_file(name)
    st = m.stat()
    key = (st.st_mtime_ns, st.st_size,
           (pred.stat().st_mtime_ns, pred.stat().st_size) if pred else None)
    hit = _SYNTH_CACHE.get(name)
    if hit and hit[0] == key:
        return hit[1]
    rows = [json.loads(l) for l in
            m.read_text(encoding="utf-8").splitlines() if l.strip()]
    if pred:
        # 검출기 예측을 같은 행에 얹는다. 없는 장은 pred 가 None 으로 남아
        # 화면에서 "상자 없음"으로 보인다 — 그게 판정에 필요한 정보다.
        by = {}
        for l in pred.read_text(encoding="utf-8").splitlines():
            if l.strip():
                j = json.loads(l)
                by[j["file_name"]] = j
        for r in rows:
            j = by.get(f"{r['id']}.png")
            if j:
                r["pred"] = j.get("pred")
                r["pred_score"] = j.get("score")
                r["pred_iou"] = j.get("iou")
    _SYNTH_CACHE[name] = (key, rows)
    return rows


def _synth_pred_file(name):
    """세트에 붙은 검출기 예측 파일 — 있으면 쓰고 없으면 그만.

    규약: _diag/synthband_v0/<세트이름>.jsonl (infer_synthband.py 의 산출).
    예: synth_coco/B -> _diag/synthband_v0/B.jsonl
    """
    leaf = name.split("/")[-1]
    p = HERE / "_diag" / "synthband_v0" / f"{leaf}.jsonl"
    return p if p.exists() else None


@route("/api/synth/corpora")
def api_synth_corpora(qs):
    out = []
    for n in _synth_dirs():
        rows = _synth_rows(n)
        profs = sorted({r.get("profile", "?") for r in rows})
        out.append({"name": n, "count": len(rows), "profiles": profs})
    return {"corpora": out}


@route("/api/synth/list")
def api_synth_list(qs):
    name = qs.get("dir", [""])[0]
    prof = qs.get("profile", [""])[0]
    off = int(qs.get("offset", ["0"])[0])
    lim = min(400, int(qs.get("limit", ["60"])[0]))
    rows = _synth_rows(name)
    if prof:
        rows = [r for r in rows if r.get("profile") == prof]
    if qs.get("miss", [""])[0] == "1":
        # 검출기가 상자를 못 낸 장만. 1000장에서 한 장을 찾는 일이라
        # 페이지를 넘겨 가며 눈으로 뒤지게 두면 안 된다.
        rows = [r for r in rows if not r.get("pred")]
    sl = rows[off:off + lim]
    # 예측 파일이 있는 코퍼스에서만 "상자 없음"을 말할 수 있다. 없는 코퍼스
    # (Roboflow 같은 실촬 COCO)에서 그 문구를 띄우면 **정답 상자가 없다**는
    # 뜻으로 읽힌다 — 실제로는 검출기를 안 돌린 것뿐이다.
    has_pred = _synth_pred_file(name) is not None
    return {"total": len(rows), "offset": off, "has_pred": has_pred, "items": [
        {"id": r["id"], "profile": r.get("profile"), "label": r.get("label"),
         "w": r["w"], "h": r["h"], "quad": r["quad"],
         "glass_quad": r.get("glass_quad"), "inverted": r.get("inverted"),
         "dropped": r.get("dropped"), "rects": r.get("rects"),
         "pred": r.get("pred"), "pred_score": r.get("pred_score"),
         "pred_iou": r.get("pred_iou")}
        for r in sl]}


# ── 프로파일 에디터 ────────────────────────────────────────────────────
# 값을 바꾸면 그 자리에서 합성 몇 장을 그려 보여 준다. 굽고 -> 보고 -> 고치는
# 왕복이 한 기기당 여러 번이라(2026-09-15 gmate 만 여덟 번) 그 고리를 줄인다.
#
# 저장은 synth_overrides.json 으로만 간다 — 코드를 기계가 고치지 않는다
# (synth_overrides.py 머리말). 미리보기도 같은 병합 경로를 쓰므로 화면에서
# 본 것과 구운 것이 같다.
_PROF_MOD = {}


def _prof_mods():
    """무거운 합성 모듈은 처음 쓸 때만 import 한다(웹툴 기동을 늦추지 않게).

    파일이 바뀌면 다시 읽는다(2026-09-15). 구판은 한 번 import 하고 캐시만
    돌려줘서, 프로파일을 고친 뒤에도 웹툴은 **기동 시점의 코드**를 계속 그렸다.
    화면이 안 바뀌니 "고쳐도 반응이 없다"로 읽히고, 사람이 다음 값을 헛짚는다.
    합성 캐시를 mtime 으로 무효화한 것과 같은 자리다. [[stale-cache-shows-
    the-old-world]]
    """
    import importlib, os
    # 의존 순서대로 — 아래 것을 먼저 읽어야 위가 새 정의를 집는다.
    # synth_panel 은 import 시점에 synth_profiles 의 이름을 당겨오므로
    # profiles 를 먼저 갈지 않으면 panel 이 옛 표를 그대로 안고 다시 선다.
    names = (("layout", "lcd_layout"), ("schema", "synth_schema"),
             ("ov", "synth_overrides"), ("profiles", "synth_profiles"),
             ("panel", "synth_panel"))
    stamp = []
    for _, mod in names:
        f = os.path.join(os.path.dirname(os.path.abspath(__file__)), mod + ".py")
        try:
            st = os.stat(f)
            stamp.append((mod, st.st_mtime_ns, st.st_size))
        except OSError:
            stamp.append((mod, 0, 0))
    stamp = tuple(stamp)
    if not _PROF_MOD:
        for key, mod in names:
            _PROF_MOD[key] = importlib.import_module(mod)
        _PROF_MOD["_stamp"] = stamp
    elif _PROF_MOD.get("_stamp") != stamp:
        for key, mod in names:
            _PROF_MOD[key] = importlib.reload(_PROF_MOD[key])
        _PROF_MOD["_stamp"] = stamp
    return _PROF_MOD


def _jsonable(v):
    if isinstance(v, tuple):
        return [_jsonable(x) for x in v]
    if isinstance(v, list):
        return [_jsonable(x) for x in v]
    if isinstance(v, dict):
        return {k: _jsonable(x) for k, x in v.items()}
    return v


@route("/api/prof/schema")
def api_prof_schema(qs):
    """값의 모양(열거 후보·범위). 에디터가 위젯을 고르는 근거 — 파이썬 쪽에
    둔다(synth_schema.py). 후보 목록이 렌더러 분기와 갈라지면 안 되므로
    소비하는 코드 옆에 있어야 한다."""
    m = _prof_mods()
    import importlib
    sch = importlib.import_module("synth_schema").schema()
    sch["band_margin"] = m["layout"].BAND_MARGIN
    sch["layout_margin"] = m["layout"].LAYOUT_MARGIN
    return sch


@route("/api/prof/get")
def api_prof_get(qs):
    m = _prof_mods()
    P, ov = m["profiles"], m["ov"]
    pid = qs.get("pid", [""])[0]
    ids = [p.get("id") for p in P.PROFILES]
    if not pid:
        return {"ids": ids}
    base = next((p for p in P.PROFILES if p.get("id") == pid), None)
    if base is None:
        return {"error": "없는 프로파일", "ids": ids}
    data = ov.load()
    return {"ids": ids, "pid": pid,
            "profile": _jsonable(base),
            "regions": _jsonable(P.REGIONS.get(pid, {})),
            "override": _jsonable(data.get(pid, {})),
            "devices": _jsonable(P.PROFILE_DEVICES.get(pid, []))}


def _prof_render(pid, prof_ov, reg_ov, seed, n, band_margin=None):
    """덮어쓰기를 얹어 n 장 그린다. 반환 [(png bytes, quad, label)]."""
    import random
    m = _prof_mods()
    P, panel, ov = m["profiles"], m["panel"], m["ov"]
    base = next((p for p in P.PROFILES if p.get("id") == pid), None)
    if base is None:
        raise ValueError("없는 프로파일")
    merged = ov._merge(base, prof_ov)
    saved = P.REGIONS.get(pid)
    out = []
    # 라벨 여백은 **그림이 아니라 정답 상자**를 바꾼다(2026-09-16 분리).
    # 눈으로 확인하라고 프리뷰에서만 잠깐 갈아끼운다 — 정본 파일은 안 건드린다.
    _lay = m["layout"]
    _saved_bm = _lay.BAND_MARGIN
    try:
        if band_margin is not None:
            _lay.BAND_MARGIN = float(band_margin)
        if reg_ov:
            # REGIONS 는 모듈 전역이라 잠깐 갈아끼운다 — 그려야 반영된다.
            P.REGIONS[pid] = ov._merge(saved or {}, reg_ov)
            panel.REGIONS[pid] = P.REGIONS[pid]
        for i in range(n):
            rng = random.Random(seed + i * 7919)
            val = panel.sample_value(rng)
            s = panel.render_panel(val, rng, profile=merged)
            okp, buf = cv2.imencode(".png", s["panel"])
            # dropped 를 같이 낸다 — 선언했는데 자리가 없어 빠진 요소가
            # 화면에 안 보이면 "고쳐도 안 바뀐다"로 읽힌다(사람 2026-09-15).
            # quad 는 **워프 후** — 학습이 실제로 받는 정답 그대로다
            # (train_band_detector.py 가 manifest 의 quad 를 쓴다).
            # 구판은 quad_panel(워프 전)을 넘겼다. rects 와 좌표계를 맞추려던
            # 것이었는데, 이미지는 워프 후라 상자만 안 기운 세계에 남았고
            # 화면에서는 "정답이 축정렬이다"로 읽혔다(사람 의심 2026-09-15).
            # 두 좌표계를 둘 다 낸다 — quad 가 정답, quad_panel 은 배치 칸.
            # [[unnamed-coordinate-frame]]
            out.append((buf.tobytes(),
                        np.round(s["quad"], 1).tolist(),
                        s["label"], s["W"], s["H"],
                        [list(r) for r in s["rects"]],
                        sorted(set(s.get("dropped") or [])),
                        np.round(s["quad_panel"], 1).tolist()))
    finally:
        _lay.BAND_MARGIN = _saved_bm
        if reg_ov:
            if saved is None:
                P.REGIONS.pop(pid, None); panel.REGIONS.pop(pid, None)
            else:
                P.REGIONS[pid] = saved; panel.REGIONS[pid] = saved
    return out


@route("/api/synth/real")
def api_synth_real(qs):
    """프로파일 -> 그 기기의 실촬 사진 id 목록.

    합성을 고칠 때 실물을 옆에 두고 보기 위한 것이다(사람 요청 2026-09-15).
    **재는 것이 아니라 보는 것**이다 — 합성 설계값을 실사진에서 뽑지 않는다는
    규칙은 그대로다([[no-real-photo-ruler-for-synth]]). 눈으로 대조만 한다.

    순서: 사람 밴드 라벨이 있는 장을 앞에 둔다. 그 장들만이 게이트에 들어가고,
    무엇을 근거로 이 프로파일을 만들었는지도 대개 거기 있다. 그 다음이
    프로파일의 evidence, 나머지는 id 순이다.
    """
    prof = qs.get("profile", [""])[0]
    if not prof:
        return {"device": None, "ids": []}
    try:
        from synth_profiles import PROFILE_DEVICES, PROFILES
    except Exception as e:
        return {"error": str(e), "device": None, "ids": []}
    names = PROFILE_DEVICES.get(prof) or []
    devs = load_device_labels()
    ids = [i for i, d in devs.items()
           if d.get("status") == "identified"
           and (d.get("brand", "") + " " + d.get("model", "")).strip() in names]
    labeled = set()
    if BAND_FILE.exists():
        for l in BAND_FILE.read_text(encoding="utf-8").splitlines():
            if l.strip():
                j = json.loads(l)
                if "quad" in j:
                    labeled.add(j["id"])
    ev = []
    for pr in PROFILES:
        if pr.get("id") == prof:
            ev = list(pr.get("evidence") or [])
            break
    rank = {p: i for i, p in enumerate(ev)}
    ids.sort(key=lambda i: (0 if i in labeled else 1,
                            rank.get(i, len(ev)), i))
    return {"device": names[0] if names else None, "n": len(ids),
            "labeled": sorted(labeled & set(ids)), "ids": ids}


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


# ---- 아틀라스 프록시 ----------------------------------------------------
# make_failure_atlas.py --serve 는 별도 서버(기본 8790)다. 편집 백엔드가 따로
# 있어(agent_review.json 저장) 이 서버로 흡수하지 않고 **주소만 합친다**.
# iframe 을 8790 으로 직접 물리면 출처가 달라(localhost:8777 vs 127.0.0.1:8790)
# 브라우저에 따라 프레임이 비어 보인다. 그래서 같은 출처로 중계한다.
# 아틀라스 페이지가 쓰는 경로는 /imgs/* · /api/cases · /api/review 뿐이고
# 이 서버에는 셋 다 없다 — 충돌하지 않는다(2026-09-11 확인).
ATLAS_PORT = 8790
ATLAS_PATHS = ("/imgs/", "/api/cases", "/api/review")


def _atlas_proxy(handler, path, method="GET", body=None):
    import http.client
    try:
        c = http.client.HTTPConnection("127.0.0.1", ATLAS_PORT, timeout=10)
        c.request(method, path, body=body,
                  headers={"Content-Type": "application/json"} if body else {})
        r = c.getresponse()
        data = r.read()
        ctype = r.getheader("Content-Type", "application/octet-stream")
        handler._send(r.status, data, ctype)
    except OSError:
        # 서버가 안 떠 있는 것은 오류가 아니라 정상 상태다 — 안내를 띄운다.
        handler._send(503, ("아틀라스 서버(포트 %d)가 떠 있지 않다. "
                            "cd assets_dev/train && conda run -n sugartrain "
                            "python make_failure_atlas.py --serve "
                            "--data-root D:/Project/sugarScan/assets_dev/train"
                            % ATLAS_PORT).encode("utf-8"),
                      "text/plain; charset=utf-8")


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
        if u.path == "/atlas":
            _atlas_proxy(self, "/")
            return
        if u.path.startswith(ATLAS_PATHS):
            _atlas_proxy(self, self.path)
            return
        if u.path == "/" or u.path == "/index.html":
            if HTML.exists():
                self._send(200, HTML.read_bytes(), "text/html; charset=utf-8")
            else:
                self._send(404, "webtool.html 없음 — 서버 옆에 만들 것".encode(), "text/plain")
            return
        if u.path == "/synth":
            if SYNTH_HTML.exists():
                self._send(200, SYNTH_HTML.read_bytes(), "text/html; charset=utf-8")
            else:
                self._send(404, "synth_view.html 없음".encode(), "text/plain")
            return
        if u.path == "/profedit":
            if PROFEDIT_HTML.exists():
                self._send(200, PROFEDIT_HTML.read_bytes(),
                           "text/html; charset=utf-8")
            else:
                self._send(404, "prof_edit.html 없음".encode(), "text/plain")
            return
        if u.path == "/synthimg":
            # 합성 PNG 를 그대로 낸다. 리사이즈하지 않는다 — 좌표가 manifest
            # 원본 화소 기준이고, 화면에서 캔버스가 비율대로 맞춘다.
            d = qs.get("dir", [""])[0]
            cid = qs.get("id", [""])[0]
            # 코퍼스 이름은 한 겹까지 허용한다(synth_coco/B). id 에는 구분자를
            # 허용하지 않는다. `..` 와 절대경로는 둘 다 막는다.
            if (".." in d or ".." in cid or "/" in cid
                    or d.startswith("/") or d.count("/") > 1):
                self._send(400, b"bad id", "text/plain")
                return
            # 이미지 폴더 이름이 코퍼스마다 다르다 — synth_panel 은 images/,
            # COCO 로 내보낸 세트는 train2017/ 이다(build_synth_coco.py).
            # 폴더 이름도 확장자도 코퍼스마다 다르다 — synth_panel 은
            # images/*.png, COCO 로 내보낸 세트는 train2017/*.png,
            # Roboflow 실촬은 train2017·val2017/*.jpg 다.
            f = None
            for sub in ("images", "train2017", "val2017"):
                for ext in (".png", ".jpg", ".jpeg"):
                    c = HERE / d / sub / (cid + ext)
                    if c.exists():
                        f = c
                        break
                if f:
                    break
            if f is None:
                self._send(404, b"not found", "text/plain")
                return
            mime = "image/png" if f.suffix == ".png" else "image/jpeg"
            self._send(200, f.read_bytes(), mime)
            return
        if u.path == "/devices":
            if DEVICES_HTML.exists():
                self._send(200, DEVICES_HTML.read_bytes(),
                           "text/html; charset=utf-8")
            else:
                self._send(404, "devices.html 없음".encode(), "text/plain")
            return
        if u.path == "/photo":
            # <img src> 가 한 번에 쓸 수 있는 이진 응답. /api/image 는 JSON 으로
            # {url: /cache/...} 를 주는 라우트라 img 태그에 직접 물리면 깨진다
            # (G34 devices.html 이 그렇게 깨져 있었다). 캐시 생성 로직은
            # api_image 를 그대로 재사용한다 — 리사이즈 규약이 갈리면 안 된다.
            meta = api_image(qs)
            if "error" in meta:
                self._send(404, str(meta["error"]).encode(), "text/plain; charset=utf-8")
                return
            f = CACHE / Path(meta["url"]).name
            if not f.exists():
                self._send(404, b"cache miss", "text/plain")
                return
            self._send(200, f.read_bytes(), "image/jpeg")
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

    def _pid_alive(self, pid):
        if not pid:
            return False
        out = subprocess.run(["tasklist", "/FI", f"PID eq {pid}"],
                             capture_output=True, text=True).stdout
        return str(pid) in out

    def do_POST(self):
        u = urlparse(self.path)
        ln = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(ln) or b"{}"
        if u.path.startswith(ATLAS_PATHS):
            _atlas_proxy(self, self.path, "POST", raw)
            return
        body = json.loads(raw)
        if u.path == "/api/prof/preview":
            # 덮어쓰기를 얹어 몇 장 그려 돌려준다. 저장하지 않는다 —
            # 눈으로 보고 마음에 들면 그때 /api/prof/save 다.
            try:
                _bm = body.get("band_margin")
                shots = _prof_render(body.get("pid", ""),
                                     body.get("profile") or {},
                                     body.get("regions") or {},
                                     int(body.get("seed", 9150)),
                                     min(6, max(1, int(body.get("n", 3)))),
                                     band_margin=(float(_bm) if _bm is not None
                                                  else None))
            except Exception as e:                       # noqa: BLE001
                self._json({"error": f"{type(e).__name__}: {e}"}, 400)
                return
            self._json({"shots": [
                {"png": "data:image/png;base64," + base64.b64encode(b).decode(),
                 "quad": q, "label": lb, "w": w, "h": h, "rects": rc,
                 "dropped": dr, "quad_panel": qp}
                for b, q, lb, w, h, rc, dr, qp in shots]})
            return
        if u.path == "/api/prof/save":
            # 정본(synth_profiles.py)은 건드리지 않는다. 덮어쓰기 JSON 만 쓴다.
            pid = body.get("pid", "")
            if not pid:
                self._json({"error": "pid 없음"}, 400)
                return
            m = _prof_mods()
            data = m["ov"].load()
            ent = {}
            if body.get("profile"):
                ent["profile"] = body["profile"]
            if body.get("regions"):
                ent["regions"] = body["regions"]
            if ent:
                data[pid] = ent
            else:
                data.pop(pid, None)      # 빈 덮어쓰기는 '정본 그대로'다
            m["ov"].save(data)
            self._json({"ok": True, "n": len(data),
                        "path": str(m["ov"].PATH.name)})
            return
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
        if u.path == "/api/devicerotation":
            # 사진 속 숫자가 향하는 방향. up 이 기본이고 예외만 기록한다.
            # 기기 정체성과 무관한 축이라 지정 경로를 따로 둔다.
            ids = body.get("ids") or []
            rot = str(body.get("rotation", "up"))
            if rot not in ("up", "right", "left", "down"):
                self._json({"error": "bad rotation"}, 400)
                return
            if not isinstance(ids, list) or not ids:
                self._json({"error": "ids 가 비었다"}, 400)
                return
            labels = load_device_labels()
            missing = [i for i in ids if i not in labels]
            if missing:
                self._json({"error": "라벨이 없는 사진: %d장" % len(missing)}, 400)
                return
            for i in ids:
                if rot == "up":
                    labels[i].pop("rotation", None)
                else:
                    labels[i]["rotation"] = rot
            save_device_labels(labels)
            self._json({"ok": True, "n": len(ids), "rotation": rot,
                        "labels": {i: labels[i] for i in ids}})
            return
        if u.path == "/api/devicelabel":
            # 사진 단위 라벨 — 여러 장을 한 번에 찍는다(성분 전체 선택이 기본).
            ids = body.get("ids") or []
            if not isinstance(ids, list) or not ids:
                self._json({"error": "ids 가 비었다"}, 400)
                return
            status = str(body.get("status", "identified"))
            if status not in ("identified", "unknown", "reset"):
                self._json({"error": "bad status"}, 400)
                return
            brand = str(body.get("brand", "")).strip()
            model = str(body.get("model", "")).strip()
            # 같은 모델명으로 팔리는 다른 외형이 실제로 있다(ACCU-CHEK Performa
            # 은색 각진 버튼 / 빨강 둥근 버튼). 기기 단절 평가는 개체가 갈려야
            # 성립하므로 외형을 정체성의 일부로 저장한다.
            variant = str(body.get("variant", "")).strip()
            if status == "identified" and not brand and not model:
                self._json({"error": "브랜드가 비었다"}, 400)
                return
            labels = load_device_labels()
            stamp = time.strftime("%Y-%m-%dT%H:%M:%S")
            for i in ids:
                i = str(i)
                if ".." in i or i.startswith("/"):
                    self._json({"error": "bad id"}, 400)
                    return
                if status == "reset":
                    labels.pop(i, None)
                else:
                    # 인쇄 언어(print)는 기기 정체성이 아니라 관찰 기록이다.
                    # 같은 기기를 다시 지정해도 지워지면 안 된다.
                    prev = labels.get(i, {})
                    row = {"id": i,
                           "brand": brand if status == "identified" else "",
                           "model": model if status == "identified" else "",
                           "variant": variant if status == "identified" else "",
                           "status": status, "by": "human", "ts": stamp}
                    keep = body.get("print", prev.get("print"))
                    if keep:
                        row["print"] = str(keep)
                    # 회전도 기기 정체성이 아니다 — 촬영 사실이라 기기를 다시
                    # 지정해도 남아야 한다.
                    rot = prev.get("rotation")
                    if rot and rot != "up":
                        row["rotation"] = rot
                    labels[i] = row
            save_device_labels(labels)
            rows = resummarize_components(labels)
            self._json({"ok": True, "n": len(ids),
                        "labels": {i: labels[i] for i in ids if i in labels},
                        "removed": [i for i in ids if i not in labels],
                        "rows": rows, "vocab": palette_vocab(rows, labels)})
            return
        if u.path == "/api/devicetag":
            comp = str(body.get("component", ""))
            if not (comp.startswith("c") and comp[1:].isdigit()):
                self._json({"error": "bad component"}, 400)
                return
            # status: identified(기종 확정) · unknown(확인했지만 식별 불가)
            #         · mixed(성분 안에 여러 기기) · reset(확인 되돌리기)
            status = str(body.get("status", "identified"))
            if status not in ("identified", "unknown", "mixed", "reset"):
                self._json({"error": "bad status"}, 400)
                return
            rows = load_device_tags()
            for r in rows:
                if r["component"] == comp:
                    if status == "reset":
                        # 잘못 저장한 것을 되돌린다. 라벨은 지우고 미확인으로.
                        r["brand"] = ""
                        r["model"] = ""
                        r["status"] = ""
                        r["confidence"] = "low"
                        r["by"] = "human"
                        r["checked"] = False
                        r["note"] = "사람이 확인 취소 " + time.strftime("%Y-%m-%d")
                    else:
                        # 사람이 저장하는 순간 판정 주체는 human(아틀라스 규약).
                        # identified 가 아니면 브랜드를 비워 둔다 — 억지로 한
                        # 기종을 고르게 만들면 그 순간 라벨이 거짓이 된다.
                        if status == "identified":
                            r["brand"] = str(body.get("brand", "")).strip()
                            r["model"] = str(body.get("model", "")).strip()
                        else:
                            r["brand"] = ""
                            r["model"] = ""
                        r["status"] = status
                        r["confidence"] = "high"
                        r["by"] = "human"
                        r["checked"] = True
                        if body.get("note") is not None:
                            r["note"] = str(body["note"])
                    save_device_tags(rows)
                    self._json({"ok": True, "row": r,
                                "vocab": device_vocab(rows)})
                    return
            self._json({"error": "no such component"}, 404)
            return
        if u.path == "/api/det/start":
            # 밴드 쿼드 검출기 학습. **오래 걸린다** — 40k 코퍼스 50에폭이
            # 1시간 반쯤이라 창을 닫아도 살아 있게 떼어 놓는다(DETACHED).
            if self._pid_alive(_det_pid()):
                self._json({"ok": False, "error": "이미 실행 중"})
                return
            if DET_LOG.exists() and (time.time() - DET_LOG.stat().st_mtime) < 120:
                self._json({"ok": False,
                            "error": "다른 학습이 방금까지 로그를 기록 중 — 잠시 후"})
                return
            data = str(body.get("data") or "").strip()
            if not data or not (HERE / data / "manifest.jsonl").exists():
                self._json({"ok": False,
                            "error": f"코퍼스가 없다: {data or '(빈 값)'}"})
                return
            try:
                epochs = max(1, min(400, int(body.get("epochs", 50))))
            except (TypeError, ValueError):
                self._json({"ok": False, "error": "에폭이 숫자가 아니다"})
                return
            out = str(body.get("out") or "").strip() or f"band_det_{data}.pt"
            if not out.endswith(".pt") or "/" in out or "\\" in out:
                self._json({"ok": False,
                            "error": "출력 이름은 .pt 파일명 하나여야 한다"})
                return
            arch = str(body.get("arch") or "fc")
            every = int(body.get("ckpt_every", 10) or 0)
            cmd = [sys.executable, str(HERE / "train_band_detector.py"),
                   "--data", data, "--epochs", str(epochs),
                   "--out", out, "--arch", arch]
            if every:
                cmd += ["--ckpt-every", str(every)]
            # 로그는 **덮어쓴다**. 이어붙이면 재개할 때마다 옛 에폭이 누적돼
            # 그래프가 부풀고, 어느 줄이 이번 실행인지 화면에서 가를 수 없다
            # (구판 CTC 로그가 그랬다 — 8월 31일 줄이 9월까지 살아 있었다).
            logf = open(DET_LOG, "wb")
            logf.write(("== " + " ".join(cmd[1:]) + " ==" + chr(10)).encode("utf-8"))
            logf.flush()
            env = dict(os.environ, PYTHONUNBUFFERED="1")
            proc = subprocess.Popen(cmd, stdout=logf,
                                    stderr=subprocess.STDOUT,
                                    creationflags=DETACHED, env=env,
                                    cwd=str(HERE))
            DET_PID.write_text(json.dumps(
                {"pid": proc.pid, "data": data, "epochs": epochs, "out": out,
                 "arch": arch, "started": time.time()}), encoding="utf-8")
            self._json({"ok": True, "pid": proc.pid, "cmd": cmd[1:]})
            return
        if u.path == "/api/det/stop":
            pid = _det_pid()
            if pid and self._pid_alive(pid):
                subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"],
                               capture_output=True)
            self._json({"ok": True})
            return
        if u.path == "/api/det/overlay":
            # 기종 탭 오버레이를 이 체크포인트로 갈아끼운다. 2,511장이라
            # 5분쯤 걸리므로 **떼어 놓고** 돌린다 — 브라우저가 기다리지 않게.
            ck = str(body.get("ckpt") or "").strip()
            if not ck.endswith(".pt") or "/" in ck or "\\" in ck                     or not (HERE / ck).exists():
                self._json({"ok": False, "error": f"체크포인트가 없다: {ck}"})
                return
            if self._pid_alive(int(OVL_PID.read_text(encoding="utf-8").strip())
                               if OVL_PID.exists()
                               and OVL_PID.read_text(encoding="utf-8").strip()
                               .isdigit() else None):
                self._json({"ok": False, "error": "이미 뽑는 중"})
                return
            logf = open(OVL_LOG, "wb")
            proc = subprocess.Popen(
                [sys.executable, str(HERE / "predict_band_quads.py"),
                 "--ckpt", ck],
                stdout=logf, stderr=subprocess.STDOUT,
                creationflags=DETACHED,
                env=dict(os.environ, PYTHONUNBUFFERED="1"), cwd=str(HERE))
            OVL_PID.write_text(str(proc.pid), encoding="utf-8")
            self._json({"ok": True, "pid": proc.pid, "ckpt": ck})
            return
        if u.path == "/api/det/gate":
            # 실사진 게이트. 사람 밴드 라벨과 견주는 **유일한** 자이고,
            # 합성 val 점수는 품질 계기가 아니다(카드 지시).
            ck = str(body.get("ckpt") or "").strip()
            if not ck.endswith(".pt") or "/" in ck or "\\" in ck                     or not (HERE / ck).exists():
                self._json({"ok": False, "error": f"체크포인트가 없다: {ck}"})
                return
            try:
                r = subprocess.run(
                    [sys.executable, str(HERE / "eval_band_detector.py"),
                     "gate", "--ckpt", ck],
                    capture_output=True, text=True, cwd=str(HERE),
                    env=dict(os.environ, PYTHONUNBUFFERED="1"), timeout=1800)
            except subprocess.TimeoutExpired:
                self._json({"ok": False, "error": "게이트가 30분을 넘겼다"})
                return
            self._json({"ok": r.returncode == 0,
                        "tag": Path(ck).stem,
                        "text": (r.stdout or "") + (r.stderr or "")})
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
