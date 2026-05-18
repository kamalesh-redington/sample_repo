from typing import Dict, List, Optional

from pydantic import BaseModel


class LoginRequest(BaseModel):
    username: str
    password: str


class UserSchema(BaseModel):
    id: int
    username: str
    role: str
    tenant_id: Optional[int]

    class Config:
        orm_mode = True


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserSchema


class MessageResponse(BaseModel):
    message: str


class TenantSchema(BaseModel):
    id: int
    name: str
    slug: str
    description: Optional[str]

    class Config:
        orm_mode = True


class ConfigSection(BaseModel):
    section: str
    data: str

    class Config:
        orm_mode = True


class TenantConfigResponse(BaseModel):
    tenant: TenantSchema
    config_sections: List[str]
    selected_section: Optional[str] = None
    content_body: str


class PlaceholderResponse(BaseModel):
    title: str
    message: str
