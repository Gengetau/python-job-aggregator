# API Examples

Start the API:

```bash
uvicorn job_aggregator.app.api.app:create_app --factory --reload
```

Seed demo data:

```bash
python -m job_aggregator.app.cli.main db seed-demo
```

Example calls:

```bash
curl http://localhost:8000/health
curl "http://localhost:8000/jobs?q=python&page=1&page_size=10"
curl "http://localhost:8000/jobs?location_type=remote&employment_type=full_time"
curl http://localhost:8000/sources
curl http://localhost:8000/runs
curl "http://localhost:8000/dedupe/candidates?limit=20&scanned_limit=1000"
curl -X POST http://localhost:8000/admin/crawl -H "Content-Type: application/json" -d "{\"adapters\":[\"demo\"]}"
```

Admin crawl requests can pass adapter-specific options:

```bash
curl -X POST http://localhost:8000/admin/crawl \
  -H "Content-Type: application/json" \
  -d "{\"adapters\":[\"lever\"],\"options\":{\"lever\":{\"company_slug\":\"example\",\"company_name\":\"Example Inc\"}}}"
```

Dedupe candidates are read-only review groups. Use `include_inactive=true` when
inactive jobs should be considered during manual review:

```bash
curl "http://localhost:8000/dedupe/candidates?include_inactive=true"
```

The API returns confidence and reason fields to support human decisions; it does
not merge or mutate job records.

OpenAPI docs are generated automatically at:

- `http://localhost:8000/docs`
- `http://localhost:8000/openapi.json`
