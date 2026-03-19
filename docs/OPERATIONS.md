## Operations Runbook

### Starting services locally

- Ensure Docker is running.
- Copy `.env.example` to `.env` and adjust values as needed.
- Start the stack:

```bash
docker compose up --build
```

Services will expose `/health` and `/metrics` on their respective ports.

### Worker runtime

- In Docker, the worker container runs the risk pipeline loop via:

```bash
python -m services.worker.main
```

- To run the worker locally without Docker:

```bash
export APP_ENV=local
export POSTGRES_HOST=localhost
export REDIS_HOST=localhost
python -m services.worker.main
```

The worker will:

- Continuously consume ingestion events from Redis.
- Persist risk assessments to PostgreSQL.
- Log startup, shutdown, and errors to stdout.

### Health and metrics

- Health endpoints:
  - `GET /health` on each service.
- Metrics:
  - `GET /metrics` on each service (Prometheus exposition format).
  - Worker-specific counter:

    - `worker_risk_assessments_total{result="success|duplicate|missing_transaction|error"}`

      - **success**: new risk assessment created.
      - **duplicate**: event already processed for the same `event_id`.
      - **missing_transaction**: event references a transaction that does not exist.
      - **error**: unrecoverable error after retries.

### Handling common failures

- **Database unavailable**
  - Symptoms:
    - Migration smoke test fails.
    - Worker logs transient database errors and eventually `error` results.
  - Actions:
    - Verify PostgreSQL is running and reachable using the configured env vars.
    - Re-run migrations:

      ```bash
      alembic upgrade head
      ```

- **Redis unavailable**
  - Symptoms:
    - Worker logs Redis errors with backoff messages.
  - Actions:
    - Ensure Redis is running and reachable.
    - Once restored, the worker will resume consuming events after backoff.

- **Worker crashes repeatedly**
  - Symptoms:
    - Logs show "Risk pipeline loop crashed" followed by restarts (depending on orchestrator).
  - Actions:
    - Inspect logs for underlying exceptions.
    - Check DB and Redis availability.
    - Verify schema is up to date (`alembic upgrade head`).

### Auth secret/key rotation

- Configuration:
  - `AUTH_SECRET_KEY`, `AUTH_ALGORITHM`, `AUTH_AUDIENCE`, `AUTH_ISSUER` are configured via environment variables (see `.env.example`).
- Rotation guidance (current HS256 setup):
  - **Do not** use the `INSECURE-DEV-ONLY` default in production.
  - Generate a strong, random secret for `AUTH_SECRET_KEY`.
  - Deploy the new secret to all backend services simultaneously (via environment or secret manager).
  - Restart services to pick up the new key.
  - If you later adopt key IDs (`kid`) and key sets, you can support overlapping keys for smoother rotation; this is a recommended future enhancement but not implemented yet.

