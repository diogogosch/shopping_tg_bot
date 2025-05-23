import asyncio
import asyncpg
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
import os
import json

logger = logging.getLogger(__name__)

class DatabaseManager:
    def __init__(self):
        self.database_url = os.getenv('DATABASE_URL', 'postgresql://botuser:secure_password_here@localhost:5432/smartshop')
        self.pool = None
    
    async def init_pool(self):
        """Initialize connection pool"""
        if not self.pool:
            self.pool = await asyncpg.create_pool(self.database_url)
            await self._create_tables()
    
    async def _create_tables(self):
        """Create necessary database tables"""
        async with self.pool.acquire() as conn:
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id BIGINT PRIMARY KEY,
                    username VARCHAR(255),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS purchases (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT REFERENCES users(id),
                    item_name VARCHAR(255) NOT NULL,
                    category VARCHAR(100),
                    quantity VARCHAR(50),
                    unit VARCHAR(20),
                    price VARCHAR(20),
                    purchase_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    raw_data JSONB
                )
            ''')
            
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS categories (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(100) UNIQUE NOT NULL,
                    keywords TEXT[],
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS user_preferences (
                    user_id BIGINT PRIMARY KEY REFERENCES users(id),
                    preferences JSONB DEFAULT '{}',
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Create indexes for better performance
            await conn.execute('CREATE INDEX IF NOT EXISTS idx_purchases_user_id ON purchases(user_id)')
            await conn.execute('CREATE INDEX IF NOT EXISTS idx_purchases_item_name ON purchases(item_name)')
            await conn.execute('CREATE INDEX IF NOT EXISTS idx_purchases_category ON purchases(category)')
            await conn.execute('CREATE INDEX IF NOT EXISTS idx_purchases_date ON purchases(purchase_date)')
            
            # Insert default categories
            await self._insert_default_categories(conn)
    
    async def _insert_default_categories(self, conn):
        """Insert default item categories"""
        default_categories = [
            ('produce', ['apple', 'banana', 'orange', 'tomato', 'lettuce', 'carrot', 'onion', 'potato', 'fruit', 'vegetable']),
            ('dairy', ['milk', 'cheese', 'yogurt', 'butter', 'cream', 'eggs']),
            ('meat', ['chicken', 'beef', 'pork', 'fish', 'salmon', 'turkey', 'ham', 'bacon']),
            ('pantry', ['rice', 'pasta', 'bread', 'flour', 'sugar', 'salt', 'oil', 'vinegar', 'spice']),
            ('beverages', ['water', 'juice', 'soda', 'coffee', 'tea', 'beer', 'wine']),
            ('frozen', ['ice cream', 'frozen', 'pizza']),
            ('household', ['soap', 'detergent', 'toilet paper', 'cleaning', 'shampoo']),
            ('snacks', ['chips', 'cookies', 'candy', 'chocolate', 'nuts']),
            ('bakery', ['bread', 'cake', 'pastry', 'muffin', 'bagel']),
            ('other', [])
        ]
        
        for category, keywords in default_categories:
            await conn.execute('''
                INSERT INTO categories (name, keywords) 
                VALUES ($1, $2) 
                ON CONFLICT (name) DO NOTHING
            ''', category, keywords)
    
    async def create_user(self, user_id: int, username: str):
        """Create or update user"""
        if not self.pool:
            await self.init_pool()
        
        async with self.pool.acquire() as conn:
            await conn.execute('''
                INSERT INTO users (id, username, last_active) 
                VALUES ($1, $2, CURRENT_TIMESTAMP)
                ON CONFLICT (id) DO UPDATE SET 
                    username = $2, 
                    last_active = CURRENT_TIMESTAMP
            ''', user_id, username)
    
    async def add_purchase(self, user_id: int, item: Dict):
        """Add a purchase record"""
        if not self.pool:
            await self.init_pool()
        
        async with self.pool.acquire() as conn:
            await conn.execute('''
                INSERT INTO purchases (user_id, item_name, category, quantity, unit, price, raw_data)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
            ''', 
                user_id,
                item.get('name', ''),
                item.get('category', 'other'),
                item.get('quantity', ''),
                item.get('unit', ''),
                item.get('price', ''),
                json.dumps(item)
            )
    
    async def get_user_purchases(self, user_id: int, days: int = 30) -> List[Dict]:
        """Get user's recent purchases"""
        if not self.pool:
            await self.init_pool()
        
        async with self.pool.acquire() as conn:
            rows = await conn.fetch('''
                SELECT * FROM purchases 
                WHERE user_id = $1 AND purchase_date >= $2
                ORDER BY purchase_date DESC
            ''', user_id, datetime.now() - timedelta(days=days))
            
            return [dict(row) for row in rows]
    
    async def get_user_categories(self, user_id: int) -> Dict[str, List[str]]:
        """Get user's items grouped by category"""
        if not self.pool:
            await self.init_pool()
        
        async with self.pool.acquire() as conn:
            rows = await conn.fetch('''
                SELECT category, item_name, COUNT(*) as frequency
                FROM purchases 
                WHERE user_id = $1
                GROUP BY category, item_name
                ORDER BY category, frequency DESC
            ''', user_id)
            
            categories = {}
            for row in rows:
                category = row['category'] or 'other'
                if category not in categories:
                    categories[category] = []
                categories[category].append(row['item_name'])
            
            return categories
    
    async def get_item_frequency(self, user_id: int, item_name: str) -> int:
        """Get how often an item has been purchased"""
        if not self.pool:
            await self.init_pool()
        
        async with self.pool.acquire() as conn:
            result = await conn.fetchval('''
                SELECT COUNT(*) FROM purchases 
                WHERE user_id = $1 AND LOWER(item_name) = LOWER($2)
            ''', user_id, item_name)
            
            return result or 0
    
    async def get_category_keywords(self) -> Dict[str, List[str]]:
        """Get all category keywords for classification"""
        if not self.pool:
            await self.init_pool()
        
        async with self.pool.acquire() as conn:
            rows = await conn.fetch('SELECT name, keywords FROM categories')
            
            return {row['name']: row['keywords'] for row in rows}
    
    async def get_user_stats(self, user_id: int) -> Optional[Dict]:
        """Get user shopping statistics"""
        if not self.pool:
            await self.init_pool()
        
        async with self.pool.acquire() as conn:
            # Basic stats
            stats = await conn.fetchrow('''
                SELECT 
                    COUNT(*) as total_purchases,
                    COUNT(DISTINCT item_name) as unique_items,
                    COUNT(DISTINCT category) as categories,
                    COUNT(DISTINCT DATE(purchase_date)) as days_tracked
                FROM purchases 
                WHERE user_id = $1
            ''', user_id)
            
            if not stats or stats['total_purchases'] == 0:
                return None
            
            # Top categories
            top_categories = await conn.fetch('''
                SELECT category, COUNT(*) as count
                FROM purchases 
                WHERE user_id = $1
                GROUP BY category
                ORDER BY count DESC
                LIMIT 5
            ''', user_id)
            
            # Top items
            top_items = await conn.fetch('''
                SELECT item_name, COUNT(*) as count
                FROM purchases 
                WHERE user_id = $1
                GROUP BY item_name
                ORDER BY count DESC
                LIMIT 5
            ''', user_id)
            
            return {
                'total_purchases': stats['total_purchases'],
                'unique_items': stats['unique_items'],
                'categories': stats['categories'],
                'days_tracked': stats['days_tracked'],
                'top_categories': [(row['category'], row['count']) for row in top_categories],
                'top_items': [(row['item_name'], row['count']) for row in top_items]
            }
    
    async def get_purchase_patterns(self, user_id: int) -> List[Dict]:
        """Get purchase patterns for ML suggestions"""
        if not self.pool:
            await self.init_pool()
        
        async with self.pool.acquire() as conn:
            rows = await conn.fetch('''
                SELECT 
                    item_name,
                    category,
                    COUNT(*) as frequency,
                    AVG(EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP - purchase_date))/86400) as avg_days_since,
                    MAX(purchase_date) as last_purchase,
                    MIN(purchase_date) as first_purchase
                FROM purchases 
                WHERE user_id = $1
                GROUP BY item_name, category
                HAVING COUNT(*) > 1
                ORDER BY frequency DESC
            ''', user_id)
            
            return [dict(row) for row in rows]
    
    async def close(self):
        """Close database connection pool"""
        if self.pool:
            await self.pool.close()
