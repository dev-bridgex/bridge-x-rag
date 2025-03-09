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
    
    MONGODB_URL: str
    MONGODB_DATABASE: str
    
    
def get_settings():
    return Settings()
    

def get_files_dir():
    base_dir = os.path.dirname( os.path.dirname(__file__) )
    files_dir = os.path.join(base_dir, "assets/files")
    if not os.path.exists(files_dir):
        os.mkdir(files_dir)    
    return files_dir