import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock
from src.bot import SmartShopBot
from src.database import DatabaseManager

@pytest.fixture
def bot():
    """Create bot instance for testing"""
    bot = SmartShopBot()
    bot.db = AsyncMock(spec=DatabaseManager)
    return bot

@pytest.mark.asyncio
async def test_start_command(bot):
    """Test /start command"""
    update = MagicMock()
    context = MagicMock()
    update.effective_user.id = 12345
    update.effective_user.username = "testuser"
    update.message.reply_text = AsyncMock()
    
    await bot.start(update, context)
    
    bot.db.create_user.assert_called_once_with(12345, "testuser")
    update.message.reply_text.assert_called_once()

@pytest.mark.asyncio
async def test_text_parsing(bot):
    """Test text parsing functionality"""
    update = MagicMock()
    context = MagicMock()
    update.effective_user.id = 12345
    update.message.text = "2kg apples, 1L milk, bread"
    update.message.reply_text = AsyncMock()
    
    context.user_data = {}
    
    await bot.handle_text(update, context)
    
    # Should process the text and add items
    assert bot.db.add_purchase.called

@pytest.mark.asyncio
async def test_quantity_clarification(bot):
    """Test quantity clarification flow"""
    update = MagicMock()
    context = MagicMock()
    
    context.user_data = {
        'pending_items': [{'name': 'apples', 'quantity': 'unknown'}],
        'current_item_index': 0
    }
    
    update.message.reply_text = AsyncMock()
    
    await bot.ask_for_quantity(update, context)
    
    update.message.reply_text.assert_called_once()
    args = update.message.reply_text.call_args[0]
    assert 'apples' in args[0]
