# Deployment Guide

## Overview

This guide covers deploying and managing the URL Shortener service using Docker Compose.

---

## Initial Deployment

### Prerequisites

1. Docker Desktop installed and running
2. At least 4GB RAM available for containers
3. Ports 80, 3000, 9090, 9093, 3100 available

### Deploy

```bash
# Clone the repository
git clone https://github.com/YOUR_USERNAME/PE-Hackathon-Template-2026.git
cd PE-Hackathon-Template-2026

# Build and start all services
docker compose up -d --build

# Verify all services are running
docker compose ps

# Check application health
curl http://127.0.0.1/health
```

### Expected Output

All 15 services should show as "Up":
- nginx, nginx-exporter
- app1, app2, app3, app4, app5
- postgres, redis
- prometheus, grafana, loki, promtail
- alertmanager, discord-webhook

---

## Updating the Application

### Code Changes (No Downtime)

For application code changes, rebuild and restart the app containers:

```bash
# Rebuild only app containers
docker compose up -d --build app1 app2 app3 app4 app5

# Verify health
curl http://127.0.0.1/health
```

This performs a rolling update - nginx continues routing to healthy instances.

### Infrastructure Changes

For docker-compose.yml or infrastructure changes:

```bash
# Stop all services
docker compose down

# Rebuild and start
docker compose up -d --build

# Verify all services
docker compose ps
```

### Configuration Changes

For Prometheus, Grafana, or Alertmanager config changes:

```bash
# Restart the specific service
docker compose restart prometheus
docker compose restart grafana
docker compose restart alertmanager
```

---

## Rollback Procedures

### Rollback Application Code

If a deployment causes issues:

```bash
# 1. Check which commit is currently deployed
git log --oneline -5

# 2. Revert to previous commit
git checkout <previous-commit-hash>

# 3. Rebuild and deploy
docker compose up -d --build app1 app2 app3 app4 app5

# 4. Verify health
curl http://127.0.0.1/health
```

### Rollback Using Git Tags

If you tag releases:

```bash
# List available tags
git tag -l

# Checkout specific version
git checkout v1.0.0

# Rebuild
docker compose up -d --build
```

### Emergency Rollback (Full Stack)

If the entire stack is broken:

```bash
# 1. Stop everything
docker compose down

# 2. Checkout known good version
git checkout <known-good-commit>

# 3. Clean Docker resources
docker system prune -f

# 4. Rebuild from scratch
docker compose up -d --build

# 5. Verify
docker compose ps
curl http://127.0.0.1/health
```

---

## Scaling

### Horizontal Scaling (More App Instances)

To add more app instances, edit `docker-compose.yml`:

```yaml
# Add app6, app7, etc. following the same pattern as app1-5
app6:
  build: .
  environment: *app-env
  depends_on:
    postgres:
      condition: service_healthy
    redis:
      condition: service_started
  restart: always
```

Then update `infra/nginx.conf` to include new backends:

```nginx
upstream flask_app {
    server app1:5000;
    server app2:5000;
    server app3:5000;
    server app4:5000;
    server app5:5000;
    server app6:5000;  # new
}
```

Apply changes:

```bash
docker compose up -d --build
docker compose restart nginx
```

### Vertical Scaling (More Resources)

Add resource limits in `docker-compose.yml`:

```yaml
app1:
  build: .
  deploy:
    resources:
      limits:
        cpus: '1.0'
        memory: 512M
      reservations:
        cpus: '0.25'
        memory: 128M
```

---

## Health Checks

### Application Health

```bash
# Single check
curl http://127.0.0.1/health

# Continuous monitoring
watch -n 5 'curl -s http://127.0.0.1/health'
```

### Service Status

```bash
# All services
docker compose ps

# Specific service logs
docker compose logs app1 --tail=50

# Resource usage
docker stats --no-stream
```

### Database Health

```bash
# PostgreSQL
docker compose exec postgres pg_isready

# Redis
docker compose exec redis redis-cli ping
```

---

## Backup and Restore

### Database Backup

```bash
# Create backup
docker compose exec postgres pg_dump -U postgres hackathon_db > backup_$(date +%Y%m%d).sql

# Restore from backup
cat backup_20260405.sql | docker compose exec -T postgres psql -U postgres hackathon_db
```

### Full Volume Backup

```bash
# Stop services
docker compose down

# Backup volumes
docker run --rm -v pe-hackathon-template-2026_postgres_data:/data -v $(pwd):/backup alpine tar cvf /backup/postgres_backup.tar /data

# Restart
docker compose up -d
```

---

## Monitoring Deployment

After any deployment:

1. **Check Grafana** - http://127.0.0.1:3000
   - Verify all instances show as UP in Command Center
   - Check for error rate spikes

2. **Check Prometheus Targets** - http://127.0.0.1:9090/targets
   - All targets should be green (UP)

3. **Check Alertmanager** - http://127.0.0.1:9093
   - No firing alerts

4. **Tail logs for errors**:
   ```bash
   docker compose logs -f app1 app2 app3 app4 app5 2>&1 | grep -i error
   ```

---

## Troubleshooting Deployments

### Build Fails

```bash
# Clean build cache
docker builder prune -f

# Rebuild without cache
docker compose build --no-cache
```

### Container Won't Start

```bash
# Check logs
docker compose logs <service-name>

# Check if port is in use
netstat -ano | findstr :80
```

### Database Connection Issues

```bash
# Restart database
docker compose restart postgres

# Check database logs
docker compose logs postgres --tail=50
```

See [Troubleshooting Guide](troubleshooting.md) for more common issues.
