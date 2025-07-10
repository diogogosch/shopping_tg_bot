import logging
from telegram import Update
from telegram.ext import ContextTypes
from app.services.database import get_db
from app.models import Receipt, ReceiptItem
from app.services.i18n_service import i18n
from app.utils.helpers import format_currency

logger = logging.getLogger(__name__)

async def show_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        with get_db() as db:
            user_id = update.effective_user.id
            receipts = db.query(Receipt).filter(Receipt.user_id == user_id).all()
            
            if not receipts:
                await update.message.reply_text("No purchase history available.")
                return
            
            total_spent = sum(receipt.total_amount for receipt in receipts if receipt.total_amount)
            receipt_count = len(receipts)
            avg_spend = total_spent / receipt_count if receipt_count else 0
            
            # Category breakdown (simplified)
            category_spending = {}
            for receipt in receipts:
                for item in receipt.items:
                    product = item.product
                    if product and product.category:
                        category_spending[product.category] = category_spending.get(product.category, 0) + item.total_price
            
            stats_text = (
                "📊 Shopping Analytics\n" +
                f"Total Receipts: {receipt_count}\n" +
                f"Total Spent: {format_currency(total_spent, context.user_data.get('currency', 'USD'))}\n" +
                f"Average Spend per Receipt: {format_currency(avg_spend, context.user_data.get('currency', 'USD'))}\n" +
                "\nCategory Breakdown:\n" +
                "\n".join(f"{cat}: {format_currency(amount, context.user_data.get('currency', 'USD'))}" 
                          for cat, amount in category_spending.items())
            )
            
            await update.message.reply_text(stats_text)
    
    except Exception as e:
        logger.error(f"Error showing stats: {e}")
        await update.message.reply_text(i18n.get_text("error_occurred", update.effective_user.language_code))