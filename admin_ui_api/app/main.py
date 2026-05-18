from fastapi import FastAPI

from app.core.config import settings
from app.db.base import Base, engine
from app.routers import auth, tenants
from app.services.auth_service import ensure_setup

app = FastAPI(title="Admin UI FastAPI")

Base.metadata.create_all(bind=engine)
ensure_setup()

app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(tenants.router, tags=["tenants"])

@app.get("/")
def read_root():
    return {"message": "Admin UI FastAPI is running", "config_path": str(settings.config_yaml_path)}
