# Fallback Dockerfile at repo root (if Render service uses Docker runtime).
FROM python:3.12-slim

WORKDIR /app

COPY creator-discovery/requirements-prod.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY creator-discovery/ .

EXPOSE 8000

CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
