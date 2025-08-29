import os
from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    # database stuff
    mongodb_url: str = Field(default="mongodb://localhost:27017", env="MONGODB_URL")
    database_name: str = Field(default="contract_intelligence", env="DATABASE_NAME")
    
    # api keys - need these to work
    ocr_space_api_key: str = Field(env="OCR_SPACE_API_KEY")
    google_ai_api_key: str = Field(env="GOOGLE_AI_API_KEY")
    
    # app settings
    secret_key: str = Field(env="SECRET_KEY")
    debug: bool = Field(default=False, env="DEBUG")
    upload_dir: str = Field(default="./uploads", env="UPLOAD_DIR")
    max_file_size: int = Field(default=52428800, env="MAX_FILE_SIZE")  # 50mb should be enough
    
    # logging level
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    
    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"  # ignore extra fields from env file


# create settings instance
settings = Settings()
