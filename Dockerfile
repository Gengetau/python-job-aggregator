FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV JOB_AGGREGATOR_DATABASE_URL=sqlite:///./data/job_aggregator.db

WORKDIR /app

COPY pyproject.toml README.md ./
COPY job_aggregator ./job_aggregator

RUN python -m pip install --no-cache-dir --upgrade pip \
    && python -m pip install --no-cache-dir .

RUN mkdir -p /app/data

EXPOSE 8000

CMD ["uvicorn", "job_aggregator.app.api.app:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
