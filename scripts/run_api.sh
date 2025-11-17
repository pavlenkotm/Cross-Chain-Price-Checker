#!/bin/bash
# Run the API server

set -e

echo "Starting Cross-Chain Price Checker API..."

# Create database tables if they don't exist
python -c "
import asyncio
from cross_chain_price_checker.database import get_db

async def init_db():
    db = get_db()
    await db.create_tables()
    print('Database initialized')

asyncio.run(init_db())
"

# Start the API server
uvicorn cross_chain_price_checker.api.app:create_app \
    --factory \
    --host 0.0.0.0 \
    --port 8000 \
    --reload \
    --log-level info
