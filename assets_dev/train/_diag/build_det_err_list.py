# 검출기 오류·오독 리스트 생성(사람 요청 2026-10-04 "오독하는 이미지 리스트
# 만들어서 가져와" + "검출기 개선방법 가져와") — 배포 스택(atone_tg640w15 ×
# v11e)의 끝단 오류를 검출기 기여 여부로 가른다:
#   det-fail         검출 실패(게이트 통과 상자 없음)
#   det-clip-오독    상자가 숫자를 온전히 안 담(contain<1.0)하고 오독
#   det-badiou-오독  contain 은 1.0 이나 IoU 하위 15%(찌그러진 상자) + 오독
#   reader-오독      상자가 멀쩡한데 오독(리더 과제 — 저대비 등)
# 산출: e2e_miss_queue.json(웹툴 열람 큐 교체 — 구 260건은 구모델 시절),
#       _diag/det_err_list_v1.txt(텍스트 목록)
# 사용: python _diag/build_det_err_list.py
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
DET = HERE / "_diag" / "band_real" / "atone_tg640w15.jsonl"
E2E = HERE / "_diag" / "e2e_bandnet" / "tg_v11e.jsonl"
DEV = HERE / "device_labels.jsonl"
QUEUE = HERE / "e2e_miss_queue.json"
TXT = HERE / "_diag" / "det_err_list_v1.txt"


def load_rows(p, key="id"):
    out = {}
    for ln in Path(p).read_text(encoding="utf-8").splitlines():
        if ln.strip():
            r = json.loads(ln)
            if key in r:
                out[r[key]] = r
    return out


det = load_rows(DET)
e2e = load_rows(E2E)
dev = load_rows(DEV)
detected = [r for r in det.values() if r.get("det")]
ious = sorted(r["iou"] for r in detected)
iou15 = ious[int(len(ious) * 0.15)]        # 하위 15% 경계

entries = []
for cid, r in sorted(e2e.items()):
    v = r["verdict"]
    d = det.get(cid, {})
    dv = dev.get(cid, {})
    devname = (dv.get("brand", "?") + " " + dv.get("model", "")).strip() or "(미식별)"
    detnote = (f"IoU {d.get('iou', 0):.3f}·포함 {d.get('contain', 0):.2f}·"
               f"면적비 {d.get('area_ratio', 0):.2f}") if d.get("det") else "검출실패"
    if v == "det":
        # e2e 자체가 게이트 통과 상자를 못 얻은 장(라벨 유무와 무관하게 실패)
        entries.append(dict(id=cid, stratum="det-fail",
                            note=f"검출실패(e2e) · {devname} · {detnote}"))
    elif v == "wrong":
        if cid not in det:
            # 밴드 사람 라벨이 없는 장 — 상자 근거 없음, 눈검으로 가린다
            entries.append(dict(id=cid, stratum="오독-상자근거없음",
                                note=f"GT {r['gt']}→{r['pred']} · 밴드라벨 없음"
                                     f"(눈검: 상자가 자른 건지 판단) · {devname}"))
        elif d.get("contain", 1.0) < 1.0:
            entries.append(dict(id=cid, stratum="det-clip-오독",
                                note=f"GT {r['gt']}→{r['pred']} · 상자가 숫자 자름 · "
                                     f"{devname} · {detnote}"))
        elif d.get("iou", 1.0) < iou15:
            entries.append(dict(id=cid, stratum="det-badiou-오독",
                                note=f"GT {r['gt']}→{r['pred']} · 찌그러진 상자 · "
                                     f"{devname} · {detnote}"))
        else:
            entries.append(dict(id=cid, stratum="reader-오독",
                                note=f"GT {r['gt']}→{r['pred']} · 상자 멀쩡 · "
                                     f"{devname} · {detnote}"))
# 검출기 단독 개선 과제: 읽기는 맞았지만 상자가 나쁜 최하위 IoU 상위 15장
ok_bad = [d for d in detected
          if e2e.get(d["id"], {}).get("verdict") == "right"
          and (d["contain"] < 1.0 or d["iou"] < iou15)]
for d in sorted(ok_bad, key=lambda x: x["iou"])[:15]:
    dv = dev.get(d["id"], {})
    devname = (dv.get("brand", "?") + " " + dv.get("model", "")).strip() or "(미식별)"
    entries.append(dict(id=d["id"], stratum="det-나쁜상자(읽기는 성공)",
                        note=f"{devname} · IoU {d['iou']:.3f}·포함 "
                             f"{d['contain']:.2f}·면적비 {d['area_ratio']:.2f}"))

order = {"det-fail": 0, "det-clip-오독": 1, "det-badiou-오독": 2,
         "오독-상자근거없음": 3, "reader-오독": 4, "det-나쁜상자(읽기는 성공)": 5}
entries.sort(key=lambda e: (order[e["stratum"]], e["id"]))

QUEUE.write_text(json.dumps(entries, ensure_ascii=False, indent=1),
                 encoding="utf-8")
with TXT.open("w", encoding="utf-8") as f:
    cur = None
    for e in entries:
        if e["stratum"] != cur:
            cur = e["stratum"]
            n = sum(1 for x in entries if x["stratum"] == cur)
            f.write(f"\n== {cur} ({n}장) ==\n")
        f.write(f"  {e['id']:24s} {e['note']}\n")

from collections import Counter  # noqa: E402
devname_of = {}
for cid, dv in dev.items():
    devname_of[cid] = (dv.get("brand", "?") + " " + dv.get("model", "")).strip() \
        or "(미식별)"
for s in order:
    sub = [e for e in entries if e["stratum"] == s]
    if not sub:
        continue
    cds = Counter(devname_of.get(e["id"], "(미식별)") for e in sub)
    print(f"[{s}] {len(sub)}장 · 기기: {cds.most_common(6)}")
print(f"\n큐: {QUEUE} ({len(entries)}행)\n목록: {TXT}")
print(f"포함률<1.0 전체(검출된 343장 중): "
      f"{sum(1 for d in detected if d['contain'] < 1.0)}장")
print(f"IoU 하위15% 경계: {iou15:.3f}")
