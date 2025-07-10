import logging
from telegram import Update
from telegram.ext import ContextTypes
from app.services.database import get_db
from app.models import ShoppingList, ShoppingListItem, Product
from app.config.settings import settings
from app.utils.validators import validate_item_name
from app.utils.helpers import parse_quantity
from app.services.i18n_service import i18n

logger = logging.getLogger(__name__)

async def add_to_shopping_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text(i18n.get_text("please_provide_item", update.effective_user.language_code))
        return
    
    item_input = " ".join(context.args)
    parsed = parse_quantity(item_input)
    item_name = re.sub(r'\d+\.?\d*\s*(kg|g|l|ml|oz|lb|pieces?|pcs?|x)', '', item_input).strip()
    
    if not validate_item_name(item_name):
        await update.message.reply_text(i18n.get_text("invalid_item_name", update.effective_user.language_code))
        return
    
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
            
            db.commit()
            
            if settings.enable_price_tracking:
                # TODO: Add logic to store price in a PriceHistory table
                pass
            
            await update.message.reply_text(
                i18n.get_text("item_added", update.effective_user.language_code).format(item=f"{item_name} ({parsed['quantity']} {parsed['unit']})")
            )
    
    except Exception as e:
        logger.error(f"Error adding item to shopping list: {e}")
        await update.message.reply_text(i18n.get_text("error_occurred", update.effective_user.language_code))

async def remove_from_shopping_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text(i18n.get_text("please_provide_item", update.effective_user.language_code))
        return
    
    item_name = " ".join(context.args)
    if not validate_item_name(item_name):
        await update.message.reply_text(i18n.get_text("invalid_item_name", update.effective_user.language_code))
        return
    
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
            
            product = db.query(Product).filter(Product.name.ilike(f"%{item_name}%")).first()
            if not product:
                await update.message.reply_text(i18n.get_text("item_not_found", update.effective_user.language_code))
                return
            
            shopping_list_item = db.query(ShoppingListItem).filter(
                ShoppingListItem.shopping_list_id == shopping_list.id,
                ShoppingListItem.product_id == product.id
            ).first()
            
            if shopping_list_item:
                db.delete(shopping_list_item)
                db.commit()
                await update.message.reply_text(
                    i18n.get_text("item_removed", update.effective_user.language_code).format(item=item_name)
                )
            else:
                await update.message.reply_text(i18n.get_text("item_not_in_list", update.effective_user.language_code))
    
    except Exception as e:
        logger.error(f"Error removing item from shopping list: {e}")
        await update.message.reply_text(i18n.get_text("error_occurred", update.effective_user.language_code))

async def show_shopping_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
            
            items = [f"{item.product.name} (x{item.quantity} {item.unit})" for item in shopping_list.items]
            if not items:
                await update.message.reply_text(i18n.get_text("empty_list", update.effective_user.language_code))
                return
            
            await update.message.reply_text(
                i18n.get_text("shopping_list_title", update.effective_user.language_code) + "\n" +
                "\n".join(items)
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
            db.commit()
            
            await update.message.reply_text(i18n.get_text("clear_list", update.effective_user.language_code))
    
    except Exception as e:
        logger.error(f"Error clearing shopping list: {e}")
        await update.message.reply_text(i18n.get_text("error_occurred", update.effective_user.language_code))