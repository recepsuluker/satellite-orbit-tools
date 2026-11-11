# syntax=docker/dockerfile:1
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    SATORBIT_HOME=/data \
    API_HOST=0.0.0.0 \
    STREAMLIT_ADDRESS=0.0.0.0

RUN useradd --create-home --uid 1000 satorbit \
    && mkdir -p /data && chown satorbit:satorbit /data

WORKDIR /app
COPY pyproject.toml README.md LICENSE ./
COPY satorbit ./satorbit
RUN pip install .

USER satorbit
VOLUME ["/data"]
EXPOSE 8000 8001 8501

HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/logs', timeout=4)" || exit 1

# Default: Mission Control dashboard. Override the command to run
# `satorbit api` or `satorbit dashboard` (see docker-compose.yml).
CMD ["satorbit", "mission-control", "--host", "0.0.0.0", "--port", "8000"]
