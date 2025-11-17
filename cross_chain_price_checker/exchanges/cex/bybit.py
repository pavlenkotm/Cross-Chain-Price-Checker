"""Bybit price fetcher."""

from typing import Optional
import aiohttp
from loguru import logger

from ..base import Exchange, ExchangePrice, ExchangeType
from ...utils import retry_on_failure


class Bybit(Exchange):
    """Bybit CEX price fetcher."""

    def __init__(self, api_key: Optional[str] = None, base_url: str = "https://api.bybit.com"):
        """
        Initialize Bybit adapter.

        Args:
            api_key: Bybit API key (optional)
            base_url: Bybit API base URL
        """
        super().__init__("Bybit", ExchangeType.CEX)
        self.api_key = api_key
        self.base_url = base_url.rstrip('/')
        self.session: Optional[aiohttp.ClientSession] = None

    async def is_available(self) -> bool:
        """Check if Bybit is available."""
        try:
            if not self.session:
                self.session = aiohttp.ClientSession()

            async with self.session.get(f"{self.base_url}/v5/market/time", timeout=5) as response:
                return response.status == 200
        except Exception:
            return False

    @retry_on_failure(max_retries=3, delay=1.0)
    async def get_price(self, token_symbol: str, **kwargs) -> ExchangePrice:
        """
        Get token price from Bybit.

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
            quote_currencies = ["USDT", "USDC"]

            for quote in quote_currencies:
                symbol = f"{token_symbol}{quote}"

                try:
                    # Bybit V5 API
                    async with self.session.get(
                        f"{self.base_url}/v5/market/tickers",
                        params={
                            "category": "spot",
                            "symbol": symbol
                        },
                        timeout=10
                    ) as response:
                        if response.status == 200:
                            data = await response.json()

                            if data.get('retCode') == 0:
                                result = data.get('result', {})
                                ticker_list = result.get('list', [])

                                if ticker_list:
                                    ticker = ticker_list[0]
                                    price = float(ticker.get('lastPrice', 0))

                                    if price > 0:
                                        return ExchangePrice(
                                            exchange_name=self.name,
                                            exchange_type=self.exchange_type,
                                            price=price,
                                            token_symbol=token_symbol,
                                            pair=f"{token_symbol}/{quote}"
                                        )
                except Exception as e:
                    logger.debug(f"Failed to get {symbol} price from Bybit: {e}")
                    continue

            return self._create_error_price(token_symbol, "No trading pairs found")

        except Exception as e:
            logger.error(f"Error getting Bybit price for {token_symbol}: {e}")
            return self._create_error_price(token_symbol, str(e))

    async def get_all_prices(self, category: str = "spot") -> dict:
        """
        Get all available prices from Bybit.

        Args:
            category: Trading category (spot, linear, inverse)

        Returns:
            Dictionary mapping symbols to prices
        """
        try:
            if not self.session:
                self.session = aiohttp.ClientSession()

            async with self.session.get(
                f"{self.base_url}/v5/market/tickers",
                params={"category": category},
                timeout=10
            ) as response:
                if response.status == 200:
                    data = await response.json()

                    if data.get('retCode') == 0:
                        result = data.get('result', {})
                        ticker_list = result.get('list', [])
                        return {
                            item['symbol']: float(item['lastPrice'])
                            for item in ticker_list
                            if item.get('lastPrice')
                        }

        except Exception as e:
            logger.error(f"Error getting all Bybit prices: {e}")

        return {}

    async def close(self):
        """Close HTTP session."""
        if self.session:
            await self.session.close()
            self.session = None
