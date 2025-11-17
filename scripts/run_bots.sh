#!/bin/bash
# Run all bots concurrently

set -e

echo "Starting Cross-Chain Price Checker Bots..."

# Check for required environment variables
if [ -z "$TELEGRAM_BOT_TOKEN" ]; then
    echo "Warning: TELEGRAM_BOT_TOKEN not set. Telegram bot will not start."
fi

if [ -z "$DISCORD_BOT_TOKEN" ]; then
    echo "Warning: DISCORD_BOT_TOKEN not set. Discord bot will not start."
fi

# Run bots in background
if [ -n "$TELEGRAM_BOT_TOKEN" ]; then
    python -m cross_chain_price_checker.bots.telegram_bot &
    TELEGRAM_PID=$!
    echo "Telegram bot started (PID: $TELEGRAM_PID)"
fi

if [ -n "$DISCORD_BOT_TOKEN" ]; then
    python -m cross_chain_price_checker.bots.discord_bot &
    DISCORD_PID=$!
    echo "Discord bot started (PID: $DISCORD_PID)"
fi

# Wait for all background processes
wait
