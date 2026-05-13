import json
import hashlib
from pathlib import Path
from typing import Dict, Optional

import yaml
from django.conf import settings
from sqlalchemy import Column, ForeignKey, Integer, String, Text
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, relationship, sessionmaker

SQLITE_DIR = Path("D:/s1_rag_engine/sql_lite_db")
SQLITE_DIR.mkdir(parents=True, exist_ok=True)
SQLITE_PATH = SQLITE_DIR / "rag_admin.sqlite3"
SQLALCHEMY_DATABASE_URI = settings.SQLALCHEMY_DATABASE_URI

engine = create_engine(SQLALCHEMY_DATABASE_URI, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()


class Role(Base):
    __tablename__ = "roles"

    id = Column(Integer, primary_key=True)
    name = Column(String(50), unique=True, nullable=False)
    description = Column(String(255), nullable=True)

    users = relationship("User", back_populates="role")


class Tenant(Base):
    __tablename__ = "tenants"

    id = Column(Integer, primary_key=True)
    name = Column(String(120), nullable=False)
    slug = Column(String(120), nullable=False, unique=True)
    description = Column(Text, nullable=True)

    users = relationship("User", back_populates="tenant")
    configs = relationship("Config", back_populates="tenant")


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    username = Column(String(120), unique=True, nullable=False)
    password_hash = Column(String(128), nullable=False)
    role_id = Column(Integer, ForeignKey("roles.id"), nullable=False)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=True)

    role = relationship("Role", back_populates="users")
    tenant = relationship("Tenant", back_populates="users")


class Config(Base):
    __tablename__ = "configs"

    id = Column(Integer, primary_key=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False)
    section = Column(String(100), nullable=False)
    data = Column(Text, nullable=False)

    tenant = relationship("Tenant", back_populates="configs")


def get_session():
    return SessionLocal()


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def verify_password(password: str, password_hash: str) -> bool:
    return hash_password(password) == password_hash


def load_config_yaml() -> Dict:
    config_path = Path(settings.CONFIG_YAML_PATH)
    if not config_path.exists():
        return {}
    with config_path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def _normalize_section_name(name: str) -> str:
    return name.replace("_", " ").title()


def _build_config_sections(raw_data: Dict) -> Dict[str, Dict]:
    if not raw_data:
        return {}

    return {
        "Source": raw_data.get("source", {}),
        "Chunking": raw_data.get("chunking", {}),
        "Embedding": raw_data.get("embedding", {}),
        "Vector Store": raw_data.get("vector_store", {}),
        "Meta Data": raw_data.get("metadata", {}),
    }


def ensure_setup() -> None:
    Base.metadata.create_all(engine)
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
            sections = _build_config_sections(config_data)
            existing_sections = {
                config.section for config in session.query(Config).filter_by(tenant_id=tenant_example.id)
            }
            for section_name, section_data in sections.items():
                if section_name not in existing_sections:
                    session.add(
                        Config(
                            tenant=tenant_example,
                            section=section_name,
                            data=json.dumps(section_data, indent=2),
                        )
                    )

        session.commit()
    finally:
        session.close()
