# GEN10D 입력 감사 보조 — 리더 체크포인트 저장 스칼라만 덤프 (2026-11-19)
# 근거: gen10d-input-audit-20261119.md §5-1 (epoch/acc 외 인자 미기록 확인)
# 사용: conda run -n melotts python _audit_reader_args.py
import torch
for name in ["ps10b_rdr", "ps10d_rdr"]:
    ck = torch.load(f"reader_out/{name}/best.pt", map_location="cpu", weights_only=False)
    if isinstance(ck, dict):
        scal = {k: ck[k] for k in ck if k in ("epoch", "acc")}
        print(name, scal)
