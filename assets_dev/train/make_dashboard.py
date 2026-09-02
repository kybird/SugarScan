# 대시보드 생성기 — dashboard/dashboard.html 을 (재)생성한다.
# 이미지는 상대경로 참조(assets_dev/train 기준), 30초 자동갱신 meta 포함.
# 학습 로그(ctc_train_gpu.log)에서 loss 궤적을 파싱해 SVG 차트로 그린다.
import html
import math
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT_DIR = HERE / "dashboard"
LOG = HERE / "ctc_train_gpu.log"


def losses_from_log():
    losses = []
    try:
        for line in LOG.read_text(encoding="utf-8", errors="ignore").splitlines():
            m = re.search(r"loss: ([0-9.]+)", line.replace("\x1b", "").replace("[0-9;]*m", ""))
            line_clean = re.sub(r"\x1b\[[0-9;]*m", "", line)
            m = re.search(r"loss: ([0-9.]+)", line_clean)
            if m:
                losses.append(float(m.group(1)))
    except FileNotFoundError:
        pass
    return losses


def loss_svg(losses, w=680, h=160):
    if not losses:
        return "<p>학습 로그 대기 중…</p>"
    hi, lo = max(losses), min(losses)
    rng = (hi - lo) or 1.0
    pts = []
    for i, v in enumerate(losses):
        x = w - 40 - (len(losses) - 1 - i) * (w - 60) / max(1, len(losses) - 1)
        y = 20 + (h - 50) * (1 - (v - lo) / rng)
        pts.append(f"{x:.0f},{y:.0f}")
    poly = " ".join(pts)
    last = losses[-1]
    return f'''<svg width="{w}" height="{h}" style="background:#fafafa;border:1px solid #ddd">
<polyline points="{poly}" fill="none" stroke="#c0392b" stroke-width="2"/>
<text x="10" y="18" font-size="12">CTC loss (최근 {len(losses)}에폭) · 최신 {last:.2f}</text>
<text x="{w-90}" y="{h-8}" font-size="11">← 최근 에폭</text>
</svg>'''


def img_card(src, title, note=""):
    note_html = f"<div class='note'>{html.escape(note)}</div>" if note else ""
    return f'''<div class="card"><img src="../{src}" loading="lazy">
<div class="cap"><b>{html.escape(title)}</b>{note_html}</div></div>'''


def main() -> int:
    OUT_DIR.mkdir(exist_ok=True)
    losses = losses_from_log()
    epoch_done = len(losses)
    total_epochs = 12 + 12
    cur = "합성 사전학습" if epoch_done <= 12 else "실사진 파인튜닝"
    pct = 100 * epoch_done / total_epochs

    cards = [
        img_card("synth_screens/sample_combo.png", "합성 LCD 화면 (렌더러 v2)",
                 "광택·비네팅·회전·폭 지터 추가 — 23,000장 생성"),
        img_card("previews/gm__glucose_batch1__1000.png",
                 "GM 검출기 전이 성공", "미학습 Datumo 기기(CareSens N, 95) 화면 온전 캡처"),
        img_card("previews/gm__glucose_batch1__10.png",
                 "GM 검출기 전이 성공 2", "106 + 시간줄 + mg/dL 전체"),
        img_card("previews/v2__glucose_batch1__1281.png",
                 "v2 밴드 검출 (참고)", "265 밴드 — 밴드 직접 검출은 전이 실패였으나 참고용"),
        img_card("previews/segvis__glucose_batch1__1040.png",
                 "세그먼트 진단: 성공 케이스", "3글자 3박스 정상 분할"),
        img_card("previews/segvis__glucose_batch1__1207.png",
                 "세그먼트 진단: 텍스트 오탐", "크롭이 영문 텍스트 영역 — 밴드 휴리스틱 한계 확인"),
        img_card("previews/segvis__glucose_batch1__1230.png",
                 "세그먼트 진단: 빈 영역", "크롭에 숫자 없음"),
        img_card("previews/rl_before__glucose_batch1__1282.png",
                 "리레이아웃 이전", "265 밴드"),
        img_card("previews/rl_after__glucose_batch1__1282.png",
                 "리레이아웃 이후(무효 실험)", "mg/dL 병합·좌측 절단 — 실험 무효 판정의 근거"),
    ]
    gallery = "\n".join(cards)

    miss_rows = ""
    miss_path = HERE / "reader_preds.json"
    miss_html = ""
    if miss_path.exists():
        try:
            preds = json.loads(miss_path.read_text(encoding="utf-8"))
            rows = []
            for cid, (s, g) in sorted(preds.items()):
                mark = "✅" if s == g else "❌"
                rows.append(f"<tr><td>{mark} {cid}</td><td>{g}</td><td>{s}</td></tr>")
            miss_html = ("<h2>hold-out 판독 결과 (미라벨 1,767장)</h2><table><tr>"
                         "<th>id</th><th>GT</th><th>판독</th></tr>"
                         + "".join(rows) + "</table>")
        except Exception:
            pass

    html_doc = f'''<!DOCTYPE html><html lang="ko"><head><meta charset="utf-8">
<meta http-equiv="refresh" content="60">
<title>SugarScan 판독 리더 대시보드</title><style>
body {{ font-family: '맑은 고딕', sans-serif; margin: 24px; background: #f5f6f7; }}
h1 {{ font-size: 22px; }} h2 {{ font-size: 17px; margin-top: 28px; }}
.stage {{ background: #fff; border: 1px solid #ddd; padding: 12px 16px; margin: 8px 0; }}
.ok {{ color: #1a7f37; font-weight: bold; }} .warn {{ color: #b58900; font-weight: bold; }}
.card {{ display: inline-block; background: #fff; border: 1px solid #ddd;
        margin: 6px; padding: 6px; vertical-align: top; width: 330px; }}
.card img {{ width: 320px; image-rendering: auto; }}
.cap {{ font-size: 13px; margin-top: 4px; }} .note {{ color: #666; font-size: 12px; }}
table {{ border-collapse: collapse; font-size: 13px; }}
td, th {{ border: 1px solid #ccc; padding: 3px 8px; }}
.bar {{ background: #eee; height: 18px; width: 400px; }}
.bar > div {{ background: #2d6cdf; height: 18px; }}
</style></head><body>
<h1>SugarScan — LCD 판독 리더 학습 대시보드</h1>
<p>생성: {html.escape(str(__import__("datetime").datetime.now().strftime("%m-%d %H:%M")))}
 · 60초마다 자동 갱신 (재생성은 make_dashboard.py)</p>

<h2>파이프라인 현황</h2>
<div class="stage">① 사진 → <span class="ok">LCD 검출 (ML) — 79.9% ✓ 전이 성공</span></div>
<div class="stage">② 화면 펴기 (호모그래피) — <span class="ok">✓</span></div>
<div class="stage">③ 화면 → 값 판독 (CTC 리더) — <span class="warn">학습 진행 중
 ({epoch_done}/{total_epochs} 에폭 · {cur})</span></div>
<div class="bar"><div style="width:{pct:.0f}%"></div></div>

<h2>CTC loss 궤적</h2>
{loss_svg(losses, 680, 160)}

<h2>실험 연혁 — 완전일치 (hold-out)</h2>
<table>
<tr><th>실험</th><th>완전일치</th><th>비고</th></tr>
<tr><td>규칙 엔진 (대조군)</td><td>0 / 1,767</td><td>검출 단계 부재</td></tr>
<tr><td>CTC v1 (사전학습 6에폭)</td><td>0 / 1,767</td><td>전부 "19" — 미수렴</td></tr>
<tr><td>CTC v2 (40+20에폭, 3k 합성)</td><td><b>139 / 1,767 (7.9%)</b></td><td>근접 오차 위주 — 학습 가능성 입증</td></tr>
<tr><td>CTC v3 (23k 합성 + 개선 렌더러, 12+12에폭)</td><td><b>진행 중</b></td><td>이 대시보드에서 추적</td></tr>
</table>

<h2>핵심 이미지</h2>
{gallery}

{miss_html}

<p style="color:#888">재생성: conda run -n sugartrain python make_dashboard.py ·
데이터: assets_dev/train/ (전부 로컬)</p>
</body></html>'''
    (OUT_DIR / "dashboard.html").write_text(html_doc, encoding="utf-8")
    print(f"dashboard → {OUT_DIR / 'dashboard.html'} | epochs={epoch_done} last_loss={losses[-1] if losses else None}")
    return 0


if __name__ == "__main__":
    import json
    raise SystemExit(main())
