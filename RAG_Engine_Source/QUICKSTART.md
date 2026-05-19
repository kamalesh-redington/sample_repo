# Quick Start Guide - Tenant Management API

## Installation & Setup

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Initialize Database
```bash
python init_db.py
```

This will:
- Create SQLite database at `D:\s1_rag_engine\sql_lite_db\rag_admin.sqlite3`
- Create tables: `tenants`, `users`, `roles`
- Create default roles: `admin`, `tenant`, `viewer`, `editor`

### 3. Start FastAPI Server
```bash
uvicorn app:app --reload
```

Server will run at: `http://localhost:8000`

## Create Your First Tenant

### 1. Create Configuration File (`tenant.yaml`)
```yaml
tenant:
  name: "Your Company Name"
  description: "Optional description"
```

### 2. Upload to Create Tenant
```bash
curl -X POST http://localhost:8000/api/v1/tenant/create \
  -H "Authorization: Bearer your-secure-token-here" \
  -F "file=@tenant.yaml"
```

### 3. Receive Credentials
```json
{
  "tenant_pkid": "your-company-name",
  "tenant_name": "Your Company Name",
  "username": "your-company-name",
  "password": "X9k@Lp2mQ#wR4vT$",
  "message": "Tenant 'Your Company Name' and user 'your-company-name' created successfully"
}
```

**Save these credentials securely!**

## Project Structure

```
db/                           # Database layer (database agnostic)
├── __init__.py
├── database.py               # SQLAlchemy setup & session management
├── models.py                 # ORM models (Tenant, User, Role)
└── crud.py                   # Database operations

auth/                          # Authentication & Security
├── __init__.py
└── security.py               # Password hashing, token verification

app.py                         # FastAPI application with endpoints
main.py                        # RAG pipeline (existing)
init_db.py                     # Database initialization script
test_tenant_api.py             # API testing script
requirements.txt               # Python dependencies

TENANT_MANAGEMENT_README.md    # Full documentation
```

## API Endpoints

### POST /api/v1/tenant/create
Create a new tenant via YAML file upload.

**Headers**:
```
Authorization: Bearer <token>
```

**Body**: YAML file (multipart/form-data)

**Response** (200):
```json
{
  "tenant_pkid": "string",
  "tenant_name": "string",
  "username": "string",
  "password": "string",
  "message": "string"
}
```

**Errors**:
- `400`: Invalid YAML format
- `401`: Missing/invalid token
- `409`: Tenant/user already exists
- `500`: Server error

## Database Models

### Tenant
- `id`: Primary key
- `tenant_pkid`: Unique identifier (auto-generated)
- `name`: Tenant name
- `description`: Optional description
- `config_file`: YAML configuration (stored as text)
- `is_active`: Boolean (default: True)
- `created_at`: Timestamp
- `updated_at`: Timestamp

### User
- `id`: Primary key
- `username`: Unique username
- `email`: Optional email
- `password_hash`: Bcrypt hash (NOT plaintext)
- `tenant_id`: Foreign key to Tenant
- `role_id`: Foreign key to Role
- `is_active`: Boolean (default: True)
- `is_admin`: Boolean (default: False)
- `created_at`: Timestamp
- `updated_at`: Timestamp
- `last_login`: Optional timestamp

### Role
- `id`: Primary key
- `name`: Role name (unique)
- `description`: Role description
- `created_at`: Timestamp

## Security Features

### Bearer Token Verification
All tenant creation requests must include a valid Bearer token:

```bash
Authorization: Bearer YOUR_TOKEN
```

**To update token**:
1. Set environment variable: `VALID_TOKEN=your-token`
2. Or update in `app.py` endpoint

### Password Security
Passwords are generated with:
- ✅ 16+ characters
- ✅ Mixed case (A-Z, a-z)
- ✅ Numbers (0-9)
- ✅ Special characters (!@#$%^&*)
- ✅ Cryptographically secure random
- ✅ Stored as bcrypt hash (never plaintext)

### Password Hashing
```python
from auth.security import get_password_hash, verify_password

# Hash password
hashed = get_password_hash("plaintext")

# Verify password
is_valid = verify_password("plaintext", hashed)
```

## Database Agnostic Design

Switch databases by changing `DATABASE_URL`:

### SQLite (Default)
```
DATABASE_URL=sqlite:///D:/s1_rag_engine/sql_lite_db/rag_admin.sqlite3
```

### PostgreSQL
```
DATABASE_URL=postgresql://user:password@localhost/rag_admin
```

### MySQL
```
DATABASE_URL=mysql+pymysql://user:password@localhost/rag_admin
```

All code remains unchanged - SQLAlchemy handles database differences.

## Testing

### Run Test Suite
```bash
python test_tenant_api.py
```

### Manual Testing with cURL
```bash
# Create tenant
curl -X POST http://localhost:8000/api/v1/tenant/create \
  -H "Authorization: Bearer your-token" \
  -F "file=@tenant.yaml"

# Test without token (should fail with 401)
curl -X POST http://localhost:8000/api/v1/tenant/create \
  -F "file=@tenant.yaml"

# Test with invalid YAML (should fail with 400)
curl -X POST http://localhost:8000/api/v1/tenant/create \
  -H "Authorization: Bearer your-token" \
  -F "file=@invalid.yaml"
```

## Environment Variables

Create `.env` file:
```env
# Database
DATABASE_URL=sqlite:///D:/s1_rag_engine/sql_lite_db/rag_admin.sqlite3

# Security
VALID_TOKEN=your-secure-token-here

# Logging
LOG_LEVEL=INFO
```

## Troubleshooting

### Database Connection Failed
```
❌ Error: unable to open database file
```
- Check directory exists: `D:\s1_rag_engine\sql_lite_db\`
- Run: `python init_db.py`

### Token Invalid
```
❌ 403 Forbidden: Invalid token
```
- Update token in `app.py` or environment variable
- Check header format: `Authorization: Bearer <token>`

### YAML Parse Error
```
❌ 400 Invalid YAML format
```
- Check YAML syntax (indentation, colons)
- Ensure `tenant.name` field exists
- Use `.yaml` or `.yml` extension

### Tenant Already Exists
```
❌ 409 Conflict: Tenant with ID '...' already exists
```
- Tenant names must be unique
- Use different name or delete existing tenant

## Common Operations

### Create Tenant Programmatically
```python
from sqlalchemy.orm import Session
from db import crud
from db.models import Tenant

def create_tenant_code(db: Session):
    tenant = crud.create_tenant(
        db=db,
        tenant_pkid="my-company",
        name="My Company",
        config_yaml="<yaml_content>"
    )
    return tenant
```

### Create User for Tenant
```python
user = crud.create_user_for_tenant(
    db=db,
    tenant_id=tenant.id,
    username="my-company",
    password="plaintext_password",
    email="admin@mycompany.com"
)
```

### Query Tenant
```python
tenant = crud.get_tenant_by_pkid(db, "my-company")
user = crud.get_user_by_username(db, "my-company")
```

## Important Notes

1. **Passwords**: Are NOT returned after creation. Save immediately!
2. **Token**: Update `VALID_TOKEN` in production code or use environment variables
3. **Database**: Auto-creates on startup via `init_db()` in `startup_event()`
4. **Roles**: Create default roles during initialization
5. **Multi-tenant**: Fully supports multiple independent tenants

## Next Steps

1. ✅ Install dependencies: `pip install -r requirements.txt`
2. ✅ Initialize database: `python init_db.py`
3. ✅ Start server: `uvicorn app:app --reload`
4. ✅ Create first tenant: Use test script or cURL
5. ✅ Implement authentication middleware for other endpoints
6. ✅ Add user login endpoint
7. ✅ Implement tenant-specific data isolation

## Support

For issues or questions, refer to:
- Full documentation: `TENANT_MANAGEMENT_README.md`
- Test examples: `test_tenant_api.py`
- Database models: `db/models.py`
- Security utilities: `auth/security.py`
