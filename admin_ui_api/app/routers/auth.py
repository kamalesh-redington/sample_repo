from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Header, status

from app.config.logger import setup_logger, get_trace_id
from app.config.timer import log_execution_time
from app.schemas.schemas import (
    LoginRequest,
    MessageResponse,
    TokenResponse,
    UserSchema,
    ResponseWrapper,
)
from app.services.auth_service import authenticate_user, get_current_user, login_user
from app.utils.response import format_response

logger = setup_logger(__name__)

router = APIRouter()



@router.post("/login", response_model=ResponseWrapper)
@log_execution_time(logger)
def login(credentials: LoginRequest, trace_id: Optional[int] = Header(None, alias="X-Trace-Id")):

    logger.info(f"Login API invoked for username: {credentials.username}")
    if trace_id is not None:
        logger.debug(f"Login invoked with X-Trace-Id: {trace_id}")

    try:
        logger.debug(f"Authenticating user: {credentials.username}")

        user = authenticate_user(credentials.username, credentials.password)

        if not user:
            logger.warning(f"Login failed for username: {credentials.username}")

            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid username or password",
            )

        logger.debug(f"Generating access token for username: {credentials.username}")

        token = login_user(credentials.username, credentials.password)

        logger.info(f"Login successful for username: {credentials.username}")

        # prefer header-provided trace id (int), else use context trace id from middleware
        context_trace = get_trace_id()
        final_trace = None
        if trace_id is not None:
            final_trace = trace_id
        elif context_trace:
            try:
                final_trace = int(context_trace)
            except Exception:
                final_trace = None

        return format_response(
            status="success",
            statu_code="200",
            status_message="OK",
            response={
                "access_token": token,
                "token_type": "bearer",
                "user": {
                    "id": user.id,
                    "username": user.username,
                    "role": user.role.name,
                    "tenant_id": user.tenant_id,
                },
            },
            trace_id=final_trace,
        )

    except HTTPException:
        raise

    except Exception as e:
        logger.exception(
            f"Unexpected login error for username " f"{credentials.username}: {str(e)}"
        )
        raise


@router.post("/logout", response_model=ResponseWrapper)
@log_execution_time(logger)
def logout(authorization: str = Header(None)):

    logger.info("Logout API invoked")

    try:
        if not authorization or not authorization.startswith("Bearer "):

            logger.warning(
                "Logout failed due to missing or invalid authorization header"
            )

            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authorization header required",
            )

        token = authorization.split(" ", 1)[1]

        logger.debug("Invalidating authentication token")

        from app.core.security import logout_token

        logout_token(token)

        logger.info("Logout completed successfully")

        return format_response(
            status="success",
            statu_code="200",
            status_message="OK",
            response={"message": "Logout successful"},
        )

    except HTTPException:
        raise

    except Exception as e:
        logger.exception(f"Logout failed: {str(e)}")
        raise


@router.get("/me", response_model=ResponseWrapper)
@log_execution_time(logger)
def read_me(current_user=Depends(get_current_user)):

    logger.info(f"Current user endpoint invoked for user_id: {current_user.id}")

    try:
        logger.debug(
            f"Fetching profile details for username: " f"{current_user.username}"
        )

        logger.info(
            f"User profile returned successfully for username: "
            f"{current_user.username}"
        )

        return format_response(
            status="success",
            statu_code="200",
            status_message="OK",
            response={
                "id": current_user.id,
                "username": current_user.username,
                "role": current_user.role.name,
                "tenant_id": current_user.tenant_id,
            },
            trace_id=get_trace_id(),
        )

    except Exception as e:
        logger.exception(f"Failed to fetch current user details: {str(e)}")
        raise
