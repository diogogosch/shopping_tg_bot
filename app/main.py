import logging
import json
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)
from app.handlers.receipt_handler import process_receipt
from app.handlers.shopping_handler import (
    add_to_shopping_list,
    remove_from_shopping_list,
    show_shopping_list,
    clear_shopping_list,
)
from app.handlers.settings_handler import (
    set_currency,
    set_language,
    manage_stores,
    show_settings,
)
from app.handlers.stats_handler import show_stats
from app.handlers.suggestion_handler import get_suggestions
from app.services.database import get_db
from app.services.cache import Cache
from app.services.ai_service import AIService
from app.services.notification_service import NotificationService
from app.services.i18n_service import i18n
from app.config.settings import settings
import schedule
import time
import threading

# Configure structured logging
logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI()
cache = Cache()
ai_service = AIService()
notification_service = NotificationService()

def create_tables():
    from app.models import Base
    from sqlalchemy import create_engine
    engine = create_engine(settings.database_url)
    Base.metadata.create_all(engine)
    logger.info("Database tables created successfully")

@app.get("/health")
async def health_check():
    status = {"status": "healthy", "components": {}}
    
    try:
        with get_db() as db:
            db.execute("SELECT 1")
        status["components"]["database"] = "healthy"
    except Exception as e:
        status["status"] = "unhealthy"
        status["components"]["database"] = f"error: {str(e)}"
    
    try:
        if cache.redis_client:
            cache.redis_client.ping()
        status["components"]["redis"] = "healthy"
    except Exception as e:
        status["status"] = "unhealthy"
        status["components"]["redis"] = f"error: {str(e)}"
    
    if settings.enable_ai_suggestions and settings.ai_provider != "none":
        try:
            ai_service.test_connection()
            status["components"]["ai"] = "healthy"
        except Exception as e:
            status["status"] = "unhealthy"
            status["components"]["ai"] = f"error: {str(e)}"
    
    if status["status"] == "unhealthy":
        return JSONResponse(status, status_code=500)
    return JSONResponse(status)

def run_scheduler():
    while True:
        schedule.run_pending()
        time.sleep(60)

def main():
    create_tables()
    
    application = Application.builder().token(settings.telegram_token).build()
    
    # Set notification service application
    notification_service.set_application(application)
    
    # Register handlers
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
        i18n.get_text("cmd_add", update.effective_user.language_code) + " - Add items (e.g., '/add milk 2L