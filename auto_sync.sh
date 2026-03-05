#!/bin/bash
# =============================================================================
# auto_sync.sh - Automatic daily Whoop data sync for local (non-Docker) usage
# =============================================================================
#
# This script can be run manually, from a user crontab, or from macOS launchd.
# It handles:
#   - Loading environment variables from .env
#   - Token refresh (automatic via the sync command)
#   - Logging with timestamps
#   - Exit code reporting
#
# Usage:
#   ./auto_sync.sh              # Run sync now
#   ./auto_sync.sh --status     # Check auth status only
#   ./auto_sync.sh --full       # Full historical sync
#
# To add to your crontab (runs daily at 11:00 AM):
#   crontab -e
#   0 11 * * * /Users/idohaber/01_production/whoop_insights/auto_sync.sh >> /tmp/whoop-sync.log 2>&1
#
# =============================================================================

set -euo pipefail

# Resolve the project directory (where this script lives)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="${SCRIPT_DIR}"
LOG_DIR="${PROJECT_DIR}/logs"
LOG_FILE="${LOG_DIR}/sync.log"

# Create logs directory
mkdir -p "${LOG_DIR}"

# Rotate log if it exceeds 5MB
MAX_LOG_SIZE=5242880
if [ -f "${LOG_FILE}" ] && [ "$(stat -f%z "${LOG_FILE}" 2>/dev/null || stat -c%s "${LOG_FILE}" 2>/dev/null || echo 0)" -gt "${MAX_LOG_SIZE}" ]; then
    mv "${LOG_FILE}" "${LOG_FILE}.old"
fi

# Logging helper
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "${LOG_FILE}"
}

log_error() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ERROR: $*" | tee -a "${LOG_FILE}" >&2
}

# Load environment variables from .env file
load_env() {
    local env_file="${PROJECT_DIR}/.env"
    if [ -f "${env_file}" ]; then
        log "Loading environment from ${env_file}"
        set -a
        # Source .env but skip comments and empty lines
        while IFS='=' read -r key value; do
            # Skip comments and empty lines
            [[ "${key}" =~ ^[[:space:]]*# ]] && continue
            [[ -z "${key}" ]] && continue
            # Remove surrounding quotes from value
            value="${value%\"}"
            value="${value#\"}"
            value="${value%\'}"
            value="${value#\'}"
            export "${key}=${value}"
        done < "${env_file}"
        set +a
    else
        log "WARNING: No .env file found at ${env_file}"
        log "Make sure WHOOP_CLIENT_ID and WHOOP_CLIENT_SECRET are set in your environment"
    fi
}

# Validate required environment
check_env() {
    if [ -z "${WHOOP_CLIENT_ID:-}" ] || [ -z "${WHOOP_CLIENT_SECRET:-}" ]; then
        log_error "WHOOP_CLIENT_ID and WHOOP_CLIENT_SECRET must be set"
        log_error "Copy .env.example to .env and fill in your credentials"
        exit 1
    fi
}

# Check for Python and required packages
check_dependencies() {
    if ! command -v python3 &>/dev/null && ! command -v python &>/dev/null; then
        log_error "Python not found. Please install Python 3.11+"
        exit 1
    fi

    # Use python3 if available, else python
    PYTHON=$(command -v python3 || command -v python)
    log "Using Python: ${PYTHON}"
}

# Main sync function
run_sync() {
    local extra_args=("$@")

    log "========================================="
    log "Starting Whoop sync"
    log "Project: ${PROJECT_DIR}"
    log "========================================="

    cd "${PROJECT_DIR}"
    load_env
    check_env
    check_dependencies

    # Set PYTHONPATH so imports work
    export PYTHONPATH="${PROJECT_DIR}"

    # Run the sync
    log "Running: ${PYTHON} main.py sync ${extra_args[*]:-}"
    if ${PYTHON} main.py sync "${extra_args[@]}" 2>&1 | tee -a "${LOG_FILE}"; then
        log "Sync completed successfully"
        exit 0
    else
        local exit_code=$?
        log_error "Sync failed with exit code ${exit_code}"
        exit ${exit_code}
    fi
}

# Status check function
run_status() {
    cd "${PROJECT_DIR}"
    load_env
    check_env
    check_dependencies

    export PYTHONPATH="${PROJECT_DIR}"
    ${PYTHON} main.py status 2>&1 | tee -a "${LOG_FILE}"
}

# Parse arguments
case "${1:-}" in
    --status)
        run_status
        ;;
    --full)
        shift
        run_sync --full "$@"
        ;;
    --help|-h)
        echo "Usage: $0 [--status|--full|--help]"
        echo ""
        echo "  (no args)   Run incremental sync"
        echo "  --status    Check authentication status"
        echo "  --full      Run full historical sync"
        echo "  --help      Show this help"
        exit 0
        ;;
    *)
        run_sync "$@"
        ;;
esac
