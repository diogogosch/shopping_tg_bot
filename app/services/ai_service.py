import openai
from typing import List, Dict, Optional
import logging
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from app.config.settings import settings
from app.core.cache import cache
from app.models.user import User
from app.models.product import Product, ShoppingListItem
from app.models.receipt import Receipt

logger = logging.getLogger(__name__)

class AIService:
    def __init__(self):
        self.provider = settings.get_active_ai_provider()
        self.model = settings.get_ai_model()
        self.ai_enabled = False
        self.client = None
        
        if self.provider == "openai" and settings.openai_api_key:
            try:
                self.client = openai.OpenAI(api_key=settings.openai_api_key)
                self.ai_enabled = True
                logger.info("OpenAI client initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize OpenAI client: {e}")
                
        elif self.provider == "gemini" and settings.gemini_api_key:
            try:
                self.client = openai.OpenAI(
                    api_key=settings.gemini_api_key,
                    base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
                )
                self.ai_enabled = True
                logger.info("Gemini client initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize Gemini client: {e}")
        
        if not self.ai_enabled:
            logger.warning(f"AI features disabled. Provider: {self.provider}, Available keys: OpenAI={bool(settings.openai_api_key)}, Gemini={bool(settings.gemini_api_key)}")
    
    def get_provider_info(self) -> Dict[str, str]:
        """Get information about the current AI provider"""
        return {
            "provider": self.provider,
            "model": self.model,
            "enabled": self.ai_enabled,
            "available_providers": self._get_available_providers()
        }
    
    def _get_available_providers(self) -> List[str]:
        """Get list of available AI providers based on configured keys"""
        providers = []
        if settings.openai_api_key:
            providers.append("openai")
        if settings.gemini_api_key:
            providers.append("gemini")
        return providers
    
    def switch_provider(self, new_provider: str) -> bool:
        """Switch to a different AI provider if available"""
        if new_provider == "openai" and settings.openai_api_key:
            try:
                self.client = openai.OpenAI(api_key=settings.openai_api_key)
                self.provider = "openai"
                self.model = settings.ai_model_openai
                self.ai_enabled = True
                logger.info("Switched to OpenAI provider")
                return True
            except Exception as e:
                logger.error(f"Failed to switch to OpenAI: {e}")
                
        elif new_provider == "gemini" and settings.gemini_api_key:
            try:
                self.client = openai.OpenAI(
                    api_key=settings.gemini_api_key,
                    base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
                )
                self.provider = "gemini"
                self.model = settings.ai_model_gemini
                self.ai_enabled = True
                logger.info("Switched to Gemini provider")
                return True
            except Exception as e:
                logger.error(f"Failed to switch to Gemini: {e}")
        
        return False
    
    def generate_smart_suggestions(self, user_id: int, db: Session) -> List[Dict]:
        """Generate AI-powered shopping suggestions"""
        if not self.ai_enabled:
            return self._get_fallback_suggestions(user_id, db)
        
        cached_suggestions = cache.get_user_suggestions(user_id)
        if cached_suggestions:
            return cached_suggestions
        
        try:
            user = db.query(User).filter(User.telegram_id == user_id).first()
            if not user:
                return []
            
            recent_receipts = db.query(Receipt).filter(
                Receipt.user_id == user.id,
                Receipt.purchase_date >= datetime.utcnow() - timedelta(days=30)
            ).limit(10).all()
            
            purchase_history = self._analyze_purchase_patterns(recent_receipts, db)
            suggestions = self._generate_ai_suggestions(user, purchase_history)
            
            cache.cache_user_suggestions(user_id, suggestions)
            return suggestions
            
        except Exception as e:
            logger.error(f"AI suggestion generation failed: {e}")
            return self._get_fallback_suggestions(user_id, db)
    
    def _analyze_purchase_patterns(self, receipts: List[Receipt], db: Session) -> Dict:
        """Analyze user's purchase patterns"""
        patterns = {
            "frequent_items": {},
            "categories": {},
            "spending_habits": {},
            "seasonal_patterns": {}
        }
        
        for receipt in receipts:
            for item in receipt.items:
                item_name = item.item_name.lower()
                patterns["frequent_items"][item_name] = patterns["frequent_items"].get(item_name, 0) + 1
                
                if item.product:
                    category = item.product.category
                    patterns["categories"][category] = patterns["categories"].get(category, 0) + 1
        
        return patterns
    
    def _generate_ai_suggestions(self, user: User, patterns: Dict) -> List[Dict]:
        """Generate suggestions using the configured AI provider"""
        try:
            context = f"""
            User Profile:
            - Dietary preferences: {user.dietary_preferences}
            - Recent purchase patterns: {patterns['frequent_items']}
            - Favorite categories: {patterns['categories']}
            
            Generate 5-10 smart shopping suggestions based on:
            1. Items they buy frequently but haven't purchased recently
            2. Complementary items to their usual purchases
            3. Seasonal recommendations
            4. Health-conscious alternatives if applicable
            
            Return as JSON array with format:
            [{{"item": "product_name", "reason": "why_suggested", "category": "category", "priority": 1-3}}]
            """
            
            # Use the configured client (works for both OpenAI and Gemini)
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": f"You are a smart shopping assistant powered by {self.provider.upper()} that provides personalized recommendations."},
                    {"role": "user", "content": context}
                ],
                max_tokens=500,
                temperature=0.7
            )
            
            import json
            suggestions_text = response.choices[0].message.content
            suggestions = json.loads(suggestions_text)
            
            # Add provider info to suggestions
            for suggestion in suggestions:
                suggestion['ai_provider'] = self.provider
            
            return suggestions
            
        except Exception as e:
            logger.error(f"{self.provider.upper()} API error: {e}")
            return self._get_fallback_suggestions_from_patterns(patterns)
    
    def _get_fallback_suggestions(self, user_id: int, db: Session) -> List[Dict]:
        """Fallback suggestions when AI is not available"""
        user = db.query(User).filter(User.telegram_id == user_id).first()
        if not user:
            return []
        
        suggestions = [
            {"item": "Milk", "reason": "Essential dairy product", "category": "dairy", "priority": 2, "ai_provider": "fallback"},
            {"item": "Bread", "reason": "Staple food item", "category": "bakery", "priority": 2, "ai_provider": "fallback"},
            {"item": "Eggs", "reason": "Protein source", "category": "dairy", "priority": 2, "ai_provider": "fallback"},
            {"item": "Bananas", "reason": "Healthy fruit option", "category": "fruits", "priority": 1, "ai_provider": "fallback"},
            {"item": "Chicken breast", "reason": "Lean protein", "category": "meat", "priority": 2, "ai_provider": "fallback"}
        ]
        
        if "vegetarian" in user.dietary_preferences:
            suggestions = [s for s in suggestions if s["category"] != "meat"]
        
        return suggestions
    
    def _get_fallback_suggestions_from_patterns(self, patterns: Dict) -> List[Dict]:
        """Generate suggestions based on patterns without AI"""
        suggestions = []
        
        for item, frequency in sorted(patterns["frequent_items"].items(), key=lambda x: x[1], reverse=True)[:5]:
            suggestions.append({
                "item": item.title(),
                "reason": f"You buy this frequently ({frequency} times recently)",
                "category": "frequent",
                "priority": 2,
                "ai_provider": "pattern_based"
            })
        
        return suggestions
    
    def test_connection(self) -> Dict[str, any]:
        """Test the AI connection and return status"""
        if not self.ai_enabled:
            return {
                "success": False,
                "provider": self.provider,
                "error": "AI not enabled or no valid API key"
            }
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "user", "content": "Hello, this is a test message. Please respond with 'Test successful'."}
                ],
                max_tokens=10
            )
            
            return {
                "success": True,
                "provider": self.provider,
                "model": self.model,
                "response": response.choices[0].message.content
            }
            
        except Exception as e:
            return {
                "success": False,
                "provider": self.provider,
                "error": str(e)
            }

# Global AI service instance
ai_service = AIService()
