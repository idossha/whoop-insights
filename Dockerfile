FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    cron \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/
COPY main.py .
COPY dashboard/ ./dashboard/
COPY crontab .
COPY entrypoint.sh /entrypoint.sh

RUN mkdir -p /app/data && \
    chmod 0644 crontab && \
    crontab crontab && \
    chmod +x /entrypoint.sh

ENV PYTHONPATH=/app

EXPOSE 8501 8080

ENTRYPOINT ["/entrypoint.sh"]
