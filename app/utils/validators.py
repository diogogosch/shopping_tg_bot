import re
from typing import Optional

def validate_email(email: str) -> bool:
    """Validate email format"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))

def validate_currency_code(code: str) -> bool:
    """Validate currency code"""
    valid_currencies = ['USD', 'EUR', 'GBP', 'BRL', 'CAD', 'AUD', 'JPY', 'CNY']
    return code.upper() in valid_currencies

def validate_language_code(code: str) -> bool:
    """Validate language code"""
    valid_languages = ['en', 'es', 'pt', 'fr', 'de', 'it', 'ru', 'zh']
    return code.lower() in valid_languages

def validate_price(price: str) -> Optional[float]:
    """Validate and parse price string"""
    try:
        # Remove currency symbols and spaces
        cleaned = re.sub(r'[^\d.,]', '', price)
        # Replace comma with dot for decimal
        cleaned = cleaned.replace(',', '.')
        
        value = float(cleaned)
        return value if value >= 0 else None
    except (ValueError, TypeError):
        return None

def validate_quantity(quantity: str) -> Optional[float]:
    """Validate and parse quantity string"""
    try:
        # Extract numeric part
        numeric = re.search(r'(\d+(?:\.\d+)?)', quantity)
        if numeric:
            value = float(numeric.group(1))
            return value if value > 0 else None
    except (ValueError, TypeError):
        pass
    return None

def sanitize_filename(filename: str) -> str:
    """Sanitize filename for safe storage"""
    # Remove or replace dangerous characters
    sanitized = re.sub(r'[<>:"/\\|?*]', '_', filename)
    # Limit length
    return sanitized[:255]

def validate_telegram_user_id(user_id: any) -> bool:
    """Validate Telegram user ID"""
    try:
        uid = int(user_id)
        return uid > 0
    except (ValueError, TypeError):
        return False
