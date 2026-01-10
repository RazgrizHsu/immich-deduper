# syntax = docker/dockerfile:1.5

# Build argument for device selection
ARG DEVICE=cpu

FROM python:3.12

WORKDIR /app

ARG DEDUP_PORT=8086
ENV PORT=${DEDUP_PORT}

RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

# Copy appropriate requirements file based on device
COPY requirements*.txt ./

# Install dependencies based on device type
RUN --mount=type=cache,target=/root/.cache \
    if [ "$DEVICE" = "cuda" ]; then \
        pip install -r requirements-cuda.txt; \
    else \
        pip install -r requirements.txt; \
    fi && \
    pip cache purge

COPY src/ ./src/

EXPOSE ${PORT}
HEALTHCHECK CMD curl -f http://127.0.0.1:${PORT} || exit 1

CMD ["python", "-m", "src.app"]
