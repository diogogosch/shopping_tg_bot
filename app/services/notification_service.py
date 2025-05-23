import logging
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.user import User
from app.models.product import Product, ShoppingListItem
from app.models.receipt import Receipt
from app.core.cache import cache

logger = logging.getLogger(__name__)

class NotificationService:
    def __init__(self):
        self.notification_types = {
            'price_drop': 'Price Drop Alert',
            'low_stock': 'Low Stock Reminder',
            'shopping_reminder': 'Shopping Reminder',
            'weekly_summary': 'Weekly Summary'
        }
    
    async def send_price_alerts(self, bot_instance):
        """Send price drop alerts to users"""
        try:
            with get_db() as db:
                # Get users with price alerts enabled
                users = db.query(User).filter(User.price_alerts_enabled == True).all()
                
                for user in users:
                    alerts = self._check_price_drops(user, db)
                    if alerts:
                        await self._send_price_alert(bot_instance, user, alerts)
                        
        except Exception as e:
            logger.error(f"Error sending price alerts: {e}")
    
    def _check_price_drops(self, user: User, db: Session) -> List[Dict]:
        """Check for price drops on user's frequent items"""
        alerts = []
        
        # Get user's frequent items from recent receipts
        recent_receipts = db.query(Receipt).filter(
            Receipt.user_id == user.id,
            Receipt.purchase_date >= datetime.utcnow() - timedelta(days=60)
        ).all()
        
        item_prices = {}
        for receipt in recent_receipts:
            for item in receipt.items:
                if item.product:
                    product_id = item.product.id
                    if product_id not in item_prices:
                        item_prices[product_id] = []
                    item_prices[product_id].append(item.unit_price)
        
        # Check for significant price drops
        for product_id, prices in item_prices.items():
            if len(prices) >= 3:  # Need at least 3 price points
                avg_price = sum(prices) / len(prices)
                recent_price = prices[-1]
                
                # If recent price is 15% or more below average
                if recent_price < avg_price * 0.85:
                    product = db.query(Product).filter(Product.id == product_id).first()
                    if product:
                        savings = avg_price - recent_price
                        savings_percent = (savings / avg_price) * 100
                        
                        alerts.append({
                            'product': product.name,
                            'old_price': avg_price,
                            'new_price': recent_price,
                            'savings': savings,
                            'savings_percent': savings_percent
                        })
        
        return alerts
    
    async def _send_price_alert(self, bot_instance, user: User, alerts: List[Dict]):
        """Send price alert message to user"""
        text = "💰 *Price Drop Alert!*\n\n"
        text += "Great news! Prices have dropped on items you frequently buy:\n\n"
        
        for alert in alerts[:5]:  # Limit to 5 alerts
            text += f"🔽 *{alert['product']}*\n"
            text += f"   Was: ${alert['old_price']:.2f} → Now: ${alert['new_price']:.2f}\n"
            text += f"   💸 Save ${alert['savings']:.2f} ({alert['savings_percent']:.1f}%)\n\n"
        
        text += "Consider stocking up while prices are low! 🛒"
        
        try:
            await bot_instance.send_message(
                chat_id=user.telegram_id,
                text=text,
                parse_mode='Markdown'
            )
        except Exception as e:
            logger.error(f"Failed to send price alert to user {user.telegram_id}: {e}")
    
    async def send_shopping_reminders(self, bot_instance):
        """Send shopping reminders to users with old lists"""
        try:
            with get_db() as db:
                # Find users with old active shopping lists
                cutoff_date = datetime.utcnow() - timedelta(days=7)
                
                from app.models.product import ShoppingList
                old_lists = db.query(ShoppingList).filter(
                    ShoppingList.is_active == True,
                    ShoppingList.created_at < cutoff_date
                ).all()
                
                for shopping_list in old_lists:
                    user = shopping_list.user
                    if user and len(shopping_list.items) > 0:
                        await self._send_shopping_reminder(bot_instance, user, shopping_list)
                        
        except Exception as e:
            logger.error(f"Error sending shopping reminders: {e}")
    
    async def _send_shopping_reminder(self, bot_instance, user: User, shopping_list):
        """Send shopping reminder to user"""
        days_old = (datetime.utcnow() - shopping_list.created_at).days
        item_count = len([item for item in shopping_list.items if not item.is_purchased])
        
        text = f"🛒 *Shopping Reminder*\n\n"
        text += f"You have {item_count} items in your shopping list from {days_old} days ago.\n\n"
        text += "Don't forget to go shopping! Your list includes:\n"
        
        # Show first few items
        for item in shopping_list.items[:5]:
            if not item.is_purchased:
                emoji = "🔴" if item.priority == 3 else "🟡" if item.priority == 2 else "⚪"
                text += f"{emoji} {item.product.name}\n"
        
        if item_count > 5:
            text += f"... and {item_count - 5} more items\n"
        
        text += f"\nUse /list to see your complete shopping list!"
        
        try:
            await bot_instance.send_message(
                chat_id=user.telegram_id,
                text=text,
                parse_mode='Markdown'
            )
        except Exception as e:
            logger.error(f"Failed to send shopping reminder to user {user.telegram_id}: {e}")
    
    async def send_weekly_summaries(self, bot_instance):
        """Send weekly shopping summaries to users"""
        try:
            with get_db() as db:
                # Get users who have been active in the last week
                week_ago = datetime.utcnow() - timedelta(days=7)
                
                active_users = db.query(User).filter(
                    User.last_active >= week_ago
                ).all()
                
                for user in active_users:
                    summary = self._generate_weekly_summary(user, db)
                    if summary:
                        await self._send_weekly_summary(bot_instance, user, summary)
                        
        except Exception as e:
            logger.error(f"Error sending weekly summaries: {e}")
    
    def _generate_weekly_summary(self, user: User, db: Session) -> Optional[Dict]:
        """Generate weekly summary for user"""
        week_ago = datetime.utcnow() - timedelta(days=7)
        
        # Get receipts from last week
        weekly_receipts = db.query(Receipt).filter(
            Receipt.user_id == user.id,
            Receipt.purchase_date >= week_ago
        ).all()
        
        if not weekly_receipts:
            return None
        
        total_spent = sum(receipt.total_amount for receipt in weekly_receipts)
        total_items = sum(len(receipt.items) for receipt in weekly_receipts)
        
        # Category breakdown
        categories = {}
        for receipt in weekly_receipts:
            for item in receipt.items:
                if item.product:
                    category = item.product.category
                    categories[category] = categories.get(category, 0) + item.total_price
        
        return {
            'total_spent': total_spent,
            'total_items': total_items,
            'receipt_count': len(weekly_receipts),
            'categories': categories,
            'avg_per_trip': total_spent / len(weekly_receipts)
        }
    
    async def _send_weekly_summary(self, bot_instance, user: User, summary: Dict):
        """Send weekly summary to user"""
        text = f"📊 *Your Weekly Shopping Summary*\n\n"
        text += f"💰 Total Spent: ${summary['total_spent']:.2f}\n"
        text += f"🛒 Shopping Trips: {summary['receipt_count']}\n"
        text += f"📦 Items Purchased: {summary['total_items']}\n"
        text += f"📈 Average per Trip: ${summary['avg_per_trip']:.2f}\n\n"
        
        if summary['categories']:
            text += "*Spending by Category:*\n"
            sorted_categories = sorted(summary['categories'].items(), key=lambda x: x[1], reverse=True)
            for category, amount in sorted_categories[:5]:
                percentage = (amount / summary['total_spent']) * 100
                text += f"• {category.title()}: ${amount:.2f} ({percentage:.1f}%)\n"
        
        text += f"\nKeep up the smart shopping! 🎯"
        
        try:
            await bot_instance.send_message(
                chat_id=user.telegram_id,
                text=text,
                parse_mode='Markdown'
            )
        except Exception as e:
            logger.error(f"Failed to send weekly summary to user {user.telegram_id}: {e}")

# Global notification service instance
notification_service = NotificationService()
