import os
from typing import Optional, Literal
from pydantic import BaseSettings, validator

class Settings(BaseSettings):
    # Bot Configuration
    telegram_token: str
    bot_username: str = "SmartShopBot"
    
    # Database Configuration
    database_url: str
    database_pool_size: int = 10
    database_max_overflow: int = 20
    
    # Redis Configuration
    redis_url: str = "redis://localhost:6379"
    redis_ttl: int = 3600
    
    # OCR Configuration
    tesseract_path: Optional[str] = None
    google_vision_api_key: Optional[str] = None
    
    # AI Configuration
    ai_provider: Literal["openai", "gemini", "auto"] = "auto"
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
    
    @validator('ai_provider')
    def validate_ai_provider(cls, v, values):
        if v == "auto":
            if values.get('openai_api_key'):
                return "openai"
            elif values.get('gemini_api_key'):
                return "gemini"
            else:
                return "none"
        return v
    
    def get_active_ai_provider(self) -> str:
        if self.ai_provider == "auto":
            if self.openai_api_key:
                return "openai"
            elif self.gemini_api_key:
                return "gemini"
            else:
                return "none"
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
