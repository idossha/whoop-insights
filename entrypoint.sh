#!/bin/bash
set -e

SYNC_HOUR=${SYNC_HOUR:-6}
SYNC_MINUTE=${SYNC_MINUTE:-0}
TOKENS_FILE=${WHOOP_TOKENS_FILE:-/app/data/tokens.json}

echo "========================================"
echo "Whoop Sync Container Starting"
echo "========================================"
echo "Sync scheduled daily at $SYNC_HOUR:$(printf '%02d' $SYNC_MINUTE)"
echo "Timezone: ${TZ:-UTC}"
echo "Tokens file: $TOKENS_FILE"
echo "========================================"

mkdir -p /var/log

echo "$SYNC_MINUTE $SYNC_HOUR * * * cd /app && python main.py sync >> /var/log/whoop-sync.log 2>&1" > /etc/cron.d/whoop-cron
chmod 0644 /etc/cron.d/whoop-cron
crontab /etc/cron.d/whoop-cron

service cron start

echo ""
echo "Checking authentication status..."
if [ -f "$TOKENS_FILE" ]; then
    echo "Tokens file found. Checking validity..."
    cd /app && python main.py status
else
    echo ""
    echo "NOT AUTHENTICATED"
    echo "=================="
    echo "Run the following command to authenticate:"
    echo "  docker exec whoop-dashboard python main.py auth"
    echo ""
    echo "Then visit the URL shown in your browser to complete authentication."
    echo ""
fi

echo ""
echo "Starting Whoop Dashboard on http://localhost:8501"
echo "Starting Auth Callback Server on http://localhost:8080"
echo ""

cd /app
exec streamlit run dashboard/dashboard.py --server.port=8501 --server.address=0.0.0.0 --server.headless=true
