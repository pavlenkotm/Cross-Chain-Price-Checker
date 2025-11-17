#!/bin/bash
# Setup script for Cross-Chain Price Checker

set -e

echo "========================================="
echo "Cross-Chain Price Checker - Setup"
echo "========================================="
echo

# Check Python version
python_version=$(python3 --version 2>&1 | awk '{print $2}')
echo "✓ Python version: $python_version"

# Create virtual environment
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
    echo "✓ Virtual environment created"
else
    echo "✓ Virtual environment already exists"
fi

# Activate virtual environment
source venv/bin/activate

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip

# Install dependencies
echo "Installing dependencies..."
if [ -f "requirements-full.txt" ]; then
    pip install -r requirements-full.txt
else
    pip install -r requirements.txt
fi
echo "✓ Dependencies installed"

# Install package in development mode
echo "Installing package..."
pip install -e .
echo "✓ Package installed"

# Copy example configuration
if [ ! -f ".env" ]; then
    if [ -f ".env.example" ]; then
        cp .env.example .env
        echo "✓ .env file created from example"
        echo "  Please edit .env file and add your API keys and RPC URLs"
    fi
fi

if [ ! -f "config.yaml" ]; then
    if [ -f "config.example.yaml" ]; then
        cp config.example.yaml config.yaml
        echo "✓ config.yaml created from example"
    fi
fi

# Initialize database
echo "Initializing database..."
python -c "
import asyncio
from cross_chain_price_checker.database import get_db

async def init():
    db = get_db()
    await db.create_tables()
    print('✓ Database tables created')

asyncio.run(init())
" || echo "Note: Database initialization requires DATABASE_URL to be set"

echo
echo "========================================="
echo "Setup Complete!"
echo "========================================="
echo
echo "Next steps:"
echo "1. Edit .env file and add your API keys"
echo "2. Edit config.yaml to configure exchanges"
echo "3. Run the CLI: ccpc check SOL"
echo "4. Run the API: ./scripts/run_api.sh"
echo "5. Run with Docker: docker-compose up"
echo
