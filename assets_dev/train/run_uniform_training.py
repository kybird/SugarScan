"""Isolated uniform-value experiment; run with sugartrain Python and -u.

Generation, checks, detector training, predicted crops, reader training, and
offline evaluation run sequentially. A failed stage stops the chain. Restarting
reuses only stages carrying successful completion markers and expected outputs.
Training accuracy and offline evaluation are not live-camera acceptance.
"""
import argparse
import collections
import contextlib
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import traceback

HERE = Path(__file__).resolve().parent
RUN = HERE / "_diag" / "uniform_20261031"
CORPUS = HERE / "synth_coco" / "UNIFORM_20261031"
DET = HERE / "band_out" / "tone" / "uniform_20261031"
DET8000 = DET.with_name(DET.name + "_step8000")
READER = HERE / "reader_out" / "uniform_20261031"
BOXES = RUN / "reader_boxes.jsonl"
RESULT = HERE / "_diag" / "e2e_bandnet" / "uniform_20261031.jsonl"
COUNT, SEED = 30000, 20261031


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n",
                   encoding="utf-8")
    os.replace(tmp, path)


def read_jsonl(path):
    return [json.loads(s) for s in path.read_text(encoding="utf-8").splitlines()
            if s.strip()]


def status(stage, state, **extra):
    write_json(RUN / "status.json", dict(stage=stage, state=state,
               pid=os.getpid(), updated_at=time.strftime("%Y-%m-%dT%H:%M:%S%z"),
               **extra))


def log(message):
    print(f"{time.strftime('%Y-%m-%d %H:%M:%S')} {message}", flush=True)


@contextlib.contextmanager
def run_lock():
    """OS releases this lock even if the parent is terminated."""
    RUN.mkdir(parents=True, exist_ok=True)
    with (RUN / "runner.lock").open("a+b") as handle:
        handle.seek(0)
        if os.name == "nt":
            import msvcrt
            if handle.read(1) == b"":
                handle.write(b"0")
                handle.flush()
            handle.seek(0)
            msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        yield


def prepare():
    import cv2
    import numpy as np
    import torch
    if not torch.cuda.is_available():
        raise RuntimeError("CUDA is required for this experiment")
    sources = ["synth_panel.py", "synth_profiles.py", "synth_lcd.py",
               "device_scene.py", "band_net.py", "train_band.py", "reader_crnn.py",
               "make_reader_boxes.py", "eval_e2e_bandnet.py", Path(__file__).name]
    hashes = {s: hashlib.sha256((HERE / s).read_bytes()).hexdigest() for s in sources}
    config = dict(count=COUNT, seed=SEED, bg="flat", scene="panel",
                  degrade=None, value_range=[30, 599], plan_mode=True,
                  detector=dict(size=640, width=1.5, steps=16000, batch=32,
                                lr=0.002, save_every=2000),
                  reader=dict(epochs=150, batch=32, lr=0.001), source_sha256=hashes)
    config_file = RUN / "config.json"
    if config_file.exists():
        if json.loads(config_file.read_text(encoding="utf-8")) != config:
            raise RuntimeError("Existing experiment config/source hashes differ; refusing reuse")
    else:
        unexpected = [p for p in [CORPUS, DET, READER, BOXES, RESULT]
                      if p.exists()]
        unexpected += list(DET.parent.glob(DET.name + "_step*"))
        if unexpected:
            raise RuntimeError(f"Unexpected existing output: {unexpected}")
        write_json(config_file, config)
    if not (RUN / "provenance.json").exists():
        head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=HERE,
                                       text=True).strip()
        write_json(RUN / "provenance.json", dict(git_head=head,
                   git_status=subprocess.check_output(["git", "status", "--short"],
                                                       cwd=HERE, text=True),
                   python=sys.version, executable=sys.executable,
                   torch=torch.__version__, numpy=np.__version__, cv2=cv2.__version__,
                   cuda=torch.version.cuda, gpu=torch.cuda.get_device_name(0),
                   config_sha256=hashlib.sha256(config_file.read_bytes()).hexdigest()))


def generation():
    import synth_panel as sp
    plan_file = RUN / "plan.jsonl"
    if plan_file.exists():
        rows = read_jsonl(plan_file)
    else:
        rows = sp.build_plan(COUNT, SEED)
        plan_file.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n"
                                     for r in rows), encoding="utf-8")
    if len(rows) != COUNT or any(r["i"] != i or r["id"] != f"panel_{SEED}_{i}"
                                  for i, r in enumerate(rows)):
        raise RuntimeError("Plan count/order/IDs mismatch")
    counts = collections.Counter(r["value"] for r in rows)
    if set(counts) != set(range(30, 600)):
        raise RuntimeError("Plan does not cover every value 30..599")
    bins = []
    for lo, hi in [(30, 100)] + [(i, i + 100) for i in range(100, 600, 100)]:
        n = sum(counts[v] for v in range(lo, hi))
        observed, expected = n / COUNT, (hi - lo) / 570
        if abs(observed - expected) > 0.02:
            raise RuntimeError(f"Plan bin {lo}..{hi-1} exceeds 2pp tolerance")
        bins.append(dict(lo=lo, hi=hi-1, n=n, observed=observed, expected=expected))
    write_json(RUN / "plan_audit.json", dict(n=COUNT, distinct=len(counts), bins=bins,
               value_counts=dict(sorted(counts.items())),
               plan_sha256=hashlib.sha256(plan_file.read_bytes()).hexdigest()))
    log(f"Plan audit passed: {COUNT} rows, {len(counts)} values")
    # Generation is never repeated after its completion marker: COCO conversion
    # relocates files, while generate() resumes exclusively from images/.
    sp.generate(COUNT, SEED, CORPUS, bg="flat", scene="panel", plan_rows=rows)


def validate_coco():
    import cv2
    rows = read_jsonl(CORPUS / "manifest.jsonl")
    plan = {r["id"]: str(r["value"]) for r in read_jsonl(RUN / "plan.jsonl")}
    ids = [r["id"] for r in rows]
    if len(rows) != COUNT or len(set(ids)) != COUNT or set(ids) != set(plan):
        raise RuntimeError("Manifest count/IDs mismatch")
    images, anns = [], []
    image_dir = CORPUS / "images"
    train_dir = CORPUS / "train2017"
    train_dir.mkdir(exist_ok=True)
    for i, r in enumerate(rows, 1):
        if str(r["label"]) != plan[r["id"]]:
            raise RuntimeError(f"Label mismatch: {r['id']}")
        if r["overlaps"] or r["band_clip"]:
            raise RuntimeError(f"Geometry failure: {r['id']}")
        fn = r["id"] + ".png"
        src, dst = image_dir / fn, train_dir / fn
        if src.exists() and dst.exists():
            raise RuntimeError(f"Duplicate image paths: {fn}")
        path = src if src.exists() else dst
        img = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)
        if img is None or img.shape != (r["h"], r["w"]):
            raise RuntimeError(f"Missing/corrupt/image-shape mismatch: {path}")
        x0, y0, x1, y1 = r["box"]
        if not (0 <= x0 < x1 <= r["w"] and 0 <= y0 < y1 <= r["h"]):
            raise RuntimeError(f"Invalid box: {r['id']}")
        if src.exists():
            src.rename(dst)
        images.append(dict(id=i, file_name=fn, width=r["w"], height=r["h"]))
        anns.append(dict(id=i, image_id=i, category_id=1,
                         bbox=[x0, y0, x1-x0, y1-y0], area=(x1-x0)*(y1-y0),
                         iscrowd=0))
        if i % 1000 == 0:
            log(f"Verified {i}/{COUNT} images")
    if list(image_dir.glob("*.png")) or len(list(train_dir.glob("*.png"))) != COUNT:
        raise RuntimeError("Unexpected images remain or train image count differs")
    write_json(CORPUS / "annotations" / "instances_train2017.json",
               dict(images=images, annotations=anns, categories=[dict(id=1, name="band")]))
    write_json(RUN / "corpus_audit.json", dict(n=COUNT, labels_match_plan=True,
               decoded_images=COUNT, overlaps=0, band_clip=0))


def check_boxes():
    rows = read_jsonl(BOXES)
    names = {r["id"] + ".png" for r in read_jsonl(CORPUS / "manifest.jsonl")}
    found = [r["file_name"] for r in rows]
    if not rows or len(set(found)) != len(found) or not set(found) <= names:
        raise RuntimeError("Reader boxes are empty/duplicated/outside corpus")
    for r in rows:
        b = r["pred"]
        if not b or len(b) != 4 or not (b[2] > b[0] and b[3] > b[1]):
            raise RuntimeError("Invalid predicted crop")
    report = dict(total=COUNT, accepted=len(rows), skipped=COUNT-len(rows),
                  coverage=len(rows)/COUNT)
    write_json(RUN / "boxes_audit.json", report)
    log(f"Predicted crop coverage: {report}")


def stage(name, args, outputs):
    marker = RUN / f"{name}.done.json"
    if marker.exists():
        if not all(p.exists() and p.stat().st_size > 0 for p in outputs):
            raise RuntimeError(f"Completed stage {name} has missing/empty output")
        log(f"Skip completed stage {name}")
        return
    status(name, "starting", command=[str(s) for s in args])
    log(f"Start {name}")
    env = dict(os.environ, PYTHONUNBUFFERED="1", PYTHONIOENCODING="utf-8")
    with (RUN / f"{name}.log").open("a", encoding="utf-8") as logfile:
        child = subprocess.Popen([str(s) for s in args], cwd=HERE, env=env,
                                 stdout=logfile, stderr=subprocess.STDOUT)
        status(name, "running", child_pid=child.pid, command=[str(s) for s in args])
        rc = child.wait()
    status(name, "finished" if rc == 0 else "failed", child_pid=child.pid, exit_code=rc)
    if rc != 0:
        raise RuntimeError(f"{name} failed with exit code {rc}; see {name}.log")
    if not all(p.exists() and p.stat().st_size > 0 for p in outputs):
        raise RuntimeError(f"{name} exited 0 but output missing/empty")
    write_json(marker, dict(exit_code=0, outputs=[str(p) for p in outputs]))


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--internal-stage", choices=["generation", "validate_coco", "check_boxes"])
    args = ap.parse_args()
    if args.internal_stage:
        globals()[args.internal_stage]()
        return
    with run_lock():
        try:
            prepare()
            py = [sys.executable, "-u"]
            own = py + [Path(__file__).resolve(), "--internal-stage"]
            stage("01_generation", own + ["generation"],
                  [CORPUS / "manifest.jsonl", RUN / "plan_audit.json"])
            stage("02_validate_coco", own + ["validate_coco"],
                  [CORPUS / "annotations" / "instances_train2017.json", RUN / "corpus_audit.json"])
            stage("03_detector", py + [HERE / "train_band.py", "--data", CORPUS,
                  "--out", DET, "--size", "640", "--width", "1.5", "--steps", "16000",
                  "--batch", "32", "--lr", "0.002", "--save-every", "2000", "--log", "500"],
                  [DET, DET8000])
            stage("04_boxes", py + [HERE / "make_reader_boxes.py", "--set", CORPUS.name,
                  "--ckpt", DET8000, "--out", BOXES], [BOXES])
            stage("05_check_boxes", own + ["check_boxes"], [RUN / "boxes_audit.json"])
            stage("06_reader", py + [HERE / "reader_crnn.py", "train", "--set", CORPUS,
                  "--boxes", BOXES, "--out", READER, "--epochs", "150", "--batch", "32",
                  "--lr", "0.001"], [READER / "best.pt", READER / "last.pt"])
            stage("07_evaluate", py + [HERE / "eval_e2e_bandnet.py", "--ckpt_det", DET8000,
                  "--ckpt_reader", READER / "best.pt", "--tag", "uniform_20261031"], [RESULT])
            status("complete", "complete", exit_code=0,
                   note="Offline evaluation only; live-camera acceptance is pending")
            log("Experiment complete; live-camera acceptance remains pending")
        except BaseException as exc:
            previous = json.loads((RUN / "status.json").read_text(encoding="utf-8")) \
                if (RUN / "status.json").exists() else {}
            status(previous.get("stage", "prepare"), "failed", error=str(exc), exit_code=1)
            traceback.print_exc()
            raise


if __name__ == "__main__":
    main()
