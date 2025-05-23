import logging
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from telegram.constants import ParseMode
import traceback

from app.config.settings import settings
from app.core.database import create_tables, get_db
from app.handlers.shopping_handler import ShoppingHandler
from app.handlers.receipt_handler import ReceiptHandler
from app.services.ai_service import ai_service
from app.services.i18n_service import i18n
from app.models.user import User

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=getattr(logging, settings.log_level.upper())
)
logger = logging.getLogger(__name__)

class SmartShopBot:
    def __init__(self):
        self.shopping_handler = ShoppingHandler()
        self.receipt_handler = ReceiptHandler()
    
    def get_user_language(self, user_id: int) -> str:
        """Get user's preferred language from database"""
        try:
            with get_db() as db:
                user = db.query(User).filter(User.telegram_id == user_id).first()
                if user and user.language:
                    return user.language
        except Exception as e:
            logger.error(f"Error getting user language: {e}")
        return settings.default_language
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Enhanced start command with user onboarding and i18n"""
        user = update.effective_user
        user_lang = self.get_user_language(user.id)
        
        # Create or update user in database
        with get_db() as db:
            db_user = db.query(User).filter(User.telegram_id == user.id).first()
            if not db_user:
                db_user = User(
                    telegram_id=user.id,
                    username=user.username,
                    first_name=user.first_name,
                    last_name=user.last_name,
                    language=user_lang
                )
                db.add(db_user)
                db.commit()
                is_new_user = True
            else:
                is_new_user = False
        
        # Get AI provider info
        ai_info = ai_service.get_provider_info()
        ai_status = i18n.get_text("ai_enabled", user_lang) if ai_info["enabled"] else i18n.get_text("ai_disabled", user_lang)
        ai_provider = f" ({ai_info['provider'].upper()})" if ai_info["enabled"] else ""
        
        # Welcome message with translations
        welcome_text = f"""
{i18n.get_text('welcome_title', user_lang)}

{i18n.get_text('welcome_message', user_lang, name=user.first_name)}

*{i18n.get_text('features_title', user_lang)}*
• {i18n.get_text('feature_lists', user_lang)}
• {i18n.get_text('feature_receipts', user_lang)}
• {i18n.get_text('feature_ai', user_lang)}
• {i18n.get_text('feature_tracking', user_lang)}
• {i18n.get_text('feature_stores', user_lang)}

*{i18n.get_text('current_status', user_lang)}*
{ai_status}{ai_provider}

*{i18n.get_text('quick_start', user_lang)}*
{i18n.get_text('cmd_add', user_lang)}
{i18n.get_text('cmd_list', user_lang)}
{i18n.get_text('cmd_suggestions', user_lang)}
{i18n.get_text('cmd_receipt', user_lang)}
{i18n.get_text('cmd_stats', user_lang)}

{i18n.get_text('ready_message', user_lang)}
        """
        
        # Create inline keyboard with translations
        keyboard = [
            [InlineKeyboardButton(i18n.get_text("add_items", user_lang), callback_data="add_items")],
            [InlineKeyboardButton(i18n.get_text("get_suggestions", user_lang), callback_data="get_suggestions")],
            [InlineKeyboardButton(i18n.get_text("settings", user_lang), callback_data="settings")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            welcome_text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=reply_markup
        )
        
        if is_new_user:
            # Send onboarding tips
            await asyncio.sleep(2)
            await update.message.reply_text(
                i18n.get_text("pro_tip", user_lang)
            )
    
    async def language_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle language selection"""
        user_id = update.effective_user.id
        user_lang = self.get_user_language(user_id)
        
        keyboard = [
            [InlineKeyboardButton(i18n.get_text("english", user_lang), callback_data="lang:en")],
            [InlineKeyboardButton(i18n.get_text("portuguese", user_lang), callback_data="lang:pt_BR")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            i18n.get_text("language_select", user_lang),
            reply_markup=reply_markup
        )
    
    async def suggestions_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Get AI-powered shopping suggestions with i18n"""
        user_id = update.effective_user.id
        user_lang = self.get_user_language(user_id)
        
        # Show typing indicator
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
        
        try:
            with get_db() as db:
                suggestions = ai_service.generate_smart_suggestions(user_id, db)
            
            if not suggestions:
                await update.message.reply_text(
                    i18n.get_text("no_suggestions_data", user_lang)
                )
                return
            
            # Format suggestions with provider info
            ai_info = ai_service.get_provider_info()
            provider_text = f" (powered by {ai_info['provider'].upper()})" if ai_info['enabled'] else ""
            
            text = f"{i18n.get_text('ai_suggestions_title', user_lang, provider=provider_text)}\n\n"
            keyboard = []
            
            for i, suggestion in enumerate(suggestions[:8]):
                priority_emoji = "🔴" if suggestion['priority'] == 3 else "🟡" if suggestion['priority'] == 2 else "🟢"
                provider_emoji = "🤖" if suggestion.get('ai_provider') in ['openai', 'gemini'] else "📊"
                
                text += f"{priority_emoji} {provider_emoji} *{suggestion['item']}*\n"
                text += f"   _{suggestion['reason']}_\n\n"
                
                # Add quick-add button
                keyboard.append([InlineKeyboardButton(
                    f"➕ {suggestion['item']}", 
                    callback_data=f"quick_add:{suggestion['item']}"
                )])
            
            keyboard.append([InlineKeyboardButton(i18n.get_text("add_all", user_lang), callback_data="add_all_suggestions")])
            keyboard.append([InlineKeyboardButton(i18n.get_text("refresh", user_lang), callback_data="refresh_suggestions")])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                text,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=reply_markup
            )
            
        except Exception as e:
            logger.error(f"Error generating suggestions: {e}")
            await update.message.reply_text(
                "❌ Sorry, I couldn't generate suggestions right now. Please try again later."
            )
    
    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle inline button callbacks with i18n"""
        query = update.callback_query
        await query.answer()
        
        data = query.data
        user_id = update.effective_user.id
        user_lang = self.get_user_language(user_id)
        
        if data.startswith("lang:"):
            new_lang = data.split(":", 1)[1]
            
            # Update user language in database
            with get_db() as db:
                user = db.query(User).filter(User.telegram_id == user_id).first()
                if user:
                    user.language = new_lang
                    db.commit()
            
            lang_name = "English" if new_lang == "en" else "Português (Brasil)"
            await query.edit_message_text(
                i18n.get_text("language_updated", new_lang, language=lang_name)
            )
            
        elif data == "get_suggestions":
            await self.suggestions_command(update, context)
        
        elif data.startswith("quick_add:"):
            item_name = data.split(":", 1)[1]
            success = await self.shopping_handler.add_items_to_list(
                user_id, 
                [{'name': item_name, 'quantity': 1.0, 'unit': 'piece'}]
            )
            if success:
                await query.edit_message_text(
                    i18n.get_text("item_added", user_lang, item=item_name)
                )
            else:
                await query.edit_message_text(
                    i18n.get_text("item_add_failed", user_lang, item=item_name)
                )
        
        # Add other callback handlers...
    
    async def error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle errors gracefully"""
        logger.error(f"Exception while handling an update: {context.error}")
        logger.error(f"Update: {update}")
        logger.error(traceback.format_exc())
        
        if update and update.effective_message:
            await update.effective_message.reply_text(
                "❌ Oops! Something went wrong. Please try again or contact support if the issue persists."
            )

def main():
    """Main function to run the bot"""
    # Create database tables
    create_tables()
    
    # Create application
    application = Application.builder().token(settings.telegram_token).build()
    
    # Initialize bot
    bot = SmartShopBot()
    
    # Add handlers
    application.add_handler(CommandHandler("start", bot.start_command))
    application.add_handler(CommandHandler("language", bot.language_command))
    application.add_handler(CommandHandler("idioma", bot.language_command))  # Portuguese alias
    application.add_handler(CommandHandler("suggestions", bot.suggestions_command))
    
    # Add shopping handlers
    application.add_handler(CommandHandler("add", bot.shopping_handler.add_command))
    application.add_handler(CommandHandler("adicionar", bot.shopping_handler.add_command))  # Portuguese alias
    application.add_handler(CommandHandler("list", bot.shopping_handler.list_command))
    application.add_handler(CommandHandler("lista", bot.shopping_handler.list_command))  # Portuguese alias
    
    # Add receipt handler
    application.add_handler(MessageHandler(filters.PHOTO, bot.receipt_handler.handle_photo))
    
    # Add callback query handler
    application.add_handler(CallbackQueryHandler(bot.button_callback))
    
    # Add error handler
    application.add_error_handler(bot.error_handler)
    
    # Add message handler for natural language
    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND, 
        bot.shopping_handler.handle_natural_language
    ))
    
    logger.info(f"Starting SmartShopBot with AI provider: {ai_service.provider}")
    
    # Run the bot
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
