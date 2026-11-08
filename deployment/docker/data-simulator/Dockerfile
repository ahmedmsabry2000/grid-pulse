FROM python:3.12-slim

WORKDIR /app

# Prefer wheels; avoid build-essential unless a dep needs compiling.
ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONDONTWRITEBYTECODE=1

COPY packages/gridpulse /app/packages/gridpulse
COPY data-simulator /app/data-simulator

# pip does not honor uv.sources; install core first, then minirepo without deps.
RUN pip install --no-cache-dir /app/packages/gridpulse \
    && pip install --no-cache-dir --no-deps /app/data-simulator \
    && find /usr/local/lib -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true

ENV GRIDPULSE_EVENTS_PATH=/data/events.jsonl
VOLUME ["/data"]

CMD ["gridpulse-simulate", "--interval", "1", "--inject-rate", "0.1", "--seed", "42"]
