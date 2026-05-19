# Tenant Management API Documentation

## Overview
This module provides multi-tenant support with SQLAlchemy-based database access. It includes:
- **Tenant Creation**: Create new tenants via YAML configuration files
- **User Management**: Automatically create tenant users with strong passwords
- **Role-Based Access Control**: Assign roles to users (tenant, admin, etc.)
- **Database Agnostic**: Works with SQLite, PostgreSQL, MySQL, and other databases

## Database Setup

### Directory Structure
```
db/
├── __init__.py         # Module init
├── database.py         # SQLAlchemy configuration and session management
├── models.py           # SQLAlchemy ORM models (Tenant, User, Role)
└── crud.py            # CRUD operations for database models
```

### Database Configuration
The database URL is configured via the `DATABASE_URL` environment variable:

```python
# Default (SQLite)
DATABASE_URL=sqlite:///D:/s1_rag_engine/sql_lite_db/rag_admin.sqlite3

# PostgreSQL
DATABASE_URL=postgresql://user:password@localhost/rag_admin

# MySQL
DATABASE_URL=mysql+pymysql://user:password@localhost/rag_admin
```

## API Endpoints

### Create Tenant via YAML Upload
**Endpoint**: `POST /api/v1/tenant/create`

**Authentication**: Bearer Token (Header: `Authorization: Bearer <token>`)

**Required Parameters**:
- `file`: YAML file upload with tenant configuration

**YAML Format**:
```yaml
tenant:
  name: "Tenant Name"
  description: "Optional description"
```

**Request Example**:
```bash
curl -X POST http://localhost:8000/api/v1/tenant/create \
  -H "Authorization: Bearer your-secure-token-here" \
  -F "file=@tenant_config.yaml"
```

**Success Response** (200):
```json
{
  "tenant_pkid": "acme-corporation",
  "tenant_name": "Acme Corporation",
  "username": "acme-corporation",
  "password": "X9k@Lp2mQ#wR4vT$",
  "message": "Tenant 'Acme Corporation' and user 'acme-corporation' created successfully"
}
```

**Error Responses**:
- `400`: Invalid YAML format or missing required fields
- `401`: Missing or invalid authentication token
- `409`: Tenant or user already exists
- `500`: Server error

## Database Models

### Tenant Model
```python
class Tenant(Base):
    id: int                    # Primary key
    tenant_pkid: str          # Unique tenant identifier (generated from name)
    name: str                 # Tenant name
    description: str          # Optional description
    config_file: str          # YAML configuration content
    is_active: bool           # Active status (default: True)
    created_at: datetime      # Creation timestamp
    updated_at: datetime      # Last update timestamp
    users: List[User]         # Related users
```

### User Model
```python
class User(Base):
    id: int                    # Primary key
    username: str             # Unique username
    email: str                # Optional email
    password_hash: str        # Hashed password (bcrypt)
    tenant_id: int            # Foreign key to Tenant
    role_id: int              # Foreign key to Role
    is_active: bool           # Active status (default: True)
    is_admin: bool            # Admin flag (default: False)
    created_at: datetime      # Creation timestamp
    updated_at: datetime      # Last update timestamp
    last_login: datetime      # Last login timestamp
    tenant: Tenant            # Related tenant
    role: Role                # Related role
```

### Role Model
```python
class Role(Base):
    id: int                    # Primary key
    name: str                 # Role name (e.g., "tenant", "admin")
    description: str          # Role description
    created_at: datetime      # Creation timestamp
    users: List[User]         # Related users
```

## CRUD Operations

All CRUD operations are located in `db/crud.py`:

### Create Tenant
```python
tenant = crud.create_tenant(
    db=db,
    tenant_pkid="acme-corp",
    name="Acme Corporation",
    config_yaml="<YAML content>"
)
```

### Get Tenant by PKID
```python
tenant = crud.get_tenant_by_pkid(db, "acme-corp")
```

### Create User for Tenant
```python
user = crud.create_user_for_tenant(
    db=db,
    tenant_id=tenant.id,
    username="acme-corp",
    password="plaintext_password",  # Will be hashed
    email="admin@acme.com",
    role_id=None  # Uses default 'tenant' role
)
```

### Get User by Username
```python
user = crud.get_user_by_username(db, "acme-corp")
```

## Security Features

### Password Generation
Strong passwords are generated with:
- Minimum 16 characters
- Mixed case letters (uppercase & lowercase)
- Numbers and special characters
- Cryptographically secure random generation

```python
from auth.security import generate_strong_password

password = generate_strong_password(length=16)
# Example: "X9k@Lp2mQ#wR4vT$"
```

### Password Hashing
Passwords are hashed using bcrypt (12 rounds) for secure storage:

```python
from auth.security import get_password_hash, verify_password

# Hash a password
hashed = get_password_hash("plaintext_password")

# Verify a password
is_valid = verify_password("plaintext_password", hashed)
```

### Bearer Token Verification
The endpoint verifies bearer tokens from the Authorization header:

```bash
# Request with token
curl -H "Authorization: Bearer your-token" \
  -F "file=@config.yaml" \
  http://localhost:8000/api/v1/tenant/create
```

**Important**: In production, update the `VALID_TOKEN` in the endpoint to use:
- Environment variables
- Database-stored tokens
- JWT tokens
- OAuth2 integration

## Environment Configuration

### Setting Database URL
```bash
# Linux/Mac
export DATABASE_URL=postgresql://user:password@localhost/rag_admin

# Windows PowerShell
$env:DATABASE_URL="postgresql://user:password@localhost/rag_admin"

# Windows CMD
set DATABASE_URL=postgresql://user:password@localhost/rag_admin
```

### Setting API Token
```bash
# Linux/Mac
export VALID_TOKEN=your-secure-token-here

# Windows PowerShell
$env:VALID_TOKEN="your-secure-token-here"

# Windows CMD
set VALID_TOKEN=your-secure-token-here
```

## Database Initialization

The database is automatically initialized on FastAPI startup:

```python
@app.on_event("startup")
def startup_event():
    init_db()  # Creates all tables if they don't exist
```

To manually initialize:
```python
from db.database import init_db
init_db()
```

## Switching to PostgreSQL/MySQL

The current setup uses SQLite. To switch to PostgreSQL:

1. Install PostgreSQL driver:
   ```bash
   pip install psycopg2-binary
   ```

2. Update `DATABASE_URL`:
   ```
   postgresql://user:password@localhost:5432/rag_admin
   ```

3. Create database:
   ```sql
   CREATE DATABASE rag_admin;
   ```

The models and code remain unchanged - the SQLAlchemy abstraction handles the database differences.

## Workflow Example

1. **Create YAML file** (`tenant_config.yaml`):
   ```yaml
   tenant:
     name: "Acme Corporation"
     description: "Main tenant for Acme Corp"
   ```

2. **Upload and create tenant**:
   ```bash
   curl -X POST http://localhost:8000/api/v1/tenant/create \
     -H "Authorization: Bearer your-token" \
     -F "file=@tenant_config.yaml"
   ```

3. **Response received**:
   ```json
   {
     "tenant_pkid": "acme-corporation",
     "tenant_name": "Acme Corporation",
     "username": "acme-corporation",
     "password": "X9k@Lp2mQ#wR4vT$",
     "message": "Tenant 'Acme Corporation' and user 'acme-corporation' created successfully"
   }
   ```

4. **Save credentials securely** for the tenant admin

5. **User can now login** with:
   - Username: `acme-corporation`
   - Password: `X9k@Lp2mQ#wR4vT$`

## Troubleshooting

### Database Connection Error
- Check `DATABASE_URL` environment variable
- Verify database server is running
- Check database credentials and permissions

### Token Invalid Error
- Verify Bearer token in Authorization header
- Check token value matches expected token in code
- Ensure `Authorization: Bearer <token>` format is correct

### YAML Parse Error
- Verify YAML file format is correct
- Ensure `tenant.name` field is present
- Check for proper indentation in YAML

## Notes

- The `tenant_pkid` is auto-generated from tenant name (lowercased, spaces replaced with hyphens)
- The initial user is created with role `tenant`
- Passwords are not stored in plain text - only bcrypt hashes are stored
- All timestamps use UTC
