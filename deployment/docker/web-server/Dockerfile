FROM python:3.12-slim

WORKDIR /app

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONDONTWRITEBYTECODE=1

COPY packages/gridpulse /app/packages/gridpulse
COPY web-server /app/web-server

RUN pip install --no-cache-dir /app/packages/gridpulse \
    && pip install --no-cache-dir "fastapi>=0.115.0" "uvicorn[standard]>=0.30.0" "websockets>=12.0" \
    && pip install --no-cache-dir --no-deps /app/web-server \
    && find /usr/local/lib -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true

ENV GRIDPULSE_EVENTS_PATH=/data/events.jsonl
EXPOSE 8000
VOLUME ["/data"]

CMD ["uvicorn", "gridpulse_server.app:app", "--host", "0.0.0.0", "--port", "8000"]
