FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY packages/gridpulse /app/packages/gridpulse
COPY data-simulator /app/data-simulator

# pip does not honor uv.sources; install core first, then minirepo without deps.
RUN pip install --no-cache-dir /app/packages/gridpulse \
    && pip install --no-cache-dir --no-deps /app/data-simulator

ENV GRIDPULSE_EVENTS_PATH=/data/events.jsonl
VOLUME ["/data"]

CMD ["gridpulse-simulate", "--interval", "1", "--inject-rate", "0.1", "--seed", "42"]
