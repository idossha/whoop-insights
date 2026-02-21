#!/bin/bash

SYNC_HOUR=${SYNC_HOUR:-6}
SYNC_MINUTE=${SYNC_MINUTE:-0}

echo "$SYNC_MINUTE $SYNC_HOUR * * * cd /app && python main.py sync >> /var/log/whoop-sync.log 2>&1" > /etc/cron.d/whoop-cron
chmod 0644 /etc/cron.d/whoop-cron
crontab /etc/cron.d/whoop-cron

service cron start

echo "Starting Whoop Dashboard..."
echo "Sync scheduled daily at $SYNC_HOUR:$(printf '%02d' $SYNC_MINUTE)"

cd /app
streamlit run dashboard/dashboard.py --server.port=8501 --server.address=0.0.0.0 --server.headless=true
