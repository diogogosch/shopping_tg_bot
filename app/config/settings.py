import os
from typing import Optional, Literal
from pydantic import BaseSettings, validator
from urllib.parse import urlparse

class Settings(BaseSettings):
    # Bot Configuration
    telegram_token: str
    bot_username: str = "SmartShopBot"
    
    # Database Configuration
    database_url: str
    database_pool_size: int = 10
    database_max_overflow: int = 20
    
    # Redis Configuration
    redis_url: str = "redis://redis:6379"
    redis_ttl: int = 3600
    
    # OCR Configuration
    tesseract_path: Optional[str] = "/usr/bin/tesseract"
    google_vision_api_key: Optional[str] = None
    
    # AI Configuration
    ai_provider: Literal["openai", "gemini", "none"] = "none"
    openai_api_key: Optional[str] = None
    gemini_api_key: Optional[str] = None
    ai_model_openai: str = "gpt-3.5-turbo"
    ai_model_gemini: str = "gemini-2.0-flash"
    
    # Internationalization
    default_language: str = "en"
    supported_languages: list = ["en", "pt_BR"]
    
    # Feature Flags
    enable_ai_suggestions: bool = True
    enable_price_tracking: bool = True
    enable_notifications: bool = True
    
    # Logging
    log_level: str = "INFO"
    
    @validator('telegram_token')
    def validate_telegram_token(cls, v):
        if not v or len(v) < 10:
            raise ValueError('Invalid Telegram token')
        return v
    
    @validator('database_url')
    def validate_database_url(cls, v):
        parsed = urlparse(v)
        if parsed.scheme != 'postgresql':
            raise ValueError('Database URL must use postgresql scheme')
        if not parsed.hostname or not parsed.username:
            raise ValueError('Database URL must include hostname and username')
        return v
    
    @validator('redis_url')
    def validate_redis_url(cls, v):
        parsed = urlparse(v)
        if parsed.scheme != 'redis':
            raise ValueError('Redis URL must use redis scheme')
        return v
    
    @validator('ai_provider')
    def validate_ai_provider(cls, v, values):
        if v == "none" and (values.get('openai_api_key') or values.get('gemini_api_key')):
            if values.get('openai_api_key'):
                return "openai"
            elif values.get('gemini_api_key'):
                return "gemini"
        if v == "openai" and not values.get('openai_api_key'):
            raise ValueError('OpenAI API key required for openai provider')
        if v == "gemini" and not values.get('gemini_api_key'):
            raise ValueError('Gemini API key required for gemini provider')
        return v
    
    def get_active_ai_provider(self) -> str:
        return self.ai_provider
    
    def get_ai_model(self) -> str:
        provider = self.get_active_ai_provider()
        if provider == "openai":
            return self.ai_model_openai
        elif provider == "gemini":
            return self.ai_model_gemini
        return ""

    class Config:
        env_file = ".env"
        case_sensitive = False

settings = Settings()