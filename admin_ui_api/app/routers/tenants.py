from fastapi import APIRouter, Depends, HTTPException, status

from app.schemas.schemas import ConfigSection, MessageResponse, PlaceholderResponse, TenantConfigResponse, TenantSchema, UserSchema
from app.services.auth_service import get_current_user
from app.services.tenant_service import authorize_tenant_access, get_all_tenants, get_configs_for_tenant, get_tenant

router = APIRouter()


@router.get("/tenants", response_model=list[TenantSchema])
def list_tenants(current_user=Depends(get_current_user)):
    if current_user.role.name != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only admin users can view all tenants")
    return [TenantSchema(id=t.id, name=t.name, slug=t.slug, description=t.description) for t in get_all_tenants()]


@router.get("/tenant/{tenant_id}", response_model=TenantSchema)
def tenant_detail(tenant_id: int, current_user=Depends(get_current_user)):
    tenant = authorize_tenant_access(current_user, tenant_id)
    return TenantSchema(id=tenant.id, name=tenant.name, slug=tenant.slug, description=tenant.description)


@router.get("/tenant/{tenant_id}/config", response_model=TenantConfigResponse)
def tenant_config(tenant_id: int, current_user=Depends(get_current_user)):
    tenant = authorize_tenant_access(current_user, tenant_id)
    configs = get_configs_for_tenant(tenant_id)
    sections = [config.section for config in configs]
    selected_section = sections[0] if sections else None
    content_body = configs[0].data if configs else "No configuration data available."
    return TenantConfigResponse(
        tenant=TenantSchema(id=tenant.id, name=tenant.name, slug=tenant.slug, description=tenant.description),
        config_sections=sections,
        selected_section=selected_section,
        content_body=content_body,
    )


@router.get("/tenant/{tenant_id}/unstructured", response_model=PlaceholderResponse)
def tenant_unstructured(tenant_id: int, current_user=Depends(get_current_user)):
    authorize_tenant_access(current_user, tenant_id)
    return PlaceholderResponse(title="Unstructured Data", message="This endpoint is a placeholder for unstructured data exploration and upload.")


@router.get("/tenant/{tenant_id}/structured", response_model=PlaceholderResponse)
def tenant_structured(tenant_id: int, current_user=Depends(get_current_user)):
    authorize_tenant_access(current_user, tenant_id)
    return PlaceholderResponse(title="Structured Data", message="This endpoint is a placeholder for structured data definitions and dataset mappings.")


@router.get("/tenant/{tenant_id}/retrieval", response_model=PlaceholderResponse)
def tenant_retrieval(tenant_id: int, current_user=Depends(get_current_user)):
    authorize_tenant_access(current_user, tenant_id)
    return PlaceholderResponse(title="Retrieval", message="This endpoint is a placeholder for retrieval and search pipeline controls.")


@router.get("/tenant/{tenant_id}/logs", response_model=PlaceholderResponse)
def tenant_logs(tenant_id: int, current_user=Depends(get_current_user)):
    authorize_tenant_access(current_user, tenant_id)
    return PlaceholderResponse(title="Logs", message="This endpoint is a placeholder for tenant logs and operational history.")
