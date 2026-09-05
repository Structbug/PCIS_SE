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

## Local Development Setup

### Prerequisites

- Python 3.12 or newer
- Node.js 20 or newer and npm
- PostgreSQL for production deployments

### 1. Configure the backend

From the repository root, create and activate a virtual environment:

PowerShell:

```powershell
cd django_migration
Copy-Item .env.example .env
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Set real values for `DJANGO_SECRET_KEY` and `ACCESS_TOKEN_SECRET` in `.env`.

For a Unix-like shell, activate the environment with:

```bash
source .venv/bin/activate
```

Set real values for `DJANGO_SECRET_KEY` and `ACCESS_TOKEN_SECRET` in `.env`.
Development uses `dev.sqlite3` by default. For production, configure
`DJANGO_SETTINGS_MODULE=config.settings.prod` and a PostgreSQL `DATABASE_URL`.

### 2. Install dependencies and migrate

From `django_migration/`:

```bash
pip install -r requirements.txt
python manage.py migrate
```

Optionally create an administrator account:

```bash
python manage.py createsuperuser
```

### 3. Start the backend

From `django_migration/`:

```bash
python manage.py runserver 127.0.0.1:8000
```

The API is available at `http://127.0.0.1:8000/api/v1/`. The health check is
available at `http://127.0.0.1:8000/healthz`.

### 4. Start the frontend

In a second terminal, from the repository root:

```bash
cd frontend
npm install
npm run dev
```

The React application opens at `http://localhost:5173`. Its Vite development
proxy forwards `/api` requests to `http://127.0.0.1:8000`.

## API Overview

The API uses cookie-based JWT authentication, with protected endpoints requiring
an authenticated user. Main route groups include:

| Route group | Purpose |
| --- | --- |
| `/api/v1/users/` | Registration, login, logout, profiles, passwords, and user administration |
| `/api/v1/floors/` | Floor management |
| `/api/v1/departments/` | Department management |
| `/api/v1/room-types/` | Room type management |
| `/api/v1/rooms/` | Room creation, search, and floor filtering |
| `/api/v1/categories/` | Categories and subcategories |
| `/api/v1/items/` | Item management, search, import, filtering, history, and status updates |
| `/api/v1/inventory/` | Inventory statistics and activity logs |

Useful endpoints include:

```text
POST /api/v1/users/login
POST /api/v1/users/register
GET  /api/v1/users/current-user
GET  /api/v1/items/all/1
GET  /api/v1/items/search
GET  /api/v1/inventory/stats
GET  /healthz
```

Permissions are enforced by the backend, so users only see and change data
allowed by their role.

## Testing

Backend tests use Django's test runner. From `django_migration/`:

```bash
python manage.py test
```

To run the frontend checks, from `frontend/`:

```bash
npm run build
npm run lint
```

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

