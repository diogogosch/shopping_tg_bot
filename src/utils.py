import logging
import os
from datetime import datetime
import json

def setup_logging():
    """Set up logging configuration"""
    log_level = os.getenv('LOG_LEVEL', 'INFO').upper()
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    # Create logs directory if it doesn't exist
    os.makedirs('logs', exist_ok=True)
    
    # Configure logging
    logging.basicConfig(
        level=getattr(logging, log_level),
        format=log_format,
        handlers=[
            logging.FileHandler(f'logs/bot_{datetime.now().strftime("%Y%m%d")}.log'),
            logging.StreamHandler()
        ]
    )

def format_price(price_str: str) -> str:
    """Format price string consistently"""
    if not price_str:
        return ""
    
    # Remove currency symbols and clean
    cleaned = ''.join(c for c in price_str if c.isdigit() or c in '.,')
    
    # Normalize decimal separator
    if ',' in cleaned and '.' in cleaned:
        # Assume comma is thousands separator
        cleaned = cleaned.replace(',', '')
    elif ',' in cleaned:
        # Assume comma is decimal separator
        cleaned = cleaned.replace(',', '.')
    
    try:
        price = float(cleaned)
        return f"{price:.2f}"
    except ValueError:
        return price_str

def normalize_item_name(name: str) -> str:
    """Normalize item name for consistent storage"""
    if not name:
        return ""
    
    # Convert to lowercase for comparison
    normalized = name.lower().strip()
    
    # Remove common variations
    replacements = {
        'organic ': '',
        'fresh ': '',
        'local ': '',
        ' each': '',
        ' ea': '',
        ' pc': '',
        ' pcs': ''
    }
    
    for old, new in replacements.items():
        normalized = normalized.replace(old, new)
    
    return normalized.strip()

def calculate_similarity(str1: str, str2: str) -> float:
    """Calculate string similarity using simple word overlap"""
    words1 = set(str1.lower().split())
    words2 = set(str2.lower().split())
    
    if not words1 and not words2:
        return 1.0
    if not words1 or not words2:
        return 0.0
    
    intersection = words1.intersection(words2)
    union = words1.union(words2)
    
    return len(intersection) / len(union)

def validate_environment():
    """Validate required environment variables"""
    required_vars = ['TELEGRAM_BOT_TOKEN', 'DATABASE_URL']
    missing_vars = []
    
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")

def safe_json_loads(json_str: str, default=None):
    """Safely load JSON string with fallback"""
    try:
        return json.loads(json_str)
    except (json.JSONDecodeError, TypeError):
        return default or {}

def format_duration(seconds: int) -> str:
    """Format duration in human-readable format"""
    if seconds < 60:
        return f"{seconds} seconds"
    elif seconds < 3600:
        minutes = seconds // 60
        return f"{minutes} minutes"
    elif seconds < 86400:
        hours = seconds // 3600
        return f"{hours} hours"
    else:
        days = seconds // 86400
        return f"{days} days"
