# Admin UI FastAPI

Lightweight administrative API for managing tenants and users, built with FastAPI and SQLAlchemy.

**Key features**
- **Authentication:** username/password login with token issuance
- **Tenant management:** list tenants, view tenant details and configs
- **Observability:** execution timing decorators applied across the codebase for latency tracking

**Prerequisites**
- Python 3.10+
- A virtual environment (recommended)

**Quick Start**

1. Create and activate a virtual environment (Windows PowerShell):

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

2. Install dependencies:

```powershell
pip install -r app/requirements.txt
```

3. Run the application (development):

```powershell
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at `http://localhost:8000` and the OpenAPI docs at `http://localhost:8000/docs`.

**Repository layout**
- **app/** — application package
**Folder & files**

- **app/** — core application package
  - [app/main.py](app/main.py#L1) : FastAPI application factory, app startup tasks and root endpoint
  - [app/config/](app/config) : configuration utilities
    - [app/config/logger.py](app/config/logger.py#L1) : logger setup used across the app
    - [app/config/timer.py](app/config/timer.py#L1) : execution timing decorator `log_execution_time`
    - other config helpers (e.g., settings) live under `app/core` and `app/config`
  - [app/core/](app/core) : core application logic and configuration
    - [app/core/config.py](app/core/config.py#L1) : application settings and paths
    - [app/core/security.py](app/core/security.py#L1) : password hashing, token management and auth helpers
  - [app/db/](app/db) : database bootstrap and session management
    - [app/db/base.py](app/db/base.py#L1) : SQLAlchemy Base and engine
    - [app/db/session.py](app/db/session.py#L1) : `get_session()` factory used by services
  - [app/models/](app/models) : SQLAlchemy table models
    - [app/models/tables.py](app/models/tables.py#L1) : `User`, `Role`, `Tenant`, `Config` table definitions
  - [app/schemas/](app/schemas) : Pydantic schema models
    - [app/schemas/schemas.py](app/schemas/schemas.py#L1) : request/response models used by routers
  - [app/routers/](app/routers) : FastAPI route modules
    - [app/routers/auth.py](app/routers/auth.py#L1) : `/auth` routes: login, logout, /me
    - [app/routers/tenants.py](app/routers/tenants.py#L1) : tenant-related endpoints and placeholders
  - [app/services/](app/services) : business logic and DB interactions
    - [app/services/auth_service.py](app/services/auth_service.py#L1) : user loading, authentication, setup helpers
    - [app/services/tenant_service.py](app/services/tenant_service.py#L1) : tenant CRUD/query helpers and authorization

- Root-level files and assets
  - [requirements.txt](app/requirements.txt) : Python dependencies (used by quick-start)
  - [config.yaml](config.yaml) : optional project configuration consumed by tenant services
  - [rag_admin.sqlite3](rag_admin.sqlite3) : example SQLite DB file created during development
  - [admin_ui_fastapi.postman_collection.json](admin_ui_fastapi.postman_collection.json) : Postman collection for manual API testing
  - [app/README.md](README.md) : this document
  - [logs/](logs) : runtime logs (created at runtime)
  - utility scripts and experiments: `nova_test.py`, `bedrock_inference.py`, `embedding_model.py`

**Observability / Timing decorator**

This project includes an execution-timing decorator implemented in [app/config/timer.py](app/config/timer.py#L1). To provide latency tracking and basic observability, the decorator `log_execution_time(logger)` has been applied across routes and service functions. Example log entries produced by the decorator:

```
authenticate_user execution started
authenticate_user execution completed successfully
authenticate_user execution completed in 0.0821 seconds
```

Notes:
- The decorator only adds logging (start/finish/duration). It does not modify function behavior, responses, or flow.
- For FastAPI routes the decorator is applied after the route decorator to preserve route behavior (e.g., `@router.post(...)` then `@log_execution_time(logger)`).

**Development notes**
- Database: uses SQLAlchemy with the local SQLite DB `rag_admin.sqlite3` by default.
- Initial setup is performed automatically on app start via `ensure_setup()` in [app/services/auth_service.py](app/services/auth_service.py#L1).
- To view logs, check the configured logger sink (see [app/config/logger.py](app/config/logger.py#L1)).

**Contributing**
- Open an issue or submit a PR. Keep changes focused and add tests where applicable.

**License**
- (Add your project license here)

--
Generated README for the Admin UI FastAPI project.
