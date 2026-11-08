FROM python:3.12-slim

WORKDIR /app

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONDONTWRITEBYTECODE=1

COPY packages/gridpulse /app/packages/gridpulse
COPY streamlit-app /app/streamlit-app

RUN pip install --no-cache-dir "/app/packages/gridpulse[ui]" \
    && pip install --no-cache-dir --no-deps /app/streamlit-app \
    && find /usr/local/lib -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true

ENV GRIDPULSE_EVENTS_PATH=/data/events.jsonl
EXPOSE 8501
VOLUME ["/data"]

CMD ["streamlit", "run", "/app/packages/gridpulse/src/gridpulse/ui/app.py", "--server.address", "0.0.0.0", "--server.port", "8501"]
