# Whoop Dashboard

Personal fitness dashboard with automated sync, monitoring, and MLR models for Recovery and HRV prediction.

## Quick Start

```bash
cp .env.example .env   # Add your Whoop API credentials
./scripts/setup.sh     # Deploy
```

See [SETUP.md](SETUP.md) for detailed instructions.

## Features

- **Automated Sync** - Daily data sync at configurable time
- **Interactive Dashboard** - Recovery, sleep, heart rate, workouts
- **MLR Models** - Predict recovery & HRV from sleep, strain, HRV
- **Monitoring** - Grafana dashboards with Prometheus metrics
- **Auto-backup** - 30-day retention database backups
- **HTTPS** - Caddy reverse proxy with auto SSL
- **CI/CD** - GitHub Actions auto-deploy to Raspberry Pi

## Services

| Service | Port | Purpose |
|---------|------|---------|
| Dashboard | 8501 | Streamlit UI |
| Grafana | 3000 | Monitoring |
| Prometheus | 9090 | Metrics |
| Caddy | 80/443 | HTTPS proxy |

## Dashboard Tabs

- **Recovery & Strain** - Daily trends
- **Sleep** - Stages, performance, efficiency  
- **Heart Rate** - Avg, max, RHR, HRV
- **Workouts** - Activity history
- **Insights** - Correlation analysis
- **MLR Recovery** - Predict recovery
- **MLR HRV** - Predict HRV

## Commands

```bash
make setup      # Full Docker setup
make auth       # Authenticate
make sync       # Sync data
make dashboard  # Local development
make docker-up  # Start services
make docker-down# Stop services
```

## Project Structure

```
whoop-dashboard/
├── main.py              # CLI entry
├── dashboard/           # Streamlit app
├── src/whoop_sync/      # Core modules
├── monitoring/          # Prometheus & Grafana
├── scripts/             # Setup & backup
└── docker-compose.yml
```

## License

MIT
