"""CRUD operations for database models.

Provides database agnostic operations for Tenant,
User, and Role management.
"""

from config.logger import setup_logger

logger = setup_logger(__name__)
from config.timer import log_execution_time

from sqlalchemy.orm import Session

from db.models import (
    Tenant,
    User,
    Role,
    Config
)

from auth.security import get_password_hash


# ────────────────────────────────────────────────────────────────────────────────
# Get or Create Tenant Role
# ────────────────────────────────────────────────────────────────────────────────

@log_execution_time(logger)
def get_or_create_tenant_role(db: Session) -> Role:
    """Get or create the default tenant role."""

    try:

        logger.info("Fetching tenant role")

        logger.debug("Executing role lookup query")

        role = (
            db.query(Role)
            .filter(Role.name == "tenant")
            .first()
        )

        if not role:

            logger.warning(
                "Tenant role not found, creating new role"
            )

            role = Role(
                name="tenant",
                description="Default role for tenant users"
            )

            logger.debug(
                "Adding tenant role to database session"
            )

            db.add(role)

            logger.debug(
                "Committing tenant role transaction"
            )

            db.commit()

            db.refresh(role)

            logger.info(
                "Tenant role created successfully"
            )

        logger.debug(
            f"Returning tenant role object: {role}"
        )

        return role

    except Exception as e:

        logger.exception(
            "Tenant role operation failed"
        )

        db.rollback()

        logger.warning(
            "Database transaction rolled back"
        )

        raise


# ────────────────────────────────────────────────────────────────────────────────
# Create Tenant
# ────────────────────────────────────────────────────────────────────────────────

@log_execution_time(logger)
def create_tenant(
    db: Session,
    tenant_pkid: str,
    name: str,
    config_yaml: str = None
) -> Tenant:
    """Create a new tenant."""

    try:

        logger.info(
            f"Creating tenant: {tenant_pkid}"
        )

        logger.debug(
            f"Tenant payload -> PKID: {tenant_pkid}, Name: {name}"
        )

        db_tenant = Tenant(
            tenant_pkid=tenant_pkid,
            name=name,
            is_active=True
        )

        logger.debug(
            "Adding tenant object to database session"
        )

        db.add(db_tenant)

        logger.debug(
            "Committing tenant transaction"
        )

        db.commit()

        db.refresh(db_tenant)

        logger.info(
            f"Tenant created successfully: {tenant_pkid}"
        )

        logger.debug(
            f"Tenant database object refreshed: {db_tenant}"
        )

        # ────────────────────────────────────────────────────────────────────────
        # Save Tenant Config
        # ────────────────────────────────────────────────────────────────────────

        if config_yaml:

            logger.info(
                "Saving tenant configuration YAML"
            )

            config_entry = Config(
                tenant_id=db_tenant.id,
                section="tenant",
                data=config_yaml
            )

            logger.debug(
                "Adding tenant config entry to database session"
            )

            db.add(config_entry)

            logger.debug(
                "Committing tenant config transaction"
            )

            db.commit()

            db.refresh(config_entry)

            logger.info(
                "Tenant configuration saved successfully"
            )

        logger.debug(
            f"Returning tenant object: {db_tenant}"
        )

        return db_tenant

    except Exception as e:

        logger.exception(
            "Tenant creation database operation failed"
        )

        db.rollback()

        logger.warning(
            "Database transaction rolled back"
        )

        raise


# ────────────────────────────────────────────────────────────────────────────────
# Get Tenant By PKID
# ────────────────────────────────────────────────────────────────────────────────

@log_execution_time(logger)
def get_tenant_by_pkid(
    db: Session,
    tenant_pkid: str
) -> Tenant:
    """Retrieve tenant using tenant PKID."""

    try:

        logger.info(
            f"Fetching tenant by PKID: {tenant_pkid}"
        )

        logger.debug(
            f"Executing tenant lookup query for PKID: {tenant_pkid}"
        )

        tenant = (
            db.query(Tenant)
            .filter(Tenant.tenant_pkid == tenant_pkid)
            .first()
        )

        logger.debug(
            f"Tenant lookup result: {tenant}"
        )

        if tenant:

            logger.info(
                f"Tenant found: {tenant_pkid}"
            )

        else:

            logger.warning(
                f"Tenant not found: {tenant_pkid}"
            )

        return tenant

    except Exception as e:

        logger.exception(
            "Failed to fetch tenant by PKID"
        )

        raise


# ────────────────────────────────────────────────────────────────────────────────
# Create User For Tenant
# ────────────────────────────────────────────────────────────────────────────────

@log_execution_time(logger)
def create_user_for_tenant(
    db: Session,
    tenant_id: int,
    username: str,
    password: str,
    email: str = None,
    role_id: int = None
) -> User:
    """Create user for tenant."""

    try:

        logger.info(
            f"Creating user for tenant: {username}"
        )

        logger.debug(
            f"Tenant ID associated with user: {tenant_id}"
        )

        logger.debug(
            f"Role ID received: {role_id}"
        )

        if role_id is None:

            logger.info(
                "Role ID not provided, fetching default tenant role"
            )

            role = get_or_create_tenant_role(db)

            role_id = role.id

            logger.debug(
                f"Resolved tenant role ID: {role_id}"
            )

        logger.debug(
            f"Creating database user object for username: {username}"
        )

        db_user = User(
            username=username,
            email=email,
            password_hash=get_password_hash(password),
            tenant_id=tenant_id,
            role_id=role_id,
            is_active=True,
            is_admin=False
        )

        logger.debug(
            "Adding user object to database session"
        )

        db.add(db_user)

        logger.debug(
            "Committing user transaction"
        )

        db.commit()

        db.refresh(db_user)

        logger.info(
            f"User created successfully: {username}"
        )

        logger.debug(
            f"User database object refreshed: {db_user}"
        )

        return db_user

    except Exception as e:

        logger.exception(
            "User creation database operation failed"
        )

        db.rollback()

        logger.warning(
            "Database transaction rolled back"
        )

        raise


# ────────────────────────────────────────────────────────────────────────────────
# Get User By Username
# ────────────────────────────────────────────────────────────────────────────────

@log_execution_time(logger)
def get_user_by_username(
    db: Session,
    username: str
) -> User:
    """Retrieve user by username."""

    try:

        logger.info(
            f"Fetching user by username: {username}"
        )

        logger.debug(
            f"Executing user lookup query for: {username}"
        )

        user = (
            db.query(User)
            .filter(User.username == username)
            .first()
        )

        logger.debug(
            f"User lookup query completed: {username}"
        )

        return user

    except Exception as e:

        logger.exception(
            "Failed to fetch user by username"
        )

        raise


# ────────────────────────────────────────────────────────────────────────────────
# User Exists
# ────────────────────────────────────────────────────────────────────────────────

@log_execution_time(logger)
def user_exists(
    db: Session,
    username: str
) -> bool:
    """Check whether user exists."""

    try:

        logger.info(
            f"Checking if user exists: {username}"
        )

        logger.debug(
            f"Executing user existence query for: {username}"
        )

        exists = (
            db.query(User)
            .filter(User.username == username)
            .first()
            is not None
        )

        logger.debug(
            f"User existence query completed: {username}"
        )

        logger.info(
            f"User existence result for {username}: {exists}"
        )

        return exists

    except Exception as e:

        logger.exception(
            "User existence check failed"
        )

        raise