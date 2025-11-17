"""Kraken price fetcher."""

from typing import Optional
import aiohttp
from loguru import logger

from ..base import Exchange, ExchangePrice, ExchangeType
from ...utils import retry_on_failure


class Kraken(Exchange):
    """Kraken CEX price fetcher."""

    def __init__(self, api_key: Optional[str] = None, base_url: str = "https://api.kraken.com"):
        super().__init__("Kraken", ExchangeType.CEX)
        self.api_key = api_key
        self.base_url = base_url.rstrip('/')
        self.session: Optional[aiohttp.ClientSession] = None

    async def is_available(self) -> bool:
        try:
            if not self.session:
                self.session = aiohttp.ClientSession()
            async with self.session.get(f"{self.base_url}/0/public/Time", timeout=5) as response:
                return response.status == 200
        except Exception:
            return False

    @retry_on_failure(max_retries=3, delay=1.0)
    async def get_price(self, token_symbol: str, **kwargs) -> ExchangePrice:
        try:
            if not self.session:
                self.session = aiohttp.ClientSession()

            token_symbol = token_symbol.upper()

            # Kraken uses different symbol format (XXBTZUSD, XETHZUSD, etc.)
            symbol_map = {
                "BTC": "XXBTZUSD",
                "ETH": "XETHZUSD",
                "SOL": "SOLUSD",
                "ADA": "ADAUSD",
                "DOT": "DOTUSD",
            }

            pair = symbol_map.get(token_symbol, f"{token_symbol}USD")

            async with self.session.get(
                f"{self.base_url}/0/public/Ticker",
                params={"pair": pair},
                timeout=10
            ) as response:
                if response.status == 200:
                    data = await response.json()

                    if data.get('error'):
                        return self._create_error_price(token_symbol, data['error'][0])

                    result = data.get('result', {})
                    for key, value in result.items():
                        price = float(value['c'][0])  # Last trade closed price

                        if price > 0:
                            return ExchangePrice(
                                exchange_name=self.name,
                                exchange_type=self.exchange_type,
                                price=price,
                                token_symbol=token_symbol,
                                pair=f"{token_symbol}/USD"
                            )

            return self._create_error_price(token_symbol, "No trading pairs found")

        except Exception as e:
            logger.error(f"Error getting Kraken price for {token_symbol}: {e}")
            return self._create_error_price(token_symbol, str(e))

    async def close(self):
        if self.session:
            await self.session.close()
            self.session = None
