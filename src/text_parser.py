import re
import logging
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

class TextParser:
    def __init__(self):
        # Common units and their variations
        self.units = {
            'weight': ['kg', 'g', 'gram', 'grams', 'kilogram', 'kilograms', 'lb', 'lbs', 'pound', 'pounds', 'oz', 'ounce', 'ounces'],
            'volume': ['l', 'liter', 'liters', 'litre', 'litres', 'ml', 'milliliter', 'milliliters', 'cup', 'cups', 'pint', 'pints'],
            'count': ['unit', 'units', 'piece', 'pieces', 'pc', 'pcs', 'item', 'items', 'pack', 'packs', 'box', 'boxes']
        }
        
        # Flatten units for easier matching
        self.all_units = []
        for unit_list in self.units.values():
            self.all_units.extend(unit_list)
    
    def parse_purchase_text(self, text: str) -> List[Dict]:
        """Parse text description of purchases into structured items"""
        items = []
        
        # Clean and normalize text
        text = self._clean_text(text)
        
        # Split by common separators
        item_strings = self._split_items(text)
        
        for item_string in item_strings:
            item = self._parse_single_item(item_string.strip())
            if item:
                items.append(item)
        
        return items
    
    def _clean_text(self, text: str) -> str:
        """Clean and normalize input text"""
        # Remove common prefixes
        text = re.sub(r'^(bought|purchased|got|i bought|i got)\s+', '', text, flags=re.IGNORECASE)
        
        # Normalize whitespace
        text = ' '.join(text.split())
        
        return text
    
    def _split_items(self, text: str) -> List[str]:
        """Split text into individual item strings"""
        # Split by common separators
        separators = [',', ';', ' and ', ' & ', '\n']
        
        items = [text]
        for separator in separators:
            new_items = []
            for item in items:
                new_items.extend(item.split(separator))
            items = new_items
        
        # Filter out empty strings
        return [item.strip() for item in items if item.strip()]
    
    def _parse_single_item(self, item_string: str) -> Optional[Dict]:
        """Parse a single item string into structured data"""
        if not item_string or len(item_string) < 2:
            return None
        
        item = {
            'name': '',
            'quantity': '',
            'unit': '',
            'raw_text': item_string
        }
        
        # Try different parsing patterns
        patterns = [
            # Pattern: "2kg apples" or "500g cheese"
            r'^(\d+(?:[.,]\d+)?)\s*([a-zA-Z]+)\s+(.+)$',
            # Pattern: "apples 2kg" or "cheese 500g"
            r'^(.+?)\s+(\d+(?:[.,]\d+)?)\s*([a-zA-Z]+)$',
            # Pattern: "2 apples" or "3 bottles"
            r'^(\d+)\s+(.+)$',
            # Pattern: "apples 2" or "bottles 3"
            r'^(.+?)\s+(\d+)$',
            # Pattern: just item name
            r'^(.+)$'
        ]
        
        for pattern in patterns:
            match = re.match(pattern, item_string.strip(), re.IGNORECASE)
            if match:
                groups = match.groups()
                
                if len(groups) == 3:  # quantity, unit, name or name, quantity, unit
                    if self._is_number(groups[0]):
                        # quantity, unit, name
                        item['quantity'] = groups[0]
                        item['unit'] = groups[1] if self._is_unit(groups[1]) else ''
                        item['name'] = groups[2]
                    else:
                        # name, quantity, unit
                        item['name'] = groups[0]
                        item['quantity'] = groups[1]
                        item['unit'] = groups[2] if self._is_unit(groups[2]) else ''
                
                elif len(groups) == 2:  # quantity, name or name, quantity
                    if self._is_number(groups[0]):
                        # quantity, name
                        item['quantity'] = groups[0]
                        item['name'] = groups[1]
                        item['unit'] = 'units'  # Default unit
                    else:
                        # name, quantity
                        item['name'] = groups[0]
                        if self._is_number(groups[1]):
                            item['quantity'] = groups[1]
                            item['unit'] = 'units'  # Default unit
                        else:
                            item['name'] = f"{groups[0]} {groups[1]}"
                
                elif len(groups) == 1:  # just name
                    item['name'] = groups[0]
                    item['quantity'] = 'unknown'
                
                break
        
        # Clean up the item
        item['name'] = self._clean_item_name(item['name'])
        
        # Validate item
        if not item['name'] or len(item['name']) < 2:
            return None
        
        return item
    
    def _is_number(self, text: str) -> bool:
        """Check if text represents a number"""
        try:
            # Handle different decimal separators
            normalized = text.replace(',', '.')
            float(normalized)
            return True
        except ValueError:
            return False
    
    def _is_unit(self, text: str) -> bool:
        """Check if text is a valid unit"""
        return text.lower() in [unit.lower() for unit in self.all_units]
    
    def _clean_item_name(self, name: str) -> str:
        """Clean and normalize item name"""
        # Remove extra whitespace
        name = ' '.join(name.split())
        
        # Remove common articles and prepositions at the beginning
        name = re.sub(r'^(a|an|the|some|of)\s+', '', name, flags=re.IGNORECASE)
        
        # Remove trailing units that might have been missed
        for unit in self.all_units:
            name = re.sub(r'\s+' + re.escape(unit) + r'$', '', name, flags=re.IGNORECASE)
        
        # Capitalize properly
        name = name.strip().title()
        
        return name
    
    def extract_quantities_from_text(self, text: str) -> List[Dict]:
        """Extract all quantities mentioned in text"""
        quantities = []
        
        # Pattern to match quantities with units
        quantity_pattern = r'(\d+(?:[.,]\d+)?)\s*([a-zA-Z]+)'
        
        matches = re.finditer(quantity_pattern, text)
        for match in matches:
            quantity = match.group(1)
            unit = match.group(2)
            
            if self._is_unit(unit):
                quantities.append({
                    'quantity': quantity,
                    'unit': unit,
                    'position': match.span()
                })
        
        return quantities
    
    def suggest_quantity_format(self, item_name: str) -> str:
        """Suggest appropriate quantity format based on item name"""
        item_lower = item_name.lower()
        
        # Weight-based items
        weight_items = ['meat', 'cheese', 'fruit', 'vegetable', 'flour', 'sugar', 'rice']
        if any(item in item_lower for item in weight_items):
            return "Please specify weight (e.g., 500g, 1kg)"
        
        # Volume-based items
        volume_items = ['milk', 'juice', 'oil', 'water', 'soup', 'sauce']
        if any(item in item_lower for item in volume_items):
            return "Please specify volume (e.g., 1L, 500ml)"
        
        # Count-based items
        count_items = ['egg', 'apple', 'banana', 'bottle', 'can', 'pack']
        if any(item in item_lower for item in count_items):
            return "Please specify quantity (e.g., 6 units, 2 pieces)"
        
        return "Please specify quantity (e.g., 2kg, 1L, 3 units)"
