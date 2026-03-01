# Whoop Dashboard Setup Guide

## Requirements

- **64-bit OS** (macOS, Linux, Raspberry Pi OS 64-bit)
- Docker & Docker Compose
- A Whoop account
- Git

### Check Your System

```bash
uname -m
```

- `aarch64` or `x86_64` = **64-bit** ✓ Proceed with setup
- `armv7l` or `armv6l` = **32-bit** ✗ See [Upgrading to 64-bit](#upgrading-to-64-bit-raspberry-pi-os)

---

## Quick Start

**1. Clone and configure:**

```bash
git clone <your-repo-url>
cd whoop_sync
cp .env.example .env
nano .env
```

**2. Get Whoop API credentials:**

1. Go to [Whoop Developer Dashboard](https://developer-dashboard.whoop.com/)
2. Create an application with redirect URI: `http://localhost:8080/callback`
3. Copy Client ID and Secret to your `.env` file

**3. Start and authenticate:**

```bash
make docker-up      # Pulls image, starts services
make docker-auth    # Visit URL shown in browser
make docker-sync    # Initial data sync
```

**4. Access dashboard:**

Open http://localhost:8501

---

## Detailed Setup

### 1. Prerequisites

Install Docker:

```bash
# macOS
brew install --cask docker

# Linux / Raspberry Pi
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
# Log out and back in
```

Verify:

```bash
docker --version
docker compose version
```

### 2. Clone Repository

```bash
git clone <your-repo-url>
cd whoop_sync
```

### 3. Get Whoop API Credentials

1. Go to [Whoop Developer Dashboard](https://developer-dashboard.whoop.com/)
2. Sign in with your Whoop account
3. Click **"Create Application"**
4. Fill in:
   - **Name**: `Whoop Dashboard`
   - **Redirect URI**: `http://localhost:8080/callback`
5. Click **"Create"**
6. Copy **Client ID** and **Client Secret**

> **Important**: The redirect URI must match exactly: `http://localhost:8080/callback`

### 4. Configure Environment

```bash
cp .env.example .env
nano .env
```

Update:

```env
WHOOP_CLIENT_ID=your_client_id_here
WHOOP_CLIENT_SECRET=your_client_secret_here
WHOOP_REDIRECT_URI=http://localhost:8080/callback

SYNC_HOUR=6
SYNC_MINUTE=0

TZ=America/New_York
```

### 5. Start Services

```bash
make docker-up
```

This pulls `idossha/whoop-sync:latest` from Docker Hub.

### 6. Authenticate

```bash
make docker-auth
```

1. Copy the URL shown
2. Open in browser
3. Authorize with Whoop
4. You'll see "Success!" when done

### 7. Sync Data

```bash
make docker-sync
```

First sync may take a few minutes depending on data history.

### 8. Access Dashboard

Open http://localhost:8501

---

## Common Commands

```bash
make docker-up          # Start services
make docker-down        # Stop services
make docker-pull        # Update to latest image
make docker-logs        # View logs
make docker-shell       # Open shell in container

make docker-auth        # Authenticate
make docker-reauth      # Re-authenticate (clear old tokens)
make docker-status      # Check auth status

make docker-sync        # Sync data
make docker-sync-full   # Full historical sync
```

---

## Upgrading to 64-bit Raspberry Pi OS

If you're on 32-bit Raspberry Pi OS, you need to upgrade to use this dashboard.

### Compatible Raspberry Pi Models

| Model | 64-bit Support |
|-------|----------------|
| Raspberry Pi 5 | ✓ Yes |
| Raspberry Pi 4 | ✓ Yes |
| Raspberry Pi 3B+ | ✓ Yes |
| Raspberry Pi 3B | ✓ Yes |
| Raspberry Pi 3A+ | ✓ Yes |
| Raspberry Pi Zero 2 W | ✓ Yes |
| Raspberry Pi 2 | ✗ No |
| Raspberry Pi Zero/Zero W | ✗ No |

### Upgrade Steps

**1. Backup your data:**

```bash
cp ~/.env ~/env-backup
```

**2. Download 64-bit Raspberry Pi OS:**

Visit: https://www.raspberrypi.com/software/operating-systems/

Select **"Raspberry Pi OS with Desktop"** - **"64-bit"** version.

**3. Flash to SD card:**

Use [Raspberry Pi Imager](https://www.raspberrypi.com/software/).

**4. Boot and setup:**

1. Insert SD card and power on
2. Complete initial setup
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

---

## Sharing with Tailscale

### Option 1: Tailnet Only (Private)

Share with people you've added to your Tailscale network:

```bash
# Install Tailscale
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up

# Share your Tailscale IP with tailnet members
# Access at: http://<your-tailscale-ip>:8501
```

To find your Tailscale IP: `tailscale ip -4`

### Option 2: Tailscale Funnel (Public)

Share publicly with anyone - they don't need Tailscale:

```bash
# Install Tailscale
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up

# Enable Funnel on your tailnet (one-time setup)
# Go to: https://login.tailscale.com/admin/dns/funnel

# Start Funnel (runs in background)
tailscale funnel --bg --https=443 http://localhost:8501

# Your public URL: https://<machine-name>.tail<id>.ts.net/
```

**Funnel commands:**
```bash
# View active funnels
tailscale funnel status

# Stop sharing
tailscale funnel --https=443 off
```

### Security Note

The dashboard is read-only. Here's what sharing exposes:

**What others CAN see:**
- Recovery, sleep, HRV, workout history
- Personal fitness patterns and trends

**What others CANNOT access:**
- Your Whoop account or credentials
- API tokens (stored securely inside container)
- Ability to modify or delete data
- Any other services on your machine

The only real risk is **privacy** - your fitness data becomes visible. This is uncomfortable but not dangerous for most people.

If you're okay sharing fitness data, Funnel is safe to use. Turn it off when done:

```bash
tailscale funnel --https=443 off
```

---

## Troubleshooting

### "no matching manifest for linux/arm/v8"

You're on 32-bit OS. Upgrade to 64-bit Raspberry Pi OS (see above).

### Container keeps restarting

```bash
docker logs whoop-dashboard
```

### Authentication fails

1. Ensure redirect URI matches: `http://localhost:8080/callback`
2. Check credentials in `.env`
3. Re-authenticate: `make docker-reauth`

### Authenticating from a remote server (Raspberry Pi / headless)

The auth callback goes to `localhost:8080` — which is the **server**, not your laptop. After login, your browser tries to reach your laptop's port 8080 and fails.

**Fix: SSH tunnel**

On your local machine, open a tunnel before authenticating:

```bash
ssh -L 8080:localhost:8080 <user>@<server-ip-or-hostname>
```

Keep that session open, then in another terminal run:

```bash
make docker-reauth
```

Open the URL it prints in your **local browser**. When Whoop redirects to `localhost:8080/callback`, the tunnel forwards it to the server automatically.
 

### No data appears

```bash
make docker-sync
docker exec whoop-dashboard python main.py stats
```

### Port conflicts

Edit ports in `docker-compose.yml` if 8501 or 8080 are in use.

