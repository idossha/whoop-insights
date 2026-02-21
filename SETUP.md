# Whoop Dashboard Setup Guide

This guide walks you through setting up the Whoop Dashboard from scratch. All operations run inside Docker containers - no local Python setup required.

---

## Table of Contents

1. [Prerequisites](#1-prerequisites)
2. [Clone the Repository](#2-clone-the-repository)
3. [Get Whoop API Credentials](#3-get-whoop-api-credentials)
4. [Configure Environment](#4-configure-environment)
5. [Build and Start Services](#5-build-and-start-services)
6. [Authenticate with Whoop](#6-authenticate-with-whoop)
7. [Sync Your Data](#7-sync-your-data)
8. [Access the Dashboard](#8-access-the-dashboard)
9. [Share Publicly with Tailscale](#9-share-publicly-with-tailscale)
10. [Optional: Raspberry Pi Deployment](#10-optional-raspberry-pi-deployment)
11. [Optional: GitHub Actions Auto-Deploy](#11-optional-github-actions-auto-deploy)
12. [Troubleshooting](#12-troubleshooting)
13. [Common Commands](#13-common-commands)

---

## 1. Prerequisites

Before starting, ensure you have:

- **Docker & Docker Compose** - [Install Docker](https://docs.docker.com/get-docker/)
- **A Whoop account** with data to sync
- **Git** for cloning the repository
- **Tailscale** (optional, for public sharing) - [Install Tailscale](https://tailscale.com/download)

### Verify Docker is installed:

```bash
docker --version
docker compose version
```

---

## 2. Clone the Repository

```bash
git clone <your-repo-url>
cd whoop_sync
```

---

## 3. Get Whoop API Credentials

1. Go to [Whoop Developer Dashboard](https://developer-dashboard.whoop.com/)
2. Sign in with your Whoop account
3. Click **"Create Application"**
4. Fill in the application details:
   - **Name**: `Whoop Dashboard` (or any name you prefer)
   - **Redirect URI**: `http://localhost:8080/callback`
5. Click **"Create"**
6. Copy your **Client ID** and **Client Secret** (save these - you'll need them next)

> **Important**: The redirect URI must match exactly: `http://localhost:8080/callback`

---

## 4. Configure Environment

Create your `.env` file from the template:

```bash
cp .env.example .env
```

Edit `.env` with your credentials:

```bash
nano .env
```

Update these values:

```env
# Whoop API (required - from step 3)
WHOOP_CLIENT_ID=your_actual_client_id_here
WHOOP_CLIENT_SECRET=your_actual_client_secret_here
WHOOP_REDIRECT_URI=http://localhost:8080/callback

# Sync schedule (daily sync time)
SYNC_HOUR=6
SYNC_MINUTE=0

# Your timezone
TZ=America/New_York

# Grafana admin password
GRAFANA_PASSWORD=admin
```

Save and exit (`Ctrl+O`, `Enter`, `Ctrl+X` in nano).

---

## 5. Build and Start Services

Build the Docker image and start all services:

```bash
make docker-build
make docker-up
```

Or manually:

```bash
docker compose build --no-cache
docker compose up -d
```

Wait for the setup to complete (takes ~1-2 minutes). The container will start and show:

```
NOT AUTHENTICATED
==================
Run the following command to authenticate:
  docker exec whoop-dashboard python main.py auth
```

---

## 6. Authenticate with Whoop

Authenticate to connect your Whoop account:

```bash
make docker-auth
```

Or:

```bash
docker exec -it whoop-dashboard python main.py auth
```

You'll see output like:

```
======================================================================
AUTHENTICATION REQUIRED
======================================================================

Visit this URL in your browser to authenticate:

https://api.prod.whoop.com/oauth/oauth2/auth?response_type=code&client_id=...

======================================================================

Waiting for authorization (timeout: 300s)...
```

1. Copy the URL shown
2. Open it in your browser
3. Log in to Whoop and authorize the application
4. You'll be redirected to `localhost:8080/callback` with "Success!" message
5. Return to your terminal - you should see "Authentication successful!"

### Check Authentication Status

```bash
make docker-status
```

Output:

```
Authentication Status:
  Tokens file: /app/data/tokens.json
  Has access token: Yes
  Has refresh token: Yes
  Token expires: 2026-02-21 12:00:00
  Token expired: No
  Token refresh: SUCCESS
```

### Re-Authenticate (if needed)

If your tokens become invalid or revoked:

```bash
make docker-reauth
```

---

## 7. Sync Your Data

Run your first data sync:

```bash
make docker-sync
```

This will sync:
- Profile information
- Body measurements
- Cycles (daily strain/recovery data)
- Recoveries
- Sleeps
- Workouts

The first sync may take a few minutes depending on your data history.

### Full Historical Sync (Optional)

To sync all historical data:

```bash
make docker-sync-full
```

### Sync Specific Date Range

```bash
docker exec whoop-dashboard python main.py sync --start 2024-01-01 --end 2024-12-31
```

### Check Database Stats

```bash
docker exec whoop-dashboard python main.py stats
```

---

## 8. Access the Dashboard

Open your browser and navigate to:

| Service | URL | Credentials |
|---------|-----|-------------|
| **Dashboard** | http://localhost:8501 | None |
| **Grafana** | http://localhost:3000 | admin / admin |
| **Prometheus** | http://localhost:9090 | None |

The main dashboard (Streamlit) displays your Whoop data with charts and metrics.

---

## 9. Share Publicly with Tailscale

Share your dashboard with anyone - they don't need Tailscale installed.

### Prerequisites

1. Install Tailscale: https://tailscale.com/download
2. Sign in to Tailscale
3. Verify it's running: `tailscale status`

### Enable Public Access

```bash
# Enable Tailscale Funnel
tailscale funnel --bg --https=443 http://localhost:8501
```

You'll see output like:

```
Available on the internet:

https://idos-macbook-pro.tail9eb77e.ts.net/
|-- proxy http://localhost:8501

Funnel started and running in the background.
```

### Share the URL

Share the URL shown (e.g., `https://idos-macbook-pro.tail9eb77e.ts.net/`) with anyone. They can access your dashboard without Tailscale.

### Stop Sharing

```bash
tailscale funnel --https=443 off
```

---

## 10. Optional: Raspberry Pi Deployment

Deploy to a Raspberry Pi for always-on monitoring:

### On the Raspberry Pi:

1. **Install Docker:**
   ```bash
   curl -fsSL https://get.docker.com | sh
   sudo usermod -aG docker $USER
   ```
   Log out and back in for group changes to take effect.

2. **Install Tailscale (recommended):**
   ```bash
   curl -fsSL https://tailscale.com/install.sh | sh
   sudo tailscale up
   ```

3. **Clone and setup:**
   ```bash
   git clone <your-repo-url>
   cd whoop_sync
   cp .env.example .env
   nano .env  # Add your credentials
   make docker-build
   make docker-up
   make docker-auth  # Complete authentication
   make docker-sync  # Initial sync
   ```

4. **Enable public access (optional):**
   ```bash
   tailscale funnel --bg --https=443 http://localhost:8501
   ```

---

## 11. Optional: GitHub Actions Auto-Deploy

Automatically deploy to your Raspberry Pi on push to `main`:

### Add GitHub Secrets:

Go to your repo → Settings → Secrets and variables → Actions

| Secret | Description |
|--------|-------------|
| `PI_HOST` | Pi IP address or domain |
| `PI_USER` | SSH username (e.g., `pi`) |
| `PI_SSH_KEY` | SSH private key |
| `PI_DEPLOY_PATH` | Path on Pi (e.g., `/home/pi/whoop_sync`) |

### Generate SSH key (on your machine):

```bash
ssh-keygen -t ed25519 -C "github-actions"
ssh-copy-id -i ~/.ssh/github-actions.pub pi@<PI_IP>
```

Paste the private key into `PI_SSH_KEY` secret.

Pushes to `main` will now auto-deploy.

---

## 12. Troubleshooting

### Authentication fails

1. Ensure redirect URI in Whoop Developer Dashboard matches exactly: `http://localhost:8080/callback`
2. Check that `WHOOP_CLIENT_ID` and `WHOOP_CLIENT_SECRET` are correct in `.env`
3. Try re-authenticating:
   ```bash
   make docker-reauth
   ```

### Token refresh fails

The Whoop API requires `scope` parameter during token refresh. This is handled automatically. If you see refresh errors:

1. Check auth status:
   ```bash
   make docker-status
   ```
2. If refresh test fails, re-authenticate:
   ```bash
   make docker-reauth
   ```

### No data appears

1. Run manual sync:
   ```bash
   make docker-sync
   ```

2. Check database stats:
   ```bash
   docker exec whoop-dashboard python main.py stats
   ```

### Container won't start

```bash
make docker-logs
```

### Port conflicts

Edit ports in `docker-compose.yml` if 8501, 8080, 3000, or 9090 are in use.

### Tailscale Funnel not working

1. Ensure Tailscale is running: `tailscale status`
2. Enable Funnel: visit the URL shown when running `tailscale funnel`
3. Check if port 443 is available

---

## 13. Common Commands

### Docker Management

```bash
make docker-up          # Start all services
make docker-down        # Stop all services
make docker-build       # Rebuild image
make docker-logs        # View dashboard logs
make docker-shell       # Open shell in container
make docker-clean       # Remove containers and volumes (WARNING: deletes data)
```

### Authentication

```bash
make docker-status      # Check auth status
make docker-auth        # Start authentication flow
make docker-reauth      # Re-authenticate (clear old tokens)
```

### Data Sync

```bash
make docker-sync        # Incremental sync
make docker-sync-full   # Full historical sync
docker exec whoop-dashboard python main.py stats  # Database stats
```

### Tailscale / Public Sharing

```bash
# Enable public access
tailscale funnel --bg --https=443 http://localhost:8501

# Check status
tailscale funnel status

# Stop sharing
tailscale funnel --https=443 off
```

---

## Quick Reference

```bash
# Complete setup from scratch
git clone <repo> && cd whoop_sync
cp .env.example .env && nano .env
make docker-build
make docker-up
make docker-auth  # Visit URL shown
make docker-sync

# Access dashboard
open http://localhost:8501

# Share publicly
tailscale funnel --bg --https=443 http://localhost:8501
```

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Docker Container                      │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐  │
│  │ Streamlit   │  │   OAuth     │  │   Cron Job      │  │
│  │ Dashboard   │  │   Callback  │  │   (Daily Sync)  │  │
│  │ :8501       │  │   :8080     │  │                 │  │
│  └─────────────┘  └─────────────┘  └─────────────────┘  │
│                          │                               │
│                          ▼                               │
│  ┌──────────────────────────────────────────────────┐   │
│  │              Docker Volume: whoop-data            │   │
│  │  ┌─────────────┐  ┌─────────────────────────┐    │   │
│  │  │ whoop.db    │  │ tokens.json             │    │   │
│  │  │ (SQLite)    │  │ (OAuth tokens)          │    │   │
│  │  └─────────────┘  └─────────────────────────┘    │   │
│  └──────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
                           │
                           ▼
              ┌────────────────────────┐
              │    Tailscale Funnel    │
              │    (Public Access)     │
              │    https://...ts.net   │
              └────────────────────────┘
```
