from fastapi import APIRouter, Depends, HTTPException, Header, status

from app.schemas.schemas import LoginRequest, MessageResponse, TokenResponse, UserSchema
from app.services.auth_service import authenticate_user, get_current_user, login_user

router = APIRouter()


@router.post("/login", response_model=TokenResponse)
def login(credentials: LoginRequest):
    user = authenticate_user(credentials.username, credentials.password)
    if not user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid username or password")

    token = login_user(credentials.username, credentials.password)
    return TokenResponse(
        access_token=token,
        user=UserSchema(
            id=user.id,
            username=user.username,
            role=user.role.name,
            tenant_id=user.tenant_id,
        ),
    )


@router.post("/logout", response_model=MessageResponse)
def logout(authorization: str = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authorization header required")
    token = authorization.split(" ", 1)[1]
    from app.core.security import logout_token

    logout_token(token)
    return MessageResponse(message="Logout successful")


@router.get("/me", response_model=UserSchema)
def read_me(current_user=Depends(get_current_user)):
    return UserSchema(
        id=current_user.id,
        username=current_user.username,
        role=current_user.role.name,
        tenant_id=current_user.tenant_id,
    )
