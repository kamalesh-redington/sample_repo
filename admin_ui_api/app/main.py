from fastapi import FastAPI

from app.config.logger import setup_logger
from app.config.timer import log_execution_time
from app.core.config import settings
from app.db.base import Base, engine
from app.routers import auth, tenants
from app.services.auth_service import ensure_setup

logger = setup_logger(__name__)

logger.info("Admin UI FastAPI application initialization started")

try:
    logger.debug("Creating FastAPI application instance")

    app = FastAPI(title="Admin UI FastAPI")

    logger.info("FastAPI application instance created successfully")

    logger.debug("Initializing database metadata")

    Base.metadata.create_all(bind=engine)

    logger.info("Database metadata initialized successfully")

    logger.debug("Executing initial setup process")

    ensure_setup()

    logger.info("Initial setup process completed successfully")

    logger.debug("Registering auth router")

    app.include_router(auth.router, prefix="/auth", tags=["auth"])

    logger.info("Auth router registered successfully")

    logger.debug("Registering tenants router")

    app.include_router(tenants.router, tags=["tenants"])

    logger.info("Tenants router registered successfully")

    logger.info("Admin UI FastAPI application initialized successfully")

except Exception as e:
    logger.exception(f"Application initialization failed: {str(e)}")
    raise


@app.get("/")
@log_execution_time(logger)
def read_root():
    logger.debug("Root endpoint invoked")

    try:
        logger.info("Returning root endpoint response")

        return {
            "message": "Admin UI FastAPI is running",
            "config_path": str(settings.config_yaml_path)
        }

    except Exception as e:
        logger.exception(f"Root endpoint execution failed: {str(e)}")
        raise