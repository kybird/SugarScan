# GEN10D 감사 후속 — 함정 31장 축의 2×2 교차 (2026-11-19)
# gen10d-input-audit-20261119.md §5-2(함정축 미측정)를 닫는 측정.
# 값 207장 교차(audit_gen10d_input.py D부)와 같은 체인·같은 조합으로
# 함정(값 없음) 31장만 잰다. 측정만 함 — 학습·기존 결과 불변.
# 사용: conda run -n melotts python audit_gen10d_trap.py
# 출력: audit_gen10d_trap_out.json

import json
from collections import Counter
from pathlib import Path

import torch

from eval_reject_stages import (CONF_GATE, MIN_FRAC, READ_CONF, VLO, VHI,
                                load_detector, load_reader)
from eval_real_judge import load_oriented

HERE = Path(__file__).resolve().parent
LABELS = HERE / "dc238_labels.jsonl"
CKPT = {"ps10b": HERE / "band_out" / "ps10b_det_neg25.pt",
        "ps10d": HERE / "band_out" / "ps10d_det640.pt"}

rows = {}
for l in LABELS.read_text(encoding="utf-8").splitlines():
    if l.strip():
        j = json.loads(l)
        rows[j["id"].split("/", 1)[1]] = j
traps = {s: g for s, g in sorted(rows.items())
         if not (g["source"] == "human" and g["value"] is not None)}

det_specs = [("ps10b@416", CKPT["ps10b"], 416),
             ("ps10b@640", CKPT["ps10b"], 640),
             ("ps10d@640", CKPT["ps10d"], 640)]
rdr_specs = [("rdr10b", "reader_out/ps10b_rdr/best.pt"),
             ("rdr10d", "reader_out/ps10d_rdr/best.pt")]

out = {"n_traps": len(traps)}
for dname, dpath, dsize in det_specs:
    ck = torch.load(dpath, map_location="cpu", weights_only=False)
    ck["size"] = dsize
    tmp = HERE / f"_audit_tmp_t_{dname}.pt"
    torch.save(ck, tmp)
    try:
        det_run, _ = load_detector(str(tmp))
        for rname, rpath in rdr_specs:
            read = load_reader(rpath)
            c = Counter()
            for stem, gt in traps.items():
                img = load_oriented(stem)
                b, score, (r, dx, dy) = det_run(img)
                p = [(b[0] - dx) / r, (b[1] - dy) / r,
                     (b[2] - dx) / r, (b[3] - dy) / r]
                frac = ((p[2] - p[0]) * (p[3] - p[1])
                        / (img.shape[0] * img.shape[1]))
                stage, val = "검출게이트", None
                if score >= CONF_GATE and frac >= MIN_FRAC:
                    stage = "판독"
                    crop = img[max(0, int(p[1])):min(img.shape[0], int(p[3])),
                               max(0, int(p[0])):min(img.shape[1], int(p[2]))]
                    text, conf = read(crop)
                    if text:
                        stage = "값검증"
                        if text.isdigit() and VLO <= int(text) <= VHI:
                            val = int(text)
                            stage = "확신도"
                            if conf >= READ_CONF:
                                stage = "확정"
                if val is None:
                    c["거절(정상)"] += 1
                elif stage != "확정":
                    c["확신도차단"] += 1
                else:
                    c["오답 확정(함정통과)"] += 1
            out[f"{dname}+{rname}"] = dict(c)
    finally:
        tmp.unlink(missing_ok=True)

print(json.dumps(out, indent=1, ensure_ascii=False))
(HERE / "audit_gen10d_trap_out.json").write_text(
    json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")
