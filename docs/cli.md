# CLI Examples

Apply Alembic migrations to the configured database:

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

Run the explicit local `--all` set. It prints the adapter list before the run
summary:

```bash
python -m job_aggregator.app.cli.main crawl run --all
```

Run a configured Greenhouse board:

```bash
python -m job_aggregator.app.cli.main crawl run --adapter greenhouse --scope example --company "Example Inc"
```

Resume from the adapter scope and latest checkpoints associated with a previous
run:

```bash
python -m job_aggregator.app.cli.main crawl resume --run-id 1
```

Show conservative cross-source duplicate candidates:

```bash
python -m job_aggregator.app.cli.main jobs dedupe
```

Inspect recent runs:

```bash
python -m job_aggregator.app.cli.main runs show
```

Deactivate stale jobs:

```bash
python -m job_aggregator.app.cli.main jobs deactivate-stale --days 30
```
