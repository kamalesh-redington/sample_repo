"""
Database initialization script.

This script initializes the SQLite database with required tables and default roles.
Run once during setup: python init_db.py
"""
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from db.database import init_db, SessionLocal
from db.models import Role


def create_default_roles():
    """Create default roles in the database."""
    db = SessionLocal()
    
    default_roles = [
        {
            "name": "admin",
            "description": "Administrator with full access"
        },
        {
            "name": "tenant",
            "description": "Default role for tenant users"
        },
        {
            "name": "viewer",
            "description": "Read-only access to documents"
        },
        {
            "name": "editor",
            "description": "Can create and edit documents"
        },
    ]
    
    try:
        for role_data in default_roles:
            # Check if role already exists
            existing = db.query(Role).filter(
                Role.name == role_data["name"]
            ).first()
            
            if not existing:
                role = Role(
                    name=role_data["name"],
                    description=role_data["description"]
                )
                db.add(role)
                print(f"✅ Created role: {role_data['name']}")
            else:
                print(f"⏭️  Role already exists: {role_data['name']}")
        
        db.commit()
        print("\n✅ Default roles created successfully!")
        
    except Exception as e:
        print(f"❌ Error creating roles: {str(e)}")
        db.rollback()
    finally:
        db.close()


def main():
    """Main initialization routine."""
    print("=" * 60)
    print("Database Initialization")
    print("=" * 60)
    
    print("\n1. Creating database tables...")
    try:
        init_db()
        print("✅ Database tables created successfully!")
    except Exception as e:
        print(f"❌ Error creating tables: {str(e)}")
        return False
    
    print("\n2. Creating default roles...")
    create_default_roles()
    
    print("\n" + "=" * 60)
    print("Database initialization complete!")
    print("=" * 60)
    print("\nNext steps:")
    print("1. Start the FastAPI server: uvicorn app:app --reload")
    print("2. Create your first tenant: python test_tenant_api.py")
    print("3. Check the database: D:/s1_rag_engine/sql_lite_db/rag_admin.sqlite3")
    
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
