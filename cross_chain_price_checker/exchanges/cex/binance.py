"""Binance price fetcher."""

from typing import Optional
import aiohttp
from loguru import logger

from ..base import Exchange, ExchangePrice, ExchangeType
from ...utils import retry_on_failure


class Binance(Exchange):
    """Binance CEX price fetcher."""

    def __init__(self, api_key: Optional[str] = None, base_url: str = "https://api.binance.com"):
        """
        Initialize Binance adapter.

        Args:
            api_key: Binance API key (optional)
            base_url: Binance API base URL
        """
        super().__init__("Binance", ExchangeType.CEX)
        self.api_key = api_key
        self.base_url = base_url.rstrip('/')
        self.session: Optional[aiohttp.ClientSession] = None

    async def is_available(self) -> bool:
        """Check if Binance is available."""
        try:
            if not self.session:
                self.session = aiohttp.ClientSession()

            async with self.session.get(f"{self.base_url}/api/v3/ping", timeout=5) as response:
                return response.status == 200
        except Exception:
            return False

    @retry_on_failure(max_retries=3, delay=1.0)
    async def get_price(self, token_symbol: str, **kwargs) -> ExchangePrice:
        """
        Get token price from Binance.

        Args:
            token_symbol: Token symbol (e.g., 'BTC', 'ETH', 'SOL')
            **kwargs: Additional parameters

        Returns:
            ExchangePrice object
        """
        try:
            if not self.session:
                self.session = aiohttp.ClientSession()

            # Normalize symbol
            token_symbol = token_symbol.upper()

            # Try different quote currencies
            quote_currencies = ["USDT", "USDC", "BUSD"]

            for quote in quote_currencies:
                symbol = f"{token_symbol}{quote}"

                try:
                    async with self.session.get(
                        f"{self.base_url}/api/v3/ticker/price",
                        params={"symbol": symbol},
                        timeout=10
                    ) as response:
                        if response.status == 200:
                            data = await response.json()
                            price = float(data.get('price', 0))

                            if price > 0:
                                return ExchangePrice(
                                    exchange_name=self.name,
                                    exchange_type=self.exchange_type,
                                    price=price,
                                    token_symbol=token_symbol,
                                    pair=f"{token_symbol}/{quote}"
                                )
                except Exception as e:
                    logger.debug(f"Failed to get {symbol} price from Binance: {e}")
                    continue

            return self._create_error_price(token_symbol, "No trading pairs found")

        except Exception as e:
            logger.error(f"Error getting Binance price for {token_symbol}: {e}")
            return self._create_error_price(token_symbol, str(e))

    async def get_all_prices(self) -> dict:
        """
        Get all available prices from Binance.

        Returns:
            Dictionary mapping symbols to prices
        """
        try:
            if not self.session:
                self.session = aiohttp.ClientSession()

            async with self.session.get(
                f"{self.base_url}/api/v3/ticker/price",
                timeout=10
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    return {item['symbol']: float(item['price']) for item in data}

        except Exception as e:
            logger.error(f"Error getting all Binance prices: {e}")

        return {}

    async def close(self):
        """Close HTTP session."""
        if self.session:
            await self.session.close()
            self.session = None
