from typing import Dict, List, Optional

from pydantic import BaseModel

from app.config.logger import setup_logger

logger = setup_logger(__name__)

logger.info("Initializing Pydantic schema models")


class LoginRequest(BaseModel):

    logger.debug("Defining LoginRequest schema")

    username: str
    password: str

    logger.info("LoginRequest schema defined successfully")


class UserSchema(BaseModel):

    logger.debug("Defining UserSchema")

    id: int
    username: str
    role: str
    tenant_id: Optional[int]

    class Config:
        orm_mode = True

    logger.info("UserSchema defined successfully")


class TokenResponse(BaseModel):

    logger.debug("Defining TokenResponse schema")

    access_token: str
    token_type: str = "bearer"
    user: UserSchema

    logger.info("TokenResponse schema defined successfully")


class MessageResponse(BaseModel):

    logger.debug("Defining MessageResponse schema")

    message: str

    logger.info("MessageResponse schema defined successfully")


class TenantSchema(BaseModel):

    logger.debug("Defining TenantSchema")

    id: int
    name: str
    slug: str
    description: Optional[str]

    class Config:
        orm_mode = True

    logger.info("TenantSchema defined successfully")


class ConfigSection(BaseModel):

    logger.debug("Defining ConfigSection schema")

    section: str
    data: str

    class Config:
        orm_mode = True

    logger.info("ConfigSection schema defined successfully")


class TenantConfigResponse(BaseModel):

    logger.debug("Defining TenantConfigResponse schema")

    tenant: TenantSchema
    config_sections: List[str]
    selected_section: Optional[str] = None
    content_body: str

    logger.info("TenantConfigResponse schema defined successfully")


class PlaceholderResponse(BaseModel):

    logger.debug("Defining PlaceholderResponse schema")

    title: str
    message: str

    logger.info("PlaceholderResponse schema defined successfully")


logger.info("All schema models initialized successfully")
