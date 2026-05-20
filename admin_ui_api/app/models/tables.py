from sqlalchemy import Column, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.config.logger import setup_logger
from app.db.base import Base

logger = setup_logger(__name__)

logger.info("Initializing database table models")


class Role(Base):
    logger.debug("Defining Role model")

    __tablename__ = "roles"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, nullable=False)
    description = Column(String(255), nullable=True)

    users = relationship("User", back_populates="role")

    logger.info("Role model defined successfully")


class Tenant(Base):
    logger.debug("Defining Tenant model")

    __tablename__ = "tenants"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(120), nullable=False)
    slug = Column(String(120), nullable=False, unique=True)
    description = Column(Text, nullable=True)

    users = relationship("User", back_populates="tenant")
    configs = relationship("Config", back_populates="tenant")

    logger.info("Tenant model defined successfully")


class User(Base):
    logger.debug("Defining User model")

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(120), unique=True, nullable=False)
    password_hash = Column(String(128), nullable=False)
    role_id = Column(Integer, ForeignKey("roles.id"), nullable=False)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=True)

    role = relationship("Role", back_populates="users")
    tenant = relationship("Tenant", back_populates="users")

    logger.info("User model defined successfully")


class Config(Base):
    logger.debug("Defining Config model")

    __tablename__ = "configs"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False)
    section = Column(String(100), nullable=False)
    data = Column(Text, nullable=False)

    tenant = relationship("Tenant", back_populates="configs")

    logger.info("Config model defined successfully")


logger.info("All database table models initialized successfully")