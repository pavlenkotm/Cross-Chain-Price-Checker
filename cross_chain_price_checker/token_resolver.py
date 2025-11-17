"""Token address resolver using CoinGecko API."""

import aiohttp
from typing import Dict, Optional, List
from loguru import logger
from .utils import retry_on_failure, AsyncCache


class TokenResolver:
    """Resolve token addresses across different blockchains."""

    COINGECKO_BASE_URL = "https://api.coingecko.com/api/v3"

    # Platform IDs used by CoinGecko
    PLATFORM_MAP = {
        'ethereum': 'ethereum',
        'bsc': 'binance-smart-chain',
        'solana': 'solana',
        'polygon': 'polygon-pos',
    }

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize token resolver.

        Args:
            api_key: CoinGecko API key (optional, but recommended for higher rate limits)
        """
        self.api_key = api_key
        self.cache = AsyncCache(ttl=3600)  # Cache for 1 hour
        self.session: Optional[aiohttp.ClientSession] = None

    async def __aenter__(self):
        """Async context manager entry."""
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()

    def _get_headers(self) -> Dict[str, str]:
        """Get request headers with optional API key."""
        headers = {'Accept': 'application/json'}
        if self.api_key:
            headers['x-cg-pro-api-key'] = self.api_key
        return headers

    @retry_on_failure(max_retries=3, delay=1.0)
    async def _make_request(self, endpoint: str, params: Optional[Dict] = None) -> Dict:
        """
        Make request to CoinGecko API.

        Args:
            endpoint: API endpoint
            params: Query parameters

        Returns:
            JSON response
        """
        if not self.session:
            self.session = aiohttp.ClientSession()

        url = f"{self.COINGECKO_BASE_URL}/{endpoint}"
        headers = self._get_headers()

        async with self.session.get(url, headers=headers, params=params, timeout=10) as response:
            response.raise_for_status()
            return await response.json()

    async def search_token(self, query: str) -> Optional[Dict]:
        """
        Search for token by name or symbol.

        Args:
            query: Token name or symbol (e.g., 'SOL', 'Solana')

        Returns:
            Token information or None if not found
        """
        cache_key = f"search_{query.lower()}"
        cached = await self.cache.get(cache_key)
        if cached:
            return cached

        try:
            # First try to get coin list and search
            coins = await self._make_request("coins/list", {"include_platform": "true"})

            # Search by symbol or name (case insensitive)
            query_lower = query.lower()
            for coin in coins:
                if (coin.get('symbol', '').lower() == query_lower or
                    coin.get('name', '').lower() == query_lower or
                    coin.get('id', '').lower() == query_lower):

                    # Get detailed info including platforms
                    coin_info = await self.get_token_info(coin['id'])
                    await self.cache.set(cache_key, coin_info)
                    return coin_info

            logger.warning(f"Token '{query}' not found")
            return None

        except Exception as e:
            logger.error(f"Error searching token '{query}': {e}")
            return None

    async def get_token_info(self, coin_id: str) -> Optional[Dict]:
        """
        Get detailed token information.

        Args:
            coin_id: CoinGecko coin ID

        Returns:
            Token information including addresses on different platforms
        """
        cache_key = f"info_{coin_id}"
        cached = await self.cache.get(cache_key)
        if cached:
            return cached

        try:
            data = await self._make_request(f"coins/{coin_id}", {
                "localization": "false",
                "tickers": "false",
                "market_data": "false",
                "community_data": "false",
                "developer_data": "false"
            })

            token_info = {
                'id': data.get('id'),
                'symbol': data.get('symbol', '').upper(),
                'name': data.get('name'),
                'platforms': {},
            }

            # Extract platform addresses
            platforms = data.get('platforms', {})
            for platform, address in platforms.items():
                if address:  # Skip empty addresses
                    # Map platform names to our standard names
                    for our_name, cg_name in self.PLATFORM_MAP.items():
                        if cg_name == platform:
                            token_info['platforms'][our_name] = address
                            break
                    else:
                        # Keep original platform name if not in our map
                        token_info['platforms'][platform] = address

            await self.cache.set(cache_key, token_info)
            return token_info

        except Exception as e:
            logger.error(f"Error getting token info for '{coin_id}': {e}")
            return None

    async def get_token_address(self, token: str, platform: str) -> Optional[str]:
        """
        Get token contract address on a specific platform.

        Args:
            token: Token symbol or name
            platform: Platform name ('ethereum', 'bsc', 'solana')

        Returns:
            Token address or None if not found
        """
        token_info = await self.search_token(token)
        if not token_info:
            return None

        platform_lower = platform.lower()
        address = token_info.get('platforms', {}).get(platform_lower)

        if not address:
            logger.warning(f"Token '{token}' not found on platform '{platform}'")
            return None

        return address

    async def get_all_addresses(self, token: str) -> Dict[str, str]:
        """
        Get token addresses on all available platforms.

        Args:
            token: Token symbol or name

        Returns:
            Dictionary mapping platform names to addresses
        """
        token_info = await self.search_token(token)
        if not token_info:
            return {}

        return token_info.get('platforms', {})

    async def get_token_symbol_for_cex(self, token: str) -> Optional[str]:
        """
        Get standardized token symbol for CEX APIs.

        Args:
            token: Token symbol or name

        Returns:
            Standardized symbol (e.g., 'SOL', 'BTC')
        """
        token_info = await self.search_token(token)
        if not token_info:
            return None

        return token_info.get('symbol')

    def close(self):
        """Close the HTTP session."""
        if self.session:
            import asyncio
            asyncio.create_task(self.session.close())
