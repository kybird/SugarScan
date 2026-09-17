# numpy 2.x 로 절인 옛 체크포인트를 지금의 sugartrain(numpy 1.23.5)에서 읽게 만든다.
#
# 증상 — YOLOX tools/train.py -c <2026-08-28 체크포인트> 가 즉사한다:
#
#   ModuleNotFoundError: No module named 'numpy._core'
#
# 원인은 모델이 아니라 환경이다. numpy 2.x 는 내부 모듈을 numpy.core 에서
# numpy._core 로 옮겼고, pickle 은 그 모듈 경로를 문자열로 저장한다.
# 2026-09-10 에 TF 2.10 을 살리려고 numpy 를 1.23.5 로 되돌리면서
# (antipatterns/unpinned-pip-in-frozen-training-env) 그 이전에 구운 체크포인트가
# 전부 읽히지 않게 됐다. 가중치는 멀쩡하다 — 경로 이름만 옛것이다.
#
# 그래서 numpy._core 를 numpy.core 로 잇고 한 번 읽어, 지금 numpy 로 다시 절인다.
# 원본은 건드리지 않는다.
#
#   python migrate_ckpt_numpy1.py <입력.pth> <출력.pth>
import sys
from pathlib import Path

import numpy as np
import torch


def install_numpy2_alias():
    """numpy._core.* -> numpy.core.* 로 잇는다. 읽기 전에만 필요하다."""
    if hasattr(np, "_core"):
        return []                      # numpy 2.x 면 할 일이 없다
    import numpy.core
    installed = []
    for suffix in ("", ".multiarray", ".umath", ".numeric", "._multiarray_umath"):
        old, new = f"numpy.core{suffix}", f"numpy._core{suffix}"
        if old in sys.modules and new not in sys.modules:
            sys.modules[new] = sys.modules[old]
            installed.append(new)
    return installed


def main():
    if len(sys.argv) != 3:
        print(__doc__)
        return 2
    src, dst = Path(sys.argv[1]), Path(sys.argv[2])
    assert src.exists(), src
    assert src.resolve() != dst.resolve(), "원본을 덮어쓰지 않는다"

    aliased = install_numpy2_alias()
    print(f"numpy {np.__version__} · 별칭 {aliased or '불필요'}")

    ckpt = torch.load(src, map_location="cpu")
    keys = sorted(ckpt.keys()) if isinstance(ckpt, dict) else type(ckpt).__name__
    print(f"읽음: {src.name} · 최상위 키 {keys}")

    # 메타데이터의 numpy 스칼라를 파이썬 값으로 내린다 — 다시 절일 때
    # numpy 경로가 아예 들어가지 않게 한다.
    if isinstance(ckpt, dict):
        for k, v in list(ckpt.items()):
            if isinstance(v, np.generic):
                ckpt[k] = v.item()
                print(f"      {k}: numpy 스칼라 -> {ckpt[k]!r}")

    dst.parent.mkdir(parents=True, exist_ok=True)
    torch.save(ckpt, dst)
    print(f"저장: {dst} ({dst.stat().st_size:,} 바이트)")

    # 별칭 없이 다시 읽혀야 성공이다.
    for m in aliased:
        del sys.modules[m]
    again = torch.load(dst, map_location="cpu")
    assert isinstance(again, dict) == isinstance(ckpt, dict)
    print("재확인: 별칭 없이 읽힌다 — OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
