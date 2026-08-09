FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app
COPY services/api /app/services/api
COPY infra /app/infra

RUN python -m pip install --upgrade pip && python -m pip install /app/services/api

WORKDIR /app/services/api
EXPOSE 8000

CMD ["sh", "-c", "alembic -c /app/infra/alembic.ini upgrade head && exec uvicorn app.main:app --host 0.0.0.0 --port 8000"]
