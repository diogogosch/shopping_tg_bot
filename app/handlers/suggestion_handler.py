import logging
from telegram import Update
from telegram.ext import ContextTypes
from app.services.ai_service import AIService
from app.services.database import get_db
from app.models import ShoppingList
from app.services.i18n_service import i18n
from app.config.settings import settings

logger = logging.getLogger(__name__)

ai_service = AIService()

async def get_suggestions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not settings.enable_ai_suggestions or settings.ai_provider == "none":
        await update.message.reply_text(i18n.get_text("ai_disabled", update.effective_user.language_code))
        return
    
    try:
        with get_db() as db:
            user_id = update.effective_user.id
            shopping_list = db.query(ShoppingList).filter(
                ShoppingList.user_id == user_id,
                ShoppingList.is_active == True
            ).first()
            
            items = []
            if shopping_list:
                items = [item.product.name for item in shopping_list.items]
            
            if not items:
                await update.message.reply_text(i18n.get_text("no_suggestions_data", update.effective_user.language_code))
                return
            
            suggestions = await ai_service.generate_suggestions(items)
            if suggestions:
                await update.message.reply_text(
                    i18n.get_text("ai_suggestions_title", update.effective_user.language_code, provider="") +
                    "\n" + ", ".join(suggestions)
                )
            else:
                await update.message.reply_text(i18n.get_text("no_suggestions_data", update.effective_user.language_code))
    
    except Exception as e:
        logger.error(f"Error getting suggestions: {e}")
        await update.message.reply_text(i18n.get_text("error_occurred", update.effective_user.language_code))