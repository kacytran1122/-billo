FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    BILLO_UPLOADS_DIR=/tmp/billo-uploads \
    PORT=8000

RUN apt-get update \
    && apt-get install --no-install-recommends -y libgl1 libglib2.0-0 libgomp1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY backend/api/requirements.txt /tmp/core-requirements.txt
RUN pip install --no-cache-dir -r /tmp/core-requirements.txt

COPY backend ./backend

RUN useradd --create-home --uid 10001 billo \
    && mkdir -p /tmp/billo-uploads \
    && chown -R billo:billo /tmp/billo-uploads /app

USER billo

EXPOSE 8000

CMD ["sh", "-c", "uvicorn backend.api.app.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers ${WEB_CONCURRENCY:-1}"]
