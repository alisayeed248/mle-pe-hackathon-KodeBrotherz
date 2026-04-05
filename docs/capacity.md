# Capacity Plan

This document outlines the performance characteristics, known limits, and scaling strategies for the URL Shortener service.

---

## Current Configuration

| Component | Count | Resources |
|-----------|-------|-----------|
| Flask App Instances | 5 | ~100MB RAM each |
| Gunicorn Workers per Instance | 4 | - |
| Total Workers | 20 | - |
| PostgreSQL | 1 | ~200MB RAM |
| Redis | 1 | ~50MB RAM |
| Nginx | 1 | ~20MB RAM |

**Total Estimated RAM:** ~1GB

---

## Tested Performance

### Load Test Results

Using Locust with gradual ramp-up:

| Users | RPS | p95 Latency | Error Rate |
|-------|-----|-------------|------------|
| 100 | ~200 | 15ms | 0% |
| 500 | ~800 | 25ms | 0% |
| 1000 | ~1500 | 40ms | 0% |
| 2500 | ~2500 | 50ms | 0% |
| 3000+ | ~2800 | 100ms+ | <1% |

**Comfortable Operating Range:** Up to 2500 concurrent users

### Bottleneck Analysis

At high load, the bottleneck is:
1. **Gunicorn workers** - Sync workers block on I/O
2. **Database connections** - Connection pool can exhaust
3. **Redis** - Not a bottleneck at this scale

---

## Scaling Thresholds

### When to Scale Horizontally (Add Instances)

| Metric | Threshold | Action |
|--------|-----------|--------|
| CPU Usage | > 80% sustained | Add app instances |
| p95 Latency | > 200ms | Add app instances |
| Error Rate | > 1% | Investigate, likely need more capacity |
| Active Connections | > 80% of pool | Increase pool or add instances |

### When to Scale Vertically (More Resources)

| Metric | Threshold | Action |
|--------|-----------|--------|
| Memory Usage | > 85% | Increase container memory limit |
| Database CPU | > 70% | Upgrade PostgreSQL resources |
| Redis Memory | > 80% | Increase Redis maxmemory |

---

## Known Limits

### Hard Limits

| Component | Limit | Impact |
|-----------|-------|--------|
| Short code length | 6 chars | ~2 billion unique codes (62^6) |
| URL length | 2048 chars | Standard browser limit |
| Request body | 1MB | Nginx default |
| Database connections | 100 per instance | PostgreSQL default |

### Soft Limits (Configurable)

| Component | Default | Can Increase To |
|-----------|---------|-----------------|
| Gunicorn workers | 4 per instance | 8-16 (CPU bound) |
| Redis cache TTL | 5 minutes | Increase for more caching |
| Nginx worker connections | 1024 | 4096+ |

---

## Failure Modes

### Single Instance Failure

**Impact:** ~20% capacity reduction (1 of 5 instances)
**Recovery:** Automatic via Nginx health checks
**User Impact:** Minimal - requests route to healthy instances

### Redis Failure

**Impact:** All requests hit database, latency increases ~10x
**Recovery:** Manual restart or automatic via Docker restart policy
**User Impact:** Slower responses but service remains available

### Database Failure

**Impact:** Complete service outage for write operations
**Recovery:** Manual intervention required
**User Impact:** Severe - redirects may work from cache, creates fail

### Nginx Failure

**Impact:** Complete service outage
**Recovery:** Docker restart policy or manual restart
**User Impact:** Total outage

---

## Scaling Strategies

### Short-term (Hackathon)

Current setup handles 2500 RPS comfortably. For higher load:

1. Add more app instances (app6, app7, etc.)
2. Increase Gunicorn workers per instance
3. Increase Redis cache TTL

### Medium-term (Production)

1. **Database Read Replicas** - Offload read traffic
2. **Redis Cluster** - Distributed caching
3. **Connection Pooling** - PgBouncer for database
4. **CDN** - Cache redirects at edge

### Long-term (Scale)

1. **Kubernetes** - Auto-scaling based on metrics
2. **Database Sharding** - Horizontal database scaling
3. **Multi-region** - Geographic distribution
4. **Service Mesh** - Advanced traffic management

---

## Monitoring for Capacity

### Key Metrics to Watch

```promql
# Request rate trend
rate(http_requests_total[5m])

# Latency trend
histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))

# Error rate
rate(http_errors_total[5m]) / rate(http_requests_total[5m])

# CPU saturation
avg(system_cpu_percent)

# Memory saturation
avg(system_memory_percent)

# Database query time
histogram_quantile(0.95, rate(db_query_duration_seconds_bucket[5m]))
```

### Alerting Thresholds

| Alert | Threshold | Meaning |
|-------|-----------|---------|
| HighCPU | > 85% for 3min | Approaching capacity |
| HighLatency | p95 > 2s | User experience degraded |
| HighMemory | > 85% for 3min | Risk of OOM |
| HighErrorRate | > 5% | Something is wrong |

---

## Capacity Planning Checklist

Before a traffic event:

- [ ] Review current metrics baseline
- [ ] Ensure at least 30% headroom on all resources
- [ ] Verify auto-restart policies are configured
- [ ] Test rollback procedure
- [ ] Have scaling runbook ready
- [ ] Monitor dashboards during event

---

## Cost Considerations

Current setup (Docker Compose on single host):

| Resource | Estimate |
|----------|----------|
| RAM | ~1-2 GB |
| CPU | ~2-4 cores under load |
| Disk | ~1 GB (logs, data) |

For cloud deployment (estimated):
- **AWS/GCP small instances:** ~$50-100/month
- **With managed database:** ~$100-200/month
- **With Redis cluster:** +$50/month
