# PCIS-SE

PCIS-SE is an inventory management system with a Django REST Framework backend
and a React + TypeScript frontend. It supports authenticated inventory
operations across floors, departments, room types, rooms, categories,
subcategories, items, and activity logs.

## Live Application

[Open PCIS-SE](https://pcis.itclub.asmitphuyal.com.np/login)

## Features

- Secure user registration, login, logout, and token-based authentication
- Inventory management for items, costs, categories, and subcategories
- Organization of inventory by floors, departments, room types, and rooms
- Searchable and filterable inventory views
- Dashboard charts for inventory and activity insights
- Activity log tracking for important inventory operations
- Role-based permissions and protected API endpoints
- Responsive React interface with dedicated management screens

## System Roles

| Role | Capabilities |
| --- | --- |
| **User** | View and manage inventory records according to assigned permissions |
| **Admin** | Manage users, inventory configuration, system-wide records, and activity oversight |

## Project Structure

```text
PCIS_SE/
├── django_migration/   Django project, REST API, migrations, and tests
├── frontend/            React + TypeScript + Vite single-page application
└── README.md            Project documentation
```

## Tech Stack

- **Frontend:** React 19, TypeScript, Vite, Axios, and React Router
- **Backend:** Django 5.2 and Django REST Framework
- **Authentication:** JWT access and refresh tokens in HTTP-only cookies
- **Database:** SQLite for development and PostgreSQL for production

## Requirements

- Python 3.12 or newer
- Node.js 20 or newer and npm
- PostgreSQL for production deployments

Development uses `django_migration/dev.sqlite3` by default. PostgreSQL is
required when using the production settings.

## Getting Started

### 1. Configure the backend

PowerShell:

```powershell
cd django_migration
Copy-Item .env.example .env
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Set real values for `DJANGO_SECRET_KEY` and `ACCESS_TOKEN_SECRET` in `.env`.
The application rejects the placeholder values from `.env.example`.

For a Unix-like shell, activate the environment with:

```bash
source .venv/bin/activate
```

### 2. Run migrations and start Django

From `django_migration/`:

```bash
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

The API is available at `http://127.0.0.1:8000/api/v1/`, and the health check
is available at `http://127.0.0.1:8000/healthz`.

### 3. Start the frontend

In a second terminal:

```bash
cd frontend
npm install
npm run dev
```

Open the Vite URL shown in the terminal, usually `http://localhost:5173`.
The frontend sends API requests to `/api/v1` and uses the development CORS
allowlist configured by the backend.

## Useful Commands

Backend, from `django_migration/`:

```bash
python manage.py test
python manage.py makemigrations
python manage.py check
```

Frontend, from `frontend/`:

```bash
npm run build
npm run lint
npm run preview
```

## Authentication

Authentication uses JWT access and refresh tokens stored in HTTP-only cookies.
The main endpoints are:

- `POST /api/v1/users/login`
- `POST /api/v1/users/register`
- `POST /api/v1/users/refresh`
- `POST /api/v1/users/logout`
- `GET /api/v1/users/current-user`

Most API endpoints require an authenticated user. See
`django_migration/apps/accounts/` for authentication, permissions, and user
management code.

## Team

Group Name: **R74WC**

- [Abhaya Shrestha](https://github.com/Abhaya-Shresthaa) (080BCT006)
- [Aman Ranabhat](https://github.com/AmanRB13) (080BCT013)
- [Aryan Dahal](https://github.com/Structbug) (080BCT016)

