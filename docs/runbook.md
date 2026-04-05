# URL Shortener - Incident Response Runbook

## Overview

This runbook provides emergency response procedures for the URL Shortener service. Use in conjunction with the **Gold - Command Center** dashboard in Grafana.

**Access Points:**
- Grafana: http://127.0.0.1:3000 (admin/admin)
- Prometheus: http://127.0.0.1:9090
- Alertmanager: http://127.0.0.1:9093
- App (via Nginx): http://127.0.0.1

---

## Alert Response Procedures

### CRITICAL: ServiceDown

**Symptom:** One or more Flask app instances are unreachable.

**Alert Rule:** `up{job="flask-app"} == 0` for 30 seconds

**Response:**
1. Check which instance is down:
   ```bash
   docker compose ps
   ```

2. View instance logs:
   ```bash
   docker compose logs app1 --tail=50
   docker compose logs app2 --tail=50
   # ... check all affected instances
   ```

3. Restart the affected instance:
   ```bash
   docker compose restart app1
   ```

4. If instance keeps crashing, check for:
   - Memory issues: `docker stats`
   - Database connectivity: `docker compose logs postgres --tail=20`
   - Redis connectivity: `docker compose logs redis --tail=20`

5. Escalate if: Instance doesn't recover after 2 restart attempts.

---

### CRITICAL: DatabaseDown

**Symptom:** PostgreSQL is unreachable.

**Alert Rule:** `pg_up == 0` for 30 seconds

**Response:**
1. Check PostgreSQL status:
   ```bash
   docker compose ps postgres
   docker compose logs postgres --tail=50
   ```

2. Restart PostgreSQL:
   ```bash
   docker compose restart postgres
   ```

3. Verify connections are restored:
   ```bash
   docker compose exec postgres pg_isready
   ```

4. Check for disk space issues:
   ```bash
   docker system df
   ```

5. Escalate if: Database doesn't recover or shows data corruption errors.

---

### WARNING: HighApplicationErrorRate

**Symptom:** Error rate exceeds 5% of requests.

**Alert Rule:** `http_errors_total / http_requests_total > 0.05` for 2 minutes

**Response:**
1. Check Command Center dashboard for error trends.

2. Query Loki for error logs:
   - Go to Grafana > Explore > Loki
   - Query: `{job="flask-app"} |= "ERROR"`

3. Identify error patterns:
   ```bash
   docker compose logs app1 app2 app3 app4 app5 2>&1 | grep -i error | tail -50
   ```

4. Common causes:
   - **Database errors**: Check PostgreSQL logs
   - **Redis errors**: Check Redis connectivity
   - **Application bugs**: Review recent deployments

5. Mitigation:
   - If database-related: Restart database connections
   - If Redis-related: `docker compose restart redis`
   - If app bug: Rollback to previous version

---

### WARNING: HighLatency

**Symptom:** p95 latency exceeds 2 seconds.

**Alert Rule:** `histogram_quantile(0.95, http_request_duration_seconds_bucket) > 2` for 2 minutes

**Response:**
1. Check Command Center for latency trends.

2. Identify slow endpoints:
   - Query: `histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket[1m])) by (le, endpoint))`

3. Check database query performance:
   - Look for slow queries in logs
   - Query: `{job="flask-app"} |= "duration_ms" | json | duration_ms > 1000`

4. Check for resource saturation:
   - CPU usage on instances
   - Memory pressure
   - Database connection pool exhaustion

5. Mitigation:
   - Scale up: Add more app instances
   - Optimize slow queries
   - Check Redis cache hit rates

---

### WARNING: HighCPUUsage / HighMemoryUsage

**Symptom:** CPU > 85% or Memory > 85% sustained.

**Alert Rule:** `system_cpu_percent > 85` or `system_memory_percent > 85` for 5 minutes

**Response:**
1. Check resource usage per container:
   ```bash
   docker stats --no-stream
   ```

2. Identify resource-heavy operations:
   - Check for traffic spikes
   - Check for expensive queries
   - Check for memory leaks

3. Mitigation:
   - **Traffic spike**: Scale horizontally (add instances)
   - **Memory leak**: Restart affected instances
   - **CPU spike**: Identify and optimize hot paths

---

## Root Cause Analysis (RCA) Procedure

When an incident occurs, follow this process:

### 1. Identify the Problem
- Open Command Center dashboard
- Note which Golden Signal is affected (Latency, Traffic, Errors, Saturation)
- Record the time range of the incident

### 2. Correlate Metrics
- Check all 4 Golden Signals for the same time period
- Look for correlations (e.g., high latency + high CPU = saturation)

### 3. Examine Logs
- Go to Grafana > Explore > Loki
- Filter by time range of incident
- Search for ERROR and WARNING levels
- Query examples:
  ```
  {job="flask-app"} |= "ERROR"
  {job="flask-app"} | json | status_code >= 500
  {job="flask-app"} | json | duration_ms > 1000
  ```

### 4. Check Instance Health
- Review "Instance Health" panel in Command Center
- Check if specific instances were affected
- Review per-instance metrics

### 5. Document Findings
- Timeline of events
- Root cause identified
- Actions taken
- Prevention measures

---

## Common Scenarios

### Scenario: Sudden Traffic Spike
**Symptoms:** High traffic, increasing latency, possible errors
**RCA Steps:**
1. Check Traffic panel - confirm spike
2. Check Saturation - CPU/Memory pressure?
3. Check Errors - are we dropping requests?
4. Check Logs for rate limiting or timeout errors

### Scenario: Database Connectivity Issues
**Symptoms:** High error rate, database errors in logs
**RCA Steps:**
1. Check Errors panel - confirm error spike
2. Query Loki: `{job="flask-app"} |= "database" |= "error"`
3. Check PostgreSQL logs
4. Verify database is up and connections available

### Scenario: Single Instance Failure
**Symptoms:** One instance shows errors, others normal
**RCA Steps:**
1. Check Instance Health table
2. Check Traffic by Instance - uneven distribution?
3. Check logs for specific instance
4. Look for OOM kills or crashes

---

## Useful Commands

```bash
# Check all services
docker compose ps

# View logs (last 100 lines)
docker compose logs --tail=100

# View specific service logs
docker compose logs app1 --tail=50 -f

# Restart a service
docker compose restart app1

# Check resource usage
docker stats --no-stream

# Check disk usage
docker system df

# Full restart (last resort)
docker compose down && docker compose up -d
```

---

## Escalation

If unable to resolve within 15 minutes:
1. Page on-call engineer (PagerDuty)
2. Notify in #incidents Slack/Discord channel
3. Begin incident bridge call

**Contact:** Alerts route to Discord, Email, and PagerDuty (critical only).
