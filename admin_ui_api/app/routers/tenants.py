from fastapi import APIRouter, Depends, HTTPException, status

from app.config.logger import setup_logger
from app.config.timer import log_execution_time
from app.schemas.schemas import (
    ConfigSection,
    MessageResponse,
    PlaceholderResponse,
    TenantConfigResponse,
    TenantSchema,
    UserSchema,
)
from app.services.auth_service import get_current_user
from app.services.tenant_service import (
    authorize_tenant_access,
    get_all_tenants,
    get_configs_for_tenant,
    get_tenant,
)

logger = setup_logger(__name__)

router = APIRouter()


@router.get("/tenants", response_model=list[TenantSchema])
@log_execution_time(logger)
def list_tenants(current_user=Depends(get_current_user)):

    logger.info(f"List tenants API invoked by user: {current_user.username}")

    try:
        if current_user.role.name != "admin":

            logger.warning(
                f"Unauthorized tenant list access attempt by "
                f"user: {current_user.username}"
            )

            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only admin users can view all tenants",
            )

        logger.debug("Fetching all tenants")

        tenants = get_all_tenants()

        logger.info(f"Tenant list fetched successfully. Count: {len(tenants)}")

        return [
            TenantSchema(id=t.id, name=t.name, slug=t.slug, description=t.description)
            for t in tenants
        ]

    except HTTPException:
        raise

    except Exception as e:
        logger.exception(f"Failed to fetch tenant list: {str(e)}")
        raise


@router.get("/tenant/{tenant_id}", response_model=TenantSchema)
@log_execution_time(logger)
def tenant_detail(tenant_id: int, current_user=Depends(get_current_user)):

    logger.info(f"Tenant detail API invoked for tenant_id: {tenant_id}")

    try:
        logger.debug(f"Authorizing tenant access for tenant_id: {tenant_id}")

        tenant = authorize_tenant_access(current_user, tenant_id)

        logger.info(
            f"Tenant details fetched successfully for tenant_id: " f"{tenant_id}"
        )

        return TenantSchema(
            id=tenant.id,
            name=tenant.name,
            slug=tenant.slug,
            description=tenant.description,
        )

    except Exception as e:
        logger.exception(
            f"Failed to fetch tenant details for tenant_id " f"{tenant_id}: {str(e)}"
        )
        raise


@router.get("/tenant/{tenant_id}/config", response_model=TenantConfigResponse)
@log_execution_time(logger)
def tenant_config(tenant_id: int, current_user=Depends(get_current_user)):

    logger.info(f"Tenant config API invoked for tenant_id: {tenant_id}")

    try:
        logger.debug(f"Authorizing config access for tenant_id: {tenant_id}")

        tenant = authorize_tenant_access(current_user, tenant_id)

        logger.debug(f"Fetching configuration sections for tenant_id: {tenant_id}")

        configs = get_configs_for_tenant(tenant_id)

        sections = [config.section for config in configs]

        selected_section = sections[0] if sections else None

        content_body = (
            configs[0].data if configs else "No configuration data available."
        )

        logger.info(
            f"Tenant configuration fetched successfully for " f"tenant_id: {tenant_id}"
        )

        return TenantConfigResponse(
            tenant=TenantSchema(
                id=tenant.id,
                name=tenant.name,
                slug=tenant.slug,
                description=tenant.description,
            ),
            config_sections=sections,
            selected_section=selected_section,
            content_body=content_body,
        )

    except Exception as e:
        logger.exception(
            f"Failed to fetch tenant configuration for tenant_id "
            f"{tenant_id}: {str(e)}"
        )
        raise


@router.get("/tenant/{tenant_id}/unstructured", response_model=PlaceholderResponse)
@log_execution_time(logger)
def tenant_unstructured(tenant_id: int, current_user=Depends(get_current_user)):

    logger.info(f"Unstructured endpoint invoked for tenant_id: {tenant_id}")

    try:
        authorize_tenant_access(current_user, tenant_id)

        logger.info(f"Unstructured placeholder returned for tenant_id: " f"{tenant_id}")

        return PlaceholderResponse(
            title="Unstructured Data",
            message=(
                "This endpoint is a placeholder for "
                "unstructured data exploration and upload."
            ),
        )

    except Exception as e:
        logger.exception(
            f"Unstructured endpoint failed for tenant_id " f"{tenant_id}: {str(e)}"
        )
        raise


@router.get("/tenant/{tenant_id}/structured", response_model=PlaceholderResponse)
@log_execution_time(logger)
def tenant_structured(tenant_id: int, current_user=Depends(get_current_user)):

    logger.info(f"Structured endpoint invoked for tenant_id: {tenant_id}")

    try:
        authorize_tenant_access(current_user, tenant_id)

        logger.info(f"Structured placeholder returned for tenant_id: " f"{tenant_id}")

        return PlaceholderResponse(
            title="Structured Data",
            message=(
                "This endpoint is a placeholder for structured "
                "data definitions and dataset mappings."
            ),
        )

    except Exception as e:
        logger.exception(
            f"Structured endpoint failed for tenant_id " f"{tenant_id}: {str(e)}"
        )
        raise


@router.get("/tenant/{tenant_id}/retrieval", response_model=PlaceholderResponse)
@log_execution_time(logger)
def tenant_retrieval(tenant_id: int, current_user=Depends(get_current_user)):

    logger.info(f"Retrieval endpoint invoked for tenant_id: {tenant_id}")

    try:
        authorize_tenant_access(current_user, tenant_id)

        logger.info(f"Retrieval placeholder returned for tenant_id: " f"{tenant_id}")

        return PlaceholderResponse(
            title="Retrieval",
            message=(
                "This endpoint is a placeholder for retrieval "
                "and search pipeline controls."
            ),
        )

    except Exception as e:
        logger.exception(
            f"Retrieval endpoint failed for tenant_id " f"{tenant_id}: {str(e)}"
        )
        raise


@router.get("/tenant/{tenant_id}/logs", response_model=PlaceholderResponse)
@log_execution_time(logger)
def tenant_logs(tenant_id: int, current_user=Depends(get_current_user)):

    logger.info(f"Logs endpoint invoked for tenant_id: {tenant_id}")

    try:
        authorize_tenant_access(current_user, tenant_id)

        logger.info(f"Logs placeholder returned for tenant_id: " f"{tenant_id}")

        return PlaceholderResponse(
            title="Logs",
            message=(
                "This endpoint is a placeholder for tenant logs "
                "and operational history."
            ),
        )

    except Exception as e:
        logger.exception(
            f"Logs endpoint failed for tenant_id " f"{tenant_id}: {str(e)}"
        )
        raise
