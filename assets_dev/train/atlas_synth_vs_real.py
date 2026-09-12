# 합성 대 실사진 차이 아틀라스 — 「합성 대 실사진 차이 아틀라스」 카드.
#
# 산출물(전부 _diag/synth_real_atlas/ 로 — 메인 워크트리와 정션 공유):
#   montage_pairs.png      실사진 40 | 합성 40 을 같은 320x160 워프로 나란히(20행x2열)
#   strip_<slug>.png       실패 기기(도루코S·Instant·Gmate·ACURA VIEW) 홀드아웃 스트립
#   grid/real_##.png       실사진 2배 확대 + 20px 격자 + 좌표 눈금(요소 위치 측정용)
#   grid/synth_##.png      합성 4장 같은 형식
#   sample_manifest.json   어떤 id 를 왜 뽑았는지(재현·근거 추적)
#
# 실사진은 train_device 캐시의 워프 배열에서만 꺼낸다(재디코드·재워프 금지 —
# duplicated-geometry-implementation · mixed-image-decode-conventions).
# device_labels.jsonl 은 읽기 전용으로만 읽는다. 이 스크립트는 아무 라벨 파일도
# 쓰지 않는다.
#
# 표본 설계(AC #3): 기기 단절 홀드아웃에서 실패한 기기를 반드시 포함.
#   도루코S Premium 33.3%(3장 전량) · ACCU-CHEK Instant 76.5%(6) ·
#   Gmate 79.8%(6) · ACURA VIEW 75.0%(2) = 17장, 나머지 23장은 홀드아웃
#   나머지 기기에서 층화 추출. 시드 17000(카드 ordinal).
import json
import random
import sys
from pathlib import Path

import cv2
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import synth_lcd  # noqa: E402  같은 폴더의 렌더러 — 합성 40장은 이걸로 그린다.

CACHE = HERE.parent / "train_device" / "data_cache_v2.npz"
LABELS = HERE / "device_labels.jsonl"          # 읽기 전용
OUT = HERE / "_diag" / "synth_real_atlas"
SEED = 17000

# 실패 기기(AC #3): (brand, model, variant) → 뽑을 장수
FAILED_DEVICES = [
    ("도루코S", "Premium", "", 3),          # 홀드아웃 3장 전량
    ("ACCU-CHEK", "Instant", "", 6),
    ("Gmate", "", "", 6),
    ("ACURA VIEW", "", "", 2),
]
N_TOTAL = 40


def load_devices():
    """id → (brand, model, variant). 두 표기('a/b'·'a__b')를 모두 등록한다."""
    m = {}
    with open(LABELS, encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            r = json.loads(line)
            key = (r["brand"].strip(), r["model"].strip(), r["variant"].strip())
            m[r["id"]] = key
            m[normalize_id(r["id"])] = key
    return m


def normalize_id(s):
    return s.replace("/", "__").removesuffix(".jpg")


def pick_real(ids, devices):
    """실패 기기 우선 + 나머지 기기 층화. (idx, id, device, reason) 목록."""
    rng = random.Random(SEED)
    by_dev = {}
    for i, raw in enumerate(ids):
        key = devices.get(str(raw)) or devices.get(normalize_id(str(raw)))
        assert key, f"기기 라벨 없는 id: {raw}"
        by_dev.setdefault(key, []).append(i)

    picked = []
    for brand, model, variant, n in FAILED_DEVICES:
        pool = by_dev.get((brand, model, variant), [])
        assert len(pool) >= n, f"홀드아웃에 기기 부족: {brand}/{model}/{variant}"
        for i in rng.sample(pool, n):
            picked.append((i, f"{brand}/{model}/{variant}".strip("/"), "failed-device"))
    assert len(picked) < N_TOTAL

    # 나머지: 실패 기기 제외한 홀드아웃 기기에서 고루(기기당 최대 2장).
    rest = [k for k in sorted(by_dev) if k not in
            [(b, m, v) for b, m, v, _ in FAILED_DEVICES]]
    rng.shuffle(rest)
    quota = N_TOTAL - len(picked)
    for k in rest:
        if quota <= 0:
            break
        pool = by_dev[k]
        take = min(2, len(pool), quota)
        for i in rng.sample(pool, take):
            picked.append((i, "/".join(p for p in k if p), "stratified"))
        quota -= take
    assert len(picked) == N_TOTAL, f"40장 못 채움: {len(picked)}"
    return picked


def decode_value(label_ids, label_len):
    return "".join(str(int(c)) for c in label_ids[:label_len])


def label_cell(img, text):
    """좌상단 반투명 띠 + 흰 글자. 원본 화소는 띠 아래에 그대로 있다."""
    out = img.copy()
    (tw, th), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.34, 1)
    cv2.rectangle(out, (0, 0), (tw + 8, th + 10), (0, 0, 0), -1)
    out[0:img.shape[0], 0:img.shape[1]] = cv2.addWeighted(
        out, 0.55, np.zeros_like(out), 0.45, 0)[0:img.shape[0], 0:img.shape[1]]
    cv2.putText(out, text, (4, th + 6), cv2.FONT_HERSHEY_SIMPLEX, 0.34,
                (255, 255, 255), 1, cv2.LINE_AA)
    return out


def grid_sheet(img, scale=2, step=20):
    """2배 확대 + step px 격자 + 40px 마다 좌표 눈금(워프 좌표계 값)."""
    big = cv2.resize(img, (img.shape[1] * scale, img.shape[0] * scale),
                     interpolation=cv2.INTER_NEAREST)
    h, w = big.shape
    for x in range(0, img.shape[1] * scale, step * scale // 2):
        cv2.line(big, (x, 0), (x, h), (170, 170, 170), 1)
    for y in range(0, img.shape[0] * scale, step * scale // 2):
        cv2.line(big, (0, y), (w, y), (170, 170, 170), 1)
    for x in range(0, img.shape[1], 40):     # 눈금 값 = 워프 px
        cv2.putText(big, str(x), (x * scale + 2, 12), cv2.FONT_HERSHEY_SIMPLEX,
                    0.32, (0, 255, 255), 1, cv2.LINE_AA)
    for y in range(40, img.shape[0], 40):
        cv2.putText(big, str(y), (2, y * scale + 12), cv2.FONT_HERSHEY_SIMPLEX,
                    0.32, (0, 255, 255), 1, cv2.LINE_AA)
    return big


def main():
    z = np.load(CACHE, allow_pickle=True)
    X = z["real_holdout_images"]
    ids = [str(x) for x in z["real_holdout_ids"]]
    lid = z["real_holdout_label_ids"]
    llen = z["real_holdout_label_lens"]
    print(f"cache holdout {len(ids)}장, id 예: {ids[:2]}", flush=True)

    devices = load_devices()
    picked = pick_real(ids, devices)

    rng = random.Random(SEED)
    synth = [synth_lcd.render_screen(rng.randint(30, 511), rng, (320, 160))
             for _ in range(N_TOTAL)]

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "grid").mkdir(exist_ok=True)

    # 몽타주: 40쌍 전량 — 20행 x ([real|synth] [real|synth]) 2쌍씩.
    def pair(r):
        i, dev, reason = picked[r]
        cap = f"#{r:02d} {normalize_id(ids[i])[-14:]} GT{decode_value(lid[i], int(llen[i]))}"
        left = label_cell(X[i], cap)
        s_img, s_lab = synth[r]
        right = label_cell(s_img, f"synth#{r:02d} {s_lab}")
        return np.hstack([left, np.full((160, 6), 255, np.uint8), right])

    rows = []
    for r in range(0, N_TOTAL, 2):
        vg = np.full((160, 10), 255, np.uint8)
        rows.append(np.hstack([pair(r), vg, pair(r + 1)]))
    sep = np.full((3, rows[0].shape[1]), 255, np.uint8)
    montage = rows[0]
    for row in rows[1:]:
        montage = np.vstack([montage, sep, row])
    p = OUT / "montage_pairs.png"
    cv2.imwrite(str(p), montage)
    print(f"montage {montage.shape} -> {p}", flush=True)

    # 실패 기기 스트립(홀드아웃 전체를 최대 12장까지)
    dev_of = {}
    for i, raw in enumerate(ids):
        dev_of[i] = devices.get(raw) or devices.get(normalize_id(raw))
    for brand, model, variant, _n in FAILED_DEVICES:
        idxs = [i for i in range(len(ids)) if dev_of[i] == (brand, model, variant)]
        sel = idxs[:12]
        cells = [label_cell(X[i], f"{normalize_id(ids[i])[-16:]} GT{decode_value(lid[i], int(llen[i]))}")
                 for i in sel]
        strip = cells[0]
        g = np.full((160, 4), 255, np.uint8)
        for c in cells[1:]:
            strip = np.hstack([strip, g, c])
        slug = f"{brand}_{model}_{variant}".strip("_").replace(" ", "-")
        p = OUT / f"strip_{slug}.png"
        cv2.imwrite(str(p), strip)
        print(f"strip {slug}: {len(sel)}장/{len(idxs)} -> {p}", flush=True)

    # 측정용 격자 시트 — 실사진 40 전량 + 합성 4장
    for n, (i, dev, reason) in enumerate(picked):
        p = OUT / "grid" / f"real_{n:02d}.png"
        cv2.imwrite(str(p), grid_sheet(X[i]))
    for n in (0, 10, 20, 30):
        p = OUT / "grid" / f"synth_{n:02d}.png"
        cv2.imwrite(str(p), grid_sheet(synth[n][0]))
    print(f"grid sheets: {len(picked)} real + 4 synth -> {OUT / 'grid'}", flush=True)

    manifest = {
        "seed": SEED,
        "source_cache": str(CACHE),
        "warp_frame": "320x160 (cache real_holdout_images, GM quad warp)",
        "real": [{"n": n, "idx": i, "id": ids[i], "device": dev, "reason": reason,
                  "gt": decode_value(lid[i], int(llen[i]))}
                 for n, (i, dev, reason) in enumerate(picked)],
        "synth": [{"n": n, "label": s[1]} for n, s in enumerate(synth)],
        "failed_devices_included": [f"{b}/{m}/{v}".strip("/") for b, m, v, _ in FAILED_DEVICES],
    }
    (OUT / "sample_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=1), encoding="utf-8")
    print("manifest ok", flush=True)


if __name__ == "__main__":
    sys.exit(main())
