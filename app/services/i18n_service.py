import json
import os
from typing import Dict, Optional
from app.config.settings import settings

class I18nService:
    def __init__(self):
        self.translations = {}
        self.load_translations()
    
    def load_translations(self):
        """Load translation files"""
        translations_dir = os.path.join(os.path.dirname(__file__), '..', 'translations')
        
        for lang in settings.supported_languages:
            translation_file = os.path.join(translations_dir, f'{lang}.json')
            if os.path.exists(translation_file):
                with open(translation_file, 'r', encoding='utf-8') as f:
                    self.translations[lang] = json.load(f)
            else:
                self.translations[lang] = {}
    
    def get_text(self, key: str, language: str = "en", **kwargs) -> str:
        """Get translated text"""
        if language not in self.translations:
            language = "en"
        
        text = self.translations[language].get(key, key)
        
        # Format with provided arguments
        if kwargs:
            try:
                text = text.format(**kwargs)
            except (KeyError, ValueError):
                pass
        
        return text
    
    def get_user_language(self, user_language: Optional[str]) -> str:
        """Get user's preferred language or default"""
        if user_language and user_language in settings.supported_languages:
            return user_language
        return settings.default_language

# Global instance
i18n = I18nService()
