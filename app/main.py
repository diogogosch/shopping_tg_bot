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
)
from app.handlers.suggestion_handler import get_suggestions
from app.services.database import get_db
from app.services.cache import Cache
from app.services.ai_service import AIService
from app.services.notification_service import NotificationService
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
    
    # Test database connection
    try:
        with get_db() as db:
            db.execute("SELECT 1")
        status["components"]["database"] = "healthy"
    except Exception as e:
        status["status"] = "unhealthy"
        status["components"]["database"] = f"error: {str(e)}"
    
    # Test Redis connection
    try:
        if cache.redis_client:
            cache.redis_client.ping()
        status["components"]["redis"] = "healthy"
    except Exception as e:
        status["status"] = "unhealthy"
        status["components"]["redis"] = f"error: {str(e)}"
    
    # Test AI connection if enabled
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
    
    # Register handlers
    application.add_handler(CommandHandler("start", lambda update, context: update.message.reply_text(
        f"Welcome to {settings.bot_username}! Use /help to see available commands."
    )))
    application.add_handler(CommandHandler("help", lambda update, context: update.message.reply_text(
        "Commands:\n/receipt - Upload a receipt photo\n/add <item> - Add item to shopping list\n/remove <item> - Remove item\n/list - Show shopping list\n/suggestions - Get AI suggestions"
    )))
    application.add_handler(MessageHandler(filters.PHOTO, process_receipt))
    application.add_handler(CommandHandler("add", add_to_shopping_list))
    application.add_handler(CommandHandler("remove", remove_from_shopping_list))
    application.add_handler(CommandHandler("list", show_shopping_list))
    application.add_handler(CommandHandler("suggestions", get_suggestions))
    
    # Schedule notifications
    if settings.enable_notifications:
        schedule.every().day.at("08:00").do(notification_service.send_daily_notifications)
        threading.Thread(target=run_scheduler, daemon=True).start()
        logger.info("Notification scheduler started")
    
    # Start FastAPI for health checks
    import uvicorn
    threading.Thread(target=lambda: uvicorn.run(app, host="0.0.0.0", port=8080), daemon=True).start()
    
    # Run bot
    logger.info("Starting SmartShopBot")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()