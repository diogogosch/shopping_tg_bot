import os
from datetime import datetime
from telegram import Update
from telegram.ext import ContextTypes
from telegram.error import TelegramError
from app.core.database import get_db
from app.models import Receipt, ReceiptItem, Product
from app.services import ocr_service, ai_service
from app.utils import i18n
from app import settings
import logging
from contextlib import contextmanager

logger = logging.getLogger(__name__)

@contextmanager
def temp_file_manager(file_id: str):
    file_path = f"temp/{file_id}.jpg"
    os.makedirs("temp", exist_ok=True)
    try:
        yield file_path
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)

async def process_receipt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.photo:
        await update.message.reply_text(i18n.get_text("cmd_receipt", update.effective_user.language_code))
        return
    
    photo = update.message.photo[-1]
    file = await photo.get_file()
    
    with temp_file_manager(photo.file_id) as file_path:
        try:
            await file.download(file_path)
        except TelegramError as te:
            logger.error(f"Failed to download photo: {te}")
            await update.message.reply_text("Failed to download receipt image. Please try again.")
            return
        
        with open(file_path, "rb") as image_file:
            image_data = image_file.read()
        receipt_data = ocr_service.extract_text_from_receipt(image_data)
        
        if not receipt_data["items"]:
            await update.message.reply_text(i18n.get_text("no_suggestions_data", update.effective_user.language_code))
            return
        
        with get_db() as db:
            receipt = Receipt(
                user_id=update.effective_user.id,
                purchase_date=datetime.now() if not receipt_data["date"] else receipt_data["date"],
                store_name=receipt_data["store_name"],
                total_amount=receipt_data["total"] or 0.0,
                ocr_confidence=receipt_data["confidence"],
                raw_text=receipt_data["raw_text"],
                processing_status="completed"
            )
            db.add(receipt)
            db.commit()
            
            for item in receipt_data["items"]:
                product = db.query(Product).filter(Product.name.ilike(f"%{item['name']}%")).first()
                if not product:
                    product = Product(name=item["name"], category="unknown", last_price=item["unit_price"])
                    db.add(product)
                    db.commit()
                
                receipt_item = ReceiptItem(
                    receipt_id=receipt.id,
                    product_id=product.id,
                    item_name=item["name"],
                    quantity=item["quantity"],
                    unit_price=item["unit_price"],
                    total_price=item["total_price"],
                    confidence_score=item.get("confidence", receipt_data["confidence"])
                )
                db.add(receipt_item)
            
            db.commit()
        
        await update.message.reply_text(
            i18n.get_text("item_added", update.effective_user.language_code).format(item=f"{len(receipt_data['items'])} items")
        )
        
        if settings.enable_ai_suggestions:
            suggestions = await ai_service.generate_suggestions([item["name"] for item in receipt_data["items"]])
            if suggestions:
                await update.message.reply_text(
                    i18n.get_text("ai_suggestions_title", update.effective_user.language_code, provider="") +
                    "\n" + ", ".join(suggestions)
                )
    
    except Exception as e:
        logger.error(f"Error processing receipt: {e}")
        await update.message.reply_text(i18n.get_text("error_occurred", update.effective_user.language_code))