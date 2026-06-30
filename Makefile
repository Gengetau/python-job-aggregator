.PHONY: install test db-init seed-demo api docker-up docker-down

install:
	python -m pip install -e ".[dev]"

test:
	python -m pytest

db-init:
	python -m job_aggregator.app.cli.main db init

seed-demo:
	python -m job_aggregator.app.cli.main db seed-demo

api:
	uvicorn job_aggregator.app.api.app:create_app --factory --reload

docker-up:
	docker compose up --build

docker-down:
	docker compose down
