# Troubleshooting Guide

Common issues encountered during development and their solutions.

---

## Docker Issues

### "invalid memory address or nil pointer dereference" on Windows

**Symptom:** Docker build fails with a Go panic about nil pointer dereference.

**Cause:** A file named `nul` (Windows reserved name) exists in the project, or line endings are wrong.

**Fix:**
```powershell
# Delete problematic file
del "\\?\C:\path\to\project\nul"

# Fix line endings
git config core.autocrlf false
git rm --cached -r .
git reset --hard

# Rebuild
docker compose up -d --build
```

### "stream terminated by RST_STREAM with error code: PROTOCOL_ERROR"

**Symptom:** Build context transfer fails.

**Fix:**
```bash
# Clean Docker state
docker compose down
docker builder prune -f
docker image prune -f

# Rebuild
docker compose up -d --build
```

### Container keeps restarting

**Symptom:** `docker compose ps` shows container in restart loop.

**Fix:**
```bash
# Check logs for error
docker compose logs <service-name> --tail=100

# Common causes:
# - Database not ready: Wait for postgres to be healthy
# - Port conflict: Check if port is already in use
# - Missing env vars: Check environment configuration
```

---

## Application Issues

### Redis connection timeout kills workers

**Symptom:** When Redis is down, all app instances crash with SIGKILL.

**Cause:** Redis client has no timeout, blocks indefinitely, Gunicorn kills worker.

**Fix:** Configure Redis client with timeouts:
```python
redis_client = redis.Redis(
    host=os.getenv("REDIS_HOST", "localhost"),
    port=int(os.getenv("REDIS_PORT", 6379)),
    socket_timeout=0.5,
    socket_connect_timeout=0.5,
    retry_on_timeout=False,
)
```

### "Short URL not found" for valid URLs

**Symptom:** Redirect returns 404 even for URLs that exist.

**Cause:** URL may be cached in Redis with stale data, or database query failing.

**Fix:**
```bash
# Clear Redis cache
docker compose exec redis redis-cli FLUSHALL

# Check database directly
docker compose exec postgres psql -U postgres hackathon_db -c "SELECT * FROM urls LIMIT 5;"
```

### High latency on all requests

**Symptom:** Every request takes several seconds.

**Cause:** Could be database connection pool exhaustion, chaos injection enabled, or resource saturation.

**Fix:**
```bash
# Check if chaos is enabled
curl http://127.0.0.1/chaos/status

# Reset chaos if enabled
curl -X POST http://127.0.0.1/chaos/reset

# Check resource usage
docker stats --no-stream

# Restart app instances
docker compose restart app1 app2 app3 app4 app5
```

---

## Database Issues

### "connection refused" to PostgreSQL

**Symptom:** App can't connect to database.

**Fix:**
```bash
# Check if postgres is running
docker compose ps postgres

# Check postgres logs
docker compose logs postgres --tail=50

# Verify postgres is healthy
docker compose exec postgres pg_isready

# Restart postgres
docker compose restart postgres
```

### Database migrations not applied

**Symptom:** Tables don't exist or schema is wrong.

**Fix:** The app auto-creates tables on startup. Restart the app:
```bash
docker compose restart app1 app2 app3 app4 app5
```

---

## Observability Issues

### Grafana shows "No data"

**Symptom:** Dashboard panels are empty.

**Cause:** Prometheus can't scrape targets, or data source not configured.

**Fix:**
```bash
# Check Prometheus targets
# Go to http://127.0.0.1:9090/targets
# All targets should be UP (green)

# If targets are down, check the service
docker compose ps

# Verify Grafana data source
# Go to http://127.0.0.1:3000 > Settings > Data Sources
# Prometheus URL should be http://prometheus:9090
```

### Prometheus shows targets as DOWN

**Symptom:** http://127.0.0.1:9090/targets shows red "DOWN" status.

**Cause:** Container DNS issues or service not exposing metrics.

**Fix:**
```bash
# Test from inside Docker network
docker compose exec prometheus wget -qO- http://app1:5000/metrics

# If that fails, check if app is running
docker compose logs app1 --tail=20
```

### Loki shows no logs

**Symptom:** Grafana Explore with Loki source returns no results.

**Fix:**
```bash
# Check Promtail is running
docker compose ps promtail

# Check Promtail logs
docker compose logs promtail --tail=50

# Verify Promtail can access Docker socket
docker compose exec promtail ls -la /var/run/docker.sock
```

### Alerts not firing

**Symptom:** Conditions are met but no alerts appear.

**Fix:**
```bash
# Check Alertmanager
curl http://127.0.0.1:9093/api/v1/alerts

# Check Prometheus alert rules
# Go to http://127.0.0.1:9090/alerts

# Verify alert rules are loaded
docker compose exec prometheus cat /etc/prometheus/alert_rules.yml
```

---

## Networking Issues

### "localhost" doesn't work, but "127.0.0.1" does

**Symptom:** Browser or curl to localhost fails.

**Cause:** Windows IPv6 issues.

**Fix:** Always use `127.0.0.1` instead of `localhost`.

### Port already in use

**Symptom:** Container fails to start with port binding error.

**Fix:**
```powershell
# Find what's using the port (Windows)
netstat -ano | findstr :80

# Kill the process
taskkill /PID <pid> /F

# Or change the port in docker-compose.yml
```

### Containers can't reach each other

**Symptom:** Services fail to connect to other services.

**Fix:**
```bash
# Verify Docker network exists
docker network ls | grep pe-hackathon

# Recreate the network
docker compose down
docker compose up -d
```

---

## Load Testing Issues

### Locust web UI not accessible

**Symptom:** http://127.0.0.1:8089 doesn't load.

**Fix:** Make sure master is running:
```bash
uv run locust -f locustfile.py --master --host=http://127.0.0.1
```

### Workers not connecting to master

**Symptom:** Locust shows 0 workers.

**Fix:**
```bash
# Ensure master is running first
# Then start workers pointing to correct host
uv run locust -f locustfile.py --worker --master-host=127.0.0.1
```

---

## Quick Diagnostic Commands

```bash
# Check all service status
docker compose ps

# Check resource usage
docker stats --no-stream

# View all logs
docker compose logs --tail=50

# Check disk space
docker system df

# Full system clean (CAUTION: removes all unused data)
docker system prune -a --volumes
```
