import logging
from telegram import Update
from telegram.ext import ContextTypes
from app.services.database import get_db
from app.models import User
from app.services.i18n_service import i18n
from app.utils.validators import validate_item_name

logger = logging.getLogger(__name__)

async def show_settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        with get_db() as db:
            user = db.query(User).filter(User.telegram_id == update.effective_user.id).first()
            if not user:
                user = User(
                    telegram_id=update.effective_user.id,
                    username=update.effective_user.username,
                    first_name=update.effective_user.first_name,
                    last_name=update.effective_user.last_name
                )
                db.add(user)
                db.commit()
            
            settings_text = (
                i18n.get_text("settings", update.effective_user.language_code) + "\n" +
                f"Language: {user.language}\n" +
                f"Currency: {user.currency}\n" +
                f"AI Suggestions: {'Enabled' if user.ai_suggestions_enabled else 'Disabled'}\n" +
                f"Price Alerts: {'Enabled' if user.price_alerts_enabled else 'Disabled'}\n" +
                f"Favorite Stores: {', '.join(user.favorite_stores) if user.favorite_stores else 'None'}"
            )
            await update.message.reply_text(settings_text)
    
    except Exception as e:
        logger.error(f"Error showing settings: {e}")
        await update.message.reply_text(i18n.get_text("error_occurred", update.effective_user.language_code))

async def set_currency(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Please provide a currency code (e.g., USD, EUR, BRL).")
        return
    
    currency = context.args[0].upper()
    supported_currencies = ["USD", "EUR", "GBP", "BRL"]
    if currency not in supported_currencies:
        await update.message.reply_text(f"Unsupported currency. Supported: {', '.join(supported_currencies)}")
        return
    
    try:
        with get_db() as db:
            user = db.query(User).filter(User.telegram_id == update.effective_user.id).first()
            if not user:
                user = User(
                    telegram_id=update.effective_user.id,
                    username=update.effective_user.username,
                    first_name=update.effective_user.first_name,
                    last_name=update.effective_user.last_name
                )
                db.add(user)
            
            user.currency = currency
            db.commit()
            
            await update.message.reply_text(f"Currency updated to {currency}!")
    
    except Exception as e:
        logger.error(f"Error setting currency: {e}")
        await update.message.reply_text(i18n.get_text("error_occurred", update.effective_user.language_code))

async def set_language(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text(i18n.get_text("language_select", update.effective_user.language_code))
        return
    
    language = context.args[0].lower()
    if language not in ["en", "pt_br"]:
        await update.message.reply_text(i18n.get_text("language_select", update.effective_user.language_code))
        return
    
    try:
        with get_db() as db:
            user = db.query(User).filter(User.telegram_id == update.effective_user.id).first()
            if not user:
                user = User(
                    telegram_id=update.effective_user.id,
                    username=update.effective_user.username,
                    first_name=update.effective_user.first_name,
                    last_name=update.effective_user.last_name
                )
                db.add(user)
            
            user.language = language
            db.commit()
            
            await update.message.reply_text(
                i18n.get_text("language_updated", language, language=language.upper())
            )
    
    except Exception as e:
        logger.error(f"Error setting language: {e}")
        await update.message.reply_text(i18n.get_text("error_occurred", update.effective_user.language_code))

async def manage_stores(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /stores add <store_name> or /stores remove <store_name>")
        return
    
    action = context.args[0].lower()
    if action not in ["add", "remove"]:
        await update.message.reply_text("Invalid action. Use 'add' or 'remove'.")
        return
    
    store_name = " ".join(context.args[1:])
    if not validate_item_name(store_name):
        await update.message.reply_text("Invalid store name.")
        return
    
    try:
        with get_db() as db:
            user = db.query(User).filter(User.telegram_id == update.effective_user.id).first()
            if not user:
                user = User(
                    telegram_id=update.effective_user.id,
                    username=update.effective_user.username,
                    first_name=update.effective_user.first_name,
                    last_name=update.effective_user.last_name
                )
                db.add(user)
            
            stores = user.favorite_stores or []
            if action == "add":
                if store_name not in stores:
                    stores.append(store_name)
                    user.favorite_stores = stores
                    db.commit()
                    await update.message.reply_text(f"Added {store_name} to favorite stores.")
                else:
                    await update.message.reply_text(f"{store_name} is already in favorite stores.")
            else:
                if store_name in stores:
                    stores.remove(store_name)
                    user.favorite_stores = stores
                    db.commit()
                    await update.message.reply_text(f"Removed {store_name} from favorite stores.")
                else:
                    await update.message.reply_text(f"{store_name} not found in favorite stores.")
    
    except Exception as e:
        logger.error(f"Error managing stores: {e}")
        await update.message.reply_text(i18n.get_text("error_occurred", update.effective_user.language_code))