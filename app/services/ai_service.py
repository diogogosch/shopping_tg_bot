import logging
from typing import List
from openai import OpenAI
from google.cloud import vision
from app import settings
from ratelimit import limits, sleep_and_retry
import aiohttp

logger = logging.getLogger(__name__)

class AIService:
    def __init__(self):
        self.ai_provider = settings.get_active_ai_provider()
        self.ai_model = settings.get_ai_model()
        self.client = None
        self.session = None
        
        if self.ai_provider == "openai" and settings.openai_api_key:
            self.client = OpenAI(api_key=settings.openai_api_key)
        elif self.ai_provider == "gemini" and settings.gemini_api_key:
            self.session = aiohttp.ClientSession()
        elif self.ai_provider == "none":
            logger.warning("No AI provider configured")
        
        self.vision_client = None
        if settings.google_vision_api_key:
            self.vision_client = vision.ImageAnnotatorClient.from_service_account_json(
                settings.google_vision_api_key
            )

    @sleep_and_retry
    @limits(calls=10, period=60)
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
            elif self.ai_provider == "gemini":
                # Hypothetical Gemini API endpoint and structure
                async with self.session.post(
                    "https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent",  # Example endpoint
                    headers={"x-goog-api-key": settings.gemini_api_key},
                    json={
                        "contents": [{"parts": [{"text": f"Based on these items: {', '.join(items)}, suggest additional shopping items."}]}],
                        "generationConfig": {"maxOutputTokens": 100}
                    }
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        suggestions = data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "").split(", ")
                        logger.info(f"Generated suggestions: {suggestions}")
                        return suggestions
                    else:
                        logger.error(f"Gemini API error: {response.status} - {await response.text()}")
                        return []
        except Exception as e:
            logger.error(f"Failed to generate suggestions: {e}")
            return []

    def extract_text_from_receipt(self, image_data: bytes) -> dict:
        if not self.vision_client:
            logger.warning("Google Vision client not configured")
            return {"items": [], "confidence": 0.0, "raw_text": "", "store_name": "", "total": 0.0, "date": None}
        
        try:
            image = vision.Image(content=image_data)
            response = self.vision_client.text_detection(image=image)
            text = response.text_annotations[0].description if response.text_annotations else ""
            
            items = []
            total = 0.0
            store_name = ""
            date = None
            confidence = response.text_annotations[0].confidence if response.text_annotations else 0.0
            
            lines = text.split("\n")
            for line in lines:
                line = line.strip()
                if "$" in line or "€" in line or "£" in line:
                    parts = line.split()
                    for i, part in enumerate(parts):
                        if part.startswith(("$", "€", "£")):
                            try:
                                price = float(part[1:])
                                item_name = " ".join(parts[:i]) if i > 0 else "Unknown Item"
                                items.append({
                                    "name": item_name,
                                    "quantity": 1.0,
                                    "unit_price": price,
                                    "total_price": price,
                                    "confidence": confidence
                                })
                                total += price
                            except ValueError:
                                continue
                
                if "store" in line.lower() or "mart" in line.lower():
                    store_name = line
                if "/" in line or "-" in line:
                    try:
                        from dateutil.parser import parse
                        date = parse(line, fuzzy=True)
                    except:
                        continue
            
            return {
                "items": items,
                "confidence": confidence,
                "raw_text": text,
                "store_name": store_name,
                "total": total,
                "date": date
            }
        except Exception as e:
            logger.error(f"Error processing receipt image: {e}")
            return {"items": [], "confidence": 0.0, "raw_text": "", "store_name": "", "total": 0.0, "date": None}

    async def close(self):
        if self.session:
            await self.session.close()

    def test_connection(self):
        if self.ai_provider == "openai" and self.client:
            self.client.models.list()
        elif self.ai_provider == "gemini" and self.session:
            async def test_gemini():
                async with self.session.get(
                    "https://generativelanguage.googleapis.com/v1beta/models",  # Example endpoint
                    headers={"x-goog-api-key": settings.gemini_api_key}
                ) as response:
                    if response.status != 200:
                        raise Exception("Gemini connection failed")
            import asyncio
            asyncio.run(test_gemini())
        elif self.vision_client:
            self.vision_client.text_detection(image=vision.Image(content=b""))