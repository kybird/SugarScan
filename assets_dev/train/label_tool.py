# Datumo 라벨링 도구(밴드·LCD 화면 2모드) — 로컬 전용(클라우드 업로드 없음).
#
# 흐름: 모델 예측 박스를 미리 깔아주면 사람이 보정하고 스페이스로 확정·다음.
#   밴드 모드  — 예측 datumo_quads.jsonl  → 산출 labeled.jsonl
#   LCD 모드   — 예측 gmscreen_quads.jsonl → 산출 screen_boxes.jsonl
#
# 실행:  conda run -n sugartrain python label_tool.py
# 조작:
#   1 / 2         모드 전환(밴드 / LCD 화면)
#   마우스 드래그  박스 안=이동, 모서리 근처=크기, 밖에서 드래그=새 박스
#   방향키        박스 이동 / Shift+방향키 크기 조절
#   Z             화면 2배 확대(박스 중심) 토글
#   R             모델 예측으로 되돌림
#   Space/Enter   저장하고 다음 / Backspace 이전
#   D             이 사진은 대상 없음(스킵으로 기록)
#   G             GT 값 수정 (gt_corrections.jsonl에 기록)
#   F2            학습 모니터 (loss 곡선·hold-out 판독)
#
# 산출: {"id", "quad", "source": "human"|"skipped"} — 모드별 파일 위 참조.
import json
import re
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, simpledialog

from PIL import Image, ImageTk

HERE = Path(__file__).resolve().parent
DATUMO = HERE.parent / "upstream" / "datumo"
LABELED = HERE / "labeled.jsonl"          # 밴드 모드 산출
SCREEN_FILE = HERE / "screen_boxes.jsonl"  # LCD 모드 산출
BAND_QUADS = HERE / "datumo_quads.jsonl"   # 밴드 모델 예측
GM_QUADS = HERE / "gmscreen_quads.jsonl"   # LCD 화면 모델 예측
VIEW_W, VIEW_H = 1100, 860
MODES = {
    "band": {"file": LABELED, "quads": BAND_QUADS, "name": "밴드"},
    "lcd": {"file": SCREEN_FILE, "quads": GM_QUADS, "name": "LCD 화면"},
}


class App:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        root.title("Datumo 라벨러 — 밴드(1) / LCD 화면(2)")

        self.readings = self._load_jsonl(DATUMO / "labels.jsonl")
        self.ids = [r["id"] for r in self.readings]
        self.gt = {r["id"]: r["reading"] for r in self.readings}
        # labels.jsonl 의 image 필드는 datumo 기준 전체 상대경로다
        self.img_path = {r["id"]: DATUMO / r["image"] for r in self.readings}
        # 모드별 데이터 — 밴드(labeled.jsonl) / LCD 화면(screen_boxes.jsonl)
        self.mode = "band"
        self.quads_all = {
            m: {j["id"]: j["quad"]
                for j in self._load_jsonl(cfg["quads"])}
            for m, cfg in MODES.items()
        }
        self.labeled_all = {
            m: {j["id"]: j for j in self._load_jsonl(cfg["file"])}
            if cfg["file"].exists() else {}
            for m, cfg in MODES.items()
        }
        self.model_quads = self.quads_all[self.mode]
        self.labeled = self.labeled_all[self.mode]
        # GT 교정 — 원본 labels.jsonl 은 건드리지 않고 별도 기록(출처 추적)
        self.gt_corrections = {
            j["id"]: j for j in self._load_jsonl(HERE / "gt_corrections.jsonl")
        }

        # 내비게이션은 전체 목록 기준 — 라벨된 장도 다시 열어 수정할 수 있어야
        # 한다(Backspace=이전 장 열람). 시작 위치는 첫 미라벨 장.
        # 밴드가 끝나 있으면 LCD 모드로 시작, 둘 다 끝이면 종료.
        for m in MODES:
            if any(cid not in self.labeled_all[m] for cid in self.ids):
                self.mode = m
                break
        else:
            messagebox.showinfo("완료", "모든 이미지에 라벨이 있다.")
            root.after(200, root.destroy)
            return
        self.model_quads = self.quads_all[self.mode]
        self.labeled = self.labeled_all[self.mode]
        self.pos = 0
        while (self.pos < len(self.ids)
               and self.ids[self.pos] in self.labeled):
            self.pos += 1

        self.bar = tk.Label(root, anchor="w", font=("맑은 고딕", 11))
        self.bar.pack(fill="x")
        modef = tk.Frame(root)
        modef.pack(fill="x")
        self.mode_btns = {}
        for m in ("band", "lcd"):
            b = tk.Button(
                modef, text=("① 밴드 (1)" if m == "band" else "② LCD 화면 (2)"),
                command=lambda mm=m: self.set_mode(mm))
            b.pack(side="left", padx=2)
            self.mode_btns[m] = b
        self._style_mode_btns()
        tk.Button(root, text="📈 학습 모니터 (F2)",
                  command=self.open_monitor).pack(fill="x")
        self.canvas = tk.Canvas(root, width=VIEW_W, height=VIEW_H, bg="#222")
        self.canvas.pack()
        self.hint = tk.Label(
            root, anchor="w", justify="left", fg="#555",
            text="1/2:모드전환  드래그:이동/크기/신규  방향키:이동 "
                 "Shift+방향키:크기  Z:2배  R:예측복원  Space:저장·다음  "
                 "Backspace:이전  D:없음스킵  G:GT수정  F2:학습모니터")
        self.hint.pack(fill="x")
        self.canvas.bind("<ButtonPress-1>", self.on_press)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)
        root.bind("<Key>", self.on_key)
        root.bind("<F2>", lambda e: self.open_monitor())

        self.view_s = 1.0
        self.view_ox = 0.0
        self.view_oy = 0.0
        self.box = None  # source 좌표 [x0,y0,x1,y1]
        self.drag = None
        self.tk_img = None
        self._thumb_imgs = []
        self.mon = None
        self.show()

    # ----- 데이터 -----
    @staticmethod
    def _load_jsonl(p: Path):
        if not p.exists():
            return []
        return [
            json.loads(l)
            for l in p.read_text(encoding="utf-8").splitlines()
            if l.strip()
        ]

    def _style_mode_btns(self):
        for m, b in self.mode_btns.items():
            active = m == self.mode
            b.config(relief="sunken" if active else "raised",
                     bg="#d8e8ff" if active else "SystemButtonFace")

    def set_mode(self, m):
        if m == self.mode:
            return
        self.mode = m
        self.model_quads = self.quads_all[m]
        self.labeled = self.labeled_all[m]
        self._zoomed = False
        self.pos = 0
        while (self.pos < len(self.ids)
               and self.ids[self.pos] in self.labeled):
            self.pos += 1
        if self.pos >= len(self.ids):
            self.pos = 0
        self._style_mode_btns()
        self.show()

    def save_current(self, skipped=False):
        cid = self.ids[self.pos]
        if skipped:
            self.labeled[cid] = {"id": cid, "quad": None, "source": "skipped"}
        else:
            if self.box is None:
                return False
            x0, y0, x1, y1 = self.box
            self.labeled[cid] = {
                "id": cid,
                "quad": [[x0, y0], [x1, y0], [x1, y1], [x0, y1]],
                "source": "human",
            }
        with open(MODES[self.mode]["file"], "w", encoding="utf-8") as f:
            for j in self.labeled.values():
                f.write(json.dumps(j, ensure_ascii=False) + "\n")
        return True

    def next_img(self, step=1, skip_labeled=False):
        i = self.pos + step
        if skip_labeled:
            while (0 <= i < len(self.ids)
                   and self.ids[i] in self.labeled):
                i += step
        self.pos = max(0, min(len(self.ids) - 1, i))
        self.show()

    # ----- 표시 -----
    def show(self):
        cid = self.ids[self.pos]
        pil = Image.open(self.img_path[cid])
        pil.load()
        self.src_img = pil.convert("RGB")
        self.src_w, self.src_h = self.src_img.size

        fit = min(VIEW_W / self.src_w, VIEW_H / self.src_h)
        if getattr(self, "_zoomed", False):
            self.view_s = fit * 2
            cx = (self.box[0] + self.box[2]) / 2 if self.box else self.src_w / 2
            cy = (self.box[1] + self.box[3]) / 2 if self.box else self.src_h / 2
            self.view_ox = cx - VIEW_W / (2 * self.view_s)
            self.view_oy = cy - VIEW_H / (2 * self.view_s)
        else:
            self.view_s = fit
            self.view_ox = self.view_oy = 0.0
        self.view_ox = max(0, min(self.src_w - VIEW_W / self.view_s, self.view_ox))
        self.view_oy = max(0, min(self.src_h - VIEW_H / self.view_s, self.view_oy))

        crop = self.src_img.crop((
            int(self.view_ox), int(self.view_oy),
            min(self.src_w, int(self.view_ox + VIEW_W / self.view_s)),
            min(self.src_h, int(self.view_oy + VIEW_H / self.view_s)),
        ))
        crop = crop.resize((max(1, int(crop.width * self.view_s)),
                            max(1, int(crop.height * self.view_s))))
        self.tk_img = ImageTk.PhotoImage(crop)
        self.canvas.delete("all")
        self.canvas.create_image(0, 0, image=self.tk_img, anchor="nw")

        mq = self.model_quads.get(cid)
        if mq:
            pts = [self.to_view(p[0], p[1]) for p in mq]
            self.canvas.create_rectangle(
                pts[0][0], pts[0][1], pts[2][0], pts[2][1],
                outline="#3aa0ff", width=1, dash=(4, 3))

        # 화면 전환마다 박스를 새로 세팅한다 — 이전 장의 박스가 남아 있으면
        # 뒤로 돌았다가 Space 때 잘못된 박스로 기록을 덮어쓴다(실측 버그).
        q = self.labeled.get(cid, {}).get("quad") or mq
        if q:
            xs = [p[0] for p in q]
            ys = [p[1] for p in q]
            self.box = [min(xs), min(ys), max(xs), max(ys)]
        else:
            self.box = None
        if self.box:
            self.draw_box()

        prev = "·" if self.pos == 0 else self.ids[self.pos - 1]
        gt_txt = self.effective_gt(cid)
        if cid in self.gt_corrections:
            gt_txt += "(수정됨)"
        labeled_tag = ("라벨: " + self.labeled[cid]["source"]
                       if cid in self.labeled else "라벨: 없음")
        self.bar.config(text=(
            f"[모드:{MODES[self.mode]['name']}]  "
            f"[{self.pos + 1}/{len(self.ids)}]  {cid}   "
            f"GT: {gt_txt}   "
            f"모델예측: {'있음' if mq else '없음'}   {labeled_tag}   "
            f"누적 라벨: {len(self.labeled)}   뒤 장: {prev}"))

    def effective_gt(self, cid):
        c = self.gt_corrections.get(cid)
        return c["corrected"] if c else self.gt.get(cid)

    def to_view(self, x, y):
        return ((x - self.view_ox) * self.view_s,
                (y - self.view_oy) * self.view_s)

    def to_src(self, vx, vy):
        return (vx / self.view_s + self.view_ox,
                vy / self.view_s + self.view_oy)

    def draw_box(self):
        self.canvas.delete("box")
        x0, y0 = self.to_view(self.box[0], self.box[1])
        x1, y1 = self.to_view(self.box[2], self.box[3])
        self.canvas.create_rectangle(
            x0, y0, x1, y1, outline="#ffd400", width=2, tags="box")
        for hx, hy in ((x0, y0), (x1, y0), (x1, y1), (x0, y1)):
            self.canvas.create_rectangle(
                hx - 4, hy - 4, hx + 4, hy + 4,
                fill="#ffd400", outline="", tags="box")

    # ----- 마우스 -----
    def on_press(self, e):
        if self.box is None:
            x, y = self.to_src(e.x, e.y)
            self.drag = ("new", (x, y))
            self.box = [x, y, x, y]
            return
        x, y = self.to_src(e.x, e.y)
        tol = 8 / self.view_s
        bx0, by0, bx1, by1 = self.box
        near = None
        for name, (hx, hy) in {
            "tl": (bx0, by0), "tr": (bx1, by0),
            "br": (bx1, by1), "bl": (bx0, by1),
        }.items():
            if abs(x - hx) < tol and abs(y - hy) < tol:
                near = name
                break
        if near:
            self.drag = ("resize", near)
        elif bx0 - tol < x < bx1 + tol and by0 - tol < y < by1 + tol:
            self.drag = ("move", (x - bx0, y - by0))
        else:
            self.drag = ("new", (x, y))
            self.box = [x, y, x, y]

    def on_drag(self, e):
        if not self.drag:
            return
        x, y = self.to_src(e.x, e.y)
        kind = self.drag[0]
        if kind == "new":
            self.box[2], self.box[3] = x, y
        elif kind == "move":
            dx, dy = self.drag[1]
            w, h = self.box[2] - self.box[0], self.box[3] - self.box[1]
            self.box = [x - dx, y - dy, x - dx + w, y - dy + h]
        else:
            i = 0 if "l" in kind else 2
            j = 1 if "t" in kind else 3
            self.box[i], self.box[j] = x, y
        self.box[0], self.box[2] = sorted((self.box[0], self.box[2]))
        self.box[1], self.box[3] = sorted((self.box[1], self.box[3]))
        self.draw_box()

    def on_release(self, e):
        if self.drag and self.drag[0] == "new" and self.box:
            self.box[0], self.box[2] = sorted((self.box[0], self.box[2]))
            self.box[1], self.box[3] = sorted((self.box[1], self.box[3]))
            if self.box[2] - self.box[0] < 4 or self.box[3] - self.box[1] < 4:
                self.box = None
        self.drag = None
        self.draw_box()

    # ----- 키보드 -----
    def on_key(self, e):
        if e.keysym == "F2":
            self.open_monitor()
            return
        if e.keysym == "1":
            self.set_mode("band")
            return
        if e.keysym == "2":
            self.set_mode("lcd")
            return
        step = 12 / self.view_s if not (e.state & 0x0001) else 0
        sstep = 12 / self.view_s if (e.state & 0x0001) else 0
        if self.box and e.keysym.startswith(("Left", "Right", "Up", "Down")):
            dx = dy = 0
            if e.keysym == "Left":
                dx = -step
            if e.keysym == "Right":
                dx = step
            if e.keysym == "Up":
                dy = -step
            if e.keysym == "Down":
                dy = step
            self.box[0] += dx
            self.box[2] += dx
            self.box[1] += dy
            self.box[3] += dy
            if sstep:
                self.box[2] += dx
                self.box[3] += dy
            self.draw_box()
            return
        if e.keysym in ("space", "Return"):
            if self.save_current():
                self.next_img(1, skip_labeled=True)
        elif e.keysym == "BackSpace":
            self.next_img(-1)
        elif e.keysym.lower() == "r":
            # 열었을 때의 값으로 복원 — 저장 라벨 우선, 없으면 모델 예측
            cid = self.ids[self.pos]
            q = self.labeled.get(cid, {}).get("quad") or self.model_quads.get(cid)
            if q:
                xs = [p[0] for p in q]
                ys = [p[1] for p in q]
                self.box = [min(xs), min(ys), max(xs), max(ys)]
                self.draw_box()
        elif e.keysym.lower() == "z":
            self._zoomed = not getattr(self, "_zoomed", False)
            self.show()
        elif e.keysym.lower() == "d":
            self.save_current(skipped=True)
            self.next_img(1, skip_labeled=True)
        elif e.keysym.lower() == "g":
            cid = self.ids[self.pos]
            new = simpledialog.askstring(
                "GT 수정",
                f"{cid} 의 표시값 (현재: {self.effective_gt(cid)})",
                initialvalue=str(self.effective_gt(cid) or ""),
                parent=self.root)
            if new is None:
                return
            new = new.strip()
            if not new:
                return
            true_orig = self.gt.get(cid)
            rec = self.gt_corrections.get(cid, {"id": cid, "original": true_orig})
            rec["corrected"] = new
            self.gt_corrections[cid] = rec
            with open(HERE / "gt_corrections.jsonl", "w", encoding="utf-8") as f:
                for j in self.gt_corrections.values():
                    f.write(json.dumps(j, ensure_ascii=False) + "\n")
            self.show()

    # ----- 학습 모니터 (F2) -----
    def open_monitor(self):
        if getattr(self, "mon", None) is not None and self.mon.winfo_exists():
            self.mon.lift()
            return
        self.mon = tk.Toplevel(self.root)
        self.mon.title("학습 모니터 — CTC 리더")
        self.mon.geometry("720x620")
        self.mon_status = tk.Label(self.mon, anchor="w", font=("맑은 고딕", 11))
        self.mon_status.pack(fill="x")
        self.mon_curve = tk.Canvas(self.mon, width=680, height=150, bg="#fafafa")
        self.mon_curve.pack()
        tk.Label(self.mon, text="hold-out 판독 (reader_preds.json)",
                 anchor="w").pack(fill="x")
        self.mon_text = tk.Text(self.mon, height=12, font=("Consolas", 9))
        self.mon_text.pack(fill="both", expand=True)
        tk.Label(self.mon, text="최근 학습 재료 (production 밴드 크롭)",
                 anchor="w").pack(fill="x")
        self.mon_thumbs = tk.Frame(self.mon)
        self.mon_thumbs.pack(fill="x")
        self._thumb_refs = []
        self._refresh_monitor()
        self.mon.after(30000, self._auto_refresh)

    def _auto_refresh(self):
        if getattr(self, "mon", None) is None or not self.mon.winfo_exists():
            return
        try:
            self._refresh_monitor()
        except Exception:
            pass
        self.mon.after(30000, self._auto_refresh)

    def _refresh_monitor(self):
        import datetime
        now = datetime.datetime.now().strftime("%H:%M:%S")
        losses, phase = self._parse_train_log()
        if losses:
            self.mon_status.config(text=(
                f"[{now}] 에폭 {len(losses)} · {phase} · 최신 loss {losses[-1]:.3f}"))
            self._draw_curve(self.mon_curve, losses)
        else:
            self.mon_status.config(text=f"[{now}] 학습 로그 없음")
            self.mon_curve.delete("all")
        self.mon_text.config(state="normal")
        self.mon_text.delete("1.0", "end")
        pj = HERE / "reader_preds.json"
        if pj.exists():
            try:
                preds = json.loads(pj.read_text(encoding="utf-8"))
                ex = sum(1 for v in preds.values() if v[0] == v[1])
                head = (f"exact {ex}/{len(preds)} "
                        f"({100 * ex / max(len(preds), 1):.1f}%)")
                self.mon_text.insert("end", head + chr(10))
                for cid, (s_, g) in sorted(preds.items()):
                    mark = "OK " if s_ == g else "MISS"
                    self.mon_text.insert(
                        "end", f"{mark} {cid}  GT {g}  pred {s_}" + chr(10))
            except Exception as e:
                self.mon_text.insert("end", f"preds 읽기 실패: {e}")
    def _parse_train_log(self):
        log = HERE / "ctc_train_gpu.log"
        if not log.exists():
            return [], ""
        out = []
        raw = log.read_text(encoding="utf-8", errors="ignore")
        raw = re.sub(chr(92) + "x1b" + chr(91) + "0-9;" + chr(92) + "*m", "", raw)
        # val_loss 를 삼키지 않게 단어 경로 차단
        for m in re.finditer(r"(?<![A-Za-z_])loss: ([0-9.]+)", raw):
            out.append(float(m.group(1)))
        if "== real finetune ==" in raw:
            phase = "파인튜닝"
        elif out:
            phase = "사전학습"
        else:
            phase = ""
        return out, phase

    def _draw_curve(self, canvas, losses):
        canvas.delete("all")
        w = int(canvas.winfo_width() or 680)
        h = int(canvas.winfo_height() or 150)
        if len(losses) < 2:
            return
        hi, lo = max(losses), min(losses)
        rng = (hi - lo) or 1.0
        pts = []
        for i, v in enumerate(losses):
            x = 10 + i * (w - 20) / max(1, len(losses) - 1)
            y = 12 + (h - 24) * (1 - (v - lo) / rng)
            pts.extend([x, y])
        canvas.create_line(pts, fill="#c0392b", width=2)
        canvas.create_text(10, 12, anchor="nw", text=f"max {hi:.2f}", fill="#888")
        canvas.create_text(10, h - 14, anchor="nw", text=f"min {lo:.2f}", fill="#888")

    def _refresh_thumbs(self):
        for w in self.mon_thumbs.winfo_children():
            w.destroy()
        crops = HERE / "crops"
        if not crops.exists():
            return
        files = sorted(crops.glob("*.png"), key=lambda p: p.stat().st_mtime,
                       reverse=True)[:10]
        for f in files:
            try:
                im = Image.open(f)
                im.thumbnail((140, 52))
                ref = ImageTk.PhotoImage(im)
                self._thumb_refs.append(ref)
                tk.Label(self.mon_thumbs, image=ref).pack(side="left", padx=2)
            except Exception:
                pass


def main():
    root = tk.Tk()
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
