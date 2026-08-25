# ── Stage 1: Build frontend ──────────────────────────────────────
FROM node:20-alpine AS frontend
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json* frontend/yarn.lock* frontend/pnpm-lock.yaml* ./
RUN npm ci || npm install
COPY frontend/ ./
RUN npm run build

# ── Stage 2: Python + Django ────────────────────────────────────
FROM python:3.12-slim AS backend
WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev gcc && \
    rm -rf /var/lib/apt/lists/*

COPY django_migration/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY django_migration/ ./

# Copy built frontend into where Django expects it (frontend/dist relative to BASE_DIR)
COPY --from=frontend /app/frontend/dist ./frontend/dist

RUN python manage.py collectstatic --noinput || true

EXPOSE 8000

CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3"]
