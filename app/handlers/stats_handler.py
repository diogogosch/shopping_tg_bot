from telegram import Update
from telegram.ext import ContextTypes
from app.database import get_db
from app.models import Receipt, User
from app.utils import i18n, format_currency
import logging

logger = logging.getLogger(__name__)

async def show_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        with get_db() as db:
            user_id = update.effective_user.id
            user = db.query(User).filter(User.telegram_id == user_id).first()
            currency = user.currency if user else 'USD'
            receipts = db.query(Receipt).filter(Receipt.user_id == user_id).all()
            
            if not receipts:
                await update.message.reply_text("No purchase history available.")
                return
            
            total_spent = sum(receipt.total_amount for receipt in receipts if receipt.total_amount)
            receipt_count = len(receipts)
            avg_spend = total_spent / receipt_count if receipt_count else 0
            
            category_spending = {}
            for receipt in receipts:
                for item in receipt.items:
                    product = item.product
                    if product and product.category:
                        category_spending[product.category] = category_spending.get(product.category, 0) + item.total_price
            
            stats_text = (
                "📊 Shopping Analytics\n" +
                f"Total Receipts: {receipt_count}\n" +
                f"Total Spent: {format_currency(total_spent, currency)}\n" +
                f"Average Spend per Receipt: {format_currency(avg_spend, currency)}\n" +
                "\nCategory Breakdown:\n" +
                "\n".join(f"{cat}: {format_currency(amount, currency)}" 
                          for cat, amount in category_spending.items())
            )
            
            await update.message.reply_text(stats_text)
    
    except Exception as e:
        logger.error(f"Error showing stats: {e}")
        await update.message.reply_text(i18n.get_text("error_occurred", update.effective_user.language_code))