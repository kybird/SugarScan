# BandNet 연산량(MACs)·파라미터 자 — 8번(416+/8) 비용 보고용. 2026-09-21.
#
# BAND_EXP_PLAN §25.2: "총 연산은 측정해 보고한다". 학습 시간은 데이터로더
# 병목을 포함하므로 배포 비용의 대리물이 못 된다(GPU 사용률 11% 관측).
# 이 자는 Conv2d MACs 만 센다 — 단말 추론 비용의 표준 근사.
#
# MACs = k^2 * (cin/groups) * cout * Hout * Wout. BN·활성화·upsample 무시.
import sys

import torch
import torch.nn as nn

from band_net import BandNet


def macs_of(model, size, stride):
    h = {}

    def hook(m, i, o):
        k = m.kernel_size[0] * m.kernel_size[1]
        h[m] = k * (m.in_channels // m.groups) * m.out_channels * o[0].numel()
    hs = [m.register_forward_hook(hook) for m in model.modules()
          if isinstance(m, nn.Conv2d)]
    with torch.no_grad():
        model(torch.zeros(1, 1, size, size))
    for x in hs:
        x.remove()
    return sum(h.values())


if __name__ == "__main__":
    print(f"{'입력':>5} {'stride':>6} {'격자':>8} {'MACs(M)':>9} {'파라미터(M)':>11}")
    for size, st in ((416, 16), (416, 8), (512, 16), (832, 16)):
        m = BandNet(width=1.0, stride=st).eval()
        n = macs_of(m, size, st)
        p = sum(q.numel() for q in m.parameters())
        print(f"{size:>5} {st:>6} {size//st:>3}x{size//st:<4} "
              f"{n/1e6:>9.1f} {p/1e6:>11.3f}")
