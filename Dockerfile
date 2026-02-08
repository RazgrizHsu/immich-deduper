# syntax = docker/dockerfile:1.5

# Build argument for device selection
ARG DEVICE=cpu

FROM python:3.12-slim-bookworm

WORKDIR /app

ARG DEVICE
ARG DEDUP_PORT=8086
ENV PORT=${DEDUP_PORT}
ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    libimage-exiftool-perl && \
    rm -rf /var/lib/apt/lists/*

# Copy appropriate requirements file based on device
COPY requirements*.txt ./

# Install dependencies based on device type
RUN --mount=type=cache,target=/root/.cache \
    if [ "$DEVICE" = "cpu" ]; then \
        pip install -r requirements-cpu.txt; \
    elif [ "$DEVICE" = "cuda" ]; then \
        pip install -r requirements-cuda.txt; \
    else \
        echo "Unsupported DEVICE=$DEVICE (expected: cpu, cuda)" >&2; exit 1; \
    fi

COPY src/ ./src/

EXPOSE ${PORT}
HEALTHCHECK CMD python -c "import os, urllib.request; urllib.request.urlopen(f'http://127.0.0.1:{os.environ[\"PORT\"]}', timeout=3)" || exit 1

CMD ["python", "-m", "src.app"]
