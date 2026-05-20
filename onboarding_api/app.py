from config.logger import setup_logger

logger = setup_logger(__name__)

from fastapi import FastAPI, HTTPException, Depends, File, UploadFile
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

# ───────────────────────────────────────────────────────────────────────────────
# FastAPI App
# ────────────────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="RAG Engine - Onboarding API",
    description="Tenant onboarding and ingestion initialization service",
    version="1.0.0",
)
logger.info("Starting Onboarding API")
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
TENANT_CONFIG_DIR = Path("tenant_configs")

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
def health_check():
    logger.info("Health check endpoint accessed")
    return HealthResponse(status="ok", service="onboarding-api")


# ────────────────────────────────────────────────────────────────────────────────
# Config Debug Endpoint
# ────────────────────────────────────────────────────────────────────────────────


@app.get("/config/debug")
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
):
    """
    Create tenant using uploaded YAML configuration
    and trigger ingestion pipeline.
    """
    logger.info("Tenant creation request received")
    # ────────────────────────────────────────────────────────────────────────────
    # Validate Bearer Token
    # ────────────────────────────────────────────────────────────────────────────
    logger.info("Validating bearer token")
    verify_bearer_token(authorization, VALID_TOKEN)
    logger.info("Bearer token validated successfully")
    # ────────────────────────────────────────────────────────────────────────────
    # Validate File Extension
    # ────────────────────────────────────────────────────────────────────────────
    logger.info(f"Uploaded file received: {file.filename}")
    if not (file.filename.endswith(".yaml") or file.filename.endswith(".yml")):
        logger.warning(f"Invalid file type uploaded: {file.filename}")
        raise HTTPException(status_code=400, detail="Only YAML files are allowed")

    try:

        # ────────────────────────────────────────────────────────────────────────
        # Read YAML File
        # ────────────────────────────────────────────────────────────────────────
        logger.info("Reading uploaded YAML file")

        content = await file.read()

        yaml_content = yaml.safe_load(content.decode("utf-8"))
        logger.info("YAML parsed successfully")
        logger.debug(f"Parsed YAML content: {yaml_content}")
        if not yaml_content:
            logger.warning("Uploaded YAML file is empty")

            raise HTTPException(status_code=400, detail="YAML file is empty")

        # ────────────────────────────────────────────────────────────────────────
        # Validate Tenant Section
        # ────────────────────────────────────────────────────────────────────────
        logger.info("Validating tenant configuration section")

        if "tenant" not in yaml_content:
            logger.warning("Tenant section missing in YAML")
            raise HTTPException(
                status_code=400, detail="YAML must contain 'tenant' section"
            )

        tenant_config = yaml_content["tenant"]
        logger.debug(f"Tenant configuration: {tenant_config}")

        tenant_name = tenant_config.get("name")
        logger.info(f"Processing tenant: {tenant_name}")
        # ────────────────────────────────────────────────────────────
        # Save tenant YAML locally
        # ────────────────────────────────────────────────────────────

        tenant_config_filename = f"{tenant_name}-config.yaml"

        tenant_config_path = TENANT_CONFIG_DIR / tenant_config_filename

        with open(tenant_config_path, "w", encoding="utf-8") as config_file:

            config_file.write(content.decode("utf-8"))

        logger.info(f"Tenant config saved: {tenant_config_path}")
        if not tenant_name:
            logger.warning("tenant.name is missing")

            raise HTTPException(status_code=400, detail="tenant.name is required")

        # ────────────────────────────────────────────────────────────────────────
        # Generate Tenant PKID
        # ────────────────────────────────────────────────────────────────────────

        tenant_pkid = tenant_name.lower().replace(" ", "-").replace("_", "-")

        tenant_pkid = "".join(c for c in tenant_pkid if c.isalnum() or c == "-")
        logger.info(f"Generated tenant PKID: {tenant_pkid}")
        logger.debug(
            f"Normalized tenant PKID generated from tenant name: {tenant_name}"
        )
        # ────────────────────────────────────────────────────────────────────────
        # Duplicate Tenant Validation
        # ────────────────────────────────────────────────────────────────────────
        logger.info(f"Checking existing tenant: {tenant_pkid}")
        logger.debug(f"Checking tenant existence in database for PKID: {tenant_pkid}")
        existing_tenant = crud.get_tenant_by_pkid(db, tenant_pkid)

        if existing_tenant:

            logger.warning(f"Duplicate tenant detected: {tenant_pkid}")
            raise HTTPException(
                status_code=409, detail=f"Tenant '{tenant_pkid}' already exists"
            )

        # ────────────────────────────────────────────────────────────────────────
        # Create Tenant
        # ────────────────────────────────────────────────────────────────────────
        logger.info(f"Creating tenant in database: {tenant_pkid}")

        db_tenant = crud.create_tenant(
            db=db,
            tenant_pkid=tenant_pkid,
            name=tenant_name,
            config_yaml=content.decode("utf-8"),
        )
        logger.info(f"Tenant created successfully: {tenant_pkid}")
        logger.debug(f"Database tenant object created: {db_tenant}")
        # ────────────────────────────────────────────────────────────────────────
        # Generate Tenant Credentials
        # ────────────────────────────────────────────────────────────────────────

        username = tenant_pkid

        password = generate_strong_password(length=16)
        logger.info(f"Generated credentials for tenant: {username}")
        logger.debug(f"Generated password length for user {username}: {len(password)}")
        # ────────────────────────────────────────────────────────────────────────
        # Duplicate User Validation
        # ────────────────────────────────────────────────────────────────────────
        logger.debug(f"Checking if user already exists: {username}")
        if crud.user_exists(db, username):
            logger.warning(f"Duplicate user detected: {username}")
            raise HTTPException(
                status_code=409, detail=f"User '{username}' already exists"
            )

        # ────────────────────────────────────────────────────────────────────────
        # Create Tenant User
        # ────────────────────────────────────────────────────────────────────────
        logger.info(f"Creating tenant user: {username}")
        
        db_user = crud.create_user_for_tenant(
            db=db,
            tenant_id=db_tenant.id,
            username=username,
            password=password,
            email=None,
            role_id=None,
        )
        logger.debug(f"Database user object created: {db_user}")
        logger.info(f"Tenant user created successfully: {username}")
        # ────────────────────────────────────────────────────────────────────────
        # Trigger Ingestion Pipeline
        # ────────────────────────────────────────────────────────────────────────
        logger.info(f"Triggering ingestion pipeline for tenant: {tenant_name}")

        try:

            config = load_config(str(tenant_config_path))

            logger.info("Pipeline configuration loaded successfully")
            logger.debug(f"Pipeline configuration loaded: {config}")

            run_pipeline(config)

            logger.info("Ingestion pipeline executed successfully")
            logger.debug(f"Pipeline execution completed for tenant: {tenant_pkid}")
        except Exception as pipeline_error:

            logger.exception("Ingestion pipeline execution failed")

            raise HTTPException(
                status_code=500,
                detail=f"Ingestion pipeline failed: {str(pipeline_error)}",
            )

        # ────────────────────────────────────────────────────────────────────────
        # Success Response
        # ────────────────────────────────────────────────────────────────────────
        logger.info(f"Tenant onboarding completed successfully: {tenant_pkid}")
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
        logger.exception("Invalid YAML uploaded")

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
        logger.debug(f"Exception details: {str(e)}")
        logger.exception("Tenant creation failed")

        raise HTTPException(status_code=500, detail=f"Tenant creation failed: {str(e)}")


# ────────────────────────────────────────────────────────────────────────────────
# Startup Event
# ────────────────────────────────────────────────────────────────────────────────


@app.on_event("startup")
def startup_event():

    logger.info("RAG ENGINE ONBOARDING API STARTED")


'''from fastapi import (
    FastAPI,
    HTTPException,
    Depends,
    File,
    UploadFile
)

from fastapi.responses import JSONResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from pydantic import BaseModel, ConfigDict

from sqlalchemy.orm import Session

from typing import Optional

import yaml

# ────────────────────────────────────────────────────────────────────────────────
# Local imports
# ────────────────────────────────────────────────────────────────────────────────

from db.database import init_db, get_db

from db import crud

from auth.security import (
    generate_strong_password,
    verify_bearer_token
)

# Optional:
# Used later for ingestion trigger if needed
from main import load_config, run_pipeline

# ────────────────────────────────────────────────────────────────────────────────
# FastAPI App
# ────────────────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="RAG Engine - Onboarding API",
    description="Tenant onboarding and ingestion initialization service",
    version="1.0.0"
)

# ────────────────────────────────────────────────────────────────────────────────
# Initialize DB on startup
# ────────────────────────────────────────────────────────────────────────────────

init_db()

# ────────────────────────────────────────────────────────────────────────────────
# Security
# ────────────────────────────────────────────────────────────────────────────────

security = HTTPBearer()

# Temporary hardcoded token for testing
# Later move to ENV or JWT auth
VALID_TOKEN = "your-secure-token-here"

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
# Health Endpoint
# ────────────────────────────────────────────────────────────────────────────────

@app.get("/health", response_model=HealthResponse)
def health_check():

    return HealthResponse(
        status="ok",
        service="onboarding-api"
    )

# ────────────────────────────────────────────────────────────────────────────────
# Root Endpoint
# ────────────────────────────────────────────────────────────────────────────────

@app.get("/")
def root():

    return {
        "message": "RAG Engine Onboarding API is running",
        "swagger": "/docs",
        "health": "/health"
    }

# ────────────────────────────────────────────────────────────────────────────────
# Tenant Onboarding Endpoint
# ────────────────────────────────────────────────────────────────────────────────

@app.post(
    "/api/v1/tenant/create",
    response_model=TenantCreationResponse
)
async def create_tenant(

    file: UploadFile = File(...),

    db: Session = Depends(get_db),

    authorization: Optional[
        HTTPAuthorizationCredentials
    ] = Depends(security)
):
    """
    Create tenant using uploaded YAML configuration.
    """

    # ────────────────────────────────────────────────────────────────────────────
    # Validate bearer token
    # ────────────────────────────────────────────────────────────────────────────

    verify_bearer_token(
        authorization,
        VALID_TOKEN
    )

    # ────────────────────────────────────────────────────────────────────────────
    # Validate file extension
    # ────────────────────────────────────────────────────────────────────────────

    if not (
        file.filename.endswith(".yaml")
        or file.filename.endswith(".yml")
    ):
        raise HTTPException(
            status_code=400,
            detail="Only YAML files are allowed"
        )

    try:

        # ────────────────────────────────────────────────────────────────────────
        # Read YAML content
        # ────────────────────────────────────────────────────────────────────────

        content = await file.read()

        yaml_content = yaml.safe_load(
            content.decode("utf-8")
        )

        if not yaml_content:
            raise HTTPException(
                status_code=400,
                detail="YAML file is empty"
            )

        # ────────────────────────────────────────────────────────────────────────
        # Validate tenant section
        # ────────────────────────────────────────────────────────────────────────

        if "tenant" not in yaml_content:
            raise HTTPException(
                status_code=400,
                detail="YAML must contain 'tenant' section"
            )

        tenant_config = yaml_content["tenant"]

        tenant_name = tenant_config.get("name")

        if not tenant_name:
            raise HTTPException(
                status_code=400,
                detail="tenant.name is required"
            )

        # ────────────────────────────────────────────────────────────────────────
        # Generate tenant PKID
        # ────────────────────────────────────────────────────────────────────────

        tenant_pkid = (
            tenant_name
            .lower()
            .replace(" ", "-")
            .replace("_", "-")
        )

        tenant_pkid = "".join(
            c for c in tenant_pkid
            if c.isalnum() or c == "-"
        )

        # ────────────────────────────────────────────────────────────────────────
        # Check duplicate tenant
        # ────────────────────────────────────────────────────────────────────────

        existing_tenant = crud.get_tenant_by_pkid(
            db,
            tenant_pkid
        )

        if existing_tenant:
            raise HTTPException(
                status_code=409,
                detail=f"Tenant '{tenant_pkid}' already exists"
            )

        # ────────────────────────────────────────────────────────────────────────
        # Create tenant
        # ────────────────────────────────────────────────────────────────────────

        tenant_description = tenant_config.get(
            "description",
            ""
        )

        db_tenant = crud.create_tenant(
            db=db,
            tenant_pkid=tenant_pkid,
            name=tenant_name,
            config_yaml=content.decode("utf-8")
        )

        # ────────────────────────────────────────────────────────────────────────
        # Generate tenant user credentials
        # ────────────────────────────────────────────────────────────────────────

        username = tenant_pkid

        password = generate_strong_password(
            length=16
        )

        # ────────────────────────────────────────────────────────────────────────
        # Check duplicate user
        # ────────────────────────────────────────────────────────────────────────

        if crud.user_exists(db, username):

            raise HTTPException(
                status_code=409,
                detail=f"User '{username}' already exists"
            )

        # ────────────────────────────────────────────────────────────────────────
        # Create tenant user
        # ────────────────────────────────────────────────────────────────────────

        db_user = crud.create_user_for_tenant(
            db=db,
            tenant_id=db_tenant.id,
            username=username,
            password=password,
            email=None,
            role_id=None
        )

        # ────────────────────────────────────────────────────────────────────────
        # OPTIONAL:
        # Trigger ingestion pipeline later if needed
        # ────────────────────────────────────────────────────────────────────────
        

        # ────────────────────────────────────────────────────────────────────────
        # Success response
        # ────────────────────────────────────────────────────────────────────────

        return TenantCreationResponse(
            tenant_pkid=tenant_pkid,
            tenant_name=tenant_name,
            username=username,
            password=password,
            message=(
                f"Tenant '{tenant_name}' "
                f"and user '{username}' "
                f"created successfully"
            )
        )

    # ────────────────────────────────────────────────────────────────────────────
    # YAML parsing errors
    # ────────────────────────────────────────────────────────────────────────────

    except yaml.YAMLError as e:

        raise HTTPException(
            status_code=400,
            detail=f"Invalid YAML: {str(e)}"
        )

    # ────────────────────────────────────────────────────────────────────────────
    # Re-raise FastAPI exceptions
    # ────────────────────────────────────────────────────────────────────────────

    except HTTPException:
        raise

    # ────────────────────────────────────────────────────────────────────────────
    # Generic server errors
    # ────────────────────────────────────────────────────────────────────────────

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=f"Tenant creation failed: {str(e)}"
        )

# ────────────────────────────────────────────────────────────────────────────────
# Startup Event
# ────────────────────────────────────────────────────────────────────────────────

@app.on_event("startup")
def startup_event():

    print("\n" + "=" * 60)
    print("RAG ENGINE ONBOARDING API STARTED")
    print("=" * 60)

    print("Available endpoints:")
    print("GET  /")
    print("GET  /health")
    print("POST /api/v1/tenant/create")

    print("\nSwagger UI:")
    print("http://127.0.0.1:8000/docs")

    print("=" * 60)
    
    '''
'''from fastapi import FastAPI, HTTPException, Depends, File, UploadFile, Header
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.security import HTTPBearer
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session
from typing import Optional
import yaml

from main import run_pipeline, load_config
from db.database import init_db, get_db
from db import crud
from auth.security import generate_strong_password, verify_bearer_token
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

app = FastAPI(title="RAG Chat UI")

# Initialize database on startup
init_db()
# @app.on_event("startup")
# def startup_event():
#     init_db()

# HTTP Bearer security scheme for tenant endpoint
security = HTTPBearer()

query_engine = None

class QueryRequest(BaseModel):
    question: str


class TenantCreationResponse(BaseModel):
    """Response model for tenant creation."""
    model_config = ConfigDict(from_attributes=True)
    
    tenant_pkid: str
    tenant_name: str
    username: str
    password: str
    message: str


def get_query_engine():
    global query_engine
    if query_engine is None:
        config = load_config()
        index = run_pipeline(config)
        query_engine = index.as_query_engine()
    return query_engine

@app.get("/", response_class=HTMLResponse)
def root():
    return """<!DOCTYPE html>
<html lang=\"en\">
<head>
    <meta charset=\"UTF-8\" />
    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\" />
    <title>RAG Document Chat</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            background: #f4f7fb;
            margin: 0;
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 100vh;
        }
        .chat-window {
            width: min(760px, 100%);
            background: #fff;
            border-radius: 14px;
            box-shadow: 0 18px 45px rgba(15, 23, 42, 0.12);
            overflow: hidden;
        }
        .header {
            background: #1f2937;
            color: #fff;
            padding: 18px 22px;
            font-size: 1.2rem;
            font-weight: 700;
        }
        .messages {
            min-height: 360px;
            max-height: 520px;
            overflow-y: auto;
            padding: 20px;
            background: #f9fafb;
        }
        .message {
            margin-bottom: 18px;
            display: flex;
        }
        .message.user { justify-content: flex-end; }
        .message.bot { justify-content: flex-start; }
        .bubble {
            max-width: 78%;
            padding: 14px 16px;
            border-radius: 16px;
            line-height: 1.5;
            white-space: pre-wrap;
        }
        .bubble.user {
            background: #2563eb;
            color: #fff;
            border-bottom-right-radius: 6px;
        }
        .bubble.bot {
            background: #e5e7eb;
            color: #111827;
            border-bottom-left-radius: 6px;
        }
        .input-area {
            display: flex;
            gap: 12px;
            padding: 18px 22px 22px;
            background: #fff;
        }
        textarea {
            flex: 1;
            resize: vertical;
            min-height: 80px;
            padding: 14px 16px;
            border: 1px solid #d1d5db;
            border-radius: 12px;
            font-size: 1rem;
        }
        button {
            background: #2563eb;
            border: none;
            color: #fff;
            padding: 0 24px;
            border-radius: 12px;
            cursor: pointer;
            font-size: 1rem;
        }
        button:disabled {
            background: #93c5fd;
            cursor: default;
        }
    </style>
</head>
<body>
    <div class=\"chat-window\">
        <div class=\"header\">RAG Document Chat</div>
        <div id=\"messages\" class=\"messages\"></div>
        <form id=\"chat-form\" class=\"input-area\">
            <textarea id=\"question\" placeholder=\"Ask a question about the documents...\"></textarea>
            <button type=\"submit\">Send</button>
        </form>
    </div>
    <script>
        const messages = document.getElementById('messages');
        const form = document.getElementById('chat-form');
        const questionInput = document.getElementById('question');

        function addMessage(text, role) {
            const wrapper = document.createElement('div');
            wrapper.className = `message ${role}`;
            const bubble = document.createElement('div');
            bubble.className = `bubble ${role}`;
            bubble.textContent = text;
            wrapper.appendChild(bubble);
            messages.appendChild(wrapper);
            messages.scrollTop = messages.scrollHeight;
        }

        async function sendQuestion(question) {
            const response = await fetch('/query', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ question }),
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || 'Unknown error');
            }

            return response.json();
        }

        form.addEventListener('submit', async (event) => {
            event.preventDefault();
            const question = questionInput.value.trim();
            if (!question) {
                return;
            }

            addMessage(question, 'user');
            questionInput.value = '';
            const button = form.querySelector('button');
            button.disabled = true;
            button.textContent = 'Thinking...';

            try {
                const data = await sendQuestion(question);
                addMessage(data.answer, 'bot');
            } catch (error) {
                addMessage(`Error: ${error.message}`, 'bot');
            } finally {
                button.disabled = false;
                button.textContent = 'Send';
            }
        });
    </script>
</body>
</html>"""

# Streamlit UI can post to this endpoint at /query with JSON payload {"question": "..."}
@app.post("/query")
def query_document(request: QueryRequest):
    question = request.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="Question may not be empty.")

    engine = get_query_engine()

    try:
        response = engine.query(question)
        answer = str(response)
        return {"question": question, "answer": answer}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Query failed: {exc}")


@app.post("/api/v1/tenant/create", response_model=TenantCreationResponse)
async def create_tenant(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    authorization: Optional[HTTPAuthorizationCredentials] = Depends(security)
):
    """
    Create a new tenant and user via YAML file upload.
    
    **Requirements:**
    - Bearer token authentication (must match valid token)
    - YAML file with tenant configuration
    
    **YAML file format:**
    ```yaml
    tenant:
      name: "Tenant Name"
      description: "Optional description"
    ```
    
    **Returns:**
    - tenant_pkid: Unique tenant identifier
    - username: Created username (tenant_pkid)
    - password: Strong password for the user
    - tenant_name: Name of the created tenant
    
    **Example:**
    ```bash
    curl -X POST http://localhost:8000/api/v1/tenant/create \\
      -H "Authorization: Bearer YOUR_TOKEN" \\
      -F "file=@config.yaml"
    ```
    """
    # Verify bearer token
    # In production, validate against a proper token store
    VALID_TOKEN = "your-secure-token-here"  # Change this to environment variable
    verify_bearer_token(authorization, VALID_TOKEN)
    
    # Validate file extension
    if not file.filename.endswith('.yaml') and not file.filename.endswith('.yml'):
        raise HTTPException(
            status_code=400,
            detail="File must be a YAML file (.yaml or .yml)"
        )
    
    try:
        # Read and parse YAML file
        content = await file.read()
        yaml_content = yaml.safe_load(content.decode('utf-8'))
        
        if not yaml_content or 'tenant' not in yaml_content:
            raise HTTPException(
                status_code=400,
                detail="Invalid YAML format. Must contain 'tenant' key with 'name' field."
            )
        
        tenant_config = yaml_content.get('tenant', {})
        tenant_name = tenant_config.get('name')
        
        if not tenant_name:
            raise HTTPException(
                status_code=400,
                detail="YAML must contain 'tenant.name' field"
            )
        
        # Generate tenant_pkid from tenant name (e.g., "Acme Corp" -> "acme-corp")
        tenant_pkid = tenant_name.lower().replace(' ', '-').replace('_', '-')
        tenant_pkid = ''.join(c for c in tenant_pkid if c.isalnum() or c == '-')
        
        # Check if tenant already exists
        existing_tenant = crud.get_tenant_by_pkid(db, tenant_pkid)
        if existing_tenant:
            raise HTTPException(
                status_code=409,
                detail=f"Tenant with ID '{tenant_pkid}' already exists"
            )
        
        # Create tenant
        tenant_description = tenant_config.get('description', '')
        db_tenant = crud.create_tenant(
            db=db,
            tenant_pkid=tenant_pkid,
            name=tenant_name,
            config_yaml=content.decode('utf-8')
        )
        
        # Generate strong password
        password = generate_strong_password(length=16)
        
        # Create user for tenant with username = tenant_pkid
        username = tenant_pkid
        
        # Check if user already exists
        if crud.user_exists(db, username):
            raise HTTPException(
                status_code=409,
                detail=f"User '{username}' already exists"
            )
        
        # Create user and assign 'tenant' role
        db_user = crud.create_user_for_tenant(
            db=db,
            tenant_id=db_tenant.id,
            username=username,
            password=password,
            email=None,
            role_id=None  # Will use default 'tenant' role
        )
        
        return TenantCreationResponse(
            tenant_pkid=tenant_pkid,
            tenant_name=tenant_name,
            username=username,
            password=password,
            message=f"Tenant '{tenant_name}' and user '{username}' created successfully"
        )
        
    except yaml.YAMLError as e:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid YAML file: {str(e)}"
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error creating tenant: {str(e)}"
        )

'''
