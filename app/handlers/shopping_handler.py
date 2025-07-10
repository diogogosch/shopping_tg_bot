import re
from datetime import datetime
from telegram import Update
from telegram.ext import ContextTypes
from app.database import get_db
from app.models import ShoppingList, ShoppingListItem, Product, PriceHistory
from app.utils import i18n
from app import settings
import logging

logger = logging.getLogger(__name__)

async def add_to_shopping_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.text:
        await update.message.reply_text(i18n.get_text("no_text", update.effective_user.language_code))
        return
    
    text = update.message.text.replace("/add", "").strip()
    parsed = parse_item(text)
    if not parsed:
        await update.message.reply_text(i18n.get_text("invalid_format", update.effective_user.language_code))
        return
    
    item_name = parsed["name"]
    try:
        with get_db() as db:
            user_id = update.effective_user.id
            shopping_list = db.query(ShoppingList).filter(
                ShoppingList.user_id == user_id,
                ShoppingList.is_active == True
            ).first()
            
            if not shopping_list:
                shopping_list = ShoppingList(user_id=user_id, is_active=True)
                db.add(shopping_list)
                db.commit()
            
            product = db.query(Product).filter(Product.name.ilike(f"%{item_name}%")).first()
            if not product:
                product = Product(name=item_name, category="unknown")
                db.add(product)
                db.commit()
            
            existing_item = db.query(ShoppingListItem).filter(
                ShoppingListItem.shopping_list_id == shopping_list.id,
                ShoppingListItem.product_id == product.id
            ).first()
            
            if existing_item:
                existing_item.quantity += parsed["quantity"]
                existing_item.unit = parsed["unit"]
            else:
                shopping_list_item = ShoppingListItem(
                    shopping_list_id=shopping_list.id,
                    product_id=product.id,
                    quantity=parsed["quantity"],
                    unit=parsed["unit"]
                )
                db.add(shopping_list_item)
            
            if settings.enable_price_tracking and product.last_price:
                price_history = PriceHistory(
                    product_id=product.id,
                    price=product.last_price,
                    currency=context.user_data.get('currency', 'USD')
                )
                db.add(price_history)
            
            db.commit()
            
            await update.message.reply_text(
                i18n.get_text("item_added", update.effective_user.language_code).format(item=f"{item_name} ({parsed['quantity']} {parsed['unit']})")
            )
    
    except Exception as e:
        logger.error(f"Error adding item to shopping list: {e}")
        await update.message.reply_text(i18n.get_text("error_occurred", update.effective_user.language_code))

async def remove_from_shopping_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.replace("/remove", "").strip()
    try:
        with get_db() as db:
            user_id = update.effective_user.id
            shopping_list = db.query(ShoppingList).filter(
                ShoppingList.user_id == user_id,
                ShoppingList.is_active == True
            ).first()
            
            if not shopping_list:
                await update.message.reply_text(i18n.get_text("no_active_list", update.effective_user.language_code))
                return
            
            item = db.query(ShoppingListItem).join(Product).filter(
                ShoppingListItem.shopping_list_id == shopping_list.id,
                Product.name.ilike(f"%{text}%")
            ).first()
            
            if item:
                db.delete(item)
                db.commit()
                await update.message.reply_text(
                    i18n.get_text("item_removed", update.effective_user.language_code).format(item=text)
                )
            else:
                await update.message.reply_text(i18n.get_text("item_not_found", update.effective_user.language_code))
    
    except Exception as e:
        logger.error(f"Error removing item: {e}")
        await update.message.reply_text(i18n.get_text("error_occurred", update.effective_user.language_code))

async def show_shopping_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        with get_db() as db:
            user_id = update.effective_user.id
            shopping_list = db.query(ShoppingList).filter(
                ShoppingList.user_id == user_id,
                ShoppingList.is_active == True
            ).first()
            
            if not shopping_list or not shopping_list.items:
                await update.message.reply_text(i18n.get_text("empty_list", update.effective_user.language_code))
                return
            
            items_text = "\n".join(
                f"- {item.product.name} ({item.quantity} {item.unit or 'unit'})"
                for item in shopping_list.items
            )
            await update.message.reply_text(
                i18n.get_text("current_list", update.effective_user.language_code) + "\n" + items_text
            )
    
    except Exception as e:
        logger.error(f"Error showing shopping list: {e}")
        await update.message.reply_text(i18n.get_text("error_occurred", update.effective_user.language_code))

async def clear_shopping_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        with get_db() as db:
            user_id = update.effective_user.id
            shopping_list = db.query(ShoppingList).filter(
                ShoppingList.user_id == user_id,
                ShoppingList.is_active == True
            ).first()
            
            if not shopping_list:
                await update.message.reply_text(i18n.get_text("no_active_list", update.effective_user.language_code))
                return
            
            db.query(ShoppingListItem).filter(
                ShoppingListItem.shopping_list_id == shopping_list.id
            ).delete()
            shopping_list.is_active = False
            db.commit()
            
            await update.message.reply_text(i18n.get_text("list_cleared", update.effective_user.language_code))
    
    except Exception as e:
        logger.error(f"Error clearing shopping list: {e}")
        await update.message.reply_text(i18n.get_text("error_occurred", update.effective_user.language_code))

def parse_item(text: str) -> dict:
    pattern = r"^(.*?)\s*(\d+\.?\d*)\s*(kg|g|l|ml|unit)?$"
    match = re.match(pattern, text.strip(), re.IGNORECASE)
    if not match:
        return None
    
    name, quantity, unit = match.groups()
    return {
        "name": name.strip(),
        "quantity": float(quantity),
        "unit": unit if unit else "unit"
    }