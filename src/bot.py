import logging
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
from dotenv import load_dotenv
import asyncio

from ocr_processor import OCRProcessor
from database import DatabaseManager
from ml_suggestions import MLSuggestions
from text_parser import TextParser
from utils import setup_logging

load_dotenv()

# Configure logging
setup_logging()
logger = logging.getLogger(__name__)

class SmartShopBot:
    def __init__(self):
        self.token = os.getenv('TELEGRAM_BOT_TOKEN')
        self.db = DatabaseManager()
        self.ocr = OCRProcessor()
        self.ml = MLSuggestions(self.db)
        self.text_parser = TextParser()
        
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        user_id = update.effective_user.id
        username = update.effective_user.username or "User"
        
        # Initialize user in database
        await self.db.create_user(user_id, username)
        
        welcome_text = f"""
🛒 **Welcome to SmartShopBot, {username}!**

I'm here to help you manage your shopping lists intelligently by:
📸 Processing receipt photos
📝 Parsing text descriptions of purchases
🏷️ Categorizing your items automatically
📊 Learning your shopping patterns
💡 Suggesting shopping lists based on your habits

**Available Commands:**
/add_receipt - Upload a receipt photo
/add_text - Add items via text description
/suggest_list - Get AI-powered shopping suggestions
/view_categories - See your categorized items
/stats - View your shopping analytics
/help - Show this help message

Let's start by adding your first purchase! 🚀
        """
        
        await update.message.reply_text(welcome_text, parse_mode='Markdown')

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command"""
        help_text = """
🤖 **SmartShopBot Commands:**

📸 `/add_receipt` - Upload a receipt photo for processing
📝 `/add_text` - Add purchases via text (e.g., "2kg apples, 1L milk")
💡 `/suggest_list` - Get personalized shopping suggestions
🏷️ `/view_categories` - See your items organized by category
📊 `/stats` - View your shopping patterns and analytics
❓ `/help` - Show this help message

**How to use:**
1. Upload receipt photos or describe your purchases in text
2. I'll extract items and ask for clarification if needed
3. Items are automatically categorized and stored
4. Get smart suggestions based on your shopping history

**Text Format Examples:**
• "bought 2kg apples, 500g cheese, bread"
• "milk 1L, eggs 12 units, chicken breast 1kg"
• "tomatoes, onions, pasta 500g"
        """
        await update.message.reply_text(help_text, parse_mode='Markdown')

    async def add_receipt(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /add_receipt command"""
        await update.message.reply_text(
            "📸 Please send me a photo of your receipt and I'll process it for you!\n\n"
            "Make sure the receipt is clearly visible and well-lit for best results."
        )

    async def add_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /add_text command"""
        await update.message.reply_text(
            "📝 Please describe what you bought in text format.\n\n"
            "**Examples:**\n"
            "• `2kg apples, 1L milk, bread`\n"
            "• `chicken breast 500g, rice 1kg, tomatoes`\n"
            "• `eggs 12 units, cheese 200g, pasta`\n\n"
            "I'll parse your text and ask for any missing quantities!",
            parse_mode='Markdown'
        )

    async def handle_photo(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Process receipt photos"""
        user_id = update.effective_user.id
        
        # Send processing message
        processing_msg = await update.message.reply_text("🔍 Processing your receipt... This may take a moment.")
        
        try:
            # Get the largest photo
            photo = update.message.photo[-1]
            file = await context.bot.get_file(photo.file_id)
            
            # Download and process image
            image_path = f"temp_receipt_{user_id}.jpg"
            await file.download_to_drive(image_path)
            
            # Extract items using OCR
            items = await self.ocr.process_receipt(image_path)
            
            # Clean up temp file
            os.remove(image_path)
            
            if not items:
                await processing_msg.edit_text(
                    "❌ I couldn't extract any items from this receipt. "
                    "Please make sure the image is clear and try again, or use /add_text to add items manually."
                )
                return
            
            # Store items and get any missing quantities
            missing_quantities = await self.process_items(user_id, items)
            
            if missing_quantities:
                context.user_data['pending_items'] = missing_quantities
                context.user_data['current_item_index'] = 0
                await self.ask_for_quantity(update, context)
            else:
                await processing_msg.edit_text(
                    f"✅ Successfully processed {len(items)} items from your receipt!\n"
                    f"Use /view_categories to see your categorized items."
                )
                
        except Exception as e:
            logger.error(f"Error processing receipt: {e}")
            await processing_msg.edit_text(
                "❌ Sorry, I encountered an error processing your receipt. Please try again."
            )

    async def handle_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Process text descriptions of purchases"""
        user_id = update.effective_user.id
        text = update.message.text
        
        # Check if user is responding to quantity question
        if 'pending_items' in context.user_data:
            await self.handle_quantity_response(update, context)
            return
        
        processing_msg = await update.message.reply_text("📝 Processing your text...")
        
        try:
            # Parse text to extract items
            items = self.text_parser.parse_purchase_text(text)
            
            if not items:
                await processing_msg.edit_text(
                    "❌ I couldn't understand the format. Please try again using examples like:\n"
                    "`2kg apples, 1L milk, bread`\n"
                    "or use /add_text for more guidance.",
                    parse_mode='Markdown'
                )
                return
            
            # Process items and check for missing quantities
            missing_quantities = await self.process_items(user_id, items)
            
            if missing_quantities:
                context.user_data['pending_items'] = missing_quantities
                context.user_data['current_item_index'] = 0
                await self.ask_for_quantity(update, context)
            else:
                await processing_msg.edit_text(
                    f"✅ Successfully added {len(items)} items!\n"
                    f"Use /view_categories to see your categorized items."
                )
                
        except Exception as e:
            logger.error(f"Error processing text: {e}")
            await processing_msg.edit_text(
                "❌ Sorry, I encountered an error processing your text. Please try again."
            )

    async def process_items(self, user_id, items):
        """Process items and return any with missing quantities"""
        missing_quantities = []
        
        for item in items:
            # Categorize item
            category = await self.ml.categorize_item(item['name'])
            item['category'] = category
            
            # Check if quantity is missing or unclear
            if not item.get('quantity') or item.get('quantity') == 'unknown':
                missing_quantities.append(item)
            else:
                # Store complete item
                await self.db.add_purchase(user_id, item)
        
        return missing_quantities

    async def ask_for_quantity(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Ask user for missing quantity information"""
        pending_items = context.user_data.get('pending_items', [])
        current_index = context.user_data.get('current_item_index', 0)
        
        if current_index >= len(pending_items):
            # All quantities collected
            await update.message.reply_text("✅ All items have been added successfully!")
            context.user_data.clear()
            return
        
        current_item = pending_items[current_index]
        
        keyboard = [
            [InlineKeyboardButton("Skip this item", callback_data="skip_quantity")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        question_text = (
            f"❓ I found **{current_item['name']}** but couldn't determine the quantity.\n\n"
            f"Please specify the quantity (e.g., 2kg, 3 units, 1L, 500g):"
        )
        
        await update.message.reply_text(
            question_text, 
            parse_mode='Markdown',
            reply_markup=reply_markup
        )

    async def handle_quantity_response(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle user's quantity response"""
        user_id = update.effective_user.id
        quantity = update.message.text.strip()
        
        pending_items = context.user_data.get('pending_items', [])
        current_index = context.user_data.get('current_item_index', 0)
        
        if current_index < len(pending_items):
            current_item = pending_items[current_index]
            current_item['quantity'] = quantity
            
            # Store the item with quantity
            await self.db.add_purchase(user_id, current_item)
            
            # Move to next item
            context.user_data['current_item_index'] = current_index + 1
            
            # Ask for next quantity or finish
            if context.user_data['current_item_index'] < len(pending_items):
                await self.ask_for_quantity(update, context)
            else:
                await update.message.reply_text(
                    f"✅ Successfully added all {len(pending_items)} items!\n"
                    f"Use /view_categories to see your categorized items."
                )
                context.user_data.clear()

    async def handle_callback_query(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle inline keyboard callbacks"""
        query = update.callback_query
        await query.answer()
        
        if query.data == "skip_quantity":
            user_id = update.effective_user.id
            pending_items = context.user_data.get('pending_items', [])
            current_index = context.user_data.get('current_item_index', 0)
            
            if current_index < len(pending_items):
                current_item = pending_items[current_index]
                current_item['quantity'] = 'unspecified'
                
                # Store item without specific quantity
                await self.db.add_purchase(user_id, current_item)
                
                # Move to next item
                context.user_data['current_item_index'] = current_index + 1
                
                await query.edit_message_text(f"⏭️ Skipped quantity for {current_item['name']}")
                
                # Continue with next item or finish
                if context.user_data['current_item_index'] < len(pending_items):
                    await self.ask_for_quantity(update, context)
                else:
                    await query.message.reply_text(
                        f"✅ Finished processing all items!\n"
                        f"Use /view_categories to see your categorized items."
                    )
                    context.user_data.clear()

    async def suggest_list(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Generate shopping suggestions based on purchase history"""
        user_id = update.effective_user.id
        
        suggestions = await self.ml.generate_shopping_suggestions(user_id)
        
        if not suggestions:
            await update.message.reply_text(
                "🤔 I don't have enough purchase history to make suggestions yet.\n"
                "Add more receipts or purchases, and I'll learn your patterns!"
            )
            return
        
        suggestion_text = "🛒 **Your Personalized Shopping List:**\n\n"
        
        for category, items in suggestions.items():
            suggestion_text += f"**{category.title()}:**\n"
            for item in items:
                confidence = item.get('confidence', 0)
                suggestion_text += f"• {item['name']} (confidence: {confidence:.0%})\n"
            suggestion_text += "\n"
        
        await update.message.reply_text(suggestion_text, parse_mode='Markdown')

    async def view_categories(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show user's categorized items"""
        user_id = update.effective_user.id
        
        categories = await self.db.get_user_categories(user_id)
        
        if not categories:
            await update.message.reply_text(
                "📦 You haven't added any items yet!\n"
                "Use /add_receipt or /add_text to start building your shopping history."
            )
            return
        
        category_text = "🏷️ **Your Items by Category:**\n\n"
        
        for category, items in categories.items():
            category_text += f"**{category.title()}:**\n"
            for item in items[:5]:  # Show max 5 items per category
                category_text += f"• {item}\n"
            if len(items) > 5:
                category_text += f"• ... and {len(items) - 5} more\n"
            category_text += "\n"
        
        await update.message.reply_text(category_text, parse_mode='Markdown')

    async def stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show user shopping statistics"""
        user_id = update.effective_user.id
        
        stats = await self.db.get_user_stats(user_id)
        
        if not stats:
            await update.message.reply_text(
                "📊 No statistics available yet!\n"
                "Start adding purchases to see your shopping patterns."
            )
            return
        
        stats_text = f"""
📊 **Your Shopping Statistics:**

🛒 Total purchases: {stats['total_purchases']}
📦 Unique items: {stats['unique_items']}
🏷️ Categories: {stats['categories']}
📅 Days tracked: {stats['days_tracked']}

**Most frequent categories:**
"""
        
        for category, count in stats['top_categories']:
            stats_text += f"• {category.title()}: {count} items\n"
        
        stats_text += "\n**Most purchased items:**\n"
        for item, count in stats['top_items']:
            stats_text += f"• {item}: {count} times\n"
        
        await update.message.reply_text(stats_text, parse_mode='Markdown')

    def run(self):
        """Start the bot"""
        application = Application.builder().token(self.token).build()
        
        # Command handlers
        application.add_handler(CommandHandler("start", self.start))
        application.add_handler(CommandHandler("help", self.help_command))
        application.add_handler(CommandHandler("add_receipt", self.add_receipt))
        application.add_handler(CommandHandler("add_text", self.add_text))
        application.add_handler(CommandHandler("suggest_list", self.suggest_list))
        application.add_handler(CommandHandler("view_categories", self.view_categories))
        application.add_handler(CommandHandler("stats", self.stats))
        
        # Message handlers
        application.add_handler(MessageHandler(filters.PHOTO, self.handle_photo))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_text))
        
        # Callback query handler
        application.add_handler(CallbackQueryHandler(self.handle_callback_query))
        
        logger.info("SmartShopBot is starting...")
        application.run_polling()

if __name__ == '__main__':
    bot = SmartShopBot()
    bot.run()
