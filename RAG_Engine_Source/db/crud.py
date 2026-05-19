"""CRUD operations for database models.

Provides database agnostic operations for Tenant, User, and Role management.
"""
from sqlalchemy.orm import Session
from db.models import Tenant, User, Role, Config
from auth.security import get_password_hash


def get_or_create_tenant_role(db: Session) -> Role:
    """Get or create the 'tenant' role.
    
    Args:
        db: SQLAlchemy database session
        
    Returns:
        Role: The tenant role
    """
    role = db.query(Role).filter(Role.name == "tenant").first()
    if not role:
        role = Role(
            name="tenant",
            description="Default role for tenant users"
        )
        db.add(role)
        db.commit()
        db.refresh(role)
    return role


def create_tenant(db: Session, tenant_pkid: str, name: str, config_yaml: str = None) -> Tenant:
    """Create a new tenant.
    
    Args:
        db: SQLAlchemy database session
        tenant_pkid: Unique tenant identifier
        name: Tenant name
        config_yaml: YAML configuration content
        
    Returns:
        Tenant: The created tenant
    """
    db_tenant = Tenant(
        tenant_pkid=tenant_pkid,
        name=name,
        is_active=True
    )
    db.add(db_tenant)
    db.commit()
    db.refresh(db_tenant)

    if config_yaml:
        config_entry = Config(
            tenant_id=db_tenant.id,
            section="tenant",
            data=config_yaml
        )
        db.add(config_entry)
        db.commit()
        db.refresh(config_entry)

    return db_tenant


def get_tenant_by_pkid(db: Session, tenant_pkid: str) -> Tenant:
    """Retrieve a tenant by primary key ID.
    
    Args:
        db: SQLAlchemy database session
        tenant_pkid: Unique tenant identifier
        
    Returns:
        Tenant: The tenant or None if not found
    """
    return db.query(Tenant).filter(Tenant.tenant_pkid == tenant_pkid).first()


def create_user_for_tenant(
    db: Session,
    tenant_id: int,
    username: str,
    password: str,
    email: str = None,
    role_id: int = None
) -> User:
    """Create a new user for a tenant.
    
    Args:
        db: SQLAlchemy database session
        tenant_id: ID of the tenant
        username: Username
        password: Plain text password (will be hashed)
        email: Optional email address
        role_id: Role ID (defaults to 'tenant' role)
        
    Returns:
        User: The created user
    """
    if role_id is None:
        role = get_or_create_tenant_role(db)
        role_id = role.id
    
    db_user = User(
        username=username,
        email=email,
        password_hash=get_password_hash(password),
        tenant_id=tenant_id,
        role_id=role_id,
        is_active=True,
        is_admin=False
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


def get_user_by_username(db: Session, username: str) -> User:
    """Retrieve a user by username.
    
    Args:
        db: SQLAlchemy database session
        username: Username to search for
        
    Returns:
        User: The user or None if not found
    """
    return db.query(User).filter(User.username == username).first()


def user_exists(db: Session, username: str) -> bool:
    """Check if a user with given username exists.
    
    Args:
        db: SQLAlchemy database session
        username: Username to check
        
    Returns:
        bool: True if user exists, False otherwise
    """
    return db.query(User).filter(User.username == username).first() is not None
