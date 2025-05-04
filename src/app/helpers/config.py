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
    COHERE_API_VERSION: int = 1

    OPENAI_API_KEY: Optional[str] = None
    OPENAI_API_URL: Optional[str] = None
    COHERE_API_KEY: Optional[str] = None
    GOOGLE_API_KEY: Optional[str] = None


    GENERATION_MODEL_ID: str
    EMBEDDING_MODEL_ID: str
    EMBEDDING_MODEL_SIZE: int


    INPUT_DAFAULT_MAX_CHARACTERS: int = 1024
    GENERATION_DAFAULT_MAX_TOKENS: int = 512
    GENERATION_DAFAULT_TEMPERATURE: float = 0.1

    # Image description settings
    IMAGE_DESCRIPTION_MAX_TOKENS: Optional[int] = 150
    IMAGE_DESCRIPTION_TEMPERATURE: Optional[float] = 0.5

    # Processing settings
    PDF_IMAGE_PROCESSING_MAX_WORKERS: int = 1  # Reduced to 1 to avoid rate limits
    API_RATE_LIMIT_DELAY: float = 3.0  # Increased to 3 seconds between API calls to avoid rate limits


    # Vector DB Provider Config

    VECTOR_DB_BACKEND: str
    VECTOR_DB_DISTANCE_METHOD: str
    VECTOR_DB_PATH: Optional[str] = ""

    QDRANT_URL: Optional[str] = None
    QDRANT_API_KEY: Optional[str] = None
    QDRANT_PREFER_GRPC: bool = False

    PRIMARY_LANG: str = "en"
    DEFAULT_LANG: str = "en"

    # NLP settings
    NLP_ENABLED: bool = True

# Global app settings instance
_app_settings = None

def get_settings():
    global _app_settings
    if _app_settings is None:
        _app_settings = Settings()
    return _app_settings


def init_files_dir():
    base_dir = os.path.dirname( os.path.dirname(__file__) )
    files_dir = os.path.join(base_dir, "assets/files")
    if not os.path.exists(files_dir):
        os.mkdir(files_dir)
    return files_dir

def init_vector_db_data_dir():
    base_dir = os.path.dirname( os.path.dirname(__file__) )
    database_dir = os.path.join(base_dir, "assets/vector_db_data/")
    if not os.path.exists(database_dir):
        os.mkdir(database_dir)
    return database_dir