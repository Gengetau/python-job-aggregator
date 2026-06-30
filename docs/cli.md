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

Resume from the adapter state captured by a previous run:

```bash
python -m job_aggregator.app.cli.main crawl resume --run-id 1
```

The resume command uses that run's stored `adapter_name`, `scope_key`, and
`checkpoint_after` values. It does not pick the newest global checkpoint.

Run a custom careers page with default selectors:

```bash
python -m job_aggregator.app.cli.main crawl run \
  --adapter custom_page \
  --listing-url "https://example.com/careers" \
  --company "Example Inc"
```

Run a custom careers page from JSON config:

```bash
python -m job_aggregator.app.cli.main crawl run \
  --adapter custom_page \
  --config-file custom-page.json
```

Show conservative cross-source duplicate candidates:

```bash
python -m job_aggregator.app.cli.main jobs dedupe --limit 20 --scanned-limit 1000
```

Include inactive jobs in the manual review set:

```bash
python -m job_aggregator.app.cli.main jobs dedupe --include-inactive
```

Candidate groups are for human review and are never merged automatically.

Inspect recent runs:

```bash
python -m job_aggregator.app.cli.main runs show
```

Deactivate stale jobs:

```bash
python -m job_aggregator.app.cli.main jobs deactivate-stale --days 30
```
