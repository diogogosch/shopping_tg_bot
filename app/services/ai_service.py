import logging
from typing import Optional
from openai import OpenAI
from google.cloud import vision
from ratelimit import limits, sleep_and_retry
from app.config.settings import settings

logger = logging.getLogger(__name__)

class AIService:
    def __init__(self):
        self.ai_provider = settings.get_active_ai_provider()
        self.ai_model = settings.get_ai_model()
        self.client = None
        
        if self.ai_provider == "openai" and settings.openai_api_key:
            self.client = OpenAI(api_key=settings.openai_api_key)
        elif self.ai_provider == "gemini" and settings.gemini_api_key:
            # Placeholder for Gemini API client initialization
            pass
        elif self.ai_provider == "none":
            logger.warning("No AI provider configured")
        
        self.vision_client = None
        if settings.google_vision_api_key:
            self.vision_client = vision.ImageAnnotatorClient.from_service_account_json(
                settings.google_vision_api_key
            )

    @sleep_and_retry
    @limits(calls=10, period=60)  # 10 calls per minute
    async def generate_suggestions(self, items: list[str]) -> list[str]:
        if self.ai_provider == "none":
            logger.warning("AI suggestions disabled")
            return []
        
        try:
            if self.ai_provider == "openai":
                prompt = f"Based on these items: {', '.join(items)}, suggest additional shopping items."
                response = self.client.chat.completions.create(
                    model=self.ai_model,
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=100
                )
                suggestions = response.choices[0].message.content.split(", ")
                logger.info(f"Generated suggestions: {suggestions}")
                return suggestions
            # Add Gemini implementation here
            return []
        except Exception as e:
            logger.error(f"Failed to generate suggestions: {e}")
            return []

    @sleep_and_retry
    @limits(calls=5, period=60)  # 5 calls per minute
    async def process_image(self, image_path: str) -> list[dict]:
        if not self.vision_client:
            logger.warning("Google Vision API not configured")
            return []
        
        try:
            with open(image_path, "rb") as image_file:
                content = image_file.read()
            image = vision.Image(content=content)
            response = self.vision_client.text_detection(image=image)
            texts = response.text_annotations
            items = [{"text": text.description, "confidence": text.score} for text in texts]
            logger.info(f"Extracted {len(items)} items from image")
            return items
        except Exception as e:
            logger.error(f"Failed to process image: {e}")
            return []

    def test_connection(self):
        if self.ai_provider == "openai" and self.client:
            self.client.models.list()
        elif self.ai_provider == "gemini":
            # Add Gemini test connection
            pass
        elif self.vision_client:
            self.vision_client.text_detection(image=vision.Image(content=b""))