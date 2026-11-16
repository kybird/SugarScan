# Datacluster 238장 값 라벨러 — 목표축 재판용 정답표 입력 (2026-11-16).
#
# 사람이 쓰는 최소 UI: 이미지를 보고 화면의 값을 숫자로 입력한다.
#   Enter      저장 + 다음
#   X 버튼     판독불가(읽히지 않는 사진에 값을 강제로 만들지 않는다)
#   ←/→        이전/다음(이동만)
# 저장: upstream/datacluster-glucometer-ocr/readings.jsonl (append, id 중복은 최신 우선)
#   {"id": ..., "value": "123" | null, "ts": ...}
# 용도: 측정(재판) 전용 — 학습에 쓰지 않는다(라이선스 정본 2026-11-16 결정).
# 실행: python label238.py  →  http://127.0.0.1:8788
import json
import time
import xml.etree.ElementTree as ET
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1] / "upstream" / "datacluster-glucometer-ocr"
IMG = ROOT / "glucometer_images"
ANN = ROOT / "Annotations" / "Annotations"
OUT = ROOT / "readings.jsonl"


def load_all():
    ids = sorted(p.stem for p in IMG.glob("*.jpg"))
    boxes = {}
    for p in ANN.glob("*.xml"):
        try:
            r = ET.parse(p).getroot()
            b = r.find("object/bndbox")
            sz = r.find("size")
            if b is not None and sz is not None:
                w = float(sz.find("width").text)
                h = float(sz.find("height").text)
                boxes[p.stem] = [float(b.find("xmin").text) / w,
                                 float(b.find("ymin").text) / h,
                                 float(b.find("xmax").text) / w,
                                 float(b.find("ymax").text) / h]
        except Exception:
            pass
    done = {}
    if OUT.exists():
        for l in OUT.read_text(encoding="utf-8").splitlines():
            if l.strip():
                j = json.loads(l)
                done[j["id"]] = j["value"]
    return ids, boxes, done


IDS, BOXES, DONE = load_all()

PAGE = """<!doctype html><html><head><meta charset="utf-8">
<title>238 값 라벨러</title><style>
body{font-family:system-ui;margin:0;background:#111;color:#eee;display:flex;height:100vh}
#left{flex:1;display:flex;align-items:center;justify-content:center;position:relative;background:#000}
#left img{max-height:100vh;max-width:100%;object-fit:contain}
#box{position:absolute;border:2px solid #4f8;pointer-events:none;display:none}
#panel{width:340px;padding:18px;background:#1b1b1b;display:flex;flex-direction:column;gap:10px}
input{font-size:26px;padding:8px;text-align:center}
button{font-size:16px;padding:8px;cursor:pointer}
#prog{font-size:14px;color:#9ab}
#hint{font-size:12px;color:#789;line-height:1.5}
.done{color:#4f8}
</style></head><body>
<div id="left"><img id="img"><div id="box"></div></div>
<div id="panel">
  <div id="prog"></div>
  <div>화면에 보이는 혈당값(mg/dL)을 입력</div>
  <input id="val" autofocus autocomplete="off" inputmode="numeric">
  <button onclick="save(null)">판독불가 (X)</button>
  <button onclick="jump(-1)">&larr; 이전</button>
  <button onclick="jump(1)">다음 &rarr;</button>
  <div id="state"></div>
  <div id="hint">Enter=저장+다음 · 값은 숫자만(예 123) · 읽히지 않는
  사진은 X · 박스(초록)는 기기 위치 — 확대 토글: 이미지 클릭</div>
  <div>완료: <span id="cnt"></span></div>
</div>
<script>
let ids=IDS, i=0, zoom=false;
function find_next(){
  for(let k=0;k<ids.length;k++){const j=(i+1+k)%ids.length;
    if(!(j in DONE))return j}
  return i}
function show(){
  const id=ids[i];
  document.getElementById('img').src='/img/'+id+'.jpg';
  const b=BOXES[id];
  const bx=document.getElementById('box');
  document.getElementById('state').textContent =
    (i in DONE ? '이미 라벨됨: '+(DONE[i]===null?'판독불가':DONE[i]) : '미라벨');
  document.getElementById('state').className = (i in DONE)?'done':'';
  bx.style.display=b?'block':'none';
  // 박스 좌표는 비율 — 이미지 표시 크기에 맞춰 img onload 에 배치
  document.getElementById('img').onload=()=>{
    const im=document.getElementById('img');
    const r=im.getBoundingClientRect(), L=document.getElementById('left').getBoundingClientRect();
    if(!b){bx.style.display='none';return}
    bx.style.display='block';
    bx.style.left=(r.left-L.left+b[0]*r.width)+'px';
    bx.style.top=(r.top-L.top+b[1]*r.height)+'px';
    bx.style.width=((b[2]-b[0])*r.width)+'px';
    bx.style.height=((b[3]-b[1])*r.height)+'px'};
  document.getElementById('val').value = (i in DONE && DONE[i]!==null)?DONE[i]:'';
  document.getElementById('val').focus();
  document.getElementById('prog').textContent = (i+1)+' / '+ids.length+'  '+id;
  document.getElementById('cnt').textContent = Object.keys(DONE).length+' / '+ids.length}
async function save(v){
  const val=v===null?null:(document.getElementById('val').value.trim()||null);
  if(v===null || val!==null){
    const r=await fetch('/api/save?id='+encodeURIComponent(ids[i])+
      '&value='+encodeURIComponent(val===null?'':val),{method:'POST'});
    const j=await r.json(); if(j.ok){DONE[i]=val===''?null:val}}}
  if(v===null || val!==null){i=find_next();show()}else{alert('값을 입력하거나 X')}}
function jump(d){i=(i+d+ids.length)%ids.length;show()}
document.getElementById('val').addEventListener('keydown',e=>{
  if(e.key==='Enter'){e.preventDefault();save(document.getElementById('val').value===''&&e.shiftKey?null:document.getElementById('val').value)}
  if(e.key.toLowerCase()==='x'&&document.activeElement!==document.getElementById('val')){save(null)}});
document.addEventListener('keydown',e=>{
  if(e.key==='ArrowLeft')jump(-1);
  if(e.key==='ArrowRight')jump(1);
  if(e.key.toLowerCase()==='x'){save(null)}});
document.getElementById('img').onclick=()=>{zoom=!zoom;
  document.getElementById('img').style.transform=zoom?'scale(1.8)':'scale(1)';
  document.getElementById('img').style.transition='transform .2s';
  document.getElementById('img').style.transformOrigin='center center'};
show();
</script></body></html>
"""


class H(BaseHTTPRequestHandler):
    def _send(self, code, body, ctype="text/html; charset=utf-8"):
        data = body if isinstance(body, bytes) else body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.path == "/" or self.path.startswith("/?"):
            html = PAGE.replace("IDS", json.dumps(IDS)).replace("BOXES", json.dumps(BOXES)) \
                       .replace("DONE", json.dumps({str(i): DONE.get(id_) for i, id_ in enumerate(IDS)}))
            # DONE 키는 인덱스 — JS 측 {인덱스: 값} 형태로
            self._send(200, html)
        elif self.path.startswith("/img/"):
            p = IMG / (unquote(self.path[5:]))
            if p.exists():
                self._send(200, p.read_bytes(), "image/jpeg")
            else:
                self._send(404, "no")
        elif self.path == "/api/export":
            self._send(200, json.dumps(DONE, ensure_ascii=False), "application/json")
        else:
            self._send(404, "no")

    def do_POST(self):
        if self.path.startswith("/api/save"):
            from urllib.parse import urlparse, parse_qs
            q = parse_qs(urlparse(self.path).query)
            id_ = q["id"][0]
            raw = q.get("value", [""])[0]
            value = int(raw) if raw.isdigit() else None
            with OUT.open("a", encoding="utf-8") as f:
                f.write(json.dumps(dict(id=id_, value=value,
                                        ts=time.strftime("%Y-%m-%d %H:%M:%S")),
                                   ensure_ascii=False) + "\n")
            DONE[id_] = value
            self._send(200, json.dumps({"ok": True, "done": len(DONE)}))
        else:
            self._send(404, "no")

    def log_message(self, *a):
        pass


if __name__ == "__main__":
    print(f"238 값 라벨러 — 이미지 {len(IDS)}장, 기기박스 {len(BOXES)}, "
          f"이미 라벨 {len(DONE)}")
    print("http://127.0.0.1:8788  (종료 Ctrl+C)  저장:", OUT)
    ThreadingHTTPServer(("127.0.0.1", 8788), H).serve_forever()
