"""Telegram bot for Cross-Chain Price Checker."""

import os
from typing import Optional
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)
from loguru import logger

from ..price_checker import PriceChecker
from ..database import get_db, Alert


class TelegramBot:
    """Telegram bot for price checking and alerts."""

    def __init__(self, token: Optional[str] = None):
        """
        Initialize Telegram bot.

        Args:
            token: Telegram bot token. If None, uses TELEGRAM_BOT_TOKEN env var.
        """
        self.token = token or os.getenv("TELEGRAM_BOT_TOKEN")
        if not self.token:
            raise ValueError("Telegram bot token not provided")

        self.application = Application.builder().token(self.token).build()
        self._setup_handlers()

    def _setup_handlers(self):
        """Setup command handlers."""
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(CommandHandler("price", self.price_command))
        self.application.add_handler(CommandHandler("compare", self.compare_command))
        self.application.add_handler(CommandHandler("alert", self.alert_command))
        self.application.add_handler(CommandHandler("alerts", self.list_alerts_command))
        self.application.add_handler(CommandHandler("portfolio", self.portfolio_command))

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command."""
        welcome_message = """
🚀 Welcome to Cross-Chain Price Checker Bot!

I help you track cryptocurrency prices across multiple exchanges and identify arbitrage opportunities.

Available commands:
/price <token> - Get current price
/compare <token1> <token2> - Compare tokens
/alert <token> <price> - Set price alert
/alerts - View your alerts
/portfolio - View your portfolio
/help - Show help

Example: /price SOL
"""
        await update.message.reply_text(welcome_message)

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command."""
        help_text = """
📖 **Available Commands**

**Price Commands:**
/price <token> - Get current price for a token
/compare <tokens> - Compare multiple tokens

**Alert Commands:**
/alert <token> <price> - Set price alert
/alerts - View active alerts

**Portfolio Commands:**
/portfolio - View your holdings

**Examples:**
/price BTC
/price SOL
/compare BTC ETH SOL
/alert SOL 150
"""
        await update.message.reply_text(help_text)

    async def price_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /price command."""
        if not context.args:
            await update.message.reply_text("Please specify a token. Example: /price SOL")
            return

        token = context.args[0].upper()
        await update.message.reply_text(f"🔍 Fetching {token} prices...")

        checker = PriceChecker()

        try:
            analysis = await checker.check_token_price(token)

            if 'error' in analysis:
                await update.message.reply_text(f"❌ Error: {analysis['error']}")
                return

            if analysis.get('valid_count', 0) == 0:
                await update.message.reply_text(f"❌ No prices found for {token}")
                return

            # Format response
            response = f"💰 **{token} Price Comparison**\n\n"
            response += f"📊 Statistics:\n"
            response += f"  Average: ${analysis['avg_price']:.6f}\n"
            response += f"  Min: ${analysis['min_price']:.6f}\n"
            response += f"  Max: ${analysis['max_price']:.6f}\n"
            response += f"  Spread: {analysis['spread_percent']:.2f}%\n\n"

            response += f"📈 Prices by Exchange:\n"
            for price in analysis['prices']:
                if price.is_valid:
                    response += f"  • {price.exchange_name}: ${price.price:.6f} ({price.pair})\n"

            # Arbitrage opportunities
            opportunities = analysis.get('opportunities', [])
            if opportunities:
                response += f"\n⚡ Top Arbitrage Opportunities:\n"
                for i, opp in enumerate(opportunities[:3], 1):
                    response += (
                        f"  {i}. Buy {opp.buy_exchange} (${opp.buy_price:.6f}) → "
                        f"Sell {opp.sell_exchange} (${opp.sell_price:.6f}) "
                        f"= +{opp.potential_profit_percent:.2f}%\n"
                    )

            await update.message.reply_text(response)

        except Exception as e:
            logger.error(f"Error in price command: {e}")
            await update.message.reply_text(f"❌ An error occurred: {str(e)}")

        finally:
            await checker.close()

    async def compare_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /compare command."""
        if not context.args:
            await update.message.reply_text("Please specify tokens. Example: /compare BTC ETH SOL")
            return

        tokens = [arg.upper() for arg in context.args]
        await update.message.reply_text(f"🔍 Comparing {', '.join(tokens)}...")

        checker = PriceChecker()

        try:
            results = await checker.check_multiple_tokens(tokens)

            response = "💰 **Token Comparison**\n\n"

            for token in tokens:
                analysis = results.get(token, {})

                if 'error' in analysis or analysis.get('valid_count', 0) == 0:
                    response += f"❌ {token}: No data\n"
                    continue

                response += f"**{token}**\n"
                response += f"  Avg: ${analysis['avg_price']:.6f}\n"
                response += f"  Spread: {analysis['spread_percent']:.2f}%\n"

                opportunities = analysis.get('opportunities', [])
                if opportunities:
                    best = opportunities[0]
                    response += f"  Best Arb: +{best.potential_profit_percent:.2f}%\n"

                response += "\n"

            await update.message.reply_text(response)

        finally:
            await checker.close()

    async def alert_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /alert command."""
        if len(context.args) < 2:
            await update.message.reply_text(
                "Usage: /alert <token> <price>\nExample: /alert SOL 150"
            )
            return

        token = context.args[0].upper()
        try:
            price = float(context.args[1])
        except ValueError:
            await update.message.reply_text("Invalid price. Please use a number.")
            return

        user_id = str(update.effective_user.id)
        db = get_db()

        async for session in db.get_session():
            alert = Alert(
                user_id=user_id,
                token_symbol=token,
                alert_type="price_above",
                threshold=price,
                notification_channel="telegram",
            )
            session.add(alert)

            await update.message.reply_text(
                f"✅ Alert created!\n"
                f"You'll be notified when {token} reaches ${price:.2f}"
            )

    async def list_alerts_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /alerts command."""
        user_id = str(update.effective_user.id)
        db = get_db()

        from sqlalchemy import select

        async for session in db.get_session():
            result = await session.execute(
                select(Alert).where(
                    Alert.user_id == user_id,
                    Alert.is_active == True,
                )
            )
            alerts = result.scalars().all()

            if not alerts:
                await update.message.reply_text("You have no active alerts.")
                return

            response = "🔔 **Your Active Alerts**\n\n"
            for alert in alerts:
                response += f"• {alert.token_symbol}: ${alert.threshold:.2f} ({alert.alert_type})\n"

            await update.message.reply_text(response)

    async def portfolio_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /portfolio command."""
        await update.message.reply_text(
            "📊 Portfolio tracking coming soon!\n"
            "Use the web dashboard to manage your portfolio."
        )

    def run(self):
        """Run the bot."""
        logger.info("Starting Telegram bot...")
        self.application.run_polling(allowed_updates=Update.ALL_TYPES)

    async def send_alert(self, user_id: str, message: str):
        """Send alert message to user."""
        try:
            await self.application.bot.send_message(chat_id=user_id, text=message)
        except Exception as e:
            logger.error(f"Error sending alert to {user_id}: {e}")


def main():
    """Main entry point for running the bot."""
    bot = TelegramBot()
    bot.run()


if __name__ == "__main__":
    main()
