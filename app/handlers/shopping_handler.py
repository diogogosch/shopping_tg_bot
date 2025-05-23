from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ParseMode
from sqlalchemy.orm import Session
import re
import logging
from typing import List

from app.core.database import get_db
from app.models.user import User
from app.models.product import Product, ShoppingList, ShoppingListItem
from app.services.ai_service import ai_service

logger = logging.getLogger(__name__)

class ShoppingHandler:
    def __init__(self):
        self.quantity_patterns = [
            re.compile(r'(\d+(?:\.\d+)?)\s*(kg|g|l|ml|pieces?|pcs?)\s+(.+)', re.IGNORECASE),
            re.compile(r'(\d+(?:\.\d+)?)\s*x\s*(.+)', re.IGNORECASE),
            re.compile(r'(\d+(?:\.\d+)?)\s+(.+)', re.IGNORECASE),
        ]
    
    async def add_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /add command"""
        if not context.args:
            await update.message.reply_text(
                "📝 *Add Items to Your List*\n\n"
                "*Usage:* `/add item1, item2, item3`\n"
                "*Examples:*\n"
                "• `/add milk, bread, eggs`\n"
                "• `/add 2kg apples, 1L orange juice`\n"
                "• `/add chicken breast and rice`\n\n"
                "You can also just send me a message with items!",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        items_text = " ".join(context.args)
        items = self._parse_items_from_text(items_text)
        
        if not items:
            await update.message.reply_text(
                "❌ I couldn't understand the items. Please try again with a format like:\n"
                "`milk, bread, 2kg apples`"
            )
            return
        
        success_count = await self.add_items_to_list(update.effective_user.id, items)
        
        if success_count > 0:
            items_text = ", ".join([item['name'] for item in items[:3]])
            if len(items) > 3:
                items_text += f" and {len(items) - 3} more"
            
            keyboard = [
                [InlineKeyboardButton("📋 View List", callback_data="view_list")],
                [InlineKeyboardButton("🤖 Get Suggestions", callback_data="get_suggestions")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                f"✅ Added {success_count} items: {items_text}",
                reply_markup=reply_markup
            )
        else:
            await update.message.reply_text("❌ Failed to add items. Please try again.")
    
    async def list_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /list command"""
        user_id = update.effective_user.id
        
        with get_db() as db:
            user = db.query(User).filter(User.telegram_id == user_id).first()
            if not user:
                await update.message.reply_text("❌ User not found. Please start with /start")
                return
            
            shopping_list = db.query(ShoppingList).filter(
                ShoppingList.user_id == user.id,
                ShoppingList.is_active == True
            ).first()
            
            if not shopping_list or not shopping_list.items:
                keyboard = [
                    [InlineKeyboardButton("➕ Add Items", callback_data="add_items")],
                    [InlineKeyboardButton("🤖 Get Suggestions", callback_data="get_suggestions")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await update.message.reply_text(
                    "📋 Your shopping list is empty!\n\n"
                    "Start adding items with `/add` or get AI suggestions.",
                    reply_markup=reply_markup
                )
                return
            
            # Format shopping list
            text = "🛒 *Your Shopping List*\n\n"
            total_items = len(shopping_list.items)
            purchased_items = len([item for item in shopping_list.items if item.is_purchased])
            
            for item in shopping_list.items:
                status = "✅" if item.is_purchased else "⬜"
                priority = "🔴" if item.priority == 3 else "🟡" if item.priority == 2 else ""
                
                quantity_text = f"{item.quantity} " if item.quantity != 1 else ""
                unit_text = f"{item.unit} " if item.unit != "piece" else ""
                
                text += f"{status} {priority}{quantity_text}{unit_text}{item.product.name}\n"
                
                if item.notes:
                    text += f"   _{item.notes}_\n"
                
                if item.is_ai_suggested:
                    text += f"   🤖 _{item.suggestion_reason}_\n"
                
                text += "\n"
            
            text += f"📊 Progress: {purchased_items}/{total_items} items"
            
            if shopping_list.estimated_total:
                text += f"\n💰 Estimated total: ${shopping_list.estimated_total:.2f}"
            
            # Create action buttons
            keyboard = [
                [InlineKeyboardButton("➕ Add More", callback_data="add_items")],
                [InlineKeyboardButton("🗑️ Clear List", callback_data="clear_list")],
                [InlineKeyboardButton("🤖 Suggestions", callback_data="get_suggestions")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                text,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=reply_markup
            )
    
    async def remove_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /remove command"""
        if not context.args:
            await update.message.reply_text(
                "❌ Please specify what to remove.\n"
                "*Usage:* `/remove item_name`"
            )
            return
        
        item_name = " ".join(context.args).lower()
        user_id = update.effective_user.id
        
        with get_db() as db:
            user = db.query(User).filter(User.telegram_id == user_id).first()
            if not user:
                return
            
            shopping_list = db.query(ShoppingList).filter(
                ShoppingList.user_id == user.id,
                ShoppingList.is_active == True
            ).first()
            
            if not shopping_list:
                await update.message.reply_text("❌ No active shopping list found.")
                return
            
            # Find matching item
            removed_item = None
            for item in shopping_list.items:
                if item_name in item.product.name.lower():
                    removed_item = item
                    db.delete(item)
                    db.commit()
                    break
            
            if removed_item:
                await update.message.reply_text(
                    f"✅ Removed '{removed_item.product.name}' from your list."
                )
            else:
                await update.message.reply_text(
                    f"❌ Item '{item_name}' not found in your list."
                )
    
    async def clear_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /clear command"""
        user_id = update.effective_user.id
        
        with get_db() as db:
            user = db.query(User).filter(User.telegram_id == user_id).first()
            if not user:
                return
            
            shopping_list = db.query(ShoppingList).filter(
                ShoppingList.user_id == user.id,
                ShoppingList.is_active == True
            ).first()
            
            if not shopping_list or not shopping_list.items:
                await update.message.reply_text("❌ Your shopping list is already empty.")
                return
            
            # Clear all items
            for item in shopping_list.items:
                db.delete(item)
            db.commit()
            
            await update.message.reply_text("✅ Shopping list cleared!")
    
    async def handle_natural_language(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle natural language input for adding items"""
        text = update.message.text.lower()
        
        # Check if it's an add request
        add_triggers = ['add', 'buy', 'need', 'get', 'purchase']
        if any(trigger in text for trigger in add_triggers):
            # Extract items from natural language
            items = self._parse_items_from_text(text)
            
            if items:
                success_count = await self.add_items_to_list(update.effective_user.id, items)
                
                if success_count > 0:
                    items_text = ", ".join([item['name'] for item in items[:3]])
                    if len(items) > 3:
                        items_text += f" and {len(items) - 3} more"
                    
                    await update.message.reply_text(
                        f"✅ Added {success_count} items: {items_text}\n\n"
                        "Use /list to see your complete shopping list!"
                    )
                    return
        
        # If not recognized as shopping request, provide help
        await update.message.reply_text(
            "🤔 I didn't understand that. Try:\n"
            "• `/add milk, bread, eggs` - to add items\n"
            "• `/list` - to see your list\n"
            "• `/help` - for all commands"
        )
    
    def _parse_items_from_text(self, text: str) -> List[dict]:
        """Parse items from natural language text"""
        # Clean up text
        text = re.sub(r'\b(add|buy|need|get|purchase|to|the|some|and)\b', '', text, flags=re.IGNORECASE)
        text = re.sub(r'[^\w\s,.-]', '', text)
        
        # Split by common separators
        items = []
        parts = re.split(r'[,;]|\band\b', text)
        
        for part in parts:
            part = part.strip()
            if len(part) < 2:
                continue
            
            # Try to extract quantity and unit
            item_data = self._extract_quantity_and_item(part)
            if item_data:
                items.append(item_data)
        
        return items
    
    def _extract_quantity_and_item(self, text: str) -> dict:
        """Extract quantity, unit, and item name from text"""
        text = text.strip()
        
        for pattern in self.quantity_patterns:
            match = pattern.match(text)
            if match:
                groups = match.groups()
                if len(groups) == 3:  # quantity, unit, item
                    return {
                        'name': groups[2].strip().title(),
                        'quantity': float(groups[0]),
                        'unit': groups[1].lower()
                    }
                elif len(groups) == 2:  # quantity, item
                    return {
                        'name': groups[1].strip().title(),
                        'quantity': float(groups[0]),
                        'unit': 'piece'
                    }
        
        # No quantity found, treat as single item
        if text:
            return {
                'name': text.strip().title(),
                'quantity': 1.0,
                'unit': 'piece'
            }
        
        return None
    
    async def add_items_to_list(self, user_id: int, items: List[dict]) -> int:
        """Add items to user's shopping list"""
        try:
            with get_db() as db:
                user = db.query(User).filter(User.telegram_id == user_id).first()
                if not user:
                    return 0
                
                # Get or create active shopping list
                shopping_list = db.query(ShoppingList).filter(
                    ShoppingList.user_id == user.id,
                    ShoppingList.is_active == True
                ).first()
                
                if not shopping_list:
                    shopping_list = ShoppingList(user_id=user.id)
                    db.add(shopping_list)
                    db.commit()
                
                success_count = 0
                
                for item_data in items:
                    # Get or create product
                    product = db.query(Product).filter(
                        Product.name.ilike(f"%{item_data['name']}%")
                    ).first()
                    
                    if not product:
                        # Create new product with basic categorization
                        category = self._categorize_product(item_data['name'])
                        product = Product(
                            name=item_data['name'],
                            category=category,
                            unit=item_data.get('unit', 'piece')
                        )
                        db.add(product)
                        db.commit()
                    
                    # Check if item already exists in list
                    existing_item = db.query(ShoppingListItem).filter(
                        ShoppingListItem.shopping_list_id == shopping_list.id,
                        ShoppingListItem.product_id == product.id
                    ).first()
                    
                    if existing_item:
                        # Update quantity
                        existing_item.quantity += item_data.get('quantity', 1.0)
                    else:
                        # Create new item
                        list_item = ShoppingListItem(
                            shopping_list_id=shopping_list.id,
                            product_id=product.id,
                            quantity=item_data.get('quantity', 1.0),
                            unit=item_data.get('unit', 'piece')
                        )
                        db.add(list_item)
                    
                    success_count += 1
                
                db.commit()
                return success_count
                
        except Exception as e:
            logger.error(f"Error adding items to list: {e}")
            return 0
    
    def _categorize_product(self, product_name: str) -> str:
        """Basic product categorization"""
        name_lower = product_name.lower()
        
        categories = {
            'fruits': ['apple', 'banana', 'orange', 'grape', 'berry', 'lemon', 'lime'],
            'vegetables': ['carrot', 'potato', 'onion', 'tomato', 'lettuce', 'spinach'],
            'dairy': ['milk', 'cheese', 'yogurt', 'butter', 'cream', 'egg'],
            'meat': ['chicken', 'beef', 'pork', 'fish', 'turkey', 'lamb'],
            'bakery': ['bread', 'roll', 'bagel', 'croissant', 'muffin'],
            'beverages': ['juice', 'soda', 'water', 'coffee', 'tea', 'beer', 'wine'],
            'pantry': ['rice', 'pasta', 'flour', 'sugar', 'salt', 'oil', 'sauce']
        }
        
        for category, keywords in categories.items():
            if any(keyword in name_lower for keyword in keywords):
                return category
        
        return 'other'
