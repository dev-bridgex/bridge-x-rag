from pydantic_settings import BaseSettings, SettingsConfigDict
import os

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        # Use top level .env file (one level above ./app/)
        env_file='.env',
        env_file_encoding='utf-8',
        env_ignore_empty=True,
        extra='ignore'
        )
    
    APP_NAME: str
    APP_VERSION: str
    OPENAI_API_KEY: str
    
    FILE_ALLOWED_TYPES: list[str]
    FILE_MAX_SIZE: int
    FILE_DEFAULT_CHUNK_SIZE: int
    
    # MongoDB Config
    MONGODB_HOST: str
    MONGODB_PORT: str
    MONGODB_USERNAME: str
    MONGODB_PASSWORD: str
    MONGODB_DATABASE: str
    MAX_DB_CONN_COUNT: int
    MIN_DB_CONN_COUNT: int
    
    # JWT Settings
    SECRET_KEY: str = "your-secret-key-here"  # In production, use a secure random key
    REFRESH_SECRET_KEY: str = "your-refresh-secret-key-here"  # Different key for refresh tokens
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # JWE Encryption Settings
    ENCRYPTION_KEY: str = "32-byte-key-for-encryption-----"  # Base64 encoded key
    ENCRYPTION_ALGORITHM: str = "A256KW"  # Key wrapping algorithm
    ENCRYPTION_METHOD: str = "A256CBC-HS512"  # Content encryption algorithm

    
    
def get_settings():
    return Settings()
    

def get_files_dir():
    base_dir = os.path.dirname( os.path.dirname(__file__) )
    files_dir = os.path.join(base_dir, "assets/files")
    if not os.path.exists(files_dir):
        os.mkdir(files_dir)    
    return files_dir