FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    cron \
    curl \
    build-essential \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p /app/data

COPY crontab /etc/cron.d/whoop-cron
RUN chmod 0644 /etc/cron.d/whoop-cron
RUN crontab /etc/cron.d/whoop-cron

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENV PYTHONPATH=/app

EXPOSE 8501

ENTRYPOINT ["/entrypoint.sh"]
