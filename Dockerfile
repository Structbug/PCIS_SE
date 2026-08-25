# ── Stage 1: Build frontend ──────────────────────────────────────
FROM node:20-alpine AS frontend
WORKDIR /app/frontend
# This project uses npm and commits package-lock.json.  Copying only the two
# files avoids a Docker build failure when optional Yarn/PNPM lockfiles do not
# exist, and npm ci keeps deployments reproducible.
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# ── Stage 2: Python + Django ────────────────────────────────────
FROM python:3.12-slim AS backend
# Keep the repository layout intact in the final image.  Django's settings
# resolve the SPA to BASE_DIR.parent / "frontend", so the backend needs to
# live in /app/django_migration and the compiled frontend in /app/frontend.
WORKDIR /app/django_migration

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev gcc wget && \
    rm -rf /var/lib/apt/lists/*

COPY django_migration/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY django_migration/ ./

# Copy the SPA into the location used by config.settings.base.
COPY --from=frontend /app/frontend/dist /app/frontend/dist

EXPOSE 8000

# `migrate` is safe to repeat and ensures a new release never starts against
# an older schema. `exec` passes termination signals on to Gunicorn cleanly.
CMD ["sh", "-c", "python manage.py migrate --noinput && exec gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 3"]

# Coolify honours a Dockerfile health check. wget is installed above solely
# for this probe; /healthz is deliberately public and does not expose data.
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD wget --no-verbose --tries=1 --spider http://127.0.0.1:8000/healthz || exit 1
