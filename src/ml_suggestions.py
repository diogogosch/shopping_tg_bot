import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import re
from collections import defaultdict
import math

logger = logging.getLogger(__name__)

class MLSuggestions:
    def __init__(self, db_manager):
        self.db = db_manager
        
    async def categorize_item(self, item_name: str) -> str:
        """Categorize an item based on keywords and patterns"""
        item_name_lower = item_name.lower()
        
        # Get category keywords from database
        category_keywords = await self.db.get_category_keywords()
        
        # Score each category
        category_scores = {}
        
        for category, keywords in category_keywords.items():
            score = 0
            for keyword in keywords:
                if keyword.lower() in item_name_lower:
                    # Exact match gets higher score
                    if keyword.lower() == item_name_lower:
                        score += 10
                    # Partial match
                    elif keyword.lower() in item_name_lower:
                        score += 5
                    # Word boundary match
                    elif re.search(r'\b' + re.escape(keyword.lower()) + r'\b', item_name_lower):
                        score += 7
            
            category_scores[category] = score
        
        # Return category with highest score, default to 'other'
        if category_scores:
            best_category = max(category_scores, key=category_scores.get)
            if category_scores[best_category] > 0:
                return best_category
        
        return 'other'
    
    async def generate_shopping_suggestions(self, user_id: int) -> Dict[str, List[Dict]]:
        """Generate shopping suggestions based on purchase patterns"""
        # Get purchase patterns
        patterns = await self.db.get_purchase_patterns(user_id)
        
        if not patterns:
            return {}
        
        suggestions = defaultdict(list)
        current_time = datetime.now()
        
        for pattern in patterns:
            item_name = pattern['item_name']
            category = pattern['category']
            frequency = pattern['frequency']
            avg_days_since = pattern['avg_days_since']
            last_purchase = pattern['last_purchase']
            
            # Calculate days since last purchase
            days_since_last = (current_time - last_purchase).days
            
            # Calculate purchase frequency (purchases per week)
            total_days = (current_time - pattern['first_purchase']).days
            if total_days > 0:
                purchases_per_week = (frequency * 7) / total_days
            else:
                purchases_per_week = 0
            
            # Calculate suggestion confidence
            confidence = self._calculate_suggestion_confidence(
                frequency, days_since_last, avg_days_since, purchases_per_week
            )
            
            # Only suggest items with reasonable confidence
            if confidence > 0.3:
                suggestions[category].append({
                    'name': item_name,
                    'confidence': confidence,
                    'frequency': frequency,
                    'days_since_last': days_since_last,
                    'avg_interval': avg_days_since
                })
        
        # Sort suggestions by confidence within each category
        for category in suggestions:
            suggestions[category].sort(key=lambda x: x['confidence'], reverse=True)
            # Limit to top 5 suggestions per category
            suggestions[category] = suggestions[category][:5]
        
        return dict(suggestions)
    
    def _calculate_suggestion_confidence(self, frequency: int, days_since_last: int, 
                                       avg_days_since: float, purchases_per_week: float) -> float:
        """Calculate confidence score for suggesting an item"""
        
        # Base confidence from frequency (more frequent = higher confidence)
        frequency_score = min(frequency / 10.0, 1.0)  # Cap at 1.0
        
        # Time-based score (should we buy this soon?)
        if avg_days_since > 0:
            expected_next_purchase = avg_days_since
            time_score = max(0, min(1.0, days_since_last / expected_next_purchase))
        else:
            time_score = 0.5
        
        # Regularity score (how regular are the purchases?)
        if purchases_per_week > 0:
            regularity_score = min(purchases_per_week, 1.0)
        else:
            regularity_score = 0.1
        
        # Combine scores with weights
        confidence = (
            frequency_score * 0.4 +
            time_score * 0.4 +
            regularity_score * 0.2
        )
        
        # Apply decay for very old items
        if days_since_last > 60:  # More than 2 months
            confidence *= 0.5
        elif days_since_last > 30:  # More than 1 month
            confidence *= 0.8
        
        return min(confidence, 1.0)
    
    async def learn_from_purchase(self, user_id: int, item_name: str, category: str):
        """Learn from a new purchase to improve future suggestions"""
        # This could be expanded to update ML models
        # For now, the database storage is sufficient for pattern recognition
        pass
    
    async def get_similar_items(self, item_name: str, user_id: int) -> List[str]:
        """Find similar items based on name similarity and user history"""
        purchases = await self.db.get_user_purchases(user_id, days=365)
        
        similar_items = []
        item_words = set(item_name.lower().split())
        
        for purchase in purchases:
            purchase_name = purchase['item_name']
            purchase_words = set(purchase_name.lower().split())
            
            # Calculate word overlap
            overlap = len(item_words.intersection(purchase_words))
            total_words = len(item_words.union(purchase_words))
            
            if total_words > 0:
                similarity = overlap / total_words
                if similarity > 0.3 and purchase_name.lower() != item_name.lower():
                    similar_items.append((purchase_name, similarity))
        
        # Sort by similarity and return top matches
        similar_items.sort(key=lambda x: x[1], reverse=True)
        return [item[0] for item in similar_items[:5]]
    
    async def predict_next_shopping_day(self, user_id: int) -> Optional[datetime]:
        """Predict when user is likely to shop next based on patterns"""
        purchases = await self.db.get_user_purchases(user_id, days=90)
        
        if len(purchases) < 3:
            return None
        
        # Group purchases by day
        purchase_days = {}
        for purchase in purchases:
            day = purchase['purchase_date'].date()
            if day not in purchase_days:
                purchase_days[day] = 0
            purchase_days[day] += 1
        
        # Calculate average interval between shopping days
        shopping_days = sorted(purchase_days.keys())
        intervals = []
        
        for i in range(1, len(shopping_days)):
            interval = (shopping_days[i] - shopping_days[i-1]).days
            intervals.append(interval)
        
        if intervals:
            avg_interval = sum(intervals) / len(intervals)
            last_shopping_day = max(shopping_days)
            next_predicted = last_shopping_day + timedelta(days=int(avg_interval))
            
            return datetime.combine(next_predicted, datetime.min.time())
        
        return None
