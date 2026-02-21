# Whoop Dashboard Setup Guide

This guide walks you through setting up the Whoop Dashboard from scratch.

---

## Table of Contents

1. [Prerequisites](#1-prerequisites)
2. [Clone the Repository](#2-clone-the-repository)
3. [Get Whoop API Credentials](#3-get-whoop-api-credentials)
4. [Configure Environment](#4-configure-environment)
5. [Run Setup](#5-run-setup)
6. [Authenticate with Whoop](#6-authenticate-with-whoop)
7. [Sync Your Data](#7-sync-your-data)
8. [Access the Dashboard](#8-access-the-dashboard)
9. [Verify Everything Works](#9-verify-everything-works)
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

## 5. Run Setup

Run the setup script:

```bash
chmod +x scripts/setup.sh
./scripts/setup.sh
```

This will:
- Verify your `.env` configuration
- Build the Docker images
- Start all services

Wait for the setup to complete (takes ~1-2 minutes).

---

## 6. Authenticate with Whoop

Authenticate to connect your Whoop account:

```bash
docker compose exec dashboard python main.py auth
```

You'll see output like:

```
Starting authentication flow...
Visit this URL to authenticate:
https://api.prod.whoop.com/oauth/oauth2/auth?response_type=code&client_id=...
```

1. Copy the URL shown
2. Open it in your browser
3. Log in to Whoop and authorize the application
4. You'll be redirected to `localhost:8080/callback` - this is expected
5. The callback URL will show `code=...` - the auth flow captures this automatically
6. Return to your terminal - you should see "Authentication successful!"

> **Note**: Authentication tokens are stored in `tokens.json` and refreshed automatically.

---

## 7. Sync Your Data

Run your first data sync:

```bash
docker compose exec dashboard python main.py sync
```

This will sync:
- Cycles (daily strain/recovery data)
- Recoveries
- Sleeps
- Workouts

The first sync may take a few minutes depending on your data history.

### Full Historical Sync (Optional)

To sync all historical data:

```bash
docker compose exec dashboard python main.py sync --full
```

### Sync Specific Date Range

```bash
docker compose exec dashboard python main.py sync --start 2024-01-01 --end 2024-12-31
```

### Check Database Stats

```bash
docker compose exec dashboard python main.py stats
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

## 9. Verify Everything Works

1. **Check container status:**
   ```bash
   docker compose ps
   ```
   All services should show `running` or `healthy`.

2. **Check logs:**
   ```bash
   docker compose logs dashboard
   ```

3. **Verify data in dashboard:**
   - Open http://localhost:8501
   - You should see your Whoop metrics and charts

4. **Check scheduled sync:**
   - Daily syncs run automatically at the time configured in `SYNC_HOUR`

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

2. **Clone and setup:**
   ```bash
   git clone <your-repo-url>
   cd whoop_sync
   cp .env.example .env
   nano .env  # Add your credentials
   ./scripts/setup.sh
   ```

3. **Configure remote access (optional):**
   ```bash
   nano Caddyfile
   ```
   Replace `YOUR_DOMAIN.com` with your actual domain.

4. **Open ports on your router:**
   - Port 80 (HTTP)
   - Port 443 (HTTPS)

5. **Point your domain** to your Pi's IP address.

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

- Ensure redirect URI in Whoop Developer Dashboard matches exactly: `http://localhost:8080/callback`
- Check that `WHOOP_CLIENT_ID` and `WHOOP_CLIENT_SECRET` are correct in `.env`

### No data appears

1. Run manual sync:
   ```bash
   docker compose exec dashboard python main.py sync
   ```

2. Check database stats:
   ```bash
   docker compose exec dashboard python main.py stats
   ```

### Container won't start

```bash
docker compose logs dashboard
```

### Port conflicts

Edit ports in `docker-compose.yml` if 8501, 3000, or 9090 are in use.

### Token expired

Re-authenticate:
```bash
docker compose exec dashboard python main.py auth
```

---

## 13. Common Commands

### Docker Management

```bash
docker compose up -d              # Start all services
docker compose down               # Stop all services
docker compose logs -f            # View all logs
docker compose logs -f dashboard  # View dashboard logs
docker compose pull && docker compose up -d  # Update images
docker compose restart            # Restart all services
```

### Data Sync

```bash
docker compose exec dashboard python main.py sync          # Incremental sync
docker compose exec dashboard python main.py sync --full   # Full historical sync
docker compose exec dashboard python main.py stats         # Database stats
docker compose exec dashboard python main.py auth          # Re-authenticate
```

### Backup

```bash
docker compose exec dashboard /app/scripts/backup.sh
```

---

## Quick Reference

```bash
# Complete setup from scratch
git clone <repo> && cd whoop_sync
cp .env.example .env && nano .env
./scripts/setup.sh
docker compose exec dashboard python main.py auth
docker compose exec dashboard python main.py sync
```

Dashboard: http://localhost:8501
