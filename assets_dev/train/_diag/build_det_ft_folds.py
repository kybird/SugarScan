# 검출기 실촉 파인튜닝 K=5 폴드 + COCO 어노테이션 생성 (2026-10-09).
# 사람 지시 "전부다 밤새돌려라" — A안(실촉 파인튜닝)의 재료.
# 폴드: 기기 층화(54종) × 같은 기기 연속 id 2장 청크를 라운드로빈 —
# 세션 누수 완화(연속 사진=같은 촬영 세션일 확률 높음) + 기기 균형.
# 라벨은 band_boxes.jsonl(사람 전수 확인 완료, 2026-10-08)에서
# band_label_excluded 제외만 한 346장 — 예측 오염 0.
# 학습 데이터: fold-train 실촬 ×8 오버샘플 + GEN2 합성 리플레이 2,216장
# (잊어버림 방지 + 규약 유지, 실촉:합성 ≈ 1:1).
# CocoBand 가 root/train2017/<file_name> 으로만 경로를 만들므로 file_name
# 에 상대경로 순회(../../../)를 쓴다 — 실촬 사진을 복사하지 않기 위해서.
import json
import random
from pathlib import Path

HERE = Path(__file__).resolve().parent
TRAIN = HERE.parent
DATUMO = TRAIN.parent / "upstream" / "datumo"
GEN2 = TRAIN / "synth_coco" / "GEN2"
OUT = HERE / "det_ft"
K = 5
REAL_REPEAT = 8
SYNTH_N = 2216          # fold-train 실촬(≈277)×8 ≈ 2,216 과 1:1

excl = set()
for ln in (TRAIN / "band_label_excluded.jsonl").read_text(
        encoding="utf-8").splitlines():
    if ln.strip():
        excl.add(json.loads(ln)["id"])
labels = []
for ln in (TRAIN / "band_boxes.jsonl").read_text(encoding="utf-8").splitlines():
    if not ln.strip():
        continue
    r = json.loads(ln)
    if r["id"] not in excl and r.get("quad"):
        labels.append(r)
imgs, read = {}, {}
for ln in (DATUMO / "labels.jsonl").read_text(encoding="utf-8").splitlines():
    if ln.strip():
        j = json.loads(ln)
        imgs[j["id"]] = j["image"]
        read[j["id"]] = str(j.get("reading", ""))

dev = {}
for ln in (TRAIN / "device_labels.jsonl").read_text(encoding="utf-8").splitlines():
    if ln.strip():
        j = json.loads(ln)
        dev[j["id"]] = " ".join(x for x in (j.get("brand"), j.get("model"),
                                            j.get("variant")) if x)

def idnum(pid):
    try:
        return int(pid.split("/")[-1])
    except ValueError:
        return 0

order = sorted(labels, key=lambda r: (dev.get(r["id"], "?"), idnum(r["id"])))
chunks = []
i = 0
while i < len(order):                      # 같은 기기 연속 2장 청크(세션 누수 완화)
    chunks.append(order[i:i + 2])
    i += 2
folds = [[] for _ in range(K)]
for ci, ch in enumerate(chunks):
    folds[ci % K].extend(ch)
sizes = [len(f) for f in folds]
print(f"라벨 {len(labels)}장 → K={K} 폴드 {sizes} (기기 {len(set(dev.get(r['id'],'?') for r in labels))}종)")

synth = json.loads((GEN2 / "annotations" / "instances_train2017.json")
                   .read_text(encoding="utf-8"))
synth_by = {a["image_id"]: a["bbox"] for a in synth["annotations"]}
synth_items = [(im["file_name"], synth_by[im["id"]])
               for im in synth["images"] if im["id"] in synth_by]

for fi in range(K):
    fdir = OUT / f"fold{fi}"
    (fdir / "annotations").mkdir(parents=True, exist_ok=True)
    hold_ids = [r["id"] for r in folds[fi]]
    train_rows = [r for r in labels if r["id"] not in set(hold_ids)]
    (fdir / "holdout_ids.json").write_text(json.dumps(hold_ids), encoding="utf-8")
    rng = random.Random(20261009 + fi)
    images, anns = [], []
    aid = 1
    for rep in range(REAL_REPEAT):
        for r in train_rows:
            q = r["quad"]
            x0 = min(p[0] for p in q); y0 = min(p[1] for p in q)
            x1 = max(p[0] for p in q); y1 = max(p[1] for p in q)
            rel = "../../../../../upstream/datumo/" + imgs[r["id"]].replace("\\", "/")
            images.append(dict(id=aid, file_name=rel))
            anns.append(dict(image_id=aid, bbox=[x0, y0, x1 - x0, y1 - y0]))
            aid += 1
    for fn, bbox in rng.sample(synth_items, SYNTH_N):
        images.append(dict(id=aid, file_name="../../../../synth_coco/GEN2/train2017/" + fn))
        anns.append(dict(image_id=aid, bbox=bbox))
        aid += 1
    (fdir / "annotations" / "instances_train2017.json").write_text(
        json.dumps(dict(images=images, annotations=anns)), encoding="utf-8")
    print(f"fold{fi}: holdout {len(hold_ids)} · 학습 실촬 {len(train_rows)}×{REAL_REPEAT}"
          f" + 합성 {SYNTH_N} = {len(images)}")

# 전량 학습용(배포 후보 — 평가는 K폴드 결과로 대신 본다)
fdir = OUT / "foldall"
(fdir / "annotations").mkdir(parents=True, exist_ok=True)
images, anns = [], []
aid = 1
for rep in range(REAL_REPEAT):
    for r in labels:
        q = r["quad"]
        x0 = min(p[0] for p in q); y0 = min(p[1] for p in q)
        x1 = max(p[0] for p in q); y1 = max(p[1] for p in q)
        rel = "../../../../../upstream/datumo/" + imgs[r["id"]].replace("\\", "/")
        images.append(dict(id=aid, file_name=rel))
        anns.append(dict(image_id=aid, bbox=[x0, y0, x1 - x0, y1 - y0]))
        aid += 1
rng = random.Random(20261009 + 99)
for fn, bbox in rng.sample(synth_items, SYNTH_N):
    images.append(dict(id=aid, file_name="../../../../synth_coco/GEN2/train2017/" + fn))
    anns.append(dict(image_id=aid, bbox=bbox))
    aid += 1
(fdir / "annotations" / "instances_train2017.json").write_text(
    json.dumps(dict(images=images, annotations=anns)), encoding="utf-8")
(fdir / "holdout_ids.json").write_text("[]", encoding="utf-8")
print(f"foldall(전량): 실촬 {len(labels)}×{REAL_REPEAT} + 합성 {SYNTH_N}")
(OUT / "folds_meta.json").write_text(
    json.dumps(dict(k=K, sizes=sizes, real_repeat=REAL_REPEAT, synth_n=SYNTH_N),
               ensure_ascii=False, indent=1), encoding="utf-8")
