#!/bin/bash

# LuluStream Bot Startup Script

echo "🚀 Starting LuluStream Auto Upload Bot..."
echo ""

# Check if .env exists
if [ ! -f .env ]; then
    echo "⚠️ .env file not found!"
    echo "Creating from .env.example..."
    cp .env.example .env
    echo "✅ Created .env file"
    echo "⚠️ Please edit .env with your credentials before running again!"
    exit 1
fi

# Install dependencies if needed
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
    echo "✅ Virtual environment created"
fi

# Activate virtual environment
echo "🔄 Activating virtual environment..."
source venv/bin/activate

# Install/update dependencies
echo "📥 Installing dependencies..."
pip install -r requirements.txt --quiet
echo "✅ Dependencies installed"

# Run bot
echo ""
echo "✅ Starting bot..."
echo "======================================"
python bot.py
