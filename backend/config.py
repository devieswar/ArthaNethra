"""
Configuration management for ArthaNethra backend
"""
from pydantic_settings import BaseSettings
from typing import Optional
import os


class Settings(BaseSettings):
    """Application settings"""
    
    # Application
    APP_NAME: str = "ArthaNethra"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True
    API_PREFIX: str = "/api/v1"
    
    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    
    # CORS
    CORS_ORIGINS: list[str] = ["http://localhost:4200", "http://localhost:3000"]
    
    # LandingAI ADE
    LANDINGAI_API_KEY: str
    # Default to US region per docs; override in .env for EU as needed
    # Docs: https://docs.landing.ai/api-reference/tools/
    LANDINGAI_API_URL: str = "https://api.va.landing.ai/v1"
    
    # AWS Bedrock
    AWS_ACCESS_KEY_ID: str
    AWS_SECRET_ACCESS_KEY: str
    AWS_REGION: str = "us-east-1"
    BEDROCK_MODEL_ID: str = "anthropic.claude-3-sonnet-20240229-v1:0"
    
    # Weaviate
    WEAVIATE_URL: str = "http://localhost:8080"
    ENABLE_WEAVIATE: bool = False
    WEAVIATE_API_KEY: Optional[str] = None
    
    # Neo4j
    NEO4J_URI: str = "bolt://localhost:7687"
    NEO4J_USER: str = "neo4j"
    NEO4J_PASSWORD: str
    ENABLE_NEO4J: bool = False
    
    # Storage
    UPLOAD_DIR: str = "./uploads"
    CACHE_DIR: str = "./cache"
    MAX_UPLOAD_SIZE: int = 104857600  # 100MB
    # ADE routing threshold: files larger than this use async jobs
    ADE_SYNC_MAX_BYTES: int = 15728640  # 15MB default
    
    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "logs/arthanethra.log"
    
    # JWT (for future auth)
    JWT_SECRET: str = "your-secret-key-change-this"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION: int = 3600  # 1 hour
    
    class Config:
        env_file = ".env"
        case_sensitive = True


# Global settings instance
settings = Settings()

# Create necessary directories
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
os.makedirs(settings.CACHE_DIR, exist_ok=True)
os.makedirs(os.path.dirname(settings.LOG_FILE), exist_ok=True)

