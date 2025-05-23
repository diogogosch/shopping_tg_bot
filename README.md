# SmartShopBot 🛒

An intelligent Telegram bot that automates shopping list management by processing receipt photos, categorizing items, and providing AI-powered shopping suggestions based on your purchase patterns.

## Features

- 📸 **Receipt OCR Processing**: Upload receipt photos for automatic item extraction
- 📝 **Text Input Processing**: Add purchases via text descriptions  
- 🏷️ **Smart Categorization**: Automatic item categorization (produce, dairy, meat, etc.)
- 🤖 **AI Suggestions**: Personalized shopping lists based on purchase frequency
- 📊 **Analytics**: View shopping patterns and statistics
- 🔍 **Quantity Clarification**: Interactive prompts for missing item quantities
- 🐳 **Docker Ready**: Fully containerized for easy deployment
- 🔒 **Secure**: PostgreSQL database with proper user management

## Quick Start

### Prerequisites

- Docker and Docker Compose
- Telegram Bot Token (from @BotFather)
- Server with at least 1GB RAM

### Installation from GitHub

```bash
git clone https://github.com/diogogosch/smartshop-bot.git
cd smartshop-bot
chmod +x setup.sh
./setup.sh
```

### Manual Installation

1. **Clone the repository:**
```bash
git clone https://github.com/diogogosch/smartshop-bot.git
cd smartshop-bot
```

2. **Set up environment variables:**
```bash
cp .env.example .env
nano .env  # Edit with your bot token and settings
```

3. **Deploy with Docker:**
```bash
docker-compose up -d --build
```

4. **Check deployment:**
```bash
docker-compose ps
docker-compose logs -f bot
```

## Bot Commands

- `/start` - Initialize bot and get welcome message
- `/add_receipt` - Upload a receipt photo for processing
- `/add_text` - Add items via text description
- `/suggest_list` - Get AI-powered shopping suggestions
- `/view_categories` - See categorized items
- `/stats` - View shopping analytics
- `/help` - Show help message

## Usage Examples

### Text Input Format
```
2kg apples, 1L milk, bread
chicken breast 500g, rice 1kg, tomatoes
eggs 12 units, cheese 200g, pasta
```

### Receipt Processing
Simply upload a clear photo of your receipt, and the bot will:
1. Extract items using OCR technology
2. Categorize them automatically
3. Ask for clarification on unclear quantities
4. Store everything for future analysis

### AI Suggestions
The bot learns your shopping patterns and suggests items based on:
- Purchase frequency
- Time since last purchase
- Seasonal patterns
- Category preferences

## Architecture

```
smartshop-bot/
├── src/                    # Main application code
│   ├── bot.py             # Telegram bot handlers and main logic
│   ├── ocr_processor.py   # Receipt image processing with OCR
│   ├── database.py        # Database operations and models
│   ├── ml_suggestions.py  # AI suggestion engine
│   ├── text_parser.py     # Text parsing and NLP logic
│   └── utils.py           # Utility functions
├── config/                # Configuration files
│   └── settings.py        # Application settings
├── migrations/            # Database migrations
│   └── init_db.sql        # Initial database schema
├── tests/                 # Unit tests
├── data/                  # Data storage (backups, uploads)
├── logs/                  # Application logs
└── docker-compose.yml     # Container orchestration
```

## Database Schema

### Tables

- **users**: User information and preferences
  - `id` (BIGINT): Telegram user ID
  - `username` (VARCHAR): Telegram username
  - `created_at`, `last_active` (TIMESTAMP)

- **purchases**: Individual purchase records
  - `id` (SERIAL): Primary key
  - `user_id` (BIGINT): Foreign key to users
  - `item_name` (VARCHAR): Name of purchased item
  - `category` (VARCHAR): Item category
  - `quantity`, `unit`, `price` (VARCHAR): Purchase details
  - `purchase_date` (TIMESTAMP): When item was purchased
  - `raw_data` (JSONB): Original OCR/input data

- **categories**: Item categories and keywords
  - `id` (SERIAL): Primary key
  - `name` (VARCHAR): Category name
  - `keywords` (TEXT[]): Keywords for classification

- **user_preferences**: User-specific settings
  - `user_id` (BIGINT): Foreign key to users
  - `preferences` (JSONB): User preferences and settings

## Configuration

### Environment Variables

Create a `.env` file with the following variables:

```env
# Required
TELEGRAM_BOT_TOKEN=your_bot_token_here
DATABASE_URL=postgresql://botuser:password@db:5432/smartshop

# Optional
GOOGLE_VISION_API_KEY=your_google_vision_key  # For advanced OCR
LOG_LEVEL=INFO
REDIS_URL=redis://redis:6379
```

### Getting a Telegram Bot Token

1. Message [@BotFather](https://t.me/BotFather) on Telegram
2. Send `/newbot` command
3. Follow the prompts to create your bot
4. Copy the provided token to your `.env` file

## Development

### Local Development Setup

1. **Install Python dependencies:**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

2. **Set up PostgreSQL:**
```bash
# Using Docker
docker run --name smartshop-db \
  -e POSTGRES_PASSWORD=password \
  -e POSTGRES_DB=smartshop \
  -p 5432:5432 -d postgres:15
```

3. **Initialize database:**
```bash
psql -h localhost -U postgres -d smartshop -f migrations/init_db.sql
```

4. **Run the bot:**
```bash
python src/bot.py
```

### Running Tests

```bash
# Install test dependencies
pip install pytest pytest-asyncio

# Run tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=src --cov-report=html
```

### Code Structure

The bot follows a modular architecture:

- **bot.py**: Main bot logic and Telegram handlers
- **ocr_processor.py**: Image processing and OCR functionality
- **database.py**: Database operations with async PostgreSQL
- **ml_suggestions.py**: Machine learning for shopping suggestions
- **text_parser.py**: Natural language processing for text input
- **utils.py**: Shared utility functions

## Deployment

### Production Deployment

1. **Server Requirements:**
   - Ubuntu 20.04+ or similar Linux distribution
   - Docker and Docker Compose installed
   - At least 1GB RAM and 10GB storage
   - Open port 443 for HTTPS (optional)

2. **Deploy to server:**
```bash
# On your server
git clone https://github.com/YOUR_USERNAME/smartshop-bot.git
cd smartshop-bot
cp .env.example .env
nano .env  # Configure your settings
./setup.sh
```

3. **Set up SSL (optional):**
```bash
# Install Nginx and Certbot
sudo apt install nginx certbot python3-certbot-nginx

# Configure domain and SSL
sudo certbot --nginx -d your-domain.com
```

### Docker Compose Services

- **bot**: Main application container
- **db**: PostgreSQL database
- **redis**: Redis cache (optional, for performance)

### Monitoring and Maintenance

```bash
# View logs
docker-compose logs -f bot

# Check container status
docker-compose ps

# Update containers
docker-compose pull
docker-compose up -d --build

# Backup database
docker-compose exec db pg_dump -U botuser smartshop > backup.sql

# Restore database
docker-compose exec -T db psql -U botuser -d smartshop < backup.sql
```

## API Integration

### Google Vision API (Optional)

For enhanced OCR capabilities, you can integrate Google Vision API:

1. Create a Google Cloud Project
2. Enable the Vision API
3. Create a service account and download the JSON key
4. Set `GOOGLE_VISION_API_KEY` in your environment

### Tesseract OCR

The bot includes Tesseract OCR by default for basic receipt processing:
- Supports multiple languages
- Configurable OCR parameters
- Image preprocessing for better accuracy

## Machine Learning Features

### Item Categorization

The bot automatically categorizes items using:
- Keyword matching
- Pattern recognition
- User feedback learning

### Shopping Suggestions

AI suggestions are based on:
- **Frequency Analysis**: How often you buy each item
- **Time Patterns**: When you typically purchase items
- **Seasonal Trends**: Seasonal shopping patterns
- **Category Preferences**: Your preferred brands and categories

### Confidence Scoring

Each suggestion includes a confidence score based on:
- Purchase frequency
- Time since last purchase
- Historical patterns
- User preferences

## Troubleshooting

### Common Issues

1. **Bot not responding:**
   - Check bot token in `.env` file
   - Verify containers are running: `docker-compose ps`
   - Check logs: `docker-compose logs bot`

2. **OCR not working:**
   - Ensure image is clear and well-lit
   - Check Tesseract installation
   - Verify image format (JPG, PNG supported)

3. **Database connection errors:**
   - Check PostgreSQL container status
   - Verify database credentials
   - Ensure database is initialized

4. **Memory issues:**
   - Increase server RAM
   - Optimize Docker memory limits
   - Clean up old logs and data

### Performance Optimization

- Use Redis for caching frequent queries
- Implement database connection pooling
- Optimize image processing parameters
- Set up log rotation

## Contributing

We welcome contributions! Please follow these steps:

1. **Fork the repository**
2. **Create a feature branch:**
   ```bash
   git checkout -b feature/amazing-feature
   ```
3. **Make your changes and add tests**
4. **Commit your changes:**
   ```bash
   git commit -m 'Add amazing feature'
   ```
5. **Push to the branch:**
   ```bash
   git push origin feature/amazing-feature
   ```
6. **Open a Pull Request**

### Development Guidelines

- Follow PEP 8 style guidelines
- Add tests for new features
- Update documentation as needed
- Use type hints where possible
- Write clear commit messages

## Security

### Best Practices

- Keep your bot token secure and never commit it to version control
- Use environment variables for sensitive configuration
- Regularly update dependencies
- Monitor logs for suspicious activity
- Use HTTPS in production

### Data Privacy

- User data is stored securely in PostgreSQL
- No sensitive information is logged
- Users can request data deletion
- Compliance with data protection regulations

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

- 📖 **Documentation**: Check this README and inline code comments
- 🐛 **Bug Reports**: Open an issue on GitHub
- 💡 **Feature Requests**: Open an issue with the "enhancement" label
- 💬 **Questions**: Start a discussion on GitHub

## Acknowledgments

- [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot) for the excellent Telegram bot framework
- [Tesseract OCR](https://github.com/tesseract-ocr/tesseract) for optical character recognition
- [PostgreSQL](https://www.postgresql.org/) for robust data storage
- [Docker](https://www.docker.com/) for containerization

## Changelog

### v1.0.0 (Initial Release)
- ✅ Receipt OCR processing
- ✅ Text input parsing
- ✅ Smart item categorization
- ✅ AI-powered shopping suggestions
- ✅ User analytics and statistics
- ✅ Docker containerization
- ✅ PostgreSQL database integration

---

**Made with ❤️ for smarter shopping**

*SmartShopBot - Making grocery shopping intelligent, one receipt at a time!*

