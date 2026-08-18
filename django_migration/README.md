# Django migration backend

This directory is the Django/DRF migration target. The current phase contains
only the project foundation and authentication; it intentionally contains no
inventory business resources.

## Configuration

```bash
cd django_migration
cp .env.example .env
```

Set `DATABASE_URL` to PostgreSQL in `.env`. Development and production both use
PostgreSQL. The `config.settings.test` module uses an isolated SQLite database
solely for fast local tests when a PostgreSQL service is unavailable.

`ACCESS_TOKEN_EXPIRY` and `REFRESH_TOKEN_EXPIRY` accept the existing MERN
format: `<number>m`, `<number>h`, or `<number>d` (for example `1d` and `10d`).
SimpleJWT uses `ACCESS_TOKEN_SECRET` as the signing key for both token types;
the legacy `REFRESH_TOKEN_SECRET` remains in the example only to make the
configuration transition explicit.

## Run against PostgreSQL

```bash
./.venv/bin/pip install -r requirements.txt
./.venv/bin/python manage.py migrate
./.venv/bin/python manage.py createsuperuser
./.venv/bin/python manage.py runserver
```

## Auth endpoints

- `POST /api/v1/users/login` — `{ "username", "password" }`; returns SimpleJWT
  access/refresh tokens and sets `accessToken`/`refreshToken` HTTP-only cookies.
- `POST /api/v1/users/register` — requires an authenticated user whose
  `role` is `Admin`; accepts `username`, `email`, `password`, `phone_number`,
  and `role`.
- `POST /api/v1/users/refresh` — `{ "refresh" }`; returns a new access token.
- `GET /api/v1/users/current-user` — requires an access token.

## Test

```bash
DJANGO_SETTINGS_MODULE=config.settings.test ./.venv/bin/python manage.py test apps.accounts -v 2
```
