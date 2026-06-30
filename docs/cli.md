# CLI Examples

Initialize the local SQLite schema:

```bash
python -m job_aggregator.app.cli.main db init
```

Seed deterministic demo jobs:

```bash
python -m job_aggregator.app.cli.main db seed-demo
```

Run the demo crawl:

```bash
python -m job_aggregator.app.cli.main crawl run
```

Run a configured Greenhouse board:

```bash
python -m job_aggregator.app.cli.main crawl run --adapter greenhouse --scope example --company "Example Inc"
```

Inspect recent runs:

```bash
python -m job_aggregator.app.cli.main runs show
```

Deactivate stale jobs:

```bash
python -m job_aggregator.app.cli.main jobs deactivate-stale --days 30
```
