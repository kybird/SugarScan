# TC+TE 혼합 코퍼스(TX) 구축 — 'TC+TE 혼합 코퍼스로 검출기를 재학습해…' 카드의 자.
#
# 하는 일: TC/TE 의 train2017 이미지를 tc_/te_ 접두를 붙여 TX 로 복사하고,
# 두 곡선 annotation(instances_curve_07998.json)을 image_id 를 재부여해 병합한다.
# 두 코퍼스의 곡선 장 목록이 1:1 로 같다는 것(2026-09-22 확인)이 전제다 —
# 파일명 접두로 구분하므로 같은 이름이 두 번 들어와도 충돌하지 않는다.
#
# 원본 코퍼스는 절대 건드리지 않는다(재생성 금지 — 기존 분포가 대조군).
# 멱등: 결과 검증이 통과하면 다시 돌려도 아무 것도 하지 않는다.
import argparse
import json
import shutil
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = ("TC", "TE")
PREFIX = {"TC": "tc_", "TE": "te_"}
ANN = "instances_curve_07998.json"


def build(dst: Path) -> int:
    train = dst / "train2017"
    train.mkdir(parents=True, exist_ok=True)
    (dst / "annotations").mkdir(parents=True, exist_ok=True)

    merged = {"images": [], "annotations": []}
    next_id = 1
    for src_name in SRC:
        src = HERE / "synth_coco" / src_name
        j = json.loads((src / "annotations" / ANN).read_text(encoding="utf-8"))
        # image_id 재부여 — 두 COCO 의 id 공간이 겹친다(2026-09-22 카드 Note 의
        # 함정). 새 id 를 순서대로 부여하고 annotation 의 image_id 만 다시 잇는다.
        id_map = {}
        for im in j["images"]:
            new_name = PREFIX[src_name] + im["file_name"]
            id_map[im["id"]] = next_id
            merged["images"].append({**im, "id": next_id, "file_name": new_name})
            next_id += 1
        for a in j["annotations"]:
            merged["annotations"].append({**a, "image_id": id_map[a["image_id"]]})
        # 이미지 복사(원본 mtime 보존 — 원본은 불변)
        t0 = time.time()
        n = 0
        for im in j["images"]:
            out = train / (PREFIX[src_name] + im["file_name"])
            if not out.exists():
                shutil.copy2(src / "train2017" / im["file_name"], out)
            n += 1
        print(f"{src_name}: {n}장 복사/확인 ({time.time()-t0:.0f}s)")

    # 검증 — 병합 무결성: 파일이 전부 있고, annotation 이 전부 이미지에 붙었고,
    # 파일명이 유일하다.
    on_disk = {p.name for p in train.glob("*.png")}
    names = [im["file_name"] for im in merged["images"]]
    assert len(names) == len(set(names)), "파일명 중복"
    missing = [n for n in names if n not in on_disk]
    assert not missing, f"이미지 없음 {len(missing)}장: {missing[:3]}"
    ann_ids = {a["image_id"] for a in merged["annotations"]}
    img_ids = {im["id"] for im in merged["images"]}
    assert ann_ids <= img_ids, "annotation 이 이미지 없는 id 를 가리킴"
    assert len(merged["annotations"]) == len(merged["images"]), "장당 1 라벨 아님"

    out_ann = dst / "annotations" / ANN
    out_ann.write_text(json.dumps(merged), encoding="utf-8")
    print(f"병합: 이미지 {len(merged['images'])} · annotation "
          f"{len(merged['annotations'])} -> {out_ann}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dst", default=str(HERE / "synth_coco" / "TX"))
    a = ap.parse_args()
    dst = Path(a.dst)
    done = dst / "annotations" / ANN
    train = dst / "train2017"
    if done.exists() and train.is_dir() and len(list(train.glob("*.png"))) >= 31992:
        print("이미 구축됨 — 검증만 통과하면 넘어간다(멱등)")
    return build(dst)


if __name__ == "__main__":
    raise SystemExit(main())
