from config.logger import setup_logger

logger = setup_logger(__name__)

from fastapi import FastAPI, HTTPException, Depends, File, UploadFile, Header, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, ConfigDict
from pathlib import Path
from sqlalchemy.orm import Session
from typing import Optional
import yaml

# ────────────────────────────────────────────────────────────────────────────────
# Local imports
# ────────────────────────────────────────────────────────────────────────────────
from db.database import init_db, get_db
from db import crud
from auth.security import generate_strong_password, verify_bearer_token
from main import load_config, run_pipeline
from config.timer import log_execution_time
from datetime import datetime
import logging

# ───────────────────────────────────────────────────────────────────────────────
# FastAPI App
# ────────────────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="RAG Engine - Onboarding API",
    description="Tenant onboarding and ingestion initialization service",
    version="1.0.0",
)
logger.info("Starting Onboarding API")


class TraceLoggerAdapter(logging.LoggerAdapter):
    def process(self, msg, kwargs):
        trace_id = self.extra.get("trace_id")
        if trace_id:
            return f"[trace_id={trace_id}] {msg}", kwargs
        return msg, kwargs


@app.middleware("http")
async def attach_trace_id(request: Request, call_next):
    """Middleware to set a per-request trace_id into the logging context.

    If client supplies `trace_id` header, use it; otherwise generate a UTC timestamp.
    """
    trace_id = request.headers.get("trace_id")

    # Use integer epoch milliseconds as trace_id. If client provided a numeric header, use it.
    if trace_id:
        # try to normalize to integer milliseconds string
        try:
            trace_ms = int(float(trace_id))
            trace_id = str(trace_ms)
        except Exception:
            # if header isn't numeric, fall back to generating one
            trace_id = None

    if not trace_id:
        import time

        trace_id = str(int(time.time() * 1000))

    # set context var in logger module
    try:
        from config.logger import trace_id_ctx

        token = trace_id_ctx.set(trace_id)
    except Exception:
        token = None

    try:
        response = await call_next(request)
        return response
    finally:
        if token is not None:
            trace_id_ctx.reset(token)
# ────────────────────────────────────────────────────────────────────────────────
# Initialize Database
# ────────────────────────────────────────────────────────────────────────────────
logger.info("Initializing database")

init_db()

logger.info("Database initialized successfully")
# ────────────────────────────────────────────────────────────────────────────────
# Security
# ────────────────────────────────────────────────────────────────────────────────
security = HTTPBearer()
# Temporary admin token for testing
VALID_TOKEN = "your-secure-token-here"

# Local tenant config storage folder
TENANT_CONFIG_DIR = Path("tenant_configs") #tenant_configs

# Create folder if not exists
TENANT_CONFIG_DIR.mkdir(exist_ok=True)

logger.info(f"Tenant config directory ready: {TENANT_CONFIG_DIR}")


# ────────────────────────────────────────────────────────────────────────────────
# Response Models
# ────────────────────────────────────────────────────────────────────────────────
class HealthResponse(BaseModel):

    status: str
    service: str


class TenantCreationResponse(BaseModel):

    model_config = ConfigDict(from_attributes=True)

    tenant_pkid: str
    tenant_name: str
    username: str
    password: str
    message: str


# ────────────────────────────────────────────────────────────────────────────────
# Root Endpoint
# ────────────────────────────────────────────────────────────────────────────────


@app.get("/")
@log_execution_time(logger)
def root():
    logger.info("Root endpoint accessed")
    return {
        "message": "RAG Engine Onboarding API is running",
        "swagger": "/docs",
        "health": "/health",
        "config_debug": "/config/debug",
    }


# ────────────────────────────────────────────────────────────────────────────────
# Health Endpoint
# ────────────────────────────────────────────────────────────────────────────────


@app.get("/health", response_model=HealthResponse)
@log_execution_time(logger)
def health_check():
    logger.info("Health check endpoint accessed")
    return HealthResponse(status="ok", service="onboarding-api")


# ────────────────────────────────────────────────────────────────────────────────
# Config Debug Endpoint
# ────────────────────────────────────────────────────────────────────────────────


@app.get("/config/debug")
@log_execution_time(logger)
def config_debug():

    try:
        logger.info("Loading configuration for debug endpoint")
        config = load_config()
        logger.info("Configuration loaded successfully")
        return {
            "status": "success",
            "message": "Config loaded successfully",
            "config": config,
        }

    except Exception as e:
        logger.exception("Configuration loading failed")
        raise HTTPException(status_code=500, detail=f"Config loading failed: {str(e)}")


# ────────────────────────────────────────────────────────────────────────────────
# Tenant Onboarding Endpoint
# ────────────────────────────────────────────────────────────────────────────────


@app.post("/api/v1/tenant/create", response_model=TenantCreationResponse)
async def create_tenant(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    authorization: Optional[HTTPAuthorizationCredentials] = Depends(security),
    trace_id: Optional[str] = Header(None),
):
    """
    Create tenant using uploaded YAML configuration
    and trigger ingestion pipeline.
    """
    # Normalize trace_id: prefer numeric header; otherwise try to read middleware-provided ContextVar
    if trace_id:
        try:
            trace_id = str(int(float(trace_id)))
        except Exception:
            # non-numeric header, ignore and use middleware value
            trace_id = None

    if not trace_id:
        try:
            from config.logger import trace_id_ctx

            trace_id = trace_id_ctx.get()
        except Exception:
            import time

            trace_id = str(int(time.time() * 1000))

    # create a logger adapter that prefixes messages with trace_id
    l = TraceLoggerAdapter(logger, {"trace_id": trace_id})
    l.info("Tenant creation request received (trace_id=%s)", trace_id)
    # ────────────────────────────────────────────────────────────────────────────
    # Validate Bearer Token
    # ────────────────────────────────────────────────────────────────────────────
    l.info("Validating bearer token")
    verify_bearer_token(authorization, VALID_TOKEN)
    l.info("Bearer token validated successfully")
    # ────────────────────────────────────────────────────────────────────────────
    # Validate File Extension
    # ────────────────────────────────────────────────────────────────────────────
    l.info("Uploaded file received: %s", file.filename)
    if not (file.filename.endswith(".yaml") or file.filename.endswith(".yml")):
        l.warning("Invalid file type uploaded: %s", file.filename)
        raise HTTPException(status_code=400, detail="Only YAML files are allowed")

    try:

        # ────────────────────────────────────────────────────────────────────────
        # Read YAML File
        # ────────────────────────────────────────────────────────────────────────
        l.info("Reading uploaded YAML file")

        content = await file.read()

        yaml_content = yaml.safe_load(content.decode("utf-8"))
        l.info("YAML parsed successfully")
        l.debug("Parsed YAML content: %s", yaml_content)
        if not yaml_content:
            l.warning("Uploaded YAML file is empty")
            raise HTTPException(status_code=400, detail="YAML file is empty")

        # ────────────────────────────────────────────────────────────────────────
        # Validate Tenant Section
        # ────────────────────────────────────────────────────────────────────────
        l.info("Validating tenant configuration section")

        if "tenant" not in yaml_content:
            l.warning("Tenant section missing in YAML")
            raise HTTPException(
                status_code=400, detail="YAML must contain 'tenant' section"
            )

        tenant_config = yaml_content["tenant"]
        l.debug("Tenant configuration: %s", tenant_config)

        tenant_name = tenant_config.get("name")
        l.info("Processing tenant: %s", tenant_name)
        # ────────────────────────────────────────────────────────────
        # Save tenant YAML locally
        # ────────────────────────────────────────────────────────────

        tenant_config_filename = f"{tenant_name}-config.yaml"

        tenant_config_path = TENANT_CONFIG_DIR / tenant_config_filename

        with open(tenant_config_path, "w", encoding="utf-8") as config_file:

            config_file.write(content.decode("utf-8"))

        l.info("Tenant config saved: %s", tenant_config_path)
        if not tenant_name:
            l.warning("tenant.name is missing")
            raise HTTPException(status_code=400, detail="tenant.name is required")

        # ────────────────────────────────────────────────────────────────────────
        # Generate Tenant PKID
        # ────────────────────────────────────────────────────────────────────────

        tenant_pkid = tenant_name.lower().replace(" ", "-").replace("_", "-")

        tenant_pkid = "".join(c for c in tenant_pkid if c.isalnum() or c == "-")
        l.info("Generated tenant PKID: %s", tenant_pkid)
        l.debug("Normalized tenant PKID generated from tenant name: %s", tenant_name)
        # ────────────────────────────────────────────────────────────────────────
        # Duplicate Tenant Validation
        # ────────────────────────────────────────────────────────────────────────
        l.info("Checking existing tenant: %s", tenant_pkid)
        l.debug("Checking tenant existence in database for PKID: %s", tenant_pkid)
        existing_tenant = crud.get_tenant_by_pkid(db, tenant_pkid)

        if existing_tenant:

            l.warning("Duplicate tenant detected: %s", tenant_pkid)
            raise HTTPException(
                status_code=409, detail=f"Tenant '{tenant_pkid}' already exists"
            )

        # ────────────────────────────────────────────────────────────────────────
        # Create Tenant
        # ────────────────────────────────────────────────────────────────────────
        l.info("Creating tenant in database: %s", tenant_pkid)

        db_tenant = crud.create_tenant(
            db=db,
            tenant_pkid=tenant_pkid,
            name=tenant_name,
            config_yaml=content.decode("utf-8"),
        )
        l.info("Tenant created successfully: %s", tenant_pkid)
        l.debug("Database tenant object created: %s", db_tenant)
        # ────────────────────────────────────────────────────────────────────────
        # Generate Tenant Credentials
        # ────────────────────────────────────────────────────────────────────────

        username = tenant_pkid

        password = generate_strong_password(length=16)
        l.info("Generated credentials for tenant: %s", username)
        l.debug("Generated password length for user %s: %d", username, len(password))
        # ────────────────────────────────────────────────────────────────────────
        # Duplicate User Validation
        # ────────────────────────────────────────────────────────────────────────
        logger.debug(f"Checking if user already exists: {username}")
        if crud.user_exists(db, username):
            l.warning("Duplicate user detected: %s", username)
            raise HTTPException(
                status_code=409, detail=f"User '{username}' already exists"
            )

        # ────────────────────────────────────────────────────────────────────────
        # Create Tenant User
        # ────────────────────────────────────────────────────────────────────────
        l.info("Creating tenant user: %s", username)
        
        db_user = crud.create_user_for_tenant(
            db=db,
            tenant_id=db_tenant.id,
            username=username,
            password=password,
            email=None,
            role_id=None,
        )
        l.debug("Database user object created: %s", db_user)
        l.info("Tenant user created successfully: %s", username)
        # ────────────────────────────────────────────────────────────────────────
        # Trigger Ingestion Pipeline
        # ────────────────────────────────────────────────────────────────────────
        l.info("Triggering ingestion pipeline for tenant: %s", tenant_name)

        try:

            config = load_config(str(tenant_config_path))

            l.info("Pipeline configuration loaded successfully")
            l.debug("Pipeline configuration loaded: %s", config)

            run_pipeline(config)

            l.info("Ingestion pipeline executed successfully")
            l.debug("Pipeline execution completed for tenant: %s", tenant_pkid)
        except Exception as pipeline_error:

            l.exception("Ingestion pipeline execution failed")

            raise HTTPException(
                status_code=500,
                detail=f"Ingestion pipeline failed: {str(pipeline_error)}",
            )

        # ────────────────────────────────────────────────────────────────────────
        # Success Response
        # ────────────────────────────────────────────────────────────────────────
        l.info("Tenant onboarding completed successfully: %s", tenant_pkid)
        return TenantCreationResponse(
            tenant_pkid=tenant_pkid,
            tenant_name=tenant_name,
            username=username,
            password=password,
            message=(
                f"Tenant '{tenant_name}' "
                f"and user '{username}' "
                f"created successfully"
            ),
        )

    # ────────────────────────────────────────────────────────────────────────────
    # YAML Validation Error
    # ────────────────────────────────────────────────────────────────────────────

    except yaml.YAMLError as e:
        l = TraceLoggerAdapter(logger, {"trace_id": trace_id})
        l.exception("Invalid YAML uploaded")

        raise HTTPException(status_code=400, detail=f"Invalid YAML: {str(e)}")

    # ────────────────────────────────────────────────────────────────────────────
    # Re-raise HTTP Exceptions
    # ────────────────────────────────────────────────────────────────────────────

    except HTTPException:
        raise

    # ────────────────────────────────────────────────────────────────────────────
    # Generic Server Errors
    # ────────────────────────────────────────────────────────────────────────────

    except Exception as e:
        l = TraceLoggerAdapter(logger, {"trace_id": trace_id})
        l.debug("Exception details: %s", str(e))
        l.exception("Tenant creation failed")

        raise HTTPException(status_code=500, detail=f"Tenant creation failed: {str(e)}")


# ────────────────────────────────────────────────────────────────────────────────
# Startup Event
# ────────────────────────────────────────────────────────────────────────────────


@app.on_event("startup")
@log_execution_time(logger)
def startup_event():

    logger.info("RAG ENGINE ONBOARDING API STARTED")
