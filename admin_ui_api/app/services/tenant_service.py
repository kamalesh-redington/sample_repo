import json
from pathlib import Path
from typing import Dict, List, Optional

import yaml
from fastapi import HTTPException, status

from app.core.config import settings
from app.db.session import get_session
from app.models.tables import Config, Tenant


def load_config_yaml() -> Dict:
    config_path = Path(settings.config_yaml_path)
    if not config_path.exists():
        return {}
    with config_path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def build_config_sections(raw_data: Dict) -> Dict[str, str]:
    if not raw_data:
        return {}

    sections = {
        "Source": raw_data.get("source", {}),
        "Chunking": raw_data.get("chunking", {}),
        "Embedding": raw_data.get("embedding", {}),
        "Vector Store": raw_data.get("vector_store", {}),
        "Meta Data": raw_data.get("metadata", {}),
    }
    return {name: json.dumps(value, indent=2, ensure_ascii=False) for name, value in sections.items()}


def get_tenant(tenant_id: int) -> Tenant:
    session = get_session()
    try:
        tenant = session.query(Tenant).filter_by(id=tenant_id).first()
        if not tenant:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")
        return tenant
    finally:
        session.close()


def get_all_tenants() -> List[Tenant]:
    session = get_session()
    try:
        return session.query(Tenant).order_by(Tenant.name).all()
    finally:
        session.close()


def get_configs_for_tenant(tenant_id: int) -> List[Config]:
    session = get_session()
    try:
        return session.query(Config).filter_by(tenant_id=tenant_id).order_by(Config.section).all()
    finally:
        session.close()


def authorize_tenant_access(user, tenant_id: int) -> Tenant:
    if user.role.name == "admin":
        return get_tenant(tenant_id)
    if user.role.name == "tenant" and user.tenant_id == tenant_id:
        return get_tenant(tenant_id)
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
