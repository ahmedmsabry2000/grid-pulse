FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY packages/gridpulse /app/packages/gridpulse
COPY streamlit-app /app/streamlit-app

RUN pip install --no-cache-dir "/app/packages/gridpulse[ui]" \
    && pip install --no-cache-dir --no-deps /app/streamlit-app

ENV GRIDPULSE_EVENTS_PATH=/data/events.jsonl
EXPOSE 8501
VOLUME ["/data"]

CMD ["streamlit", "run", "/app/packages/gridpulse/src/gridpulse/ui/app.py", "--server.address", "0.0.0.0", "--server.port", "8501"]
