import json
from pathlib import Path
from typing import Dict, List, Optional

import yaml
from fastapi import HTTPException, status

from app.config.logger import setup_logger
from app.core.config import settings
from app.db.session import get_session
from app.models.tables import Config, Tenant

logger = setup_logger(__name__)


def load_config_yaml() -> Dict:

    logger.info("Configuration YAML loading initiated")

    try:
        config_path = Path(settings.config_yaml_path)

        logger.debug(f"Resolved config path: {config_path}")

        if not config_path.exists():

            logger.warning(f"Configuration YAML file not found at: {config_path}")

            return {}

        logger.debug("Opening configuration YAML file")

        with config_path.open("r", encoding="utf-8") as handle:

            config_data = yaml.safe_load(handle) or {}

        logger.info("Configuration YAML loaded successfully")

        return config_data

    except Exception as e:
        logger.exception(f"Failed to load configuration YAML: {str(e)}")
        raise


def build_config_sections(raw_data: Dict) -> Dict[str, str]:

    logger.info("Building configuration sections initiated")

    try:
        if not raw_data:

            logger.warning("Empty configuration data received")

            return {}

        sections = {
            "Source": raw_data.get("source", {}),
            "Chunking": raw_data.get("chunking", {}),
            "Embedding": raw_data.get("embedding", {}),
            "Vector Store": raw_data.get("vector_store", {}),
            "Meta Data": raw_data.get("metadata", {}),
        }

        formatted_sections = {
            name: json.dumps(value, indent=2, ensure_ascii=False)
            for name, value in sections.items()
        }

        logger.info(
            f"Configuration sections built successfully. "
            f"Count: {len(formatted_sections)}"
        )

        return formatted_sections

    except Exception as e:
        logger.exception(f"Failed to build configuration sections: {str(e)}")
        raise


def get_tenant(tenant_id: int) -> Tenant:

    logger.info(f"Fetching tenant for tenant_id: {tenant_id}")

    session = get_session()

    try:
        logger.debug(f"Executing tenant query for tenant_id: {tenant_id}")

        tenant = session.query(Tenant).filter_by(id=tenant_id).first()

        if not tenant:

            logger.warning(f"Tenant not found for tenant_id: {tenant_id}")

            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found"
            )

        logger.info(f"Tenant fetched successfully for tenant_id: {tenant_id}")

        return tenant

    except HTTPException:
        raise

    except Exception as e:
        logger.exception(
            f"Failed to fetch tenant for tenant_id " f"{tenant_id}: {str(e)}"
        )
        raise

    finally:
        logger.debug("Closing tenant database session")
        session.close()
        logger.debug("Tenant database session closed")


def get_all_tenants() -> List[Tenant]:

    logger.info("Fetching all tenants initiated")

    session = get_session()

    try:
        logger.debug("Executing all tenant retrieval query")

        tenants = session.query(Tenant).order_by(Tenant.name).all()

        logger.info(f"All tenants fetched successfully. " f"Count: {len(tenants)}")

        return tenants

    except Exception as e:
        logger.exception(f"Failed to fetch all tenants: {str(e)}")
        raise

    finally:
        logger.debug("Closing tenant list database session")
        session.close()
        logger.debug("Tenant list database session closed")


def get_configs_for_tenant(tenant_id: int) -> List[Config]:

    logger.info(f"Fetching configuration sections for tenant_id: " f"{tenant_id}")

    session = get_session()

    try:
        logger.debug(f"Executing configuration query for tenant_id: " f"{tenant_id}")

        configs = (
            session.query(Config)
            .filter_by(tenant_id=tenant_id)
            .order_by(Config.section)
            .all()
        )

        logger.info(
            f"Configuration sections fetched successfully "
            f"for tenant_id: {tenant_id}. "
            f"Count: {len(configs)}"
        )

        return configs

    except Exception as e:
        logger.exception(
            f"Failed to fetch configurations for tenant_id " f"{tenant_id}: {str(e)}"
        )
        raise

    finally:
        logger.debug("Closing configuration database session")
        session.close()
        logger.debug("Configuration database session closed")


def authorize_tenant_access(user, tenant_id: int) -> Tenant:

    logger.info(
        f"Tenant access authorization initiated for "
        f"user: {user.username}, tenant_id: {tenant_id}"
    )

    try:
        if user.role.name == "admin":

            logger.info(f"Admin access granted for user: " f"{user.username}")

            return get_tenant(tenant_id)

        if user.role.name == "tenant" and user.tenant_id == tenant_id:

            logger.info(f"Tenant access granted for user: " f"{user.username}")

            return get_tenant(tenant_id)

        logger.warning(
            f"Tenant access denied for user: "
            f"{user.username}, tenant_id: {tenant_id}"
        )

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Access denied"
        )

    except HTTPException:
        raise

    except Exception as e:
        logger.exception(
            f"Tenant authorization failed for user " f"{user.username}: {str(e)}"
        )
        raise
