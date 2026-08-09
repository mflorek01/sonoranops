FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONPATH=/app/simulator

WORKDIR /app
COPY simulator /app/simulator
COPY packages/contracts /app/packages/contracts

RUN python -m pip install --upgrade pip \
    && python -m pip install "jsonschema>=4.23,<5.0"

WORKDIR /app/simulator
ENTRYPOINT ["python", "-m", "sonoran_sim.run"]
