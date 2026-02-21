┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                              WHOOP SYNC - TECH STACK                                     │
└─────────────────────────────────────────────────────────────────────────────────────────┘
  EXTERNAL SERVICES
  ═════════════════
  ┌──────────────┐          ┌─────────────────────────────┐          ┌───────────────┐
  │  WHOOP Band  │ ───────► │       WHOOP API             │ ◄──────► │ User/Browser  │
  │  (Wearable)  │   BLE    │  api.prod.whoop.com         │  :8501   │               │
  └──────────────┘          │  OAuth 2.0 · REST           │          └───────────────┘
                            │  Endpoints:                 │                 ▲
                            │  cycles, recoveries,        │                 │
                            │  sleeps, workouts, profile  │                 │
                            └─────────────────────────────┘                 │
                                    ▲                                       │
                                    │                                       │
                                    │ API Requests                          │
                                    │                                       │
  ┌─────────────────────────────────┼───────────────────────────────────────┼─────────┐
  │ DOCKER CONTAINER                │                                       │         │
  │ whoop-dashboard                 │                                       │         │
  │ ────────────────────────────────┼───────────────────────────────────────┼─────────│
  │                                 │                                       │         │
  │  ┌──────────────────────────────┘                                       │         │
  │  │                                                                      │         │
  │  ▼                                                                      │         │
  │  ┌───────────────────────────────────────────────────────────────────┐  │         │
  │  │  AUTHENTICATION (auth.py · WhoopAuth)                             │  │         │
  │  │  ─────────────────────────────────────                            │  │         │
  │  │  • OAuth 2.0 Flow          • Callback Server (:8080)              │  │         │
  │  │  • Token Storage           • Auto-refresh (5min buffer)           │  │         │
  │  │  • tokens.json             • 3x retry w/ exponential backoff      │  │         │
  │  └───────────────────────────────────────────────────────────────────┘  │         │
  │                                    │                                     │         │
  │                                    │ token                                │         │
  │                                    ▼                                     │         │
  │  ┌───────────────────────────────────────────────────────────────────┐  │         │
  │  │  API CLIENT (api.py · WhoopAPI)                                  │  │         │
  │  │  ──────────────────────────────                                   │  │         │
  │  │  • Paginated Fetcher (25/page)    • Auto Token Refresh on 401    │  │         │
  │  │  • Endpoints: cycles, recoveries, sleeps, workouts, profile,     │  │         │
  │  │                body, user                                         │  │         │
  │  └───────────────────────────────────────────────────────────────────┘  │         │
  │                                    │                                     │         │
  │                                    │ data                                │         │
  │                                    ▼                                     │         │
  │  ┌───────────────────────────────────────────────────────────────────┐  │         │
  │  │  SYNC ENGINE (sync.py · WhoopSync)                               │  │         │
  │  │  ───────────────────────────────────                              │  │         │
  │  │  • Incremental Sync (latest - 1 day overlap)                      │  │         │
  │  │  • Full Sync (--full flag)                                        │  │         │
  │  │  • Orchestrates: auth → api → db                                  │  │         │
  │  │  • Upserts all entity types                                       │  │         │
  │  └───────────────────────────────────────────────────────────────────┘  │         │
  │                                    │                                     │         │
  │                                    │ upsert                              │         │
  │                                    ▼                                     │         │
  │  ┌───────────────────────────────────────────────────────────────────┐  │         │
  │  │  SQLite DATABASE (whoop.db)                                       │  │         │
  │  │  ───────────────────────────                                      │  │         │
  │  │  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌────────────┐  │  │         │
  │  │  │  cycles    │  │ recoveries │  │  sleeps    │  │ workouts   │  │  │         │
  │  │  └────────────┘  └────────────┘  └────────────┘  └────────────┘  │  │         │
  │  │  ┌────────────┐  ┌────────────┐                                   │  │         │
  │  │  │user_profile│  │body_measure│                                   │  │         │
  │  │  └────────────┘  └────────────┘                                   │  │         │
  │  │                                                                   │  │         │
  │  │  • UPSERT (INSERT OR REPLACE)                                     │  │         │
  │  │  • Indexes: start, cycle_id                                       │  │         │
  │  │  • Volume: whoop-data → /app/data                                 │  │         │
  │  └───────────────────────────────────────────────────────────────────┘  │         │
  │                                    │                                     │         │
  │                                    │ read                                 │         │
  │                                    ▼                                     │         │
  │  ┌───────────────────────────────────────────────────────────────────┐  │         │
  │  │  STREAMLIT DASHBOARD (dashboard.py · :8501)                       ◄──┼─────────┘
  │  │  ──────────────────────────────────────────                        │
  │  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐              │
  │  │  │ Recovery │ │  Sleep   │ │ HR/HRV   │ │ Workouts │              │
  │  │  │ & Strain │ │ Analysis │ │          │ │Breakdown │              │
  │  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘              │
  │  │  ┌──────────┐ ┌──────────┐ ┌──────────┐                          │
  │  │  │Workouts  │ │ Insights │ │   MLR    │                          │
  │  │  │          │ │& Corr.   │ │ Recovery │                          │
  │  │  └──────────┘ └──────────┘ └──────────┘                          │
  │  │                                                                   │
  │  │  Stack: Streamlit · Pandas · Plotly · Statsmodels · SciPy        │
  │  │  Features: OLS regression · Correlation matrix · Interactive      │
  │  │            charts · Date filtering · Dark theme                   │
  │  └───────────────────────────────────────────────────────────────────┘
  │
  │  ┌──────────────────────────┐    ┌──────────────────────────┐
  │  │  CRON SCHEDULER          │    │  CLI (main.py)           │
  │  │  ─────────────────       │    │  ──────────────          │
  │  │  • Daily sync at         │    │  Commands:               │
  │  │    $SYNC_HOUR            │──► │  • auth  · reauth        │
  │  │  • python main.py sync   │    │  • sync  · status        │
  │  │  • Logs: whoop-sync.log  │    │  • stats                 │
  │  └──────────────────────────┘    └──────────────────────────┘
  │
  └───────────────────────────────────────────────────────────────────────────────────────┘
  INFRASTRUCTURE (outside Docker)
  ═══════════════════════════════
  ┌──────────────────┐  ┌─────────────────────────┐  ┌──────────────────┐  ┌──────────────┐
  │  Docker Hub      │  │  CONFIGURATION          │  │  NETWORK ACCESS  │  │  WATCHTOWER  │
  │  ────────────    │  │  ─────────────          │  │  ──────────────  │  │  ─────────── │
  │  idossha/        │  │  .env:                  │  │  • Tailscale VPN │  │  Auto-update │
  │  whoop-sync      │  │  CLIENT_ID              │  │    (private)     │  │  container   │
  │  :latest         │  │  CLIENT_SECRET          │  │  • Tailscale     │  │  Daily 4AM   │
  │                  │  │  TZ                     │  │    Funnel (pub)  │  │              │
  │                  │  │                         │  │  • Caddy reverse │  │              │
  │                  │  │  config.py:             │  │    proxy (opt)   │  │              │
  │                  │  │  OAuth URLs, Scopes     │  │                  │  │              │
  └────────┬─────────┘  └─────────────────────────┘  └──────────────────┘  └──────┬───────┘
           │                                                               │             │
           │                                                               │             │
           └───────────────────────────────────────────────────────────────┼─────────────┘
                                                                           │
                                                                    pulls image
  DATA FLOW
  ═════════
  WHOOP Band ──BLE──► WHOOP App ──► WHOOP Cloud API
                                            │
                                            │ OAuth 2.0
                                            ▼
  ┌─────────────────────────────────────────────────────────────────┐
  │  Auth Layer ──token──► API Client ──data──► Sync Engine        │
  │                                                  │              │
  │                                                  ▼              │
  │  User ◄──charts── Streamlit ◄──read── SQLite ◄──upsert         │
  └─────────────────────────────────────────────────────────────────┘
  TECH STACK SUMMARY
  ══════════════════
  Language:     Python 3.11
  Container:    Docker (python:3.11-slim)
  Database:     SQLite
  HTTP Client:  Requests
  Dashboard:    Streamlit
  Viz:          Plotly
  Data:         Pandas
  Stats:        Statsmodels, SciPy
  Scheduler:    CRON
  Auth:         OAuth 2.0
  Network:      Tailscale (VPN/Funnel)
  CI/CD:        Docker Hub + Watchtower
