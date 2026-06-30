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
curl -X POST http://localhost:8000/admin/crawl -H "Content-Type: application/json" -d "{\"adapters\":[\"demo\"]}"
```

OpenAPI docs are generated automatically at:

- `http://localhost:8000/docs`
- `http://localhost:8000/openapi.json`
