FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY backend/fetch.ai/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

COPY backend/fetch.ai ./backend/fetch.ai
COPY backend/observability ./backend/observability

RUN useradd --create-home --uid 10001 billo \
    && chown -R billo:billo /app

USER billo
WORKDIR /app/backend/fetch.ai

CMD ["python", "coordinator.py"]
