# Whoop Dashboard

Personal fitness dashboard with automated sync and MLR models for Recovery and HRV prediction.

## Quick Start

```bash
cp .env.example .env    # Add your Whoop API credentials
make docker-build       # Build the Docker image
make docker-up          # Start services
make docker-auth        # Authenticate (visit URL in browser)
make docker-sync        # Sync your data
```

Then open http://localhost:8501

See [SETUP.md](SETUP.md) for detailed instructions.

## Features

- **Automated Sync** - Daily data sync at configurable time
- **Interactive Dashboard** - Recovery, sleep, heart rate, workouts
- **MLR Models** - Predict recovery & HRV from sleep, strain, HRV
- **Auto-backup** - 30-day retention database backups
- **HTTPS** - Caddy reverse proxy with auto SSL
- **Easy Sharing** - Tailscale Funnel for public access

## Services

| Service | Port | Purpose |
|---------|------|---------|
| Dashboard | 8501 | Streamlit UI |
| Callback | 8080 | OAuth callback server |
| Caddy | 80/443 | HTTPS proxy |

## Dashboard Tabs

- **Recovery & Strain** - Daily trends
- **Sleep** - Stages, performance, efficiency  
- **Heart Rate** - Avg, max, RHR, HRV
- **Workouts** - Activity history
- **Insights** - Correlation analysis
- **MLR Recovery** - Predict recovery
- **MLR HRV** - Predict HRV

## MLR Models

The dashboard includes Multiple Linear Regression models to predict Recovery and HRV based on your sleep, strain, and other metrics.

### Correlation Analysis

Understanding which metrics influence each other:

![Correlation Matrix](docs/correlation_matrix.png)

The correlation matrix shows relationships between key metrics - helping identify which factors most impact recovery and HRV.

### Model Coefficients

See the weight of each variable in the prediction models:

![Coefficients](docs/coefficients.png)

Positive coefficients increase the predicted value, negative coefficients decrease it. The magnitude shows the strength of each factor's influence.

### Prediction Accuracy

Compare predicted vs actual values:

![Actual vs Predicted](docs/actual_vs_predicted.png)

The closer points align to the diagonal line, the more accurate the predictions. This helps validate model performance.

## Commands

### Docker Operations

```bash
make docker-build     # Build Docker image
make docker-up        # Start all services
make docker-down      # Stop all services
make docker-logs      # View dashboard logs
make docker-shell     # Open shell in container
```

### Authentication

```bash
make docker-status    # Check auth status
make docker-auth      # Start authentication flow
make docker-reauth    # Re-authenticate (clear old tokens)
```

### Data Sync

```bash
make docker-sync      # Sync data once
make docker-sync-full # Full historical sync
```

### Local Development

```bash
make install          # Install Python deps
make auth             # Authenticate (local)
make sync             # Sync data (local)
make dashboard        # Run Streamlit locally
```

## Sharing Publicly

Share your dashboard with anyone (no Tailscale required for them):

```bash
# Enable public access
tailscale funnel --bg --https=443 http://localhost:8501

# Your dashboard URL will be:
# https://<your-machine-name>.tail<tailnet-id>.ts.net/

# Stop sharing
tailscale funnel --https=443 off
```

## Project Structure

```
whoop_sync/
├── main.py              # CLI entry point
├── dashboard/           # Streamlit app
├── src/whoop_sync/      # Core modules
│   ├── auth.py          # OAuth authentication
│   ├── api.py           # Whoop API client
│   ├── db.py            # SQLite database
│   ├── sync.py          # Data synchronization
│   └── config.py        # Configuration
├── docs/                # Documentation images
├── scripts/             # Setup & backup
├── Dockerfile           # Container definition
├── docker-compose.yml   # Service orchestration
└── entrypoint.sh        # Container startup
```

## Data Storage

All data persists in Docker volumes:

- `whoop-data` - Database and auth tokens
- `caddy-data` - SSL certificates

## License

MIT
