# URL Shortener — KodeBrotherz

Production Engineering Hackathon submission by Sayeed & Naimul.

A high-availability URL shortener with load balancing, caching, metrics, and observability.

## Quick Start

```bash
# Start everything
docker-compose up --build

# That's it. Everything runs in containers.
```

## Access Points

| Service | URL | Description |
|---------|-----|-------------|
| **App** | http://localhost | Landing page + API |
| **Grafana** | http://localhost:3000 | Dashboards (admin/admin) |
| **Prometheus** | http://localhost:9090 | Metrics |

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | Landing page (UI) |
| `GET` | `/health` | Health check → `{"status": "ok"}` |
| `POST` | `/shorten` | Create short URL |
| `GET` | `/<code>` | Redirect to original URL |
| `GET` | `/<code>/stats` | Get URL statistics |
| `GET` | `/metrics` | Prometheus metrics |

### POST /shorten

```bash
curl -X POST http://localhost/shorten \
  -H "Content-Type: application/json" \
  -d '{"url": "https://github.com"}'

# Response:
# {"short_code": "abc123", "short_url": "http://localhost/abc123"}

# With custom code:
curl -X POST http://localhost/shorten \
  -H "Content-Type: application/json" \
  -d '{"url": "https://github.com", "custom_code": "gh"}'
```

## Architecture

```
Client
  │
  ▼
┌─────────────────────────────────────────────────┐
│                 Nginx (port 80)                 │
│              Load Balancer + Static             │
└─────────────────────────────────────────────────┘
         │              │              │
         ▼              ▼              ▼
    ┌─────────┐   ┌─────────┐   ┌─────────┐
    │  App 1  │   │  App 2  │   │  App 3  │
    │ :5000   │   │ :5000   │   │ :5000   │
    └────┬────┘   └────┬────┘   └────┬────┘
         │              │              │
         └──────────────┼──────────────┘
                        │
         ┌──────────────┼──────────────┐
         ▼              ▼              ▼
    ┌─────────┐   ┌─────────┐   ┌─────────────┐
    │  Redis  │   │Postgres │   │ Prometheus  │
    │ (cache) │   │  (db)   │   │  (metrics)  │
    └─────────┘   └─────────┘   └──────┬──────┘
                                       │
                                       ▼
                                ┌─────────────┐
                                │   Grafana   │
                                │ (dashboards)│
                                └─────────────┘
```

## Tech Stack

- **Flask** — Python web framework
- **PostgreSQL** — Primary database
- **Redis** — Caching layer (coming soon)
- **Nginx** — Load balancer + reverse proxy
- **Prometheus** — Metrics collection
- **Grafana** — Dashboards
- **Docker Compose** — Container orchestration

## Development

```bash
# Install dependencies locally (optional, for IDE support)
uv sync

# Run without Docker (requires local Postgres)
uv run run.py
```

## TODO

### Completed
- [x] Core URL shortening API
- [x] Input validation + error handling
- [x] Docker Compose with all services
- [x] Nginx load balancing (3 replicas)
- [x] Prometheus metrics endpoint
- [x] Landing page UI

### In Progress
- [ ] Grafana dashboard (4 panels)
- [ ] Redis caching layer

### Tomorrow
- [ ] Structured logging (structlog)
- [ ] Load testing (k6 or Locust)
- [ ] OpenTelemetry tracing + Jaeger
- [ ] Alertmanager + Discord webhooks
- [ ] Auto-remediation script
- [ ] pytest + GitHub Actions CI
- [ ] SLOs + error budget tracking

### Stretch Goals
- [ ] Kubernetes deployment (Helm chart)
- [ ] Deploy to custom domain
