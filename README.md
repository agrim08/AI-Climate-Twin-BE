# ClimateTwin India Backend

This is the production-ready FastAPI backend for **ClimateTwin India**, structured using a modular architecture with support for SQLAlchemy 2.0 (async), Alembic migrations, Pydantic v2, and Supabase PostgreSQL.

## Features

- **FastAPI**: Fully asynchronous web framework.
- **SQLAlchemy 2.0 (Async)**: Asynchronous database connection with modern Declarative Mapped models.
- **Supabase Integration**: Direct configuration for Supabase PostgreSQL. Includes connection pool-pre-pinging to avoid dropped connections.
- **Alembic**: Asynchronous migration setup.
- **Pydantic v2**: Type safety and data validation.
- **Modular Directory Structure**: Organized by core logic, models, schemas, routers, services, and utils.

---

## Folder Structure

```
backend/
├── app/
│   ├── main.py                 # Application entrypoint & configurations
│   ├── core/
│   │   ├── config.py           # Settings management (pydantic-settings)
│   │   └── database.py         # SQLAlchemy async engine & session setup
│   ├── models/
│   │   ├── __init__.py         # Imports models for Alembic autogeneration
│   │   └── climate_data.py     # SQLAlchemy declarative models
│   ├── schemas/
│   │   ├── __init__.py
│   │   └── climate_data.py     # Pydantic v2 validation models
│   ├── routers/
│   │   ├── __init__.py
│   │   └── climate_data.py     # API routes (GET, POST, PUT, DELETE)
│   ├── services/
│   │   ├── __init__.py
│   │   └── climate_data.py     # Business logic & database operations
│   └── utils/
│       └── __init__.py         # Utility functions & helpers
├── alembic/
│   ├── env.py                  # Alembic migration environment
│   ├── script.py.mako          # Migration template
│   └── versions/               # Directory for migration files
├── alembic.ini                 # Alembic configuration
├── requirements.txt            # Package dependencies
├── .env.example                # Sample environment variables config
└── README.md                   # Setup and execution guide
```

---

## Setup Instructions

### 1. Prerequisites
- Python 3.12+
- Access to a Supabase PostgreSQL instance (or any standard Postgres DB).

### 2. Local Setup
Clone/open the repository, navigate to the `backend/` directory, and perform the following steps:

1. **Create a virtual environment:**
   ```bash
   python -m venv venv
   source venv/Scripts/activate  # Windows (CMD/PowerShell)
   # OR
   source venv/bin/activate      # macOS/Linux
   ```

2. **Install dependencies:**
   ```bash
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

3. **Configure Environment Variables:**
   Copy `.env.example` to `.env` and configure your database parameters:
   ```bash
   cp .env.example .env
   ```
   *Note: If using Supabase, navigate to **Project Settings -> Database** in your Supabase dashboard and copy the connection string under **Connection string -> URI** to `DATABASE_URL` in `.env`.*

---

## Database Migrations (Alembic)

All migrations run asynchronously.

### 1. Generating a migration
When you update or add any model in `app/models/`, run:
```bash
alembic revision --autogenerate -m "Add climate records table"
```

### 2. Applying migrations
To apply all pending migrations to your database:
```bash
alembic upgrade head
```

### 3. Downgrading migrations
To rollback the latest migration:
```bash
alembic downgrade -1
```

---

## Running the Server

Start the local development server with Uvicorn:
```bash
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

- **API Documentation**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs) (Swagger UI)
- **Alternative Documentation**: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc) (ReDoc)
- **Health Check Endpoint**: [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health)
