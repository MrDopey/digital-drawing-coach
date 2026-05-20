FROM python:3.12-slim AS builder

ARG VERSION=dev
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /build

COPY pyproject.toml ./
COPY src/ src/
COPY scripts/build_version.py scripts/

RUN pip install --no-cache-dir --upgrade pip && \
    GITHUB_REF_NAME="${VERSION}" python scripts/build_version.py && \
    pip install --no-cache-dir ".[server]"

# ---- runtime ---------------------------------------------------------------
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DRAWING_COACH_HEADLESS=1

WORKDIR /app

COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin/drawing-coach /usr/local/bin/drawing-coach

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/health')"

ENTRYPOINT ["python", "-m", "drawing_coach", "--headless"]
