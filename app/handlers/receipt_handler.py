import logging
from telegram import Update
from telegram.ext import ContextTypes
from app.services.ocr_service import OCRService
from app.services.ai_service import AIService
from app.services.database import get_db
from app.models import Receipt, ReceiptItem, Product
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)

ocr_service = OCRService()
ai_service = AIService()

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
async def process_receipt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.photo:
        await update.message.reply_text("Please upload a receipt photo.")
        return
    
    photo = update.message.photo[-1]
    file = await photo.get_file()
    file_path = f"temp/{photo.file_id}.jpg"
    
    try:
        await file.download(file_path)
        
        # Process with OCR
        items = await ocr_service.extract_text(file_path)
        if not items:
            await update.message.reply_text("Could not extract items from the receipt. Please try a clearer image.")
            return
        
        # Filter low-confidence results
        valid_items = [item for item in items if item["confidence"] > 0.7]
        if not valid_items:
            await update.message.reply_text("No reliable items detected. Please upload a higher quality image.")
            return
        
        # Save to database
        with get_db() as db:
            receipt = Receipt(user_id=update.effective_user.id, purchase_date=datetime.now())
            db.add(receipt)
            db.commit()
            
            for item in valid_items:
                product = db.query(Product).filter(Product.name.ilike(f"%{item['text']}%")).first()
                if not product:
                    product = Product(name=item["text"], category="unknown")
                    db.add(product)
                    db.commit()
                
                receipt_item = ReceiptItem(receipt_id=receipt.id, product_id=product.id, quantity=1, price=0.0)
                db.add(receipt_item)
            
            db.commit()
        
        await update.message.reply_text(f"Processed receipt with {len(valid_items)} items.")
        
        # Generate AI suggestions
        if settings.enable_ai_suggestions:
            suggestions = await ai_service.generate_suggestions([item["text"] for item in valid_items])
            if suggestions:
                await update.message.reply_text(f"Suggestions: {', '.join(suggestions)}")
    
    except Exception as e:
        logger.error(f"Error processing receipt: {e}")
        await update.message.reply_text("An error occurred while processing the receipt. Please try again.")
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)