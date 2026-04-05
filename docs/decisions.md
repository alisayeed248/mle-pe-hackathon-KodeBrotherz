# Architecture Decision Records (ADR)

This document records the key technical decisions made for this project and the rationale behind them.

---

## ADR-001: Flask as Web Framework

**Status:** Accepted

**Context:**
We needed a web framework for building a URL shortener API. Options considered:
- Flask (Python)
- FastAPI (Python)
- Express (Node.js)
- Go net/http

**Decision:**
Use Flask with Gunicorn as the WSGI server.

**Rationale:**
- Team familiarity with Python
- Lightweight and simple for a URL shortener
- Large ecosystem of extensions
- Easy integration with Prometheus client library
- Gunicorn provides production-ready multi-worker deployment

**Consequences:**
- Synchronous by default (not ideal for high I/O)
- Need to manage worker processes carefully
- Good enough performance for our scale (~2500 RPS)

---

## ADR-002: PostgreSQL as Primary Database

**Status:** Accepted

**Context:**
Need a reliable database for storing URL mappings. Options:
- PostgreSQL
- MySQL
- SQLite
- MongoDB

**Decision:**
Use PostgreSQL 16.

**Rationale:**
- ACID compliance for data integrity
- Excellent performance for read-heavy workloads
- Strong ecosystem and tooling
- Team experience
- Free and open source

**Consequences:**
- Need to manage connection pooling
- Slightly more setup than SQLite
- Proven reliability at scale

---

## ADR-003: Redis for Caching

**Status:** Accepted

**Context:**
URL redirects are read-heavy. Most URLs are accessed repeatedly. We need to reduce database load.

**Decision:**
Use Redis as a caching layer with 5-minute TTL.

**Rationale:**
- Sub-millisecond read latency
- Simple key-value model perfect for URL lookups
- Built-in TTL support
- Industry standard for caching
- Reduces database queries by ~90% for popular URLs

**Consequences:**
- Additional infrastructure component
- Need graceful fallback when Redis is unavailable
- Cache invalidation complexity (mitigated by TTL)

**Implementation:**
```python
# Check cache first
cached = redis_client.get(f"url:{code}")
if cached:
    return redirect(cached)
# Fall back to database
```

---

## ADR-004: Nginx as Load Balancer

**Status:** Accepted

**Context:**
Running multiple Flask instances requires load balancing. Options:
- Nginx
- HAProxy
- Traefik
- AWS ALB

**Decision:**
Use Nginx as reverse proxy and load balancer.

**Rationale:**
- Industry standard, battle-tested
- Handles 10,000+ concurrent connections
- Built-in health checks
- Static file serving
- Familiar configuration
- Excellent documentation

**Consequences:**
- Single point of entry (could be SPOF without HA setup)
- Configuration file management
- Good performance for our scale

**Configuration:**
```nginx
upstream flask_app {
    server app1:5000;
    server app2:5000;
    server app3:5000;
    server app4:5000;
    server app5:5000;
}
```

---

## ADR-005: 5 Application Replicas

**Status:** Accepted

**Context:**
Need to determine the number of Flask instances for high availability and performance.

**Decision:**
Deploy 5 Flask application replicas.

**Rationale:**
- Provides redundancy (can lose 4 instances and still serve traffic)
- Distributes load across multiple workers
- Each instance runs 4 Gunicorn workers = 20 total workers
- Matches typical production deployment patterns
- Sufficient for handling 2500+ RPS

**Consequences:**
- Higher resource usage
- More containers to monitor
- Better fault tolerance

---

## ADR-006: Prometheus for Metrics

**Status:** Accepted

**Context:**
Need metrics collection for observability. Options:
- Prometheus
- InfluxDB
- Datadog
- CloudWatch

**Decision:**
Use Prometheus with pull-based scraping.

**Rationale:**
- Open source and free
- Pull model is simpler (no agent push configuration)
- Powerful query language (PromQL)
- Native Grafana integration
- Industry standard for Kubernetes/containers
- Alertmanager integration

**Consequences:**
- Need to expose /metrics endpoint
- Scrape intervals affect data resolution
- Storage management for long retention

---

## ADR-007: Grafana + Loki for Observability

**Status:** Accepted

**Context:**
Need dashboards and log aggregation. Options:
- Grafana + Loki
- ELK Stack (Elasticsearch, Logstash, Kibana)
- Datadog
- Splunk

**Decision:**
Use Grafana for dashboards and Loki for log aggregation.

**Rationale:**
- Loki is lightweight (doesn't index log content)
- Native Grafana integration
- Lower resource usage than ELK
- Label-based querying matches Prometheus model
- Promtail agent is simple to configure
- Free and open source

**Consequences:**
- Less powerful full-text search than Elasticsearch
- Sufficient for our log analysis needs
- Easy correlation between metrics and logs

---

## ADR-008: Structured JSON Logging

**Status:** Accepted

**Context:**
Need consistent, parseable logs for debugging and analysis.

**Decision:**
Use structured JSON logging for all application logs.

**Rationale:**
- Machine-parseable
- Easy to query in Loki
- Consistent format across all instances
- Rich context (timestamps, levels, components)
- Industry best practice

**Example:**
```json
{
  "timestamp": "2026-04-05T12:00:00Z",
  "level": "INFO",
  "component": "urls",
  "message": "URL shortened",
  "short_code": "abc123"
}
```

---

## ADR-009: Three-Tier Alerting

**Status:** Accepted

**Context:**
Need to notify the team of issues without causing alert fatigue.

**Decision:**
Implement three severity tiers with different notification channels.

**Rationale:**
- Critical: Wake someone up (PagerDuty + Discord + Email)
- Warning: Investigate soon (Discord + Email)
- Info: Awareness only (Discord)

**Consequences:**
- Clear escalation path
- Reduces alert fatigue
- Ensures critical issues get immediate attention

---

## ADR-010: Docker Compose for Orchestration

**Status:** Accepted

**Context:**
Need container orchestration for local development and deployment. Options:
- Docker Compose
- Kubernetes
- Docker Swarm
- Nomad

**Decision:**
Use Docker Compose.

**Rationale:**
- Simple single-file configuration
- Perfect for hackathon/development
- Easy to run locally
- No cluster management overhead
- Sufficient for our scale

**Consequences:**
- Single-host limitation
- No built-in service mesh
- Would need Kubernetes for true production scale

---

## ADR-011: Graceful Redis Fallback

**Status:** Accepted

**Context:**
Redis failure shouldn't cause complete service outage.

**Decision:**
Implement graceful degradation when Redis is unavailable.

**Rationale:**
- Service continues working (slower, but functional)
- Database serves as fallback
- Logs indicate Redis issues for investigation
- Follows "design for failure" principle

**Implementation:**
```python
try:
    cached = redis_client.get(f"url:{code}")
except Exception:
    logger.warning("Redis unavailable", extra={"redis_down": True})
    # Fall through to database query
```

**Consequences:**
- Higher latency when Redis is down
- Database load increases during Redis outage
- Service remains available

---

## Future Considerations

### Not Implemented (Out of Scope)

1. **Kubernetes** - Would be next step for production scale
2. **Service Mesh** - Not needed at current scale
3. **Distributed Tracing** - Considered Tempo, but added complexity
4. **Rate Limiting** - Would add for production
5. **Authentication** - Not required for hackathon scope
