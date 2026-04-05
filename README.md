# URL Shortener - KodeBrotherz

Production Engineering Hackathon submission by Sayeed & Naimul.

A high-availability URL shortener with load balancing, caching, comprehensive observability, and incident response capabilities.

---

## Quick Start

### Prerequisites
- Docker Desktop installed and running
- Git

### Setup (3 commands)

```bash
# 1. Clone the repo
git clone https://github.com/YOUR_USERNAME/PE-Hackathon-Template-2026.git
cd PE-Hackathon-Template-2026

# 2. Start all services
docker compose up -d --build

# 3. Verify everything is running
docker compose ps
```

That's it! All 15 services start automatically.

### Verify It Works

```bash
# Health check
curl http://127.0.0.1/health
# Expected: {"status":"ok"}

# Create a short URL
curl -X POST http://127.0.0.1/shorten \
  -H "Content-Type: application/json" \
  -d '{"url": "https://github.com"}'
# Expected: {"short_code": "abc123", "short_url": "http://127.0.0.1/abc123"}
```

---

## Access Points

| Service | URL | Credentials |
|---------|-----|-------------|
| **App** | http://127.0.0.1 | - |
| **Grafana** | http://127.0.0.1:3000 | admin / admin |
| **Prometheus** | http://127.0.0.1:9090 | - |
| **Alertmanager** | http://127.0.0.1:9093 | - |
| **Loki** | http://127.0.0.1:3100 | - |

---

## API Endpoints

### Core Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health` | Health check |
| `POST` | `/shorten` | Create short URL |
| `GET` | `/<code>` | Redirect to original URL |
| `GET` | `/<code>/stats` | Get URL statistics |
| `GET` | `/metrics` | Prometheus metrics |

### POST /shorten

Create a shortened URL.

**Request:**
```bash
curl -X POST http://127.0.0.1/shorten \
  -H "Content-Type: application/json" \
  -d '{"url": "https://github.com"}'
```

**Response:**
```json
{
  "short_code": "abc123",
  "short_url": "http://127.0.0.1/abc123"
}
```

**With custom code:**
```bash
curl -X POST http://127.0.0.1/shorten \
  -H "Content-Type: application/json" \
  -d '{"url": "https://github.com", "custom_code": "gh"}'
```

### GET /<code>/stats

Get statistics for a short URL.

**Request:**
```bash
curl http://127.0.0.1/abc123/stats
```

**Response:**
```json
{
  "short_code": "abc123",
  "original_url": "https://github.com",
  "created_at": "2026-04-05T12:00:00",
  "click_count": 42,
  "is_active": true
}
```

---

## Architecture

```
                              ┌─────────────────┐
                              │     Client      │
                              └────────┬────────┘
                                       │
                              ┌────────▼────────┐
                              │   Nginx (LB)    │
                              │    Port 80      │
                              └────────┬────────┘
                                       │
        ┌──────────┬──────────┬────────┼────────┬──────────┐
        │          │          │        │        │          │
   ┌────▼───┐ ┌────▼───┐ ┌────▼───┐ ┌──▼────┐ ┌─▼──────┐   │
   │  App1  │ │  App2  │ │  App3  │ │ App4  │ │  App5  │   │
   │ :5000  │ │ :5000  │ │ :5000  │ │ :5000 │ │ :5000  │   │
   └────┬───┘ └────┬───┘ └────┬───┘ └───┬───┘ └────┬───┘   │
        │          │          │         │          │       │
        └──────────┴──────────┼─────────┴──────────┘       │
                              │                            │
              ┌───────────────┼───────────────┐            │
              │               │               │            │
         ┌────▼────┐    ┌─────▼─────┐   ┌─────▼─────┐      │
         │  Redis  │    │ PostgreSQL│   │Prometheus │      │
         │ (cache) │    │   (DB)    │   │ (metrics) │      │
         └─────────┘    └───────────┘   └─────┬─────┘      │
                                              │            │
                        ┌─────────────────────┼────────────┘
                        │                     │
                   ┌────▼─────┐         ┌─────▼─────┐
                   │   Loki   │         │  Grafana  │
                   │  (logs)  │◄────────│(dashboard)│
                   └────▲─────┘         └───────────┘
                        │
                   ┌────┴─────┐
                   │ Promtail │
                   │(collector)│
                   └──────────┘
```

### Component Summary

| Component | Purpose | Why We Chose It |
|-----------|---------|-----------------|
| **Nginx** | Load balancer, reverse proxy | Industry standard, handles 10k+ concurrent connections |
| **Flask (x5)** | Application servers | Lightweight, Python ecosystem, easy to scale |
| **PostgreSQL** | Primary database | ACID compliance, reliable, proven |
| **Redis** | Caching layer | Sub-millisecond latency, reduces DB load |
| **Prometheus** | Metrics collection | Pull-based, powerful PromQL |
| **Grafana** | Dashboards & visualization | Industry standard, great integrations |
| **Loki** | Log aggregation | Lightweight, Grafana-native |
| **Alertmanager** | Alert routing | Severity-based routing, multiple channels |

---

## Observability Stack

### Dashboards (Grafana)

1. **Gold - Command Center** - 4 Golden Signals real-time monitoring
2. **Bronze - Observability** - Basic metrics overview
3. **URL Shortener** - Application-specific metrics
4. **Nginx** - Load balancer statistics

### Alerting

Three severity tiers with different notification channels:

| Severity | Examples | Notification |
|----------|----------|--------------|
| **Critical** | ServiceDown, DatabaseDown | Discord + Email + PagerDuty |
| **Warning** | HighLatency, HighErrorRate | Discord + Email |
| **Info** | InstanceDegraded | Discord |

### Logging

- Structured JSON logs from all Flask apps
- Centralized in Loki
- Queryable via Grafana Explore

---

## Documentation

| Document | Description |
|----------|-------------|
| [Runbook](docs/runbook.md) | Incident response procedures |
| [Deployment Guide](docs/deployment.md) | Deploy and rollback instructions |
| [Troubleshooting](docs/troubleshooting.md) | Common issues and fixes |
| [Environment Variables](docs/environment.md) | Configuration reference |
| [Decision Log](docs/decisions.md) | Architecture decision records |
| [Capacity Plan](docs/capacity.md) | Performance limits and scaling |

---

## Development

### Local Development (without Docker)

```bash
# Install uv (Python package manager)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install dependencies
uv sync

# Set environment variables (see docs/environment.md)
export DATABASE_HOST=localhost
export REDIS_HOST=localhost

# Run the app
uv run run.py
```

### Running Tests

```bash
uv run pytest
```

### Load Testing

```bash
# Start locust master
uv run locust -f locustfile.py --master --host=http://127.0.0.1

# Start workers (in separate terminals)
uv run locust -f locustfile.py --worker --master-host=127.0.0.1

# Open http://127.0.0.1:8089 for the web UI
```

---

## Tech Stack

- **Runtime:** Python 3.13, Flask, Gunicorn
- **Database:** PostgreSQL 16, Redis 7
- **Infrastructure:** Nginx, Docker Compose
- **Observability:** Prometheus, Grafana, Loki, Alertmanager
- **Alerting:** Discord webhooks, Email, PagerDuty

---

## Team

**KodeBrotherz**
- Sayeed
- Naimul
