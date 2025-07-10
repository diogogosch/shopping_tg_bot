import re
import logging

logger = logging.getLogger(__name__)

def validate_item_name(item_name: str) -> bool:
    """
    Validate item name to prevent XSS and SQL injection.
    Allows alphanumeric characters, spaces, and common punctuation.
    """
    if not item_name or len(item_name) > 100:
        logger.warning(f"Invalid item name length: {item_name}")
        return False
    
    # Allow letters, numbers, spaces, and common punctuation
    pattern = r'^[a-zA-Z0-9\s\-\,\.\(\)]+$'
    if not re.match(pattern, item_name):
        logger.warning(f"Invalid characters in item name: {item_name}")
        return False
    
    # Prevent common SQL injection patterns
    dangerous_patterns = [r'\bSELECT\b', r'\bINSERT\b', r'\bDELETE\b', r'\bUPDATE\b', r'--', r';']
    for pattern in dangerous_patterns:
        if re.search(pattern, item_name, re.IGNORECASE):
            logger.warning(f"Potential SQL injection detected: {item_name}")
            return False
    
    return True