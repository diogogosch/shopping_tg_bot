import os
from dotenv import load_dotenv

load_dotenv()

# Bot Configuration
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
BOT_USERNAME = os.getenv('BOT_USERNAME', 'SmartShopBot')

# Database Configuration
DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://botuser:secure_password_here@localhost:5432/smartshop')

# OCR Configuration
GOOGLE_VISION_API_KEY = os.getenv('GOOGLE_VISION_API_KEY')
TESSERACT_CONFIG = '--oem 3 --psm 6 -c tessedit_char_whitelist=0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz.,€$£¥₹ '

# ML Configuration
MIN_FREQUENCY_FOR_SUGGESTION = 2
SUGGESTION_CONFIDENCE_THRESHOLD = 0.3
MAX_SUGGESTIONS_PER_CATEGORY = 5

# Logging Configuration
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
LOG_FILE_MAX_SIZE = 10 * 1024 * 1024  # 10MB
LOG_FILE_BACKUP_COUNT = 5

# Cache Configuration
REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379')
CACHE_TTL = 3600  # 1 hour

# File Upload Configuration
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
ALLOWED_IMAGE_FORMATS = ['jpg', 'jpeg', 'png', 'bmp', 'tiff']
TEMP_UPLOAD_DIR = 'temp_uploads'

# Rate Limiting
RATE_LIMIT_REQUESTS = 30
RATE_LIMIT_WINDOW = 60  # seconds
