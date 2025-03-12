from fastapi import APIRouter, Depends, HTTPException, status, Body
from fastapi.security import OAuth2PasswordRequestForm
from datetime import timedelta
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.dependencies.database import get_database
from app.models.db_schemes.user import Token, UserCreate, User
from app.auth.utils import (
    authenticate_user, create_access_token, create_refresh_token,
    get_password_hash, get_current_active_user, refresh_access_token,
    revoke_token
)
from app.helpers.config import get_settings
from app.models.UserModel import UserModel

auth_router = APIRouter(
    prefix="/api/v1/auth",
    tags=["auth"],
)

@auth_router.post("/token", response_model=Token)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncIOMotorDatabase = Depends(get_database),
    settings = Depends(get_settings)
):
    user = await authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Create access token
    access_token = create_access_token(user.username)
    
    # Create refresh token
    refresh_token = create_refresh_token(user.username)
    
    return {
        "access_token": access_token, 
        "token_type": "bearer",
        "refresh_token": refresh_token,
        "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60  # in seconds
    }

@auth_router.post("/refresh", response_model=Token)
async def refresh_token(
    refresh_token: str = Body(..., embed=True),
    db: AsyncIOMotorDatabase = Depends(get_database),
    settings = Depends(get_settings)
):
    """Refresh an access token using a refresh token"""
    token_data = await refresh_access_token(refresh_token, db)
    return {
        **token_data,
        "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60  # in seconds
    }

@auth_router.post("/revoke")
async def revoke_token_endpoint(
    token: str = Body(..., embed=True),
    current_user: User = Depends(get_current_active_user)
):
    """Revoke a token"""
    revoke_token(token)
    return {"message": "Token revoked successfully"}

@auth_router.post("/register", response_model=User)
async def register_user(
    user_create: UserCreate,
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    # Check if user already exists
    user_model = UserModel(db_client=db)
    existing_user = await user_model.get_user_by_username(user_create.username)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username already registered"
        )
    
    # Check if email already exists
    existing_email = await user_model.get_user_by_email(user_create.email)
    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered"
        )
    
    # Create new user
    hashed_password = get_password_hash(user_create.password)
    user = await user_model.create_user(
        username=user_create.username,
        email=user_create.email,
        hashed_password=hashed_password
    )
    
    return user

@auth_router.get("/me", response_model=User)
async def read_users_me(current_user: User = Depends(get_current_active_user)):
    return current_user 