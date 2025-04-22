from pydantic_settings import BaseSettings, SettingsConfigDict
import os
from typing import Optional

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
    
    
    # LLM Providers Config
    
    GENERATION_BACKEND: str
    EMBEDDING_BACKEND: str
    COHERE_API_VESION: int = 1
    
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_API_URL: Optional[str] = None
    COHERE_API_KEY: Optional[str] = None


    GENERATION_MODEL_ID: str
    EMBEDDING_MODEL_ID: str
    EMBEDDING_MODEL_SIZE: int


    INPUT_DAFAULT_MAX_CHARACTERS: int = 1024
    GENERATION_DAFAULT_MAX_TOKENS: int = 512
    GENERATION_DAFAULT_TEMPERATURE: float = 0.1

    # Vector DB Provider Config
    
    VECTOR_DB_BACKEND: str
    VECTOR_DB_DISTANCE_METHOD: str
    VECTOR_DB_PATH: Optional[str] = ""
    
    QDRANT_URL: Optional[str] = None
    QDRANT_API_KEY: Optional[str] = None
    QDRANT_PREFER_GRPC: bool = False
    
    
    
def get_settings():
    return Settings()
    

def init_files_dir():
    base_dir = os.path.dirname( os.path.dirname(__file__) )
    files_dir = os.path.join(base_dir, "assets/files")
    if not os.path.exists(files_dir):
        os.mkdir(files_dir)    
    return files_dir

def init_database_dir():
    base_dir = os.path.dirname( os.path.dirname(__file__) )
    database_dir = os.path.join(base_dir, "assets/database")
    if not os.path.exists(database_dir):
        os.mkdir(database_dir)    
    return database_dir