from typing import Optional

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import joinedload

from app.config.logger import setup_logger
from app.core.security import (
    create_access_token,
    get_user_by_token,
    hash_password,
    verify_password
)
from app.db.session import get_session
from app.models.tables import Role, Tenant, User
from app.schemas.schemas import UserSchema

logger = setup_logger(__name__)


def load_user_by_username(username: str) -> Optional[User]:

    logger.info(f"Loading user by username: {username}")

    session = get_session()

    try:
        logger.debug(
            f"Executing user lookup query for username: {username}"
        )

        user = (
            session.query(User)
            .options(joinedload(User.role))
            .filter(User.username == username)
            .first()
        )

        if user:
            logger.info(
                f"User loaded successfully for username: {username}"
            )
        else:
            logger.warning(
                f"User not found for username: {username}"
            )

        return user

    except Exception as e:
        logger.exception(
            f"Failed to load user for username {username}: {str(e)}"
        )
        raise

    finally:
        logger.debug("Closing user lookup database session")
        session.close()
        logger.debug("User lookup database session closed")


def authenticate_user(username: str, password: str) -> Optional[User]:

    logger.info(f"Authentication initiated for username: {username}")

    try:
        user = load_user_by_username(username)

        if user and verify_password(password, user.password_hash):

            logger.info(
                f"Authentication successful for username: {username}"
            )

            return user

        logger.warning(
            f"Authentication failed for username: {username}"
        )

        return None

    except Exception as e:
        logger.exception(
            f"Authentication error for username "
            f"{username}: {str(e)}"
        )
        raise


def login_user(username: str, password: str) -> Optional[str]:

    logger.info(f"Login process initiated for username: {username}")

    try:
        user = authenticate_user(username, password)

        if not user:

            logger.warning(
                f"Login failed for username: {username}"
            )

            return None

        logger.debug(
            f"Generating access token for username: {username}"
        )

        token = create_access_token(user.id)

        logger.info(
            f"Access token generated successfully for username: "
            f"{username}"
        )

        return token

    except Exception as e:
        logger.exception(
            f"Login process failed for username "
            f"{username}: {str(e)}"
        )
        raise


def get_current_user(
    authorization: Optional[str] = Header(None)
) -> User:

    logger.info("Current user authentication initiated")

    try:
        if not authorization or not authorization.startswith("Bearer "):

            logger.warning(
                "Missing or invalid authorization header"
            )

            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authorization header required"
            )

        logger.debug("Extracting bearer token")

        token = authorization.split(" ", 1)[1]

        logger.debug("Fetching user from authentication token")

        user = get_user_by_token(token)

        logger.info(
            f"Current user authenticated successfully: "
            f"{user.username}"
        )

        return user

    except HTTPException:
        raise

    except Exception as e:
        logger.exception(
            f"Current user authentication failed: {str(e)}"
        )
        raise


def get_current_user_schema(
    current_user: User = Depends(get_current_user)
) -> UserSchema:

    logger.debug(
        f"Building UserSchema for username: "
        f"{current_user.username}"
    )

    try:
        schema = UserSchema(
            id=current_user.id,
            username=current_user.username,
            role=current_user.role.name,
            tenant_id=current_user.tenant_id,
        )

        logger.info(
            f"UserSchema created successfully for username: "
            f"{current_user.username}"
        )

        return schema

    except Exception as e:
        logger.exception(
            f"Failed to build UserSchema: {str(e)}"
        )
        raise


def ensure_setup() -> None:

    logger.info("Initial application setup started")

    from app.db.base import engine
    from app.db.session import get_session
    from app.models.tables import Config, Role, Tenant, User
    from app.services.tenant_service import (
        load_config_yaml,
        build_config_sections
    )

    from sqlalchemy.orm import sessionmaker

    session = get_session()

    try:
        logger.debug("Checking admin role existence")

        admin_role = session.query(Role).filter_by(name="admin").first()

        logger.debug("Checking tenant role existence")

        tenant_role = session.query(Role).filter_by(name="tenant").first()

        if not admin_role:

            logger.info("Creating admin role")

            admin_role = Role(
                name="admin",
                description="Platform administrator"
            )

            session.add(admin_role)

        if not tenant_role:

            logger.info("Creating tenant role")

            tenant_role = Role(
                name="tenant",
                description="Tenant-level user"
            )

            session.add(tenant_role)

        session.commit()

        logger.info("Role setup completed successfully")

        admin_user = (
            session.query(User)
            .filter_by(username="admin")
            .first()
        )

        if not admin_user:

            logger.info("Creating default admin user")

            admin_user = User(
                username="admin",
                password_hash=hash_password("Hap$y#2@26"),
                role=admin_role,
                tenant=None,
            )

            session.add(admin_user)

        tenant_example = (
            session.query(Tenant)
            .filter_by(slug="example-tenant")
            .first()
        )

        if not tenant_example:

            logger.info("Creating default example tenant")

            tenant_example = Tenant(
                name="Example Tenant",
                slug="example-tenant",
                description="Default tenant created automatically.",
            )

            session.add(tenant_example)

        if not session.query(User).filter_by(username="tenant").first():

            logger.info("Creating default tenant user")

            tenant_user = User(
                username="tenant",
                password_hash=hash_password("tenant123"),
                role=tenant_role,
                tenant=tenant_example,
            )

            session.add(tenant_user)

        session.commit()

        logger.info("Default user and tenant setup completed")

        logger.debug("Loading configuration YAML")

        config_data = load_config_yaml()

        if config_data:

            logger.info("Configuration YAML loaded successfully")

            sections = build_config_sections(config_data)

            existing_sections = {
                config.section
                for config in session.query(Config)
                .filter_by(tenant_id=tenant_example.id)
            }

            for section_name, section_data in sections.items():

                if section_name not in existing_sections:

                    logger.info(
                        f"Creating configuration section: "
                        f"{section_name}"
                    )

                    session.add(
                        Config(
                            tenant=tenant_example,
                            section=section_name,
                            data=section_data,
                        )
                    )

        session.commit()

        logger.info("Initial application setup completed successfully")

    except SQLAlchemyError as e:

        logger.exception(
            f"Database setup transaction failed: {str(e)}"
        )

        session.rollback()

        logger.warning("Database transaction rolled back")

        raise

    except Exception as e:

        logger.exception(
            f"Unexpected setup failure: {str(e)}"
        )

        session.rollback()

        logger.warning("Database transaction rolled back")

        raise

    finally:
        logger.debug("Closing setup database session")
        session.close()
        logger.debug("Setup database session closed")