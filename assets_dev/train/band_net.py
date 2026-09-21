# 밴드 검출망 — 우리가 직접 설계한다 (docs/SPEC.md §5.3).
#
# 왜 기성 검출기를 안 쓰는가: 우리 과제는 **장당 물체 1개 · 클래스 1개 · 물체가
# 항상 large** 다(SPEC §8). 범용 검출기의 기계 — 다중 스케일 FPN · NMS · 동적
# 라벨 배정 — 가 전부 과잉이다. 그리고 사전학습을 쓰지 않으므로(§5.3) 구조를
# 남의 체크포인트 모양에 맞출 이유도 없다.
#
# 설계 요지
#   입력   1채널 그레이스케일. 합성기가 이미 1채널로 굽고, 실사진은 추론 때
#          gray 로 바꾼다. 첫 conv 비용이 1/3 이다.
#   출력   특징맵 한 장(단일 스케일). /16 이 기본이고 /8 을 고를 수 있다.
#          ~~stride 8 을 만들지 않는다 — 실측으로 밴드 짧은변이 입력 416 에서
#          실촬 중앙 87px 라 stride 16 에서도 5.4칸을 덮는다~~ → **2026-09-21
#          사람 결정으로 /8 을 허용했다(SPEC §5.3).** 그 실측은 사람 밴드
#          라벨 기준이고 실촬 하위 10~15% 는 /16 격자에서 세로 2.5칸 미만이라
#          성적 절벽이 있다(BAND_EXP_PLAN §21.5). stride 32 는 성기다 — 안 쓴다.
#          다중 스케일 FPN 은 여전히 제외: /8 칸 하나에 검출 헤드를 얹는다.
#   헤드   칸마다 objectness 1 + box 4. box 는 **칸 중심에서 네 변까지의 거리**
#          (l, t, r, b) 다. 절대 좌표를 내면 칸마다 좌표를 외워야 해서 CNN 의
#          평행이동 등변성과 싸운다. 거리는 항상 양수고 국소 정보라 안정적이다.
#   후처리 argmax(objectness). **NMS 가 없다** — 물체가 하나뿐이다.
#   분류   없다. 클래스가 하나뿐이다.
#
# 폭(width)은 인자로 둔다. 온디바이스 예산이 아직 측정 0건이라(SPEC §10)
# 크기를 고정할 근거가 없다 — 스윕으로 고르고 예산이 나오면 다시 본다.
import torch
import torch.nn as nn
import torch.nn.functional as F


def _c(ch, w, lo=8):
    """폭 배수를 적용하고 8의 배수로 맞춘다(채널 정렬이 커널에 유리하다)."""
    return max(lo, int(round(ch * w / 8)) * 8)


class ConvBN(nn.Module):
    def __init__(self, cin, cout, k=3, s=1, g=1):
        super().__init__()
        self.conv = nn.Conv2d(cin, cout, k, s, k // 2, groups=g, bias=False)
        self.bn = nn.BatchNorm2d(cout)
        self.act = nn.SiLU(inplace=True)

    def forward(self, x):
        return self.act(self.bn(self.conv(x)))


class DWBlock(nn.Module):
    """depthwise 3x3 + pointwise 1x1. 채널이 같으면 잔차를 더한다.

    잔차를 쓰는 이유: 스크래치 학습이라 깊이가 곧 최적화 난이도다. 얕은 망이라도
    잔차가 있으면 초기 수렴이 눈에 띄게 안정적이다.
    """

    def __init__(self, ch):
        super().__init__()
        self.dw = ConvBN(ch, ch, 3, 1, g=ch)
        self.pw = ConvBN(ch, ch, 1, 1)

    def forward(self, x):
        return x + self.pw(self.dw(x))


class BandNet(nn.Module):
    def __init__(self, width=1.0, in_ch=1, blocks=(2, 2, 3, 2), stride=16):
        super().__init__()
        if stride not in (8, 16):
            raise ValueError(f"stride 는 8 또는 16 만 지원 — {stride}")
        c1, c2, c3, c4, c5 = (_c(16, width), _c(24, width), _c(48, width),
                              _c(96, width), _c(128, width))
        self.stem = ConvBN(in_ch, c1, 3, 2)                  # /2
        self.s1 = nn.Sequential(ConvBN(c1, c2, 3, 2),        # /4
                                *[DWBlock(c2) for _ in range(blocks[0])])
        self.s2 = nn.Sequential(ConvBN(c2, c3, 3, 2),        # /8
                                *[DWBlock(c3) for _ in range(blocks[1])])
        self.s3 = nn.Sequential(ConvBN(c3, c4, 3, 2),        # /16
                                *[DWBlock(c4) for _ in range(blocks[2])])
        self.s4 = nn.Sequential(ConvBN(c4, c5, 3, 2),        # /32
                                *[DWBlock(c5) for _ in range(blocks[3])])
        # /32 를 /16 으로 올려 더한다 — 큰 물체의 문맥을 헤드에 준다.
        self.lat = ConvBN(c5, c4, 1, 1)
        self.fuse = ConvBN(c4, c4, 3, 1)
        if stride == 8:
            # /8 헤드 — 2026-09-21 사람 결정(SPEC §5.3). /16 맵(그 안에 /32
            # 문맥이 이미 들어 있다)을 한 번 더 올려 s2(/8) 에 더한다. 융합
            # 방식은 /16 헤드가 /32 를 더하는 것과 같은 이치다. 헤드 자체는
            # /16 팔과 동일하다(채널·깊이 그대로).
            self.up2 = ConvBN(c3, c4, 1, 1)
            self.lat2 = ConvBN(c4, c4, 1, 1)
            self.fuse8 = ConvBN(c4, c4, 3, 1)
        self.head = nn.Sequential(ConvBN(c4, c4, 3, 1), ConvBN(c4, c4, 3, 1))
        self.obj = nn.Conv2d(c4, 1, 1)
        self.reg = nn.Conv2d(c4, 4, 1)
        self.stride = stride
        self._init()

    def _init(self):
        for m in self.modules():
            if isinstance(m, nn.Conv2d):
                nn.init.kaiming_normal_(m.weight, mode="fan_out",
                                        nonlinearity="relu")
            elif isinstance(m, nn.BatchNorm2d):
                nn.init.ones_(m.weight); nn.init.zeros_(m.bias)
        # objectness 를 낮은 사전확률로 시작한다. 양성 칸이 전체의 1% 미만이라
        # 0 에서 시작하면 초기 손실이 배경에 끌려간다(focal 논문의 prior trick).
        nn.init.constant_(self.obj.bias, -4.595)   # sigmoid ~= 0.01
        nn.init.zeros_(self.reg.bias)

    def forward(self, x):
        x = self.stem(x)
        x = self.s1(x)
        x2 = self.s2(x)
        p4 = self.s3(x2)
        p5 = self.s4(p4)
        p = self.fuse(p4 + F.interpolate(self.lat(p5), size=p4.shape[-2:],
                                         mode="nearest"))
        if self.stride == 8:
            # 416 + /8 격자는 832 + /16 과 같은 칸 수다(52x52). 백본이 보는
            # 화소는 4분의 1이다.
            p = self.fuse8(self.up2(x2)
                           + F.interpolate(self.lat2(p), size=x2.shape[-2:],
                                           mode="nearest"))
        p = self.head(p)
        # reg 는 **칸 중심에서 네 변까지의 거리**다. 항상 양수여야 하므로 exp 대신
        # softplus 를 쓴다 — exp 는 초기에 발산하기 쉽다.
        return self.obj(p), F.softplus(self.reg(p))


def decode(obj, reg, stride=16):
    """(B,1,H,W), (B,4,H,W) -> (B,4) 상자와 (B,) 점수. argmax 하나만 고른다."""
    B, _, H, W = obj.shape
    flat = obj.view(B, -1)
    idx = flat.argmax(1)
    score = torch.sigmoid(flat.gather(1, idx[:, None]))[:, 0]
    gy = (idx // W).float(); gx = (idx % W).float()
    cx = (gx + 0.5) * stride; cy = (gy + 0.5) * stride
    r = reg.view(B, 4, -1).gather(2, idx[:, None, None].expand(B, 4, 1))[:, :, 0]
    box = torch.stack([cx - r[:, 0], cy - r[:, 1],
                       cx + r[:, 2], cy + r[:, 3]], 1)
    return box, score


if __name__ == "__main__":
    for w in (0.5, 1.0, 2.0):
        m = BandNet(width=w)
        n = sum(p.numel() for p in m.parameters())
        o, _ = m(torch.zeros(1, 1, 416, 416))
        m8 = BandNet(width=w, stride=8)
        n8 = sum(p.numel() for p in m8.parameters())
        o8, _ = m8(torch.zeros(1, 1, 416, 416))
        print(f"width={w:<4} /16 파라미터 {n/1e6:.3f}M 출력 {tuple(o.shape)} · "
              f"/8 파라미터 {n8/1e6:.3f}M 출력 {tuple(o8.shape)}")
