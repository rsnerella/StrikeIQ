import os
from typing import List
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

import socket


# Static localhost defaults instead of dynamic detection
LOCAL_IP = 'localhost'

class Settings:
    LOG_LEVEL: str = "INFO"
    
    # Environment setting
    ENVIRONMENT: str = os.getenv('ENVIRONMENT', 'development')
    
    # Load with fallback to empty string - SECURITY: No hardcoded credentials
    UPSTOX_API_KEY: str = os.getenv('UPSTOX_API_KEY', "")
    UPSTOX_API_SECRET: str = os.getenv('UPSTOX_API_SECRET', "")
    
    # Frontend/Backend URLs - Removed dynamic host detection 
    FRONTEND_URL: str = os.getenv('FRONTEND_URL', "http://localhost:3000")
    BACKEND_URL: str = os.getenv('BACKEND_URL', "http://localhost:8000")
    
    REDIRECT_URI: str = os.getenv('UPSTOX_REDIRECT_URI', "http://localhost:8000/api/v1/auth/upstox/callback")
    
    ALLOWED_HOSTS: List[str] = [
        "http://localhost:3000", 
        "http://127.0.0.1:3000", 
        FRONTEND_URL,
        BACKEND_URL,
        "*" # Safety for dev, CORS handles it properly in main.py
    ]
    
    # Security settings
    SECRET_KEY: str = os.getenv('SECRET_KEY', "your-secret-key-change-in-production")
    
    # Database Settings
    DATABASE_URL: str = os.getenv('DATABASE_URL', "postgresql://strikeiq:strikeiq123@localhost:5432/strikeiq")
    REDIS_URL: str = os.getenv('REDIS_URL', "redis://localhost:6379")
    
    # Redis Settings
    REDIS_HOST: str = os.getenv('REDIS_HOST', LOCAL_IP if ENVIRONMENT == 'production' else 'localhost')
    REDIS_PORT: int = int(os.getenv('REDIS_PORT', '6379'))
    REDIS_DB: int = int(os.getenv('REDIS_DB', '0'))
    
    # Upstash Redis Settings
    UPSTASH_REDIS_URL: str = os.getenv('UPSTASH_REDIS_URL', '')
    UPSTASH_REDIS_TOKEN: str = os.getenv('UPSTASH_REDIS_TOKEN', '')
    UPSTASH_REDIS_REST_URL: str = os.getenv('UPSTASH_REDIS_REST_URL', '')
    
    # Redis Provider Selection
    REDIS_PROVIDER: str = os.getenv('REDIS_PROVIDER', 'local')  # 'local', 'upstash', 'auto'
    
    @property
    def is_upstash_enabled(self) -> bool:
        """Check if Upstash Redis is configured and enabled"""
        if self.REDIS_PROVIDER == 'local':
            return False
        if self.REDIS_PROVIDER == 'upstash':
            return bool(self.UPSTASH_REDIS_URL and self.UPSTASH_REDIS_TOKEN)
        # Auto mode: prefer Upstash if configured, otherwise use local
        return bool(self.UPSTASH_REDIS_URL and self.UPSTASH_REDIS_TOKEN)
    
    @property
    def effective_redis_url(self) -> str:
        """Get the effective Redis URL based on configuration"""
        if self.is_upstash_enabled:
            return self.UPSTASH_REDIS_URL
        return self.REDIS_URL
    
    def __init__(self):
        # Additional initialization if needed, but class attributes cover defaults
        pass

settings = Settings()
