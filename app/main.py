import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import threading
import schedule
import time
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from app.handlers.shopping_handler import add_to_shopping_list, remove_from_shopping_list, show_shopping_list, clear_shopping_list
from app.handlers.settings_handler import set_currency, set_language, manage_stores, show_settings
from app.handlers.stats_handler import show_stats
from app.handlers.suggestion_handler import get_suggestions
from app.handlers.receipt_handler import process_receipt
from app.core.database import create_tables
from app.services.notification_service import NotificationService
from app.utils import i18n
from app import settings
import logging
from aiohttp import web

logger = logging.getLogger(__name__)
notification_service = NotificationService()

async def health_check(request):
    return web.Response(text="OK", status=200)

def run_scheduler():
    while True:
        schedule.run_pending()
        time.sleep(1)

def run_health_server():
    app = web.Application()
    app.add_routes([web.get('/health', health_check)])
    runner = web.AppRunner(app)
    loop = asyncio.get_event_loop()
    loop.run_until_complete(runner.setup())
    site = web.TCPSite(runner, '0.0.0.0', 8080)
    loop.run_until_complete(site.start())

def main():
    create_tables()
    
    application = Application.builder().token(settings.telegram_token).build()
    
    notification_service.set_application(application)
    
    if settings.enable_notifications:
        schedule.every().day.at("08:00").do(notification_service.send_daily_notifications)
    
    application.add_handler(CommandHandler("start", lambda update, context: update.message.reply_text(
        i18n.get_text("welcome_message", update.effective_user.language_code, name=update.effective_user.first_name) +
        "\n\n" + i18n.get_text("features_title", update.effective_user.language_code) +
        "\n" + i18n.get_text("feature_lists", update.effective_user.language_code) +
        "\n" + i18n.get_text("feature_receipts", update.effective_user.language_code) +
        "\n" + i18n.get_text("feature_ai", update.effective_user.language_code) +
        "\n" + i18n.get_text("feature_tracking", update.effective_user.language_code) +
        "\n" + i18n.get_text("feature_stores", update.effective_user.language_code) +
        "\n\n" + i18n.get_text("quick_start", update.effective_user.language_code) +
        "\n" + i18n.get_text("cmd_add", update.effective_user.language_code) +
        "\n" + i18n.get_text("cmd_list", update.effective_user.language_code) +
        "\n" + i18n.get_text("cmd_suggestions", update.effective_user.language_code) +
        "\n" + i18n.get_text("cmd_receipt", update.effective_user.language_code) +
        "\n" + i18n.get_text("cmd_stats", update.effective_user.language_code) +
        "\n" + i18n.get_text("ready_message", update.effective_user.language_code)
    )))
    application.add_handler(CommandHandler("help", lambda update, context: update.message.reply_text(
        "Commands:\n" +
        i18n.get_text("cmd_add", update.effective_user.language_code) + " - Add items (e.g., '/add milk 2L')\n" +
        i18n.get_text("cmd_list", update.effective_user.language_code) + " - View shopping list\n" +
        i18n.get_text("cmd_suggestions", update.effective_user.language_code) + " - Get AI recommendations\n" +
        i18n.get_text("cmd_receipt", update.effective_user.language_code) + " - Process receipt photo\n" +
        i18n.get_text("cmd_stats", update.effective_user.language_code) + " - View shopping analytics\n" +
        i18n.get_text("cmd_settings", update.effective_user.language_code) + " - Configure preferences\n" +
        i18n.get_text("cmd_currency", update.effective_user.language_code) + " - Set currency\n" +
        i18n.get_text("cmd_language", update.effective_user.language_code) + " - Set language\n" +
        i18n.get_text("cmd_stores", update.effective_user.language_code) + " - Manage favorite stores\n" +
        i18n.get_text("cmd_clear", update.effective_user.language_code) + " - Clear shopping list"
    )))
    application.add_handler(CommandHandler("add", add_to_shopping_list))
    application.add_handler(CommandHandler("remove", remove_from_shopping_list))
    application.add_handler(CommandHandler("list", show_shopping_list))
    application.add_handler(CommandHandler("clear", clear_shopping_list))
    application.add_handler(CommandHandler("currency", set_currency))
    application.add_handler(CommandHandler("language", set_language))
    application.add_handler(CommandHandler("stores", manage_stores))
    application.add_handler(CommandHandler("settings", show_settings))
    application.add_handler(CommandHandler("stats", show_stats))
    application.add_handler(CommandHandler("suggestions", get_suggestions))
    application.add_handler(CommandHandler("receipt", process_receipt))
    application.add_handler(MessageHandler(filters.PHOTO, process_receipt))
    
    scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
    scheduler_thread.start()
    
    health_thread = threading.Thread(target=run_health_server, daemon=True)
    health_thread.start()
    
    application.run_polling()

if __name__ == "__main__":
    import asyncio
    main()