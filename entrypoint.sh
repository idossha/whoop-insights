#!/bin/bash
set -e

SYNC_HOUR=${SYNC_HOUR:-11}
SYNC_MINUTE=${SYNC_MINUTE:-0}
TOKENS_FILE=${WHOOP_TOKENS_FILE:-/app/data/tokens.json}

echo "========================================"
echo "Whoop Sync Container Starting"
echo "========================================"
echo "Sync scheduled daily at $SYNC_HOUR:$(printf '%02d' $SYNC_MINUTE)"
echo "Timezone: ${TZ:-UTC}"
echo "Tokens file: $TOKENS_FILE"
echo "========================================"

# Export all environment variables so cron can source them.
# Cron runs in a minimal environment and does NOT inherit container env vars.
env | grep -v -E '^(HOSTNAME|TERM|SHLVL|_)=' > /app/.env.cron 2>/dev/null || true

# Build cron job. Output goes to Docker stdout/stderr via /proc/1/fd/*.
cat > /etc/cron.d/whoop-cron <<CRON_EOF
${SYNC_MINUTE} ${SYNC_HOUR} * * * root cd /app && set -a && . /app/.env.cron && set +a && PYTHONPATH=/app python main.py sync >> /proc/1/fd/1 2>> /proc/1/fd/2
CRON_EOF
chmod 0644 /etc/cron.d/whoop-cron

# Start cron daemon
cron

echo "Cron daemon started. Verifying..."
crontab -l
echo "========================================"

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
