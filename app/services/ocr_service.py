import pytesseract
from PIL import Image, ImageEnhance, ImageFilter
import cv2
import numpy as np
from typing import Dict, List, Optional, Tuple
import re
import logging
from io import BytesIO

from app.config.settings import settings

logger = logging.getLogger(__name__)

class OCRService:
    def __init__(self):
        if settings.tesseract_path:
            pytesseract.pytesseract.tesseract_cmd = settings.tesseract_path
        
        self.price_pattern = re.compile(r'\$?(\d+[.,]\d{2})')
        self.item_patterns = [
            re.compile(r'^([A-Za-z\s]+)\s+(\d+[.,]\d{2})$'),
            re.compile(r'^([A-Za-z\s]+)\s+(\d+)\s*x\s*(\d+[.,]\d{2})\s*=?\s*(\d+[.,]\d{2})$'),
        ]
    
    def preprocess_image(self, image_data: bytes) -> Image.Image:
        """Enhanced image preprocessing for better OCR accuracy"""
        try:
            image = Image.open(BytesIO(image_data))
            
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            cv_image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
            cv_image = self._enhance_image(cv_image)
            processed_image = Image.fromarray(cv2.cvtColor(cv_image, cv2.COLOR_BGR2RGB))
            
            return processed_image
            
        except Exception as e:
            logger.error(f"Image preprocessing error: {e}")
            return Image.open(BytesIO(image_data))
    
    def _enhance_image(self, cv_image: np.ndarray) -> np.ndarray:
        """Apply various image enhancement techniques"""
        gray = cv2.cvtColor(cv_image, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        thresh = cv2.adaptiveThreshold(
            blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
        )
        
        kernel = np.ones((2, 2), np.uint8)
        cleaned = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)
        
        return cv2.cvtColor(cleaned, cv2.COLOR_GRAY2BGR)
    
    def extract_text_from_receipt(self, image_data: bytes) -> Dict:
        """Extract and parse text from receipt image"""
        try:
            processed_image = self.preprocess_image(image_data)
            
            custom_config = r'--oem 3 --psm 6 -c tessedit_char_whitelist=0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz.,$/€£¥ '
            raw_text = pytesseract.image_to_string(processed_image, config=custom_config)
            
            confidence_data = pytesseract.image_to_data(processed_image, output_type=pytesseract.Output.DICT)
            avg_confidence = np.mean([int(conf) for conf in confidence_data['conf'] if int(conf) > 0])
            
            parsed_data = self._parse_receipt_text(raw_text)
            parsed_data['raw_text'] = raw_text
            parsed_data['confidence'] = avg_confidence
            
            return parsed_data
            
        except Exception as e:
            logger.error(f"OCR processing error: {e}")
            return {
                'items': [],
                'total': 0.0,
                'store_name': None,
                'date': None,
                'raw_text': '',
                'confidence': 0.0,
                'error': str(e)
            }
    
    def _parse_receipt_text(self, text: str) -> Dict:
        """Parse receipt text to extract structured data"""
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        
        result = {
            'items': [],
            'total': 0.0,
            'store_name': None,
            'date': None,
            'tax': 0.0
        }
        
        for i, line in enumerate(lines[:5]):
            if len(line) > 3 and not any(char.isdigit() for char in line):
                result['store_name'] = line
                break
        
        for line in lines:
            item_data = self._extract_item_from_line(line)
            if item_data:
                result['items'].append(item_data)
        
        total = self._extract_total(lines)
        if total:
            result['total'] = total
        
        date = self._extract_date(text)
        if date:
            result['date'] = date
        
        return result
    
    def _extract_item_from_line(self, line: str) -> Optional[Dict]:
        """Extract item information from a single line"""
        for pattern in self.item_patterns:
            match = pattern.match(line.strip())
            if match:
                groups = match.groups()
                if len(groups) == 2:
                    return {
                        'name': groups[0].strip(),
                        'quantity': 1,
                        'unit_price': float(groups[1].replace(',', '.')),
                        'total_price': float(groups[1].replace(',', '.'))
                    }
                elif len(groups) == 4:
                    return {
                        'name': groups[0].strip(),
                        'quantity': int(groups[1]),
                        'unit_price': float(groups[2].replace(',', '.')),
                        'total_price': float(groups[3].replace(',', '.'))
                    }
        
        prices = self.price_pattern.findall(line)
        if prices and len(line.split()) > 1:
            price = float(prices[-1].replace(',', '.'))
            item_name = re.sub(self.price_pattern, '', line).strip()
            if item_name and len(item_name) > 2:
                return {
                    'name': item_name,
                    'quantity': 1,
                    'unit_price': price,
                    'total_price': price
                }
        
        return None
    
    def _extract_total(self, lines: List[str]) -> Optional[float]:
        """Extract total amount from receipt"""
        total_keywords = ['total', 'sum', 'amount', 'gesamt', 'suma']
        
        for line in reversed(lines):
            line_lower = line.lower()
            if any(keyword in line_lower for keyword in total_keywords):
                prices = self.price_pattern.findall(line)
                if prices:
                    return float(prices[-1].replace(',', '.'))
        
        all_prices = []
        for line in lines:
            prices = self.price_pattern.findall(line)
            all_prices.extend([float(p.replace(',', '.')) for p in prices])
        
        if all_prices:
            return max(all_prices)
        
        return None
    
    def _extract_date(self, text: str) -> Optional[str]:
        """Extract date from receipt text"""
        date_patterns = [
            re.compile(r'(\d{1,2}[./]\d{1,2}[./]\d{2,4})'),
            re.compile(r'(\d{2,4}[-]\d{1,2}[-]\d{1,2})'),
        ]
        
        for pattern in date_patterns:
            match = pattern.search(text)
            if match:
                return match.group(1)
        
        return None

ocr_service = OCRService()
