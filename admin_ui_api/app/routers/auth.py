from fastapi import APIRouter, Depends, HTTPException, Header, status

from app.config.logger import setup_logger
from app.schemas.schemas import LoginRequest, MessageResponse, TokenResponse, UserSchema
from app.services.auth_service import authenticate_user, get_current_user, login_user

logger = setup_logger(__name__)

router = APIRouter()


@router.post("/login", response_model=TokenResponse)
def login(credentials: LoginRequest):

    logger.info(f"Login API invoked for username: {credentials.username}")

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

        return TokenResponse(
            access_token=token,
            user=UserSchema(
                id=user.id,
                username=user.username,
                role=user.role.name,
                tenant_id=user.tenant_id,
            ),
        )

    except HTTPException:
        raise

    except Exception as e:
        logger.exception(
            f"Unexpected login error for username " f"{credentials.username}: {str(e)}"
        )
        raise


@router.post("/logout", response_model=MessageResponse)
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

        return MessageResponse(message="Logout successful")

    except HTTPException:
        raise

    except Exception as e:
        logger.exception(f"Logout failed: {str(e)}")
        raise


@router.get("/me", response_model=UserSchema)
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

        return UserSchema(
            id=current_user.id,
            username=current_user.username,
            role=current_user.role.name,
            tenant_id=current_user.tenant_id,
        )

    except Exception as e:
        logger.exception(f"Failed to fetch current user details: {str(e)}")
        raise
