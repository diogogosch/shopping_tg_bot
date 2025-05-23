import logging
import cv2
import numpy as np
from PIL import Image
import pytesseract
import re
from typing import List, Dict
import os

logger = logging.getLogger(__name__)

class OCRProcessor:
    def __init__(self):
        self.tesseract_config = '--oem 3 --psm 6 -c tessedit_char_whitelist=0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz.,€$£¥₹ '
        
    async def process_receipt(self, image_path: str) -> List[Dict]:
        """Process receipt image and extract items"""
        try:
            # Preprocess image
            processed_image = self._preprocess_image(image_path)
            
            # Extract text using OCR
            text = pytesseract.image_to_string(processed_image, config=self.tesseract_config)
            
            # Parse text to extract items
            items = self._parse_receipt_text(text)
            
            logger.info(f"Extracted {len(items)} items from receipt")
            return items
            
        except Exception as e:
            logger.error(f"Error processing receipt: {e}")
            return []
    
    def _preprocess_image(self, image_path: str) -> Image.Image:
        """Preprocess image for better OCR results"""
        # Read image with OpenCV
        img = cv2.imread(image_path)
        
        # Convert to grayscale
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # Apply Gaussian blur to reduce noise
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        
        # Apply adaptive thresholding
        thresh = cv2.adaptiveThreshold(
            blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
        )
        
        # Morphological operations to clean up
        kernel = np.ones((1, 1), np.uint8)
        cleaned = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)
        
        # Convert back to PIL Image
        return Image.fromarray(cleaned)
    
    def _parse_receipt_text(self, text: str) -> List[Dict]:
        """Parse OCR text to extract items with quantities and prices"""
        items = []
        lines = text.split('\n')
        
        # Common patterns for receipt items
        item_patterns = [
            r'([A-Za-z\s]+)\s+(\d+[.,]\d+|\d+)\s*([A-Za-z]*)\s*([€$£¥₹]?\d+[.,]\d+)',
            r'(\d+[.,]?\d*)\s*([A-Za-z]+)\s+([A-Za-z\s]+)\s*([€$£¥₹]?\d+[.,]\d+)',
            r'([A-Za-z\s]+)\s*([€$£¥₹]?\d+[.,]\d+)',
        ]
        
        for line in lines:
            line = line.strip()
            if len(line) < 3:  # Skip very short lines
                continue
                
            # Skip header/footer lines
            if any(word in line.lower() for word in ['total', 'subtotal', 'tax', 'receipt', 'thank', 'store', 'address']):
                continue
            
            # Try different patterns
            for pattern in item_patterns:
                match = re.search(pattern, line, re.IGNORECASE)
                if match:
                    item = self._extract_item_from_match(match, pattern)
                    if item:
                        items.append(item)
                    break
        
        # Clean and validate items
        cleaned_items = []
        for item in items:
            if self._is_valid_item(item):
                cleaned_items.append(item)
        
        return cleaned_items
    
    def _extract_item_from_match(self, match, pattern: str) -> Dict:
        """Extract item information from regex match"""
        groups = match.groups()
        
        # Different extraction logic based on pattern
        if len(groups) >= 3:
            # Try to identify name, quantity, unit, price
            item = {
                'name': '',
                'quantity': '',
                'unit': '',
                'price': '',
                'raw_text': match.group(0)
            }
            
            # Extract based on pattern structure
            for i, group in enumerate(groups):
                group = group.strip()
                
                # Check if it's a price (contains currency symbol or is at the end)
                if re.match(r'[€$£¥₹]?\d+[.,]\d+', group):
                    item['price'] = group
                # Check if it's a quantity (number + optional unit)
                elif re.match(r'\d+[.,]?\d*\s*[A-Za-z]*', group):
                    parts = re.split(r'(\d+[.,]?\d*)', group)
                    if len(parts) >= 2:
                        item['quantity'] = parts[1]
                        if len(parts) > 2 and parts[2].strip():
                            item['unit'] = parts[2].strip()
                # Otherwise, it's likely the item name
                else:
                    if not item['name'] or len(group) > len(item['name']):
                        item['name'] = group
            
            return item
        
        return None
    
    def _is_valid_item(self, item: Dict) -> bool:
        """Validate if extracted item is reasonable"""
        name = item.get('name', '').strip()
        
        # Must have a name
        if not name or len(name) < 2:
            return False
        
        # Filter out common non-item text
        invalid_words = ['total', 'subtotal', 'tax', 'change', 'cash', 'card', 'receipt', 'thank', 'store']
        if any(word in name.lower() for word in invalid_words):
            return False
        
        # Must contain at least one letter
        if not re.search(r'[A-Za-z]', name):
            return False
        
        return True
    
    def _clean_item_name(self, name: str) -> str:
        """Clean and normalize item name"""
        # Remove extra whitespace
        name = ' '.join(name.split())
        
        # Remove common prefixes/suffixes
        name = re.sub(r'^(organic|fresh|local)\s+', '', name, flags=re.IGNORECASE)
        name = re.sub(r'\s+(each|ea|pc|pcs)$', '', name, flags=re.IGNORECASE)
        
        # Capitalize properly
        return name.title()
