# Environment Variables

All configuration is done through environment variables. This document lists all variables used by the application.

---

## Application Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `FLASK_DEBUG` | No | `false` | Enable Flask debug mode (never in production) |
| `DATABASE_HOST` | Yes | `localhost` | PostgreSQL hostname |
| `DATABASE_PORT` | No | `5432` | PostgreSQL port |
| `DATABASE_NAME` | Yes | `hackathon_db` | Database name |
| `DATABASE_USER` | Yes | `postgres` | Database username |
| `DATABASE_PASSWORD` | Yes | `postgres` | Database password |
| `REDIS_HOST` | Yes | `localhost` | Redis hostname |
| `REDIS_PORT` | No | `6379` | Redis port |

---

## Docker Compose Configuration

These are set in `docker-compose.yml` for container deployment:

```yaml
environment:
  - FLASK_DEBUG=false
  - DATABASE_NAME=hackathon_db
  - DATABASE_HOST=postgres
  - DATABASE_PORT=5432
  - DATABASE_USER=postgres
  - DATABASE_PASSWORD=postgres
  - REDIS_HOST=redis
  - REDIS_PORT=6379
```

---

## Local Development

For running without Docker, create a `.env` file or export these:

```bash
export FLASK_DEBUG=true
export DATABASE_HOST=localhost
export DATABASE_PORT=5432
export DATABASE_NAME=hackathon_db
export DATABASE_USER=postgres
export DATABASE_PASSWORD=postgres
export REDIS_HOST=localhost
export REDIS_PORT=6379
```

Or create a `.env` file:

```env
FLASK_DEBUG=true
DATABASE_HOST=localhost
DATABASE_PORT=5432
DATABASE_NAME=hackathon_db
DATABASE_USER=postgres
DATABASE_PASSWORD=postgres
REDIS_HOST=localhost
REDIS_PORT=6379
```

---

## Alerting Configuration

These are configured in `infra/alertmanager.yml`:

| Variable | Description |
|----------|-------------|
| `DISCORD_WEBHOOK_URL` | Discord webhook for notifications |
| `SMTP_HOST` | Email server hostname |
| `SMTP_FROM` | Email sender address |
| `PAGERDUTY_SERVICE_KEY` | PagerDuty integration key |

Example configuration in `alertmanager.yml`:

```yaml
receivers:
  - name: 'discord'
    webhook_configs:
      - url: 'http://discord-webhook:9094'

  - name: 'email'
    email_configs:
      - to: 'oncall@example.com'
        from: 'alerts@example.com'
        smarthost: 'smtp.example.com:587'

  - name: 'pagerduty'
    pagerduty_configs:
      - service_key: '<your-pagerduty-key>'
```

---

## Grafana Configuration

Default credentials (change in production):

| Variable | Default |
|----------|---------|
| Admin username | `admin` |
| Admin password | `admin` |

Configured via `docker-compose.yml`:

```yaml
grafana:
  environment:
    - GF_SECURITY_ADMIN_USER=admin
    - GF_SECURITY_ADMIN_PASSWORD=admin
    - GF_USERS_ALLOW_SIGN_UP=false
```

---

## Prometheus Configuration

Scrape targets are configured in `infra/prometheus.yml`:

```yaml
scrape_configs:
  - job_name: 'flask'
    static_configs:
      - targets:
        - 'app1:5000'
        - 'app2:5000'
        - 'app3:5000'
        - 'app4:5000'
        - 'app5:5000'
```

---

## Security Notes

**For Production:**

1. **Change all default passwords**
   - PostgreSQL password
   - Grafana admin password
   - Redis password (add `requirepass`)

2. **Use secrets management**
   - Docker secrets
   - Vault
   - Cloud provider secrets (AWS Secrets Manager, etc.)

3. **Never commit sensitive values**
   - Use `.env` files (add to `.gitignore`)
   - Use environment-specific configs

4. **Example production setup:**
   ```yaml
   services:
     app:
       environment:
         - DATABASE_PASSWORD_FILE=/run/secrets/db_password
       secrets:
         - db_password

   secrets:
     db_password:
       external: true
   ```
