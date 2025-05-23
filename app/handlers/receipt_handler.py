from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ParseMode
import logging
from datetime import datetime

from app.core.database import get_db
from app.models.user import User
from app.models.receipt import Receipt, ReceiptItem
from app.models.product import Product
from app.services.ocr_service import ocr_service

logger = logging.getLogger(__name__)

class ReceiptHandler:
    async def handle_photo(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle receipt photo processing"""
        user_id = update.effective_user.id
        
        # Send processing message
        processing_msg = await update.message.reply_text(
            "📸 Processing your receipt...\n"
            "This may take a few seconds."
        )
        
        try:
            # Get the largest photo
            photo = update.message.photo[-1]
            file = await context.bot.get_file(photo.file_id)
            
            # Download image data
            image_data = await file.download_as_bytearray()
            
            # Process with OCR
            receipt_data = ocr_service.extract_text_from_receipt(bytes(image_data))
            
            if receipt_data.get('error'):
                await processing_msg.edit_text(
                    f"❌ Failed to process receipt: {receipt_data['error']}\n"
                    "Please try with a clearer image."
                )
                return
            
            # Save to database
            receipt_id = await self._save_receipt_to_db(user_id, receipt_data)
            
            if receipt_id:
                # Format results
                await self._send_receipt_results(update, receipt_data, processing_msg)
            else:
                await processing_msg.edit_text(
                    "❌ Failed to save receipt data. Please try again."
                )
                
        except Exception as e:
            logger.error(f"Receipt processing error: {e}")
            await processing_msg.edit_text(
                "❌ An error occurred while processing your receipt. "
                "Please try again with a clearer image."
            )
    
    async def _save_receipt_to_db(self, user_id: int, receipt_data: dict) -> int:
        """Save receipt data to database"""
        try:
            with get_db() as db:
                user = db.query(User).filter(User.telegram_id == user_id).first()
                if not user:
                    return None
                
                # Create receipt record
                receipt = Receipt(
                    user_id=user.id,
                    store_name=receipt_data.get('store_name'),
                    total_amount=receipt_data.get('total', 0.0),
                    currency=user.currency,
                    ocr_confidence=receipt_data.get('confidence', 0.0),
                    processing_status='processed',
                    raw_text=receipt_data.get('raw_text', ''),
                    purchase_date=datetime.utcnow()
                )
                
                if receipt_data.get('date'):
                    try:
                        # Try to parse the date
                        receipt.purchase_date = datetime.strptime(
                            receipt_data['date'], '%d/%m/%Y'
                        )
                    except:
                        pass
                
                db.add(receipt)
                db.commit()
                
                # Add receipt items
                for item_data in receipt_data.get('items', []):
                    # Try to find existing product
                    product = db.query(Product).filter(
                        Product.name.ilike(f"%{item_data['name']}%")
                    ).first()
                    
                    if not product:
                        # Create new product
                        product = Product(
                            name=item_data['name'],
                            category=self._categorize_product(item_data['name']),
                            last_price=item_data['unit_price']
                        )
                        db.add(product)
                        db.commit()
                    else:
                        # Update price information
                        product.last_price = item_data['unit_price']
                        if product.average_price:
                            product.average_price = (product.average_price + item_data['unit_price']) / 2
                        else:
                            product.average_price = item_data['unit_price']
                    
                    # Create receipt item
                    receipt_item = ReceiptItem(
                        receipt_id=receipt.id,
                        product_id=product.id,
                        item_name=item_data['name'],
                        quantity=item_data.get('quantity', 1),
                        unit_price=item_data['unit_price'],
                        total_price=item_data['total_price']
                    )
                    db.add(receipt_item)
                
                db.commit()
                return receipt.id
                
        except Exception as e:
            logger.error(f"Database error saving receipt: {e}")
            return None
    
    async def _send_receipt_results(self, update: Update, receipt_data: dict, processing_msg):
        """Send formatted receipt processing results"""
        confidence = receipt_data.get('confidence', 0)
        
        # Header
        text = "🧾 *Receipt Processed Successfully!*\n\n"
        
        if receipt_data.get('store_name'):
            text += f"🏪 *Store:* {receipt_data['store_name']}\n"
        
        if receipt_data.get('date'):
            text += f"📅 *Date:* {receipt_data['date']}\n"
        
        text += f"🎯 *Confidence:* {confidence:.1f}%\n\n"
        
        # Items
        items = receipt_data.get('items', [])
        if items:
            text += "*Items Found:*\n"
            for i, item in enumerate(items[:10]):  # Limit to 10 items
                quantity = item.get('quantity', 1)
                if quantity != 1:
                    text += f"• {quantity}x {item['name']} - ${item['total_price']:.2f}\n"
                else:
                    text += f"• {item['name']} - ${item['total_price']:.2f}\n"
            
            if len(items) > 10:
                text += f"• ... and {len(items) - 10} more items\n"
        
        # Total
        total = receipt_data.get('total', 0)
        if total > 0:
            text += f"\n💰 *Total:* ${total:.2f}"
        
        # Add action buttons
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
        
        keyboard = [
            [InlineKeyboardButton("➕ Add to Shopping List", callback_data="add_receipt_items")],
            [InlineKeyboardButton("📊 View Stats", callback_data="view_stats")]
        ]
        
        if confidence < 70:
            text += f"\n\n⚠️ *Low confidence score.* Some items might be incorrect."
            keyboard.insert(0, [InlineKeyboardButton("✏️ Edit Items", callback_data="edit_receipt")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await processing_msg.edit_text(
            text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=reply_markup
        )
    
    def _categorize_product(self, product_name: str) -> str:
        """Basic product categorization"""
        name_lower = product_name.lower()
        
        categories = {
            'fruits': ['apple', 'banana', 'orange', 'grape', 'berry', 'lemon', 'lime'],
            'vegetables': ['carrot', 'potato', 'onion', 'tomato', 'lettuce', 'spinach'],
            'dairy': ['milk', 'cheese', 'yogurt', 'butter', 'cream', 'egg'],
            'meat': ['chicken', 'beef', 'pork', 'fish', 'turkey', 'lamb'],
            'bakery': ['bread', 'roll', 'bagel', 'croissant', 'muffin'],
            'beverages': ['juice', 'soda', 'water', 'coffee', 'tea', 'beer', 'wine'],
            'pantry': ['rice', 'pasta', 'flour', 'sugar', 'salt', 'oil', 'sauce']
        }
        
        for category, keywords in categories.items():
            if any(keyword in name_lower for keyword in keywords):
                return category
        
        return 'other'
