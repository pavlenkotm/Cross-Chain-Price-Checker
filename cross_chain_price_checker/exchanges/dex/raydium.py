"""Raydium price fetcher for Solana."""

from typing import Optional
import aiohttp
from loguru import logger

from ..base import Exchange, ExchangePrice, ExchangeType
from ...utils import retry_on_failure


class Raydium(Exchange):
    """Raydium DEX price fetcher for Solana."""

    # Raydium API endpoint
    RAYDIUM_API = "https://api.raydium.io/v2"

    # Common quote tokens on Solana
    USDC_MINT = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
    USDT_MINT = "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB"
    SOL_MINT = "So11111111111111111111111111111111111111112"

    def __init__(self, rpc_url: str):
        """
        Initialize Raydium adapter.

        Args:
            rpc_url: Solana RPC URL
        """
        super().__init__("Raydium", ExchangeType.DEX)
        self.rpc_url = rpc_url
        self.session: Optional[aiohttp.ClientSession] = None

    async def is_available(self) -> bool:
        """Check if Raydium is available."""
        try:
            if not self.session:
                self.session = aiohttp.ClientSession()

            async with self.session.get(f"{self.RAYDIUM_API}/main/pairs", timeout=5) as response:
                return response.status == 200
        except Exception:
            return False

    @retry_on_failure(max_retries=3, delay=1.0)
    async def get_price(self, token_address: str, token_symbol: str = "TOKEN", **kwargs) -> ExchangePrice:
        """
        Get token price from Raydium.

        Args:
            token_address: Token mint address on Solana
            token_symbol: Token symbol
            **kwargs: Additional parameters

        Returns:
            ExchangePrice object
        """
        try:
            if not self.session:
                self.session = aiohttp.ClientSession()

            # Get all pairs from Raydium
            async with self.session.get(
                f"{self.RAYDIUM_API}/main/pairs",
                timeout=10
            ) as response:
                if response.status != 200:
                    return self._create_error_price(token_symbol, f"API returned status {response.status}")

                data = await response.json()

                # Find pairs with our token
                best_price = None
                best_pair = None
                highest_liquidity = 0

                for pair_info in data:
                    base_mint = pair_info.get('baseMint', '')
                    quote_mint = pair_info.get('quoteMint', '')

                    # Check if this pair includes our token
                    if base_mint.lower() == token_address.lower():
                        # Our token is the base
                        if quote_mint in [self.USDC_MINT, self.USDT_MINT]:
                            price = float(pair_info.get('price', 0))
                            liquidity = float(pair_info.get('liquidity', 0))

                            if liquidity > highest_liquidity and price > 0:
                                best_price = price
                                quote_symbol = "USDC" if quote_mint == self.USDC_MINT else "USDT"
                                best_pair = f"{token_symbol}/{quote_symbol}"
                                highest_liquidity = liquidity

                    elif quote_mint.lower() == token_address.lower():
                        # Our token is the quote
                        if base_mint in [self.USDC_MINT, self.USDT_MINT]:
                            price = float(pair_info.get('price', 0))
                            if price > 0:
                                price = 1 / price  # Invert price
                                liquidity = float(pair_info.get('liquidity', 0))

                                if liquidity > highest_liquidity:
                                    best_price = price
                                    base_symbol = "USDC" if base_mint == self.USDC_MINT else "USDT"
                                    best_pair = f"{token_symbol}/{base_symbol}"
                                    highest_liquidity = liquidity

                if best_price and best_price > 0:
                    return ExchangePrice(
                        exchange_name=self.name,
                        exchange_type=self.exchange_type,
                        price=best_price,
                        token_symbol=token_symbol,
                        chain="Solana",
                        pair=best_pair,
                        liquidity=highest_liquidity
                    )

                return self._create_error_price(token_symbol, "No liquid pairs found")

        except Exception as e:
            logger.error(f"Error getting Raydium price for {token_symbol}: {e}")
            return self._create_error_price(token_symbol, str(e))

    async def close(self):
        """Close HTTP session."""
        if self.session:
            await self.session.close()
            self.session = None
