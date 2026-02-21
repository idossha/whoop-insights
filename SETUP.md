# Setup Guide

## Prerequisites

- Docker & Docker Compose
- Whoop API credentials (get them at [developer.whoop.com](https://developer-dashboard.whoop.com/))

## Quick Setup

### 1. Get API Credentials

1. Go to [Whoop Developer Dashboard](https://developer-dashboard.whoop.com/)
2. Create a new application
3. Set redirect URI: `http://localhost:8080/callback`
4. Copy Client ID and Secret

### 2. Configure Environment

```bash
cp .env.example .env
```

Edit `.env`:
```
WHOOP_CLIENT_ID=your_client_id
WHOOP_CLIENT_SECRET=your_client_secret
SYNC_HOUR=6              # Daily sync time
TZ=America/New_York      # Your timezone
```

### 3. Deploy

```bash
./scripts/setup.sh
```

### 4. Authenticate & Sync

```bash
docker compose exec dashboard python main.py auth
docker compose exec dashboard python main.py sync
```

## Access

| Service | URL |
|---------|-----|
| Dashboard | http://localhost:8501 |
| Grafana | http://localhost:3000 (admin/admin) |
| Prometheus | http://localhost:9090 |

## Raspberry Pi

Same steps apply. For remote access:

1. Edit `Caddyfile` with your domain
2. Open ports 80 & 443 on your router
3. Point your domain to your Pi's IP

## GitHub Actions (Auto-Deploy)

Add secrets to your GitHub repo:
- `PI_HOST` - Pi IP/domain
- `PI_USER` - SSH username
- `PI_SSH_KEY` - SSH private key
- `PI_DEPLOY_PATH` - Path on Pi (e.g., `/home/pi/whoop-dashboard`)

Pushes to `main` branch will auto-deploy.

## Local Development

```bash
pip install -r requirements.txt
python main.py auth
python main.py sync
streamlit run dashboard/dashboard.py
```

## Common Commands

```bash
# Docker
docker compose up -d        # Start
docker compose down         # Stop
docker compose logs -f      # Logs
docker compose pull && docker compose up -d  # Update

# Manual sync
docker compose exec dashboard python main.py sync

# Full historical sync
docker compose exec dashboard python main.py sync --full

# Backup
docker compose exec dashboard /app/scripts/backup.sh
```

## Troubleshooting

**Auth fails**: Ensure redirect URI matches exactly in Whoop dashboard

**No data**: Run `docker compose exec dashboard python main.py sync`

**Container won't start**: Check logs with `docker compose logs dashboard`

**Port conflicts**: Edit ports in `docker-compose.yml`
