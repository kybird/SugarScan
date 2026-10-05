# 사다리 전환 와처(2026-10-05 사람 지시) — 15,000점 e2e 결과가 나오면:
# 오독 > 121(5,000점 대비 악화 확정)이면 기존 사다리를 중단하고 정밀
# 사다리(fine_ladder_chain)를 띄운다. 그렇지 않으면(회복) 원래 사다리가
# 스스로 20k 로 넘어가게 둔다. 판정 기준과 경위는 로그에 남긴다.
import json
import subprocess
import time
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
P15 = HERE / "_diag" / "e2e_bandnet" / "gen2lad15000.jsonl"
LOG = HERE / "_diag" / "ladder_switch_watcher.log"
ROT = {"1213", "1226", "1564", "1565", "940", "283", "2431"}


def log(msg):
    line = f"{datetime.now():%Y-%m-%d %H:%M:%S}  {msg}"
    print(line, flush=True)
    with LOG.open("a", encoding="utf-8") as f:
        f.write(line + "\n")


log("와처 시작 — gen2lad15000.jsonl 대기(최대 3시간)")
# e2e 는 행마다 증분 기록한다 — 파일 '존재'가 아니라 '완결'(회전·오염 제외
# 후 n>=2505)을 봐야 한다. 1차 판정은 447행(18%) 짜리 부분 파일을 읽어
# "회복"으로 오판했다(우연히 전량 결과와 결론은 같았지만 근거가 무효).
for _ in range(180):
    if P15.exists():
        try:
            got = [json.loads(l) for l in
                   P15.read_text(encoding="utf-8").splitlines() if l.strip()]
        except json.JSONDecodeError:
            got = []
        got = [r for r in got if r["id"].split("/")[-1] not in ROT
               and r.get("verdict") != "skip"]
        if len(got) >= 2505:
            break
    time.sleep(60)
else:
    log("3시간 내 결과 없음 — 와처 종료(사다리는 계속 진행 중이므로 개입 없음)")
    raise SystemExit(0)

rows = [json.loads(l) for l in P15.read_text(encoding="utf-8").splitlines()
        if l.strip()]
rows = [r for r in rows if r["id"].split("/")[-1] not in ROT]
wrong = sum(1 for r in rows if r["verdict"] == "wrong")
n = len(rows)
log(f"15,000점 결과: 오독 {wrong} / n={n} (판정 문턱: 121 초과면 악화 확정)")

if wrong <= 121:
    log("회복 — 원래 사다리 유지, 와처 종료")
    raise SystemExit(0)

log("악화 확정 — 기존 사다리 중단(20k 학습이 막 시작했을 것이므로 "
    "reader_crnn 자식도 함께 종료)")
out = subprocess.check_output(
    ["powershell", "-NoProfile", "-Command",
     "Get-CimInstance Win32_Process -Filter \"Name like '%python%'\" | "
     "Where-Object {$_.CommandLine -match 'reader_ladder_chain|reader_crnn'}"
     " | ForEach-Object { Stop-Process -Id $_.ProcessId -Force; "
     "$_.ProcessId }"], text=True)
log("종료한 PID: " + " ".join(out.split()))
time.sleep(3)
r = subprocess.run(
    ["C:\\Users\\admin\\miniconda3\\envs\\sugartrain\\python.exe",
     str(HERE / "_diag" / "fine_ladder_chain.py")],
    cwd=str(HERE), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    creationflags=subprocess.DETACHED_PROCESS)
log(f"정밀 사다리 기동 rc={r.returncode} — 로그: "
    "_diag/reader_fine_ladder.log")
