# Failure Modes & Recovery

## 1. App Container Crashes
**What happens:** A Flask container dies unexpectedly.  
**How we handle it:** `restart: always` in docker-compose.yml automatically restarts any crashed container within seconds.  
**Evidence:** Kill a container with `docker stop <container>` → watch it resurrect in `docker ps`.

## 2. Bad Input / Invalid URLs
**What happens:** User sends malformed JSON, missing fields, or invalid URLs.  
**How we handle it:** Input validation in `services.py` catches bad data before it hits the database. Returns a clean JSON error with the appropriate HTTP status code (400, 409, 410) — never a stack trace.  
**Example response:**
```json
{"error": "URL must start with http:// or https://"}
```

## 3. Duplicate Short Codes
**What happens:** Two users try to create the same custom short code simultaneously.  
**How we handle it:** Database uniqueness constraint + ConflictError handler returns 409. The short_code field has a unique index enforced at the DB level.

## 4. Expired or Inactive URLs
**What happens:** A user tries to visit a short URL that has expired or been deactivated.  
**How we handle it:** Returns 410 Gone with a clear JSON message. Does not redirect.

## 5. Database Unavailable
**What happens:** PostgreSQL container goes down.  
**How we handle it:** App returns 500 with `{"error": "Internal server error"}` — no stack trace exposed to users. Postgres has a healthcheck; app containers won't start unless DB is healthy.

## 6. All App Instances Overloaded
**What happens:** Traffic spike overwhelms all 3 Flask containers.  
**How we handle it:** Nginx load balances across 3 instances. Redis caches frequent lookups reducing DB pressure. Tested with 500 concurrent users — 0% error rate at 276 RPS.

## 7. CI Blocks Bad Code
**What happens:** A developer pushes broken code.  
**How we handle it:** GitHub Actions runs 30 tests with 93% coverage on every push. Deployment is blocked if any test fails.