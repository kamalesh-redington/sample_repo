from fastapi import FastAPI, HTTPException, Depends, File, UploadFile, Header
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

