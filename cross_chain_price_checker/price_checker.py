"""Main price checker orchestrator."""

import asyncio
from typing import List, Dict, Optional
from dataclasses import dataclass
from loguru import logger

from .config import Config, get_config
from .token_resolver import TokenResolver
from .exchanges.base import Exchange, ExchangePrice
from .exchanges.dex.uniswap import UniswapV2, UniswapV3
from .exchanges.dex.pancakeswap import PancakeSwapV2
from .exchanges.dex.raydium import Raydium
from .exchanges.cex.binance import Binance
from .exchanges.cex.bybit import Bybit
from .utils import calculate_price_difference


@dataclass
class ArbitrageOpportunity:
    """Represents an arbitrage opportunity between two exchanges."""
    buy_exchange: str
    sell_exchange: str
    buy_price: float
    sell_price: float
    price_difference_percent: float
    potential_profit_percent: float

    def __repr__(self) -> str:
        return (
            f"Buy on {self.buy_exchange} at ${self.buy_price:.6f}, "
            f"Sell on {self.sell_exchange} at ${self.sell_price:.6f} "
            f"(+{self.potential_profit_percent:.2f}%)"
        )


class PriceChecker:
    """Main price checker orchestrator."""

    def __init__(self, config: Optional[Config] = None):
        """
        Initialize price checker.

        Args:
            config: Configuration object. If None, uses default config.
        """
        self.config = config or get_config()
        self.token_resolver = TokenResolver(self.config.get_api_key('coingecko'))
        self.exchanges: List[Exchange] = []
        self._setup_exchanges()

    def _setup_exchanges(self):
        """Set up all enabled exchanges."""
        # DEX exchanges
        if self.config.is_exchange_enabled('dex', 'uniswap_v2'):
            eth_rpc = self.config.get_rpc_url('ethereum')
            factory = self.config.get('exchanges.dex.uniswap_v2.factory')
            router = self.config.get('exchanges.dex.uniswap_v2.router')
            self.exchanges.append(UniswapV2(eth_rpc, factory, router))

        if self.config.is_exchange_enabled('dex', 'uniswap_v3'):
            eth_rpc = self.config.get_rpc_url('ethereum')
            quoter = self.config.get('exchanges.dex.uniswap_v3.quoter')
            self.exchanges.append(UniswapV3(eth_rpc, quoter))

        if self.config.is_exchange_enabled('dex', 'pancakeswap_v2'):
            bsc_rpc = self.config.get_rpc_url('bsc')
            factory = self.config.get('exchanges.dex.pancakeswap_v2.factory')
            router = self.config.get('exchanges.dex.pancakeswap_v2.router')
            self.exchanges.append(PancakeSwapV2(bsc_rpc, factory, router))

        if self.config.is_exchange_enabled('dex', 'raydium'):
            sol_rpc = self.config.get_rpc_url('solana')
            self.exchanges.append(Raydium(sol_rpc))

        # CEX exchanges
        if self.config.is_exchange_enabled('cex', 'binance'):
            api_key = self.config.get_api_key('binance')
            base_url = self.config.get('exchanges.cex.binance.base_url')
            self.exchanges.append(Binance(api_key, base_url))

        if self.config.is_exchange_enabled('cex', 'bybit'):
            api_key = self.config.get_api_key('bybit')
            base_url = self.config.get('exchanges.cex.bybit.base_url')
            self.exchanges.append(Bybit(api_key, base_url))

        logger.info(f"Initialized {len(self.exchanges)} exchanges")

    async def get_token_prices(self, token: str) -> List[ExchangePrice]:
        """
        Get token prices from all exchanges.

        Args:
            token: Token symbol or name (e.g., 'SOL', 'BTC')

        Returns:
            List of ExchangePrice objects
        """
        logger.info(f"Fetching prices for {token}...")

        # Resolve token addresses and symbol
        async with self.token_resolver:
            token_info = await self.token_resolver.search_token(token)
            if not token_info:
                logger.error(f"Could not resolve token: {token}")
                return []

            token_symbol = token_info['symbol']
            addresses = token_info.get('platforms', {})

            logger.info(f"Resolved {token} to {token_symbol}")
            logger.debug(f"Addresses: {addresses}")

        # Fetch prices from all exchanges concurrently
        tasks = []
        for exchange in self.exchanges:
            if exchange.exchange_type.value == "DEX":
                # DEX needs token address
                if isinstance(exchange, (UniswapV2, UniswapV3)):
                    token_address = addresses.get('ethereum')
                    if token_address:
                        tasks.append(exchange.get_price(token_address, token_symbol))
                elif isinstance(exchange, PancakeSwapV2):
                    token_address = addresses.get('bsc')
                    if token_address:
                        tasks.append(exchange.get_price(token_address, token_symbol))
                elif isinstance(exchange, Raydium):
                    token_address = addresses.get('solana')
                    if token_address:
                        tasks.append(exchange.get_price(token_address, token_symbol))
            else:
                # CEX uses symbol
                tasks.append(exchange.get_price(token_symbol))

        if not tasks:
            logger.warning("No exchanges available for this token")
            return []

        # Execute all price fetches concurrently
        prices = await asyncio.gather(*tasks, return_exceptions=True)

        # Filter out exceptions and invalid prices
        valid_prices = []
        for price in prices:
            if isinstance(price, ExchangePrice):
                valid_prices.append(price)
            elif isinstance(price, Exception):
                logger.error(f"Error fetching price: {price}")

        logger.info(f"Successfully fetched {len(valid_prices)} prices")
        return valid_prices

    def analyze_prices(self, prices: List[ExchangePrice]) -> Dict:
        """
        Analyze prices and find arbitrage opportunities.

        Args:
            prices: List of ExchangePrice objects

        Returns:
            Analysis dictionary with stats and opportunities
        """
        valid_prices = [p for p in prices if p.is_valid]

        if not valid_prices:
            return {
                'count': 0,
                'valid_count': 0,
                'error_count': len(prices),
                'prices': prices,
                'opportunities': []
            }

        # Calculate statistics
        price_values = [p.price for p in valid_prices]
        min_price = min(price_values)
        max_price = max(price_values)
        avg_price = sum(price_values) / len(price_values)
        spread_percent = ((max_price - min_price) / min_price) * 100

        # Find arbitrage opportunities
        opportunities = []
        min_diff = self.config.get('comparison.min_price_difference_percent', 0.5)

        for i, price1 in enumerate(valid_prices):
            for price2 in valid_prices[i + 1:]:
                diff_percent = abs(calculate_price_difference(price1.price, price2.price))

                if diff_percent >= min_diff:
                    # Determine buy/sell exchanges
                    if price1.price < price2.price:
                        buy_exchange = price1.exchange_name
                        sell_exchange = price2.exchange_name
                        buy_price = price1.price
                        sell_price = price2.price
                    else:
                        buy_exchange = price2.exchange_name
                        sell_exchange = price1.exchange_name
                        buy_price = price2.price
                        sell_price = price1.price

                    profit_percent = ((sell_price - buy_price) / buy_price) * 100

                    opportunities.append(ArbitrageOpportunity(
                        buy_exchange=buy_exchange,
                        sell_exchange=sell_exchange,
                        buy_price=buy_price,
                        sell_price=sell_price,
                        price_difference_percent=diff_percent,
                        potential_profit_percent=profit_percent
                    ))

        # Sort opportunities by profit potential
        opportunities.sort(key=lambda x: x.potential_profit_percent, reverse=True)

        return {
            'count': len(prices),
            'valid_count': len(valid_prices),
            'error_count': len(prices) - len(valid_prices),
            'min_price': min_price,
            'max_price': max_price,
            'avg_price': avg_price,
            'spread_percent': spread_percent,
            'prices': prices,
            'opportunities': opportunities
        }

    async def check_token_price(self, token: str) -> Dict:
        """
        Check token price across all exchanges and analyze.

        Args:
            token: Token symbol or name

        Returns:
            Analysis dictionary
        """
        prices = await self.get_token_prices(token)
        return self.analyze_prices(prices)

    async def check_multiple_tokens(self, tokens: List[str]) -> Dict[str, Dict]:
        """
        Check prices for multiple tokens.

        Args:
            tokens: List of token symbols or names

        Returns:
            Dictionary mapping token to analysis
        """
        results = {}
        for token in tokens:
            try:
                results[token] = await self.check_token_price(token)
            except Exception as e:
                logger.error(f"Error checking price for {token}: {e}")
                results[token] = {'error': str(e)}

        return results

    async def close(self):
        """Close all exchange connections."""
        for exchange in self.exchanges:
            if hasattr(exchange, 'close'):
                await exchange.close()

        if hasattr(self.token_resolver, 'close'):
            self.token_resolver.close()
