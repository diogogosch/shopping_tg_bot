#!/bin/bash

# SmartShopBot Setup Script

set -e

echo "🛒 Setting up SmartShopBot..."

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker first."
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi

# Create necessary directories
echo "📁 Creating directories..."
mkdir -p data/backups logs temp_uploads

# Check if .env file exists
if [ ! -f .env ]; then
    echo "⚙️ Creating .env file from template..."
    cp .env.example .env
    echo "📝 Please edit .env file with your bot token and settings:"
    echo "   nano .env"
    echo ""
    echo "Required settings:"
    echo "   - TELEGRAM_BOT_TOKEN (get from @BotFather)"
    echo "   - DATABASE_URL (default is fine for Docker setup)"
    echo ""
    read -p "Press Enter after editing .env file..."
fi

# Validate environment file
echo "🔍 Validating environment configuration..."
if ! grep -q "TELEGRAM_BOT_TOKEN=" .env || grep -q "your_bot_token_here" .env; then
    echo "❌ Please set your TELEGRAM_BOT_TOKEN in .env file"
    exit 1
fi

# Build and start containers
echo "🐳 Building and starting Docker containers..."
docker-compose down --remove-orphans
docker-compose up -d --build

# Wait for database to be ready
echo "⏳ Waiting for database to be ready..."
sleep 10

# Check if containers are running
echo "🔍 Checking container status..."
if docker-compose ps | grep -q "Up"; then
    echo "✅ Containers are running successfully!"
else
    echo "❌ Some containers failed to start. Check logs:"
    docker-compose logs
    exit 1
fi

# Show logs
echo "📋 Showing bot logs (Ctrl+C to exit):"
docker-compose logs -f bot
