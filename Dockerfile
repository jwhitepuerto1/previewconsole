# CRM backend (FastAPI). Build context is crm/ itself, not the repo root —
# see docker-compose.yml. Inside the container there's no root app/ package
# to collide with (that's a repo-root-only concern from local dev, handled
# there via --app-dir), so app.main:app resolves naturally.
FROM python:3.12-slim

WORKDIR /code

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ ./app/
COPY migrations/ ./migrations/
COPY alembic.ini .
COPY scripts/ ./scripts/

EXPOSE 8001

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]
