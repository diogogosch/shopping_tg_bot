import logging
from telegram.ext import Application
from app.services.database import get_db
from app.models import ShoppingList

logger = logging.getLogger(__name__)

class NotificationService:
    def __init__(self):
        self.application = None
    
    def set_application(self, application: Application):
        self.application = application
    
    async def send_notification(self, chat_id: int, message: str):
        if self.application:
            await self.application.bot.send_message(chat_id=chat_id, text=message)
            logger.info(f"Notification sent to chat_id {chat_id}: {message}")
        else:
            logger.error("Application not set for NotificationService")
    
    def send_daily_notifications(self):
        with get_db() as db:
            active_lists = db.query(ShoppingList).filter(ShoppingList.is_active == True).all()
            for shopping_list in active_lists:
                user_id = shopping_list.user_id
                items = [item.product.name for item in shopping_list.items]
                if items:
                    message = f"Reminder: Your active shopping list contains: {', '.join(items)}"
                    if self.application:
                        self.application.create_task(self.send_notification(user_id, message))
                    else:
                        logger.error("Cannot send notification: Application not set")