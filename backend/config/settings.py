from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    ENVIRONMENT: str = Field(pattern=r"^(dev|ppr|prod)$")
    
    BACK_NAME: str = Field(min_length=3, max_length=20)
    BACK_VERSION: str = Field(pattern=r"^\d+\.\d+\.\d+$")
    BACK_DESCRIPTION: str = Field(min_length=3, max_length=200)
    
    BACK_CACHE_DURATION: int
    
    BACK_LOGGING_LEVEL: str = Field(pattern=r"^(DEBUG|INFO|WARNING|ERROR|CRITICAL)$")
    
    BACK_LOG_MAX_BYTES: int
    BACK_LOG_BACKUP_COUNT: int
    
    BACK_PANDA_BASE_URL: str
    BACK_PANDA_API_KEY: str
    BACK_PANDA_REFRESH_INTERVAL: int
    
    model_config = SettingsConfigDict(env_file=".env")
    
    
@lru_cache
def get_settings() -> Settings:
    return Settings()

