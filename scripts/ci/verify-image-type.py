#!/usr/bin/env python3

import os
import sys

import torch
import torchvision


def fail(msg: str) -> None:
    raise SystemExit(msg)


def main() -> None:
    device = os.environ.get("DEVICE")
    if device not in {"cpu", "cuda"}:
        fail(f"Unsupported DEVICE={device!r}; expected 'cpu' or 'cuda'")

    torch_ver = torch.__version__
    tv_ver = torchvision.__version__
    cuda_ver = torch.version.cuda

    print(f"device={device}")
    print(f"torch={torch_ver}")
    print(f"torchvision={tv_ver}")
    print(f"torch.version.cuda={cuda_ver}")
    print(f"torch.cuda.is_available={torch.cuda.is_available()}")

    if device == "cpu":
        if cuda_ver is not None:
            fail(f"CPU image should not include CUDA runtime metadata (got {cuda_ver})")
        if "+cpu" not in torch_ver or "+cpu" not in tv_ver:
            fail("CPU image expected +cpu torch/torchvision wheels")
        return

    if not cuda_ver:
        fail("CUDA image expected non-empty torch.version.cuda")
    if "+cu" not in torch_ver or "+cu" not in tv_ver:
        fail("CUDA image expected CUDA-enabled torch/torchvision wheels")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"verification failed: {exc}", file=sys.stderr)
        raise
