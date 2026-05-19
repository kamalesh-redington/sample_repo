# Verification Checklist

Use this checklist to verify the tenant management system is properly installed and working.

## Pre-Installation Checklist

- [ ] Python 3.8+ installed
- [ ] pip package manager available
- [ ] FastAPI previously running on http://localhost:8000
- [ ] SQLite database directory exists: `D:\s1_rag_engine\sql_lite_db\`
- [ ] Working directory is: `d:\s1_rag_engine\onboarding_api`

## Installation Steps

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

**Verify**:
- [ ] Command completed without errors
- [ ] Check installed packages:
  ```bash
  pip list | find "sqlalchemy"
  pip list | find "passlib"
  pip list | find "bcrypt"
  ```
- [ ] All three packages should appear in output

### 2. Verify File Structure
Check that all new files exist:

```bash
dir db\             # Should show: __init__.py, database.py, models.py, crud.py
dir auth\           # Should show: __init__.py, security.py
dir *.md            # Should show: QUICKSTART.md, TENANT_MANAGEMENT_README.md, etc.
```

**Checklist**:
- [ ] `db\database.py` exists
- [ ] `db\models.py` exists
- [ ] `db\crud.py` exists
- [ ] `db\__init__.py` exists
- [ ] `auth\security.py` exists
- [ ] `auth\__init__.py` exists
- [ ] `init_db.py` exists
- [ ] `test_tenant_api.py` exists
- [ ] `QUICKSTART.md` exists
- [ ] `TENANT_MANAGEMENT_README.md` exists
- [ ] `.env.sample` exists
- [ ] `tenant_config.sample.yaml` exists

### 3. Initialize Database
```bash
python init_db.py
```

**Expected Output**:
```
============================================================
Database Initialization
============================================================

1. Creating database tables...
✅ Database tables created successfully!

2. Creating default roles...
✅ Created role: admin
✅ Created role: tenant
✅ Created role: viewer
✅ Created role: editor

✅ Default roles created successfully!

============================================================
Database initialization complete!
============================================================
```

**Verify**:
- [ ] Script runs without errors
- [ ] Database file created: `D:\s1_rag_engine\sql_lite_db\rag_admin.sqlite3`
- [ ] All four roles created (admin, tenant, viewer, editor)

### 4. Verify Database Structure
You can verify the database using SQLite tools:

```bash
# Using sqlite3 command line (if installed)
sqlite3 "D:\s1_rag_engine\sql_lite_db\rag_admin.sqlite3" ".tables"
```

**Expected tables**:
- [ ] `tenants` table exists
- [ ] `users` table exists
- [ ] `roles` table exists

### 5. Start FastAPI Server
```bash
uvicorn app:app --reload
```

**Expected Output** (last few lines):
```
INFO:     Uvicorn running on http://127.0.0.1:8000
INFO:     Application startup complete
```

**Verify**:
- [ ] Server starts successfully
- [ ] No errors in console
- [ ] Can access http://localhost:8000 in browser
- [ ] See "RAG Document Chat" page (existing endpoint)

### 6. Test API Endpoint

#### Test 6a: GET / (existing endpoint)
```bash
curl http://localhost:8000/
```

**Expected**: HTML page returns  
**Verify**: [ ] 200 OK response with HTML content

#### Test 6b: Missing Token (should fail)
```bash
curl -X POST http://localhost:8000/api/v1/tenant/create ^
  -F "file=@tenant_config.sample.yaml"
```

**Expected**: 401 Unauthorized  
**Verify**: [ ] Error message: "Missing authentication credentials"

#### Test 6c: Invalid Token (should fail)
```bash
curl -X POST http://localhost:8000/api/v1/tenant/create ^
  -H "Authorization: Bearer wrong-token" ^
  -F "file=@tenant_config.sample.yaml"
```

**Expected**: 403 Forbidden  
**Verify**: [ ] Error message: "Invalid token"

#### Test 6d: Valid Token with Valid YAML (should succeed)
First, update the token in `app.py` temporarily for testing:

```python
VALID_TOKEN = "test-token-12345"  # Line ~250 in app.py
```

Then:
```bash
curl -X POST http://localhost:8000/api/v1/tenant/create ^
  -H "Authorization: Bearer test-token-12345" ^
  -F "file=@tenant_config.sample.yaml"
```

**Expected**: 200 OK with response
```json
{
  "tenant_pkid": "test-tenant-corp",
  "tenant_name": "Test Tenant Corp",
  "username": "test-tenant-corp",
  "password": "X9k@Lp2mQ#wR4vT$...",
  "message": "Tenant 'Test Tenant Corp' and user 'test-tenant-corp' created successfully"
}
```

**Verify**:
- [ ] Response status is 200
- [ ] tenant_pkid is generated
- [ ] username is set to tenant_pkid
- [ ] password is 16+ characters with mixed case/numbers/special chars
- [ ] message confirms success

### 7. Verify Database Contents
After successful tenant creation, verify in database:

```python
# Quick Python script to verify
import sqlite3

db = sqlite3.connect(r"D:\s1_rag_engine\sql_lite_db\rag_admin.sqlite3")
cursor = db.cursor()

# Check tenants
print("Tenants:")
cursor.execute("SELECT id, tenant_pkid, name FROM tenants")
for row in cursor.fetchall():
    print(f"  ID={row[0]}, PKID={row[1]}, Name={row[2]}")

# Check users  
print("\nUsers:")
cursor.execute("SELECT id, username, tenant_id, role_id FROM users")
for row in cursor.fetchall():
    print(f"  ID={row[0]}, Username={row[1]}, Tenant={row[2]}, Role={row[3]}")

# Check roles
print("\nRoles:")
cursor.execute("SELECT id, name FROM roles")
for row in cursor.fetchall():
    print(f"  ID={row[0]}, Name={row[1]}")

db.close()
```

**Verify**:
- [ ] Tenant row created with correct pkid and name
- [ ] User row created with correct username and tenant_id
- [ ] User has role_id pointing to 'tenant' role
- [ ] Default roles (4) exist

### 8. Run Full Test Suite
```bash
python test_tenant_api.py
```

**Expected Output**:
```
============================================================
Testing Tenant Creation API
============================================================
...
✅ SUCCESS! Tenant created:
{
  "tenant_pkid": "...",
  "tenant_name": "...",
  "username": "...",
  "password": "...",
  "message": "..."
}
```

**Verify**:
- [ ] Test suite runs without errors
- [ ] All tests complete (3 tests minimum)
- [ ] At least one "SUCCESS" message appears

## Common Issues & Solutions

### Issue: "ModuleNotFoundError: No module named 'db'"
**Solution**:
```bash
# Make sure you're in the correct directory
cd d:\s1_rag_engine\onboarding_api

# Verify __init__.py files exist
dir db\__init__.py
dir auth\__init__.py
```

### Issue: Database file not created
**Solution**:
```bash
# Create directory if missing
mkdir "D:\s1_rag_engine\sql_lite_db"

# Run init script again
python init_db.py
```

### Issue: "token" error from security module
**Solution**:
```bash
# Reinstall passlib and bcrypt
pip install --upgrade passlib bcrypt
```

### Issue: Port 8000 already in use
**Solution**:
```bash
# Use different port
uvicorn app:app --reload --port 8001

# Or kill process using port 8000
netstat -ano | findstr :8000
taskkill /PID <PID> /F
```

### Issue: YAML parsing error with sample file
**Solution**:
```bash
# Create new YAML with proper format
echo tenant: > test.yaml
echo.  name: "Test Company" >> test.yaml
echo.  description: "Test" >> test.yaml

# Try again
curl -X POST http://localhost:8000/api/v1/tenant/create ^
  -H "Authorization: Bearer test-token" ^
  -F "file=@test.yaml"
```

## Code Verification

### Check imports in app.py
```python
# Should be able to run this without errors:
python -c "from app import app; print('✅ app.py imports OK')"
```

**Verify**: [ ] No import errors

### Check database module
```python
python -c "from db.database import init_db, get_db, engine; print('✅ db.database imports OK')"
```

**Verify**: [ ] No import errors

### Check models
```python
python -c "from db.models import Tenant, User, Role; print('✅ db.models imports OK')"
```

**Verify**: [ ] No import errors

### Check CRUD operations
```python
python -c "from db import crud; print('✅ db.crud imports OK')"
```

**Verify**: [ ] No import errors

### Check security
```python
python -c "from auth.security import generate_strong_password; p=generate_strong_password(); print(f'✅ auth.security OK, Generated password: {p}')"
```

**Verify**: [ ] No import errors, password generated

## Performance Verification

### Database Response Time
```bash
# Time the tenant creation
$timer = [System.Diagnostics.Stopwatch]::StartNew()
# Make curl request
$timer.Stop()
Write-Host "Request took $($timer.ElapsedMilliseconds)ms"
```

**Expected**: [ ] Response < 500ms

### Password Generation Performance
```python
import time
from auth.security import generate_strong_password

start = time.time()
for _ in range(100):
    generate_strong_password()
elapsed = time.time() - start

print(f"✅ Generated 100 passwords in {elapsed:.2f}s")
```

**Expected**: [ ] < 1 second for 100 passwords

## Security Verification

### Password Hash Verification
```python
from auth.security import get_password_hash, verify_password

password = "MyTestPassword123!"
hashed = get_password_hash(password)

# Verify it's actually hashed
print(f"Original:  {password}")
print(f"Hashed:    {hashed}")
print(f"Match:     {verify_password(password, hashed)}")
print(f"Wrong pwd: {verify_password('WrongPassword', hashed)}")
```

**Verify**:
- [ ] Hashed password doesn't match original
- [ ] Correct password verifies as True
- [ ] Wrong password verifies as False

### Token Verification
```python
from auth.security import verify_bearer_token, HTTPAuthCredentials

# Create mock credentials
class MockCreds:
    def __init__(self, token):
        self.scheme = "Bearer"
        self.credentials = token

# Test with correct token
try:
    verify_bearer_token(MockCreds("correct-token"), "correct-token")
    print("✅ Correct token verified")
except:
    print("❌ Correct token rejected")

# Test with wrong token
try:
    verify_bearer_token(MockCreds("wrong-token"), "correct-token")
    print("❌ Wrong token accepted (SECURITY ISSUE!)")
except:
    print("✅ Wrong token rejected")
```

**Verify**:
- [ ] Correct token is accepted
- [ ] Wrong token is rejected

## Final Verification Checklist

**Installation**:
- [ ] All dependencies installed
- [ ] All files created
- [ ] Database initialized
- [ ] No import errors

**Functionality**:
- [ ] Server starts without errors
- [ ] Existing endpoints still work (GET /)
- [ ] Bearer token validation works
- [ ] Tenant creation succeeds with valid token
- [ ] Tenant creation fails with invalid token
- [ ] Database is populated correctly
- [ ] Passwords are hashed (not plaintext)

**Security**:
- [ ] Bearer tokens required
- [ ] Passwords are bcrypt hashed
- [ ] Invalid tokens rejected
- [ ] Duplicate tenants prevented

**Performance**:
- [ ] Requests respond < 500ms
- [ ] Password generation < 10ms per password
- [ ] Database queries efficient

**Documentation**:
- [ ] QUICKSTART.md reviewed
- [ ] TENANT_MANAGEMENT_README.md reviewed
- [ ] IMPLEMENTATION_SUMMARY.md reviewed
- [ ] Sample YAML file correct

## Success Criteria

✅ **All tests pass**: No errors when running `test_tenant_api.py`  
✅ **Database created**: SQLite file exists with correct tables  
✅ **Server runs**: FastAPI starts without errors  
✅ **Token auth works**: Token validation enabled and tested  
✅ **Tenant created**: Can create tenant via API  
✅ **Password hashed**: Passwords are bcrypt hashed, not plaintext  
✅ **Database isolated**: Each tenant has its own users  
✅ **Documentation complete**: All README files present

## Rollback Instructions

If you need to revert to the original state:

1. **Remove new files**:
   ```bash
   rmdir /s db
   rmdir /s auth
   del init_db.py
   del test_tenant_api.py
   del .env.sample
   del tenant_config.sample.yaml
   del QUICKSTART.md
   del TENANT_MANAGEMENT_README.md
   del IMPLEMENTATION_SUMMARY.md
   del VERIFICATION_CHECKLIST.md
   ```

2. **Revert app.py**:
   - Replace with original version from git
   - Or restore from backup

3. **Revert requirements.txt**:
   - Remove: sqlalchemy, passlib, bcrypt entries
   - Keep original dependencies

4. **Uninstall packages**:
   ```bash
   pip uninstall sqlalchemy passlib bcrypt -y
   ```

## Next Steps

After successful verification:

1. [ ] Update VALID_TOKEN in app.py to secure value
2. [ ] Configure environment variables (.env file)
3. [ ] Set up production database (PostgreSQL recommended)
4. [ ] Implement user login endpoint
5. [ ] Add tenant isolation middleware
6. [ ] Create admin dashboard
7. [ ] Set up monitoring and logging
8. [ ] Deploy to production

## Support

For issues, refer to:
- [QUICKSTART.md](QUICKSTART.md) - Quick reference
- [TENANT_MANAGEMENT_README.md](TENANT_MANAGEMENT_README.md) - Full documentation  
- [test_tenant_api.py](test_tenant_api.py) - Working examples
- [IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md) - Architecture details
