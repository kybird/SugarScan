# synth_panel 코퍼스를 YOLOX 가 읽는 COCO 형식으로 내보낸다.
#
# 산출: <out>/{A,B,C}/{annotations/instances_train2017.json, train2017/*.png,
#                      manifest.jsonl}  +  <out>/seeds.json
#
# 상자는 매니페스트 quad(워프 후 밴드 쿼드, 캔버스 픽셀)의 축정렬 외접 상자
# 하나뿐이다. 쿼드 펴기·기울기 예측은 이 파이프라인에서 쓰지 않는다 — 검출기는
# 축정렬 사각형만 내놓는다.
#
# 세트별로 시드가 다른 것이 요구사항이다. 같은 시드로 구우면 검출기가 외운 장에
# 추론하게 되고, 그러면 리더가 학습 때 본 상자가 배포 때 받는 상자보다 좋다.
# A=검출기 학습 · B=리더 학습(검출기가 처음 보는 장) · C=끝단 평가.
#
# manifest.jsonl 을 세트 안에 같이 남긴다 — COCO 에는 숫자 라벨이 없고
# 리더 학습(B)·끝단 평가(C)가 그 라벨을 필요로 한다.
import argparse
import json
import shutil
from pathlib import Path

import cv2
import numpy as np

import synth_panel

HERE = Path(__file__).resolve().parent

# 세트 이름: (장수, 시드). 시드는 굽는 날짜에서 따 왔고 과거 코퍼스
# (22000·23000·10000·20000·40000·80000 대)와 겹치지 않는다.
SETS = {
    "A": (1000, 20260916),
    "B": (1000, 20260917),
    "C": (300, 20260918),
    # B2·C2 — 새 렌더러 세대 코퍼스(2026-09-24): 파라메트릭 글리프(58c12cc)
    # · 장면별 잔상(4ef09f3) · 기기 균등 밴드 기하(a82f3db)가 모두 반영된
    # 첫 굽기. B2=리더 학습 · C2=끝단 평가(역할은 B·C 계승, 시드는 신규 —
    # 옛 B·C 의 주석·_annotations 은 계보 기록으로 남긴다).
    "B2": (1000, 20260924),
    "C2": (300, 20260925),
    # A2 — 검출기 학습을 두껍게 하려고 더 구운 학습 세트(2026-09-17).
    # A 900장 25에폭으로는 한계 장이 남았다(세트 B 1000장 중 1장이 conf 0.25
    # 를 못 넘었고, 그 장은 위치는 맞고 신뢰도만 0.19 였다 —
    # diag_synthband_miss.py). 얇아서인지 보려고 5배로 늘린다.
    # **시드는 A·B·C 어느 것과도 겹치지 않는다** — 겹치면 B 가 검출기가 외운
    # 장이 되어 리더가 배포보다 좋은 상자를 본다.
    "A2": (5000, 20260919),
    # A3 — 가로형을 켜고 구운 학습 세트(2026-09-17). A2 와 **장수·설정이 같고**
    # 바뀐 것은 synth_panel.EXCLUDE_WIDE = False 하나다. 두 가지를 동시에
    # 바꾸면 무엇이 움직였는지 못 가른다.
    # 시드는 A·A2·B·C 어느 것과도 겹치지 않는다.
    "A3": (5000, 20260920),
    # ── 소규모 탐침 한 쌍(2026-09-17, 사람 지시) ──────────────────────
    # 물음: **가로형을 배울 수 있기는 한가.** A3(5,000장·가로 13.9%)는 세로형을
    # 무너뜨려 답을 못 줬다. 여기서는 예산을 200장으로 줄이고 가로 비중만
    # 달리한 **한 쌍**을 굽는다.
    #
    # 쌍으로 굽는 이유: 200장 결과를 v2(5,000장)와 견주면 예산이 달라 비교가
    # 성립하지 않는다([[experiment-budget-parity]]). 같은 200장의 세로형 전용
    # 대조군이 있어야 "가로형 때문"과 "200장이라서"를 가른다.
    #
    # 세 번째 값은 가로형 추첨 비중(set_wide_share).
    "P50": (200, 20260921, 0.50),   # 가로:세로 = 50:50 (각 약 100장)
    "P00": (200, 20260922, 0.00),   # 대조군 — 같은 예산, 세로형만

    # S — 규모 곡선의 모(母) 코퍼스(2026-09-17, 사람 지시).
    # 물음: **세로형·가로형 각각 몇 장이면 되는가.** 100/200/400/800/1600/3200
    # 여섯 점을 재는데, 여섯 번 굽지 않고 **한 번 굽고 중첩 부분집합**으로
    # 자른다(build_scaling_sets.py). 각각 다른 시드로 구우면 인접 점의 차이에
    # 시드 잡음이 섞여 곡선의 기울기를 못 믿는다.
    #
    # 7,600 x 0.50 -> 방향별 기대 3,800장. 필요량은 3,200(학습) + 200(공통 val)
    # = 3,400 이라 여유가 있다(이항 표준편차 ~44).
    #
    # 왜 실측 비중(2%)이 아니라 50:50 인가: 그건 분류기 논리다. 검출기는 장마다
    # 물체가 하나라 클래스 사전확률이 없고, 드문 변종을 덜 학습시키면 그냥
    # 덜 배운다. 합성이 공짜인데 일부러 적게 줄 이유가 없다.
    # A3(가로 13.9%)가 실패한 것은 가로형을 **더해서**가 아니라 세로형을
    # 5,000 -> 4,300 으로 **빼앗아서**였다. 여기서는 방향별 장수가 독립이다.
    #
    # 감수하는 것: 가로형 프로파일이 2종(onetouch_ultramini · wide_unknown)
    # 뿐이라 가로형 N장은 기기 1종당 N/2 장이고 세로형은 13종에 N/13 장이다.
    # 가로형 2종의 생김새를 외울 위험이 있으므로 결과를 기기별로도 볼 것.
    "S": (7600, 20260925, 0.50),

    # Z1 — 촬영 배율 난수(CAM_ZOOM_RANGE)의 효과를 재는 탐침(2026-09-17).
    # **P00 이 통제군이다** — 같은 세로형 전용(share 0.00)이고 변경 **전**
    # 코드로 구워졌다. 바뀐 것은 배율 난수·포즈 폭·워프 경계색 셋뿐이다.
    # 재는 것은 성적이 아니라 분포다: measure_panel_stats.py coco 의 선형비 퍼짐.
    "Z1": (400, 20260924, 0.00),

    # ── 코퍼스 크기 곡선 (2026-09-17 사람 지시) ────────────────────────────
    # 물음: **방향별 몇 장이면 되는가.** 모델을 하나로 고정하고(BandNet width 1.0)
    # 장수만 바꾼다. T 를 한 번 굽고 중첩 부분집합으로 자른다 — 세트마다 시드를
    # 달리하면 인접 점의 차이에 시드 잡음이 섞인다.
    #   T  학습 풀. 방향별 8,000 (50:50)
    #   V  검증. **시드가 다르다**(SPEC 9.4) — 학습이 외운 장에서 재면 게이트가
    #      통과를 남발한다.
    "T": (16000, 20261001, 0.50),
    "V": (1000, 20261002, 0.50),

    # ── 단계 2: 절차적 배경 (2026-09-19 사람 결정, SPEC §9.7.2) ──────────
    # TB·VB 는 T·V 와 **시드가 같다.** 보통은 시드 중복을 금지하지만 여기서는
    # 그것이 요구사항이다 — 두 코퍼스가 같은 기기·자세·값·라벨을 갖고 배경만
    # 달라야 "배경만 바꾼 비교"가 된다. 난수 분리는 synth_panel 이 하고
    # (rng 소비 횟수를 안 바꾼다), 일치는 check_bg_parity.py 가 확인한다.
    # 네 번째 값이 배경 종류다.
    "TB": (16000, 20261001, 0.50, "procedural"),
    "VB": (1000, 20261002, 0.50, "procedural"),

    # ── 톤 선언 이후 (2026-09-20) ────────────────────────────────────────
    # TB/VB 와 **시드가 같다.** 배경 밝기 선언(어두움:밝음 = 50:50)만 다르다 —
    # 생성기가 rng 소비를 안 늘리므로 기기·자세·값이 그대로다. 그래서 TB 와
    # TC 를 맞대면 **톤 하나만 바꾼 비교**가 된다.
    "TC": (16000, 20261001, 0.50, "procedural"),
    "VC": (1000, 20261002, 0.50, "procedural"),
    # TD/VD 는 위에 **전체 기기 장면**(몸체·버튼)을 더한다. scene=mixed 는
    # 전체 기기와 기존 크롭을 섞는다 — 실촬에 둘 다 있다.
    "TD": (16000, 20261001, 0.50, "procedural", "mixed"),
    "VD": (1000, 20261002, 0.50, "procedural", "mixed"),

    # ── 생성기 배율·위치 수정 이후 (2026-09-20 사람 선언) ─────────────────
    # TD/VD 와 **시드가 같다.** 생성기가 바뀐 것뿐이다:
    #   CAM_ZOOM_RANGE  (0.25, 1.0) -> (0.10, 1.0)
    #   CAM_OFFCENTER   0(중앙 고정) -> 0.75(남는 여백의 최대 75%까지)
    # 실측(n=150, scene=mixed):
    #   밴드높이/긴변  구판 0.484 -> **0.139** (실촬 0.118)
    #   중심거리      구판 0.058 -> **0.101** (실촬 0.105)
    #   중심y 산포    구판 0.031 -> **0.084** (실촬 0.091)
    # 위치는 **여백 비율**로 정의하므로 밴드가 화면 밖으로 안 나간다(잘림 0장).
    # 구도 축 목표 분포의 정본 근거(2026-09-21 카드 B4): 로보플로우 dev 586 의
    # READING area_frac p10 0.0103 / 중앙 0.0266 / p90 0.0527, 중심거리 중앙
    # 0.169(classify_rf_miss.py — docs/reports/rf-miss-trichotomy-2026-09-21.md).
    "TE": (16000, 20261001, 0.50, "procedural", "mixed"),
    "VE": (1000, 20261002, 0.50, "procedural", "mixed"),
}

CATEGORY = {"id": 1, "name": "glucose_band", "supercategory": "none"}

MIN_SIDE = 8            # 이보다 작은 상자는 학습에 쓸 수 없다 — 하드 실패시킨다


def box_to_bbox(box, w, h):
    """매니페스트 box [x0,y0,x1,y1] → COCO bbox [x, y, w, h].

    생성기가 이미 축정렬 사각형을 정답으로 준다(2026-09-17). 구판은 쿼드를
    받아 여기서 외접상자를 계산했는데, 그러면 정답의 형식이 소비자마다
    달라진다 — 생성기가 하나로 못박는 쪽이 맞다."""
    x0 = float(np.clip(box[0], 0, w - 1))
    y0 = float(np.clip(box[1], 0, h - 1))
    x1 = float(np.clip(box[2], 0, w - 1))
    y1 = float(np.clip(box[3], 0, h - 1))
    return [round(x0, 2), round(y0, 2), round(x1 - x0, 2), round(y1 - y0, 2)]


def build_set(name, count, seed, out_root, wide_share=None, bg="flat",
              scene="panel", degrade_spec=None):
    set_dir = out_root / name
    if set_dir.exists():
        shutil.rmtree(set_dir)
    set_dir.mkdir(parents=True)

    # 가로형 비중은 추첨 가중치로 준다 — 코퍼스를 두 번 굽고 합치지 않는다.
    # 세트가 값을 안 주면 **기본은 50:50** 이다(synth_panel.DEFAULT_WIDE_SHARE,
    # docs/SPEC.md §9.6). 구판은 None 을 넘겨 프로파일 균등(가로 13.3%)이 됐다.
    synth_panel.set_wide_share(
        synth_panel.DEFAULT_WIDE_SHARE if wide_share is None else wide_share)
    # 열화 사슬(2026-09-21 카드) — off 면 기존 코퍼스 바이트 동일 재현.
    synth_panel.generate(count, seed, set_dir, bg=bg, scene=scene,
                         degrade_spec=degrade_spec)
    (set_dir / "images").rename(set_dir / "train2017")

    rows = [json.loads(l) for l in
            (set_dir / "manifest.jsonl").read_text(encoding="utf-8").splitlines()
            if l.strip()]
    assert len(rows) == count, f"{name}: 매니페스트 {len(rows)} != 요청 {count}"

    coco = {
        "info": {"description": f"sugarScan synth panels set {name}",
                 "generator": "synth_panel.py via build_synth_coco.py",
                 "set": name, "seed": seed, "count": count},
        "licenses": [],
        "categories": [CATEGORY],
        "images": [],
        "annotations": [],
    }
    for i, r in enumerate(rows):
        fname = f"{r['id']}.png"
        assert (set_dir / "train2017" / fname).exists(), fname
        bbox = box_to_bbox(r["box"], r["w"], r["h"])
        assert bbox[2] > MIN_SIDE and bbox[3] > MIN_SIDE, (r["id"], bbox)
        coco["images"].append({"id": i, "file_name": fname,
                               "width": r["w"], "height": r["h"]})
        coco["annotations"].append({
            "id": i, "image_id": i, "category_id": CATEGORY["id"],
            "bbox": bbox, "area": round(bbox[2] * bbox[3], 2),
            "iscrowd": 0, "segmentation": [],
        })

    (set_dir / "annotations").mkdir()
    ann_path = set_dir / "annotations" / "instances_train2017.json"
    ann_path.write_text(json.dumps(coco), encoding="utf-8")

    n_img, n_ann = len(coco["images"]), len(coco["annotations"])
    assert n_img == n_ann, f"{name}: 이미지 {n_img} != 어노테이션 {n_ann}"
    print(f"[{name}] seed={seed}  이미지 {n_img}장 / 상자 {n_ann}개 -> {ann_path}")
    return coco


def box_sheet(set_dir, coco, out_png, n=10, cols=5):
    """상자를 원본에 그려 눈으로 확인하는 판. 초록=COCO bbox, 파랑=원본 quad."""
    rows = [json.loads(l) for l in
            (set_dir / "manifest.jsonl").read_text(encoding="utf-8").splitlines()
            if l.strip()]
    step = max(1, len(rows) // n)
    picks = [(rows[i], coco["annotations"][i]) for i in range(0, len(rows), step)][:n]

    cell_w, cell_h = 420, 520
    tiles = []
    for r, a in picks:
        img = cv2.imread(str(set_dir / "train2017" / f"{r['id']}.png"))
        _b = [int(v) for v in r["box"]]
        cv2.rectangle(img, (_b[0], _b[1]), (_b[2], _b[3]), (255, 120, 0), 2)
        x, y, w, h = a["bbox"]
        cv2.rectangle(img, (int(x), int(y)), (int(x + w), int(y + h)),
                      (0, 220, 0), 2)
        cv2.putText(img, r["label"], (6, 26), cv2.FONT_HERSHEY_SIMPLEX,
                    0.8, (0, 220, 0), 2)
        s = min(cell_w / img.shape[1], cell_h / img.shape[0])
        img = cv2.resize(img, (int(img.shape[1] * s), int(img.shape[0] * s)))
        pad = np.zeros((cell_h, cell_w, 3), np.uint8)
        pad[:img.shape[0], :img.shape[1]] = img
        tiles.append(pad)

    grid = [np.hstack(tiles[i:i + cols]) for i in range(0, len(tiles), cols)]
    width = max(g.shape[1] for g in grid)
    grid = [np.pad(g, ((0, 0), (0, width - g.shape[1]), (0, 0))) for g in grid]
    cv2.imwrite(str(out_png), np.vstack(grid))
    print(f"      상자 확인판 {len(picks)}장 -> {out_png}")


def verify(out_root, names):
    """구운 결과를 디스크에서 다시 잰다 — 빌드와 독립한 자.

    세트 간 겹침은 파일명이 아니라 픽셀 해시로 본다. 파일명에 시드가 박혀
    있어서 이름 비교는 시드가 달랐다는 사실만 되풀이하고, 장면이 정말 달라
    졌는지는 말해 주지 않는다.
    """
    import hashlib

    ok = True
    hashes = {}
    for name in names:
        d = out_root / name
        ann = d / "annotations" / "instances_train2017.json"
        j = json.loads(ann.read_text(encoding="utf-8"))
        files = sorted(p.name for p in (d / "train2017").iterdir())
        n_img, n_ann = len(j["images"]), len(j["annotations"])

        checks = {
            "annotations/instances_train2017.json 존재": ann.exists(),
            "어노테이션 수 = 이미지 수": n_img == n_ann,
            "train2017/ 파일 수 = 이미지 수": len(files) == n_img,
            "file_name 전부 실재": {i["file_name"] for i in j["images"]} == set(files),
            "image_id 유일": len({a["image_id"] for a in j["annotations"]}) == n_ann,
            "클래스 하나": len(j["categories"]) == 1,
            "상자가 이미지 안": all(
                a["bbox"][0] >= 0 and a["bbox"][1] >= 0
                and a["bbox"][0] + a["bbox"][2] <= im["width"]
                and a["bbox"][1] + a["bbox"][3] <= im["height"]
                for im, a in zip(j["images"], j["annotations"])),
        }
        print(f"[{name}] seed={j['info']['seed']} 이미지 {n_img} / 상자 {n_ann}")
        for k, v in checks.items():
            print(f"      {'OK ' if v else 'FAIL'} {k}")
            ok &= v
        hashes[name] = {hashlib.md5((d / "train2017" / f).read_bytes()).hexdigest()
                        for f in files}

    seeds = json.loads((out_root / "seeds.json").read_text(encoding="utf-8"))["sets"]
    uniq = len({s["seed"] for s in seeds.values()}) == len(seeds)
    print(f"[시드] {'OK ' if uniq else 'FAIL'} seeds.json 의 시드가 서로 다르다: "
          f"{ {k: v['seed'] for k, v in seeds.items()} }")
    ok &= uniq
    for a in names:
        for b in names:
            if a < b:
                n = len(hashes[a] & hashes[b])
                print(f"[겹침] {'OK ' if n == 0 else 'FAIL'} {a}∩{b} 동일 픽셀 {n}장")
                ok &= n == 0
    print("VERIFY PASS" if ok else "VERIFY FAIL")
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(HERE / "synth_coco"))
    ap.add_argument("--sets", default="A,B,C")
    ap.add_argument("--sheet-n", type=int, default=10)
    ap.add_argument("--verify", action="store_true",
                    help="굽지 않고 이미 구운 결과만 검사한다")
    ap.add_argument("--degrade", default="off",
                    help="열화 사슬을 모든 세트에 적용 — synth_panel.py 의 "
                         "형식(blur=…,noise=…,jpeg=…). off 면 기존 재현.")
    args = ap.parse_args()

    out_root = Path(args.out)
    names = [s.strip() for s in args.sets.split(",") if s.strip()]
    if args.verify:
        return verify(out_root, names)

    out_root.mkdir(parents=True, exist_ok=True)

    seeds = {}
    for name in names:
        spec = SETS[name]
        count, seed = spec[0], spec[1]
        share = spec[2] if len(spec) > 2 else None
        bg = spec[3] if len(spec) > 3 else "flat"
        scene = spec[4] if len(spec) > 4 else "panel"
        # 배경만 다른 짝(T/TB, V/VB)은 **시드가 같아야** 한다. 그 외에는
        # 겹치면 검출기가 외운 장에 추론하게 되므로 계속 막는다.
        if bg == "flat":
            assert seed not in seeds.values(), f"시드 중복: {name}"
        coco = build_set(name, count, seed, out_root, share, bg, scene,
                         synth_panel.parse_degrade(args.degrade))
        seeds[name] = seed
        box_sheet(out_root / name, coco, out_root / f"{name}_boxcheck.png",
                  n=args.sheet_n)

    seed_path = out_root / "seeds.json"
    seed_path.write_text(json.dumps(
        {"sets": {n: {"count": SETS[n][0], "seed": SETS[n][1]} for n in names},
         "note": "세트마다 다른 시드 — B 는 A 로 학습한 검출기가 처음 보는 장이어야 "
                 "리더가 배포와 같은 품질의 상자를 본다."},
        ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"시드 기록 -> {seed_path}: {seeds}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
