"""Discord bot for Cross-Chain Price Checker."""

import os
from typing import Optional
import discord
from discord.ext import commands
from loguru import logger

from ..price_checker import PriceChecker


class DiscordBot(commands.Bot):
    """Discord bot for price checking and alerts."""

    def __init__(self, token: Optional[str] = None):
        """
        Initialize Discord bot.

        Args:
            token: Discord bot token. If None, uses DISCORD_BOT_TOKEN env var.
        """
        self.token = token or os.getenv("DISCORD_BOT_TOKEN")
        if not self.token:
            raise ValueError("Discord bot token not provided")

        intents = discord.Intents.default()
        intents.message_content = True

        super().__init__(command_prefix="!", intents=intents)

        self._setup_commands()

    def _setup_commands(self):
        """Setup bot commands."""

        @self.command(name="price", help="Get current price for a token")
        async def price(ctx, token: str):
            """Get price for a token."""
            token = token.upper()
            await ctx.send(f"🔍 Fetching {token} prices...")

            checker = PriceChecker()

            try:
                analysis = await checker.check_token_price(token)

                if 'error' in analysis or analysis.get('valid_count', 0) == 0:
                    await ctx.send(f"❌ Could not fetch prices for {token}")
                    return

                # Create embed
                embed = discord.Embed(
                    title=f"💰 {token} Price Comparison",
                    color=discord.Color.green(),
                )

                embed.add_field(
                    name="📊 Statistics",
                    value=(
                        f"Average: ${analysis['avg_price']:.6f}\n"
                        f"Min: ${analysis['min_price']:.6f}\n"
                        f"Max: ${analysis['max_price']:.6f}\n"
                        f"Spread: {analysis['spread_percent']:.2f}%"
                    ),
                    inline=False,
                )

                # Add prices
                prices_text = ""
                for price in analysis['prices'][:10]:  # Limit to 10
                    if price.is_valid:
                        prices_text += f"{price.exchange_name}: ${price.price:.6f}\n"

                embed.add_field(name="📈 Prices", value=prices_text or "No prices", inline=False)

                # Add arbitrage opportunities
                opportunities = analysis.get('opportunities', [])
                if opportunities:
                    arb_text = ""
                    for i, opp in enumerate(opportunities[:3], 1):
                        arb_text += (
                            f"{i}. {opp.buy_exchange} → {opp.sell_exchange}: "
                            f"+{opp.potential_profit_percent:.2f}%\n"
                        )
                    embed.add_field(name="⚡ Arbitrage", value=arb_text, inline=False)

                await ctx.send(embed=embed)

            except Exception as e:
                logger.error(f"Error in price command: {e}")
                await ctx.send(f"❌ An error occurred: {str(e)}")

            finally:
                await checker.close()

        @self.command(name="compare", help="Compare multiple tokens")
        async def compare(ctx, *tokens):
            """Compare multiple tokens."""
            if not tokens:
                await ctx.send("Please specify tokens. Example: !compare BTC ETH SOL")
                return

            tokens = [t.upper() for t in tokens]
            await ctx.send(f"🔍 Comparing {', '.join(tokens)}...")

            checker = PriceChecker()

            try:
                results = await checker.check_multiple_tokens(tokens)

                embed = discord.Embed(
                    title="💰 Token Comparison",
                    color=discord.Color.blue(),
                )

                for token in tokens:
                    analysis = results.get(token, {})

                    if 'error' in analysis or analysis.get('valid_count', 0) == 0:
                        embed.add_field(name=token, value="No data", inline=True)
                        continue

                    value = (
                        f"Avg: ${analysis['avg_price']:.6f}\n"
                        f"Spread: {analysis['spread_percent']:.2f}%"
                    )

                    opportunities = analysis.get('opportunities', [])
                    if opportunities:
                        best = opportunities[0]
                        value += f"\nArb: +{best.potential_profit_percent:.2f}%"

                    embed.add_field(name=token, value=value, inline=True)

                await ctx.send(embed=embed)

            finally:
                await checker.close()

        @self.command(name="trending", help="Show trending arbitrage opportunities")
        async def trending(ctx):
            """Show trending arbitrage opportunities."""
            await ctx.send("📈 This feature requires the API server running.")

        @self.event
        async def on_ready():
            """Bot ready event."""
            logger.info(f"Discord bot logged in as {self.user}")
            await self.change_presence(
                activity=discord.Activity(
                    type=discord.ActivityType.watching,
                    name="crypto prices | !price <token>",
                )
            )

    def start_bot(self):
        """Start the Discord bot."""
        logger.info("Starting Discord bot...")
        self.run(self.token)


def main():
    """Main entry point for running the bot."""
    bot = DiscordBot()
    bot.start_bot()


if __name__ == "__main__":
    main()
