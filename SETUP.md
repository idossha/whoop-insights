# Whoop Dashboard Setup Guide

This guide covers three deployment options. Choose based on your system:

| Option | Best For | Requirements |
|--------|----------|--------------|
| **Option 1: Docker (Full)** | 64-bit OS | 64-bit Raspberry Pi OS, macOS, Linux |
| **Option 2: Upgrade to 64-bit** | 32-bit users wanting Docker | Raspberry Pi 3B+ or newer |
| **Option 3: Local/venv** | 32-bit systems | Any system with Python 3.11+ |

---

## Check Your System

Run this command to check if you're on 64-bit or 32-bit:

```bash
uname -m
```

- `aarch64` or `x86_64` = **64-bit** → Use **Option 1**
- `armv7l` or `armv6l` = **32-bit** → Use **Option 2** or **Option 3**

---

## Option 1: Docker Deployment (64-bit OS)

Best for: macOS, Linux desktops, Raspberry Pi with 64-bit OS.

### Prerequisites

- Docker & Docker Compose - [Install Docker](https://docs.docker.com/get-docker/)
- A Whoop account with data
- Git

### Steps

**1. Clone and configure:**

```bash
git clone <your-repo-url>
cd whoop_sync
cp .env.example .env
nano .env  # Add your Whoop API credentials
```

**2. Get Whoop API credentials:**

1. Go to [Whoop Developer Dashboard](https://developer-dashboard.whoop.com/)
2. Create an application with redirect URI: `http://localhost:8080/callback`
3. Copy Client ID and Secret to your `.env` file

**3. Start services:**

```bash
make docker-up          # Pulls image and starts
make docker-auth        # Authenticate (visit URL shown)
make docker-sync        # Initial data sync
```

**4. Access dashboard:**

Open http://localhost:8501

### Common Commands

```bash
make docker-up          # Start services
make docker-down        # Stop services
make docker-pull        # Update to latest image
make docker-logs        # View logs
make docker-auth        # Re-authenticate
make docker-sync        # Sync data
```

---

## Option 2: Upgrade to 64-bit Raspberry Pi OS

If you have a 32-bit OS and want to use Docker, upgrade to 64-bit.

### Compatible Raspberry Pi Models

| Model | 64-bit Support |
|-------|----------------|
| Raspberry Pi 5 | Yes |
| Raspberry Pi 4 | Yes |
| Raspberry Pi 3B+ | Yes |
| Raspberry Pi 3B | Yes |
| Raspberry Pi 3A+ | Yes |
| Raspberry Pi Zero 2 W | Yes |
| Raspberry Pi 2 | No (32-bit only) |
| Raspberry Pi Zero/Zero W | No (32-bit only) |

### Upgrade Steps

**1. Backup your data:**

```bash
# On your Pi, backup these files:
cp ~/.env ~/env-backup
cp -r ~/whoop_sync ~/whoop_sync-backup
```

**2. Download 64-bit Raspberry Pi OS:**

Visit: https://www.raspberrypi.com/software/operating-systems/

Look for **"Raspberry Pi OS with Desktop"** and select **"64-bit"** version.

**3. Flash to SD card:**

Use [Raspberry Pi Imager](https://www.raspberrypi.com/software/):

```bash
# On macOS/Linux
rpi-imager
```

Or with dd:
```bash
# Replace /dev/disk2 with your SD card
sudo dd if=raspberry-pi-os-64bit.img of=/dev/disk2 bs=4M status=progress
```

**4. Boot and setup:**

1. Insert SD card and power on
2. Complete initial setup (timezone, WiFi, etc.)
3. Install Docker:
   ```bash
   curl -fsSL https://get.docker.com | sh
   sudo usermod -aG docker $USER
   # Log out and back in
   ```

**5. Restore your setup:**

```bash
git clone <your-repo-url>
cd whoop_sync
cp ~/env-backup .env
make docker-up
make docker-auth
make docker-sync
```

Then proceed with **Option 1** above.

---

## Option 3: Local/venv Deployment (32-bit Systems)

Run the app directly with Python. Works on any system with Python 3.11+.

### Prerequisites

- Python 3.11 or higher
- pip and venv
- A Whoop account with data

### Steps

**1. Clone and configure:**

```bash
git clone <your-repo-url>
cd whoop_sync
cp .env.example .env
nano .env  # Add your Whoop API credentials
```

**2. Get Whoop API credentials:**

Same as Option 1 - see [Whoop Developer Dashboard](https://developer-dashboard.whoop.com/)

**3. Create virtual environment:**

```bash
make venv-setup
```

This creates a `venv/` directory and installs all dependencies.

**4. Authenticate:**

```bash
make auth
# Or: ./venv/bin/python main.py auth
```

Visit the URL shown in your browser.

**5. Sync data:**

```bash
make sync
```

**6. Run dashboard:**

```bash
make dashboard
```

Open http://localhost:8501

### Common Commands

```bash
make venv-setup     # Create venv and install deps
make auth           # Authenticate
make sync           # Sync data
make dashboard      # Run dashboard
make status         # Check auth status
```

### Run as Systemd Service (Auto-start on boot)

**1. Copy the service file:**

```bash
sudo cp whoop-sync.service /etc/systemd/system/
```

**2. Edit the paths if needed:**

```bash
sudo nano /etc/systemd/system/whoop-sync.service
```

Update `User`, `WorkingDirectory`, and paths to match your setup.

**3. Enable and start:**

```bash
sudo systemctl daemon-reload
sudo systemctl enable whoop-sync
sudo systemctl start whoop-sync
```

**4. Check status:**

```bash
sudo systemctl status whoop-sync
```

### Set Up Daily Sync Cron Job

```bash
# Edit crontab
crontab -e

# Add this line (sync at 6 AM daily)
0 6 * * * cd /home/pi/whoop_sync && ./venv/bin/python main.py sync >> /var/log/whoop-sync.log 2>&1
```

---

## Optional: HTTPS with Caddy (All Options)

For HTTPS access, you can run Caddy as a reverse proxy.

### For Docker (Option 1)

Caddy is included in `docker-compose.yml`. Just configure your domain:

```bash
nano Caddyfile
# Replace YOUR_DOMAIN.com with your actual domain
```

### For Local/venv (Option 3)

Run Caddy separately:

```bash
# Using Docker
docker compose -f docker-compose.lite.yml up -d

# Or install Caddy directly
sudo apt install caddy
```

---

## Sharing Publicly with Tailscale

Share your dashboard with anyone (no Tailscale required for them):

```bash
# Install Tailscale
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up

# Enable public access
tailscale funnel --bg --https=443 http://localhost:8501

# Your URL will be:
# https://<your-machine-name>.tail<id>.ts.net/

# Stop sharing
tailscale funnel --https=443 off
```

---

## Troubleshooting

### Docker: "no matching manifest for linux/arm/v8"

Your Pi is running 32-bit OS. Use **Option 2** (upgrade to 64-bit) or **Option 3** (local/venv).

### Docker: Container keeps restarting

Check logs:
```bash
docker logs whoop-dashboard
```

If empty logs on 32-bit Pi → use Option 3 instead.

### pip install fails on 32-bit

Install build dependencies:
```bash
sudo apt install python3-dev build-essential
make venv-setup
```

### Authentication fails

1. Ensure redirect URI matches exactly: `http://localhost:8080/callback`
2. Check credentials in `.env`
3. Re-authenticate: `make auth` or `make docker-auth`

### Port 8501 already in use

Kill the process:
```bash
lsof -i :8501
kill <PID>
```

Or change the port in the dashboard command:
```bash
./venv/bin/streamlit run dashboard/dashboard.py --server.port 8502
```

---

## Quick Reference

### Option 1 (Docker, 64-bit)

```bash
git clone <repo> && cd whoop_sync
cp .env.example .env && nano .env
make docker-up
make docker-auth
make docker-sync
```

### Option 3 (Local/venv, 32-bit)

```bash
git clone <repo> && cd whoop_sync
cp .env.example .env && nano .env
make venv-setup
make auth
make sync
make dashboard
```

---

## Architecture Comparison

```
Option 1: Docker (64-bit)
┌─────────────────────────────────────────┐
│         Docker Container                 │
│  ┌─────────┐ ┌─────────┐ ┌───────────┐  │
│  │Dashboard│ │ OAuth   │ │  Cron     │  │
│  │ :8501   │ │ :8080   │ │  (sync)   │  │
│  └─────────┘ └─────────┘ └───────────┘  │
└─────────────────────────────────────────┘

Option 3: Local/venv (32-bit)
┌─────────────────────────────────────────┐
│         Local Python (venv)              │
│  ┌─────────┐ ┌─────────┐                │
│  │Dashboard│ │ OAuth   │                │
│  │ :8501   │ │ :8080   │                │
│  └─────────┘ └─────────┘                │
│                                         │
│  Systemd: Auto-start on boot            │
│  Cron: Daily sync                       │
└─────────────────────────────────────────┘

Optional (both options):
┌─────────────────────────────────────────┐
│         Tailscale Funnel                 │
│         https://...ts.net               │
└─────────────────────────────────────────┘
```
