import logging
from telegram import Update
from telegram.ext import ContextTypes
from app.services.database import get_db
from app.models import ShoppingList, ShoppingListItem, Product
from app.config.settings import settings
from app.utils.validators import validate_item_name

logger = logging.getLogger(__name__)

async def add_to_shopping_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text(get_text("please_provide_item", update.effective_user.language_code))
        return
    
    item_name = " ".join(context.args)
    if not validate_item_name(item_name):
        await update.message.reply_text(get_text("invalid_item_name", update.effective_user.language_code))
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
            
            # Check for existing item
            existing_item = db.query(ShoppingListItem).filter(
                ShoppingListItem.shopping_list_id == shopping_list.id,
                ShoppingListItem.product_id == product.id
            ).first()
            
            if existing_item:
                existing_item.quantity += 1
            else:
                shopping_list_item = ShoppingListItem(
                    shopping_list_id=shopping_list.id,
                    product_id=product.id,
                    quantity=1
                )
                db.add(shopping_list_item)
            
            db.commit()
            
            # Store price history (placeholder)
            if settings.enable_price_tracking:
                # Add logic to store price in a PriceHistory table
                pass
            
            await update.message.reply_text(
                get_text("item_added", update.effective_user.language_code).format(item_name=item_name)
            )
    
    except Exception as e:
        logger.error(f"Error adding item to shopping list: {e}")
        await update.message.reply_text(get_text("error_occurred", update.effective_user.language_code))

async def remove_from_shopping_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text(get_text("please_provide_item", update.effective_user.language_code))
        return
    
    item_name = " ".join(context.args)
    if not validate_item_name(item_name):
        await update.message.reply_text(get_text("invalid_item_name", update.effective_user.language_code))
        return
    
    try:
        with get_db() as db:
            user_id = update.effective_user.id
            shopping_list = db.query(ShoppingList).filter(
                ShoppingList.user_id == user_id,
                ShoppingList.is_active == True
            ).first()
            
            if not shopping_list:
                await update.message.reply_text(get_text("no_active_list", update.effective_user.language_code))
                return
            
            product = db.query(Product).filter(Product.name.ilike(f"%{item_name}%")).first()
            if not product:
                await update.message.reply_text(get_text("item_not_found", update.effective_user.language_code))
                return
            
            shopping_list_item = db.query(ShoppingListItem).filter(
                ShoppingListItem.shopping_list_id == shopping_list.id,
                ShoppingListItem.product_id == product.id
            ).first()
            
            if shopping_list_item:
                db.delete(shopping_list_item)
                db.commit()
                await update.message.reply_text(
                    get_text("item_removed", update.effective_user.language_code).format(item_name=item_name)
                )
            else:
                await update.message.reply_text(get_text("item_not_in_list", update.effective_user.language_code))
    
    except Exception as e:
        logger.error(f"Error removing item from shopping list: {e}")
        await update.message.reply_text(get_text("error_occurred", update.effective_user.language_code))

async def show_shopping_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        with get_db() as db:
            user_id = update.effective_user.id
            shopping_list = db.query(ShoppingList).filter(
                ShoppingList.user_id == user_id,
                ShoppingList.is_active == True
            ).first()
            
            if not shopping_list:
                await update.message.reply_text(get_text("no_active_list", update.effective_user.language_code))
                return
            
            items = [f"{item.product.name} (x{item.quantity})" for item in shopping_list.items]
            if not items:
                await update.message.reply_text(get_text("empty_list", update.effective_user.language_code))
                return
            
            await update.message.reply_text(
                get_text("shopping_list", update.effective_user.language_code).format(items="\n".join(items))
            )
    
    except Exception as e:
        logger.error(f"Error showing shopping list: {e}")
        await update.message.reply_text(get_text("error_occurred", update.effective_user.language_code))

def get_text(key: str, language_code: str) -> str:
    translations = {
        "en": {
            "please_provide_item": "Please provide an item name.",
            "invalid_item_name": "Invalid item name. Please use alphanumeric characters.",
            "item_added": "Added {} to your shopping list.",
            "item_removed": "Removed {} from your shopping list.",
            "item_not_found": "Item not found.",
            "item_not_in_list": "Item not in your shopping list.",
            "no_active_list": "No active shopping list found. Add items to create one.",
            "empty_list": "Your shopping list is empty.",
            "shopping_list": "Your shopping list:\n{}",
            "error_occurred": "An error occurred. Please try again.",
        },
        "pt_BR": {
            "please_provide_item": "Por favor, forneça o nome do item.",
            "invalid_item_name": "Nome do item inválido. Use caracteres alfanuméricos.",
            "item_added": "{} adicionado à sua lista de compras.",
            "item_removed": "{} removido da sua lista de compras.",
            "item_not_found": "Item não encontrado.",
            "item_not_in_list": "Item não está na sua lista de compras.",
            "no_active_list": "Nenhuma lista de compras ativa encontrada. Adicione itens para criar uma.",
            "empty_list": "Sua lista de compras está vazia.",
            "shopping_list": "Sua lista de compras:\n{}",
            "error_occurred": "Ocorreu um erro. Tente novamente.",
        }
    }
    return translations.get(language_code, translations["en"]).get(key, translations["en"][key])