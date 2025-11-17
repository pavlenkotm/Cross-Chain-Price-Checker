"""OKX price fetcher."""

from typing import Optional
import aiohttp
from loguru import logger

from ..base import Exchange, ExchangePrice, ExchangeType
from ...utils import retry_on_failure


class OKX(Exchange):
    """OKX CEX price fetcher."""

    def __init__(self, api_key: Optional[str] = None, base_url: str = "https://www.okx.com"):
        super().__init__("OKX", ExchangeType.CEX)
        self.api_key = api_key
        self.base_url = base_url.rstrip('/')
        self.session: Optional[aiohttp.ClientSession] = None

    async def is_available(self) -> bool:
        try:
            if not self.session:
                self.session = aiohttp.ClientSession()
            async with self.session.get(f"{self.base_url}/api/v5/public/time", timeout=5) as response:
                return response.status == 200
        except Exception:
            return False

    @retry_on_failure(max_retries=3, delay=1.0)
    async def get_price(self, token_symbol: str, **kwargs) -> ExchangePrice:
        try:
            if not self.session:
                self.session = aiohttp.ClientSession()

            token_symbol = token_symbol.upper()
            inst_id = f"{token_symbol}-USDT"

            async with self.session.get(
                f"{self.base_url}/api/v5/market/ticker",
                params={"instId": inst_id},
                timeout=10
            ) as response:
                if response.status == 200:
                    data = await response.json()

                    if data.get('code') == '0' and data.get('data'):
                        ticker = data['data'][0]
                        price = float(ticker['last'])

                        if price > 0:
                            return ExchangePrice(
                                exchange_name=self.name,
                                exchange_type=self.exchange_type,
                                price=price,
                                token_symbol=token_symbol,
                                pair=f"{token_symbol}/USDT"
                            )

            return self._create_error_price(token_symbol, "No trading pairs found")

        except Exception as e:
            logger.error(f"Error getting OKX price for {token_symbol}: {e}")
            return self._create_error_price(token_symbol, str(e))

    async def close(self):
        if self.session:
            await self.session.close()
            self.session = None
