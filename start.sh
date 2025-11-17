#!/bin/bash
# DevSwarm Startup Script

echo "🤖 Starting DevSwarm Multi-Agent System..."
echo ""

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "📥 Installing dependencies..."
pip install -q -r requirements.txt

# Check for .env file
if [ ! -f ".env" ]; then
    echo "⚠️  Warning: .env file not found!"
    echo "   Please copy .env.example to .env and configure your API keys"
    echo ""
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Start the application
echo ""
echo "🚀 Starting web server..."
echo "   Access the UI at: http://localhost:3000"
echo ""

python src/web/app.py
