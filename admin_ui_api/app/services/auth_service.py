from typing import Optional

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.exc import SQLAlchemyError

from app.core.security import create_access_token, get_user_by_token, hash_password, verify_password
from app.db.session import get_session
from app.models.tables import Role, Tenant, User
from app.schemas.schemas import UserSchema


def load_user_by_username(username: str) -> Optional[User]:
    session = get_session()
    try:
        return session.query(User).filter(User.username == username).first()
    finally:
        session.close()


def authenticate_user(username: str, password: str) -> Optional[User]:
    user = load_user_by_username(username)
    if user and verify_password(password, user.password_hash):
        return user
    return None


def login_user(username: str, password: str) -> Optional[str]:
    user = authenticate_user(username, password)
    if not user:
        return None
    return create_access_token(user.id)


def get_current_user(authorization: Optional[str] = Header(None)) -> User:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authorization header required")
    token = authorization.split(" ", 1)[1]
    return get_user_by_token(token)


def get_current_user_schema(current_user: User = Depends(get_current_user)) -> UserSchema:
    return UserSchema(
        id=current_user.id,
        username=current_user.username,
        role=current_user.role.name,
        tenant_id=current_user.tenant_id,
    )


def ensure_setup() -> None:
    from app.db.base import engine
    from app.db.session import get_session
    from app.models.tables import Config, Role, Tenant, User
    from app.services.tenant_service import load_config_yaml, build_config_sections

    from sqlalchemy.orm import sessionmaker

    session = get_session()
    try:
        admin_role = session.query(Role).filter_by(name="admin").first()
        tenant_role = session.query(Role).filter_by(name="tenant").first()

        if not admin_role:
            admin_role = Role(name="admin", description="Platform administrator")
            session.add(admin_role)

        if not tenant_role:
            tenant_role = Role(name="tenant", description="Tenant-level user")
            session.add(tenant_role)

        session.commit()

        admin_user = session.query(User).filter_by(username="admin").first()
        if not admin_user:
            admin_user = User(
                username="admin",
                password_hash=hash_password("Hap$y#2@26"),
                role=admin_role,
                tenant=None,
            )
            session.add(admin_user)

        tenant_example = session.query(Tenant).filter_by(slug="example-tenant").first()
        if not tenant_example:
            tenant_example = Tenant(
                name="Example Tenant",
                slug="example-tenant",
                description="Default tenant created automatically.",
            )
            session.add(tenant_example)

        if not session.query(User).filter_by(username="tenant").first():
            tenant_user = User(
                username="tenant",
                password_hash=hash_password("tenant123"),
                role=tenant_role,
                tenant=tenant_example,
            )
            session.add(tenant_user)

        session.commit()

        config_data = load_config_yaml()
        if config_data:
            sections = build_config_sections(config_data)
            existing_sections = {
                config.section for config in session.query(Config).filter_by(tenant_id=tenant_example.id)
            }
            for section_name, section_data in sections.items():
                if section_name not in existing_sections:
                    session.add(
                        Config(
                            tenant=tenant_example,
                            section=section_name,
                            data=section_data,
                        )
                    )

        session.commit()
    except SQLAlchemyError:
        session.rollback()
        raise
    finally:
        session.close()
