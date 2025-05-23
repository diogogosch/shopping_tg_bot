import re
from typing import List, Dict, Optional
from datetime import datetime, timedelta

def clean_text(text: str) -> str:
    """Clean and normalize text input"""
    if not text:
        return ""
    
    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text.strip())
    
    # Remove special characters but keep basic punctuation
    text = re.sub(r'[^\w\s,.-]', '', text)
    
    return text

def parse_quantity(text: str) -> Dict[str, any]:
    """Parse quantity from text like '2kg', '1.5L', '3 pieces'"""
    patterns = [
        r'(\d+(?:\.\d+)?)\s*(kg|g|l|ml|oz|lb|pieces?|pcs?)',
        r'(\d+(?:\.\d+)?)\s*x',
        r'(\d+(?:\.\d+)?)'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text.lower())
        if match:
            quantity = float(match.group(1))
            unit = match.group(2) if len(match.groups()) > 1 else 'piece'
            return {'quantity': quantity, 'unit': unit}
    
    return {'quantity': 1.0, 'unit': 'piece'}

def format_currency(amount: float, currency: str = 'USD') -> str:
    """Format currency amount"""
    symbols = {
        'USD': '$',
        'EUR': '€',
        'GBP': '£',
        'BRL': 'R$'
    }
    
    symbol = symbols.get(currency, currency)
    return f"{symbol}{amount:.2f}"

def calculate_savings(current_price: float, average_price: float) -> Dict:
    """Calculate savings percentage and amount"""
    if not average_price or average_price == 0:
        return {'percentage': 0, 'amount': 0}
    
    savings_amount = average_price - current_price
    savings_percentage = (savings_amount / average_price) * 100
    
    return {
        'percentage': round(savings_percentage, 1),
        'amount': round(savings_amount, 2)
    }

def get_time_ago(timestamp: datetime) -> str:
    """Get human-readable time ago string"""
    now = datetime.utcnow()
    diff = now - timestamp
    
    if diff.days > 0:
        return f"{diff.days} day{'s' if diff.days > 1 else ''} ago"
    elif diff.seconds > 3600:
        hours = diff.seconds // 3600
        return f"{hours} hour{'s' if hours > 1 else ''} ago"
    elif diff.seconds > 60:
        minutes = diff.seconds // 60
        return f"{minutes} minute{'s' if minutes > 1 else ''} ago"
    else:
        return "Just now"

def chunk_list(lst: List, chunk_size: int) -> List[List]:
    """Split list into chunks of specified size"""
    return [lst[i:i + chunk_size] for i in range(0, len(lst), chunk_size)]

def fuzzy_match(query: str, options: List[str], threshold: float = 0.6) -> List[str]:
    """Simple fuzzy matching for product names"""
    query_lower = query.lower()
    matches = []
    
    for option in options:
        option_lower = option.lower()
        
        # Exact match
        if query_lower == option_lower:
            matches.append((option, 1.0))
            continue
        
        # Contains match
        if query_lower in option_lower or option_lower in query_lower:
            matches.append((option, 0.8))
            continue
        
        # Word overlap
        query_words = set(query_lower.split())
        option_words = set(option_lower.split())
        overlap = len(query_words & option_words)
        total_words = len(query_words | option_words)
        
        if total_words > 0:
            score = overlap / total_words
            if score >= threshold:
                matches.append((option, score))
    
    # Sort by score and return
    matches.sort(key=lambda x: x[1], reverse=True)
    return [match[0] for match in matches]
