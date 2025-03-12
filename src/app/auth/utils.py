from passlib.context import CryptContext
import jwt
from jwt.exceptions import PyJWTError
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from app.models.db_schemes.user import TokenData, User, UserInDB, TokenPayload
from app.helpers.config import get_settings
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.dependencies.database import get_database
import uuid
import json
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
import base64
import os

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 scheme for access and refresh tokens
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/v1/auth/token")

# Settings
settings = get_settings()

# Token blacklist (in-memory for demo, use Redis or DB in production)
token_blacklist = set()

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_token_payload(subject: str, token_type: str = "access") -> Dict[str, Any]:
    """Create a standardized token payload with security best practices"""
    now = datetime.now(timezone.utc)
    
    # Standard JWT claims
    payload = {
        "sub": subject,  # Subject (typically user ID or username)
        "iat": int(now.timestamp()),  # Issued at
        "jti": str(uuid.uuid4()),  # JWT ID (unique identifier for this token)
        "type": token_type,  # Token type (access or refresh)
    }
    
    # Add expiration based on token type
    if token_type == "access":
        payload["exp"] = int((now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)).timestamp())
    else:  # refresh token
        payload["exp"] = int((now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)).timestamp())
    
    return payload

def create_access_token(subject: str) -> str:
    """Create a new access token"""
    payload = create_token_payload(subject, "access")
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

def create_refresh_token(subject: str) -> str:
    """Create a new refresh token"""
    payload = create_token_payload(subject, "refresh")
    return jwt.encode(payload, settings.REFRESH_SECRET_KEY, algorithm=settings.ALGORITHM)

def encrypt_data(data: Dict[str, Any]) -> str:
    """Encrypt data using AES-GCM"""
    # Convert encryption key from string to bytes
    key = base64.urlsafe_b64decode(settings.ENCRYPTION_KEY + "=" * (4 - len(settings.ENCRYPTION_KEY) % 4))
    
    # Generate a random 96-bit nonce (12 bytes)
    nonce = os.urandom(12)
    
    # Convert data to JSON string and then to bytes
    data_bytes = json.dumps(data).encode('utf-8')
    
    # Create AESGCM cipher with the key
    aesgcm = AESGCM(key)
    
    # Encrypt the data
    ciphertext = aesgcm.encrypt(nonce, data_bytes, None)
    
    # Combine nonce and ciphertext and encode as base64
    encrypted = base64.urlsafe_b64encode(nonce + ciphertext).decode('utf-8')
    
    return encrypted

def decrypt_data(encrypted: str) -> Dict[str, Any]:
    """Decrypt data using AES-GCM"""
    # Convert encryption key from string to bytes
    key = base64.urlsafe_b64decode(settings.ENCRYPTION_KEY + "=" * (4 - len(settings.ENCRYPTION_KEY) % 4))
    
    # Decode the base64 encrypted data
    encrypted_bytes = base64.urlsafe_b64decode(encrypted + "=" * (4 - len(encrypted) % 4))
    
    # Extract nonce (first 12 bytes) and ciphertext
    nonce = encrypted_bytes[:12]
    ciphertext = encrypted_bytes[12:]
    
    # Create AESGCM cipher with the key
    aesgcm = AESGCM(key)
    
    # Decrypt the data
    plaintext = aesgcm.decrypt(nonce, ciphertext, None)
    
    # Convert bytes to JSON object
    data = json.loads(plaintext.decode('utf-8'))
    
    return data

def create_encrypted_token(data: Dict[str, Any]) -> str:
    """Create an encrypted token for sensitive data"""
    # First create a regular JWT
    token = jwt.encode(data, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    
    # Then encrypt the token
    return encrypt_data({"token": token})

def decrypt_token(encrypted_token: str) -> Dict[str, Any]:
    """Decrypt a token and verify it"""
    # Decrypt the token
    decrypted_data = decrypt_data(encrypted_token)
    token = decrypted_data["token"]
    
    # Verify and decode the JWT
    return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])

def revoke_token(token: str) -> None:
    """Add a token to the blacklist"""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        token_id = payload.get("jti")
        if token_id:
            token_blacklist.add(token_id)
    except PyJWTError:
        pass

def is_token_revoked(payload: Dict[str, Any]) -> bool:
    """Check if a token has been revoked"""
    token_id = payload.get("jti")
    return token_id in token_blacklist

async def get_user(db: AsyncIOMotorDatabase, username: str):
    user_doc = await db.users.find_one({"username": username})
    if user_doc:
        return UserInDB(**user_doc)
    return None

async def authenticate_user(db: AsyncIOMotorDatabase, username: str, password: str):
    user = await get_user(db, username)
    if not user:
        return False
    if not verify_password(password, user.hashed_password):
        return False
    return user

async def get_current_user(token: str = Depends(oauth2_scheme), db: AsyncIOMotorDatabase = Depends(get_database)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(
            token, 
            settings.SECRET_KEY, 
            algorithms=[settings.ALGORITHM]
        )
        
        # Check if token is of correct type
        if payload.get("type") != "access":
            raise credentials_exception
        
        # Check if token has been revoked
        if is_token_revoked(payload):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has been revoked",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
            
        token_data = TokenData(username=username)
    except PyJWTError:
        raise credentials_exception
        
    user = await get_user(db, username=token_data.username)
    if user is None:
        raise credentials_exception
        
    return user

async def get_current_active_user(current_user: User = Depends(get_current_user)):
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user

async def refresh_access_token(refresh_token: str, db: AsyncIOMotorDatabase = Depends(get_database)):
    """Create a new access token using a refresh token"""
    try:
        payload = jwt.decode(
            refresh_token, 
            settings.REFRESH_SECRET_KEY, 
            algorithms=[settings.ALGORITHM]
        )
        
        # Check if token is of correct type
        if payload.get("type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Check if token has been revoked
        if is_token_revoked(payload):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has been revoked",
                headers={"WWW-Authenticate": "Bearer"},
            )
            
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token",
                headers={"WWW-Authenticate": "Bearer"},
            )
            
        # Verify user still exists
        user = await get_user(db, username=username)
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
                headers={"WWW-Authenticate": "Bearer"},
            )
            
        # Create new access token
        access_token = create_access_token(username)
        return {"access_token": access_token, "token_type": "bearer"}
        
    except PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        ) 