"""Uniswap V2 and V3 price fetchers."""

from typing import Optional
from web3 import Web3
from loguru import logger

from ..base import Exchange, ExchangePrice, ExchangeType
from ...utils import retry_on_failure


# Minimal ABI for getting reserves and price
PAIR_ABI = [
    {
        "constant": True,
        "inputs": [],
        "name": "getReserves",
        "outputs": [
            {"internalType": "uint112", "name": "_reserve0", "type": "uint112"},
            {"internalType": "uint112", "name": "_reserve1", "type": "uint112"},
            {"internalType": "uint32", "name": "_blockTimestampLast", "type": "uint32"}
        ],
        "payable": False,
        "stateMutability": "view",
        "type": "function"
    },
    {
        "constant": True,
        "inputs": [],
        "name": "token0",
        "outputs": [{"internalType": "address", "name": "", "type": "address"}],
        "payable": False,
        "stateMutability": "view",
        "type": "function"
    },
    {
        "constant": True,
        "inputs": [],
        "name": "token1",
        "outputs": [{"internalType": "address", "name": "", "type": "address"}],
        "payable": False,
        "stateMutability": "view",
        "type": "function"
    }
]

FACTORY_ABI = [
    {
        "constant": True,
        "inputs": [
            {"internalType": "address", "name": "", "type": "address"},
            {"internalType": "address", "name": "", "type": "address"}
        ],
        "name": "getPair",
        "outputs": [{"internalType": "address", "name": "", "type": "address"}],
        "payable": False,
        "stateMutability": "view",
        "type": "function"
    }
]

QUOTER_V3_ABI = [
    {
        "inputs": [
            {"internalType": "address", "name": "tokenIn", "type": "address"},
            {"internalType": "address", "name": "tokenOut", "type": "address"},
            {"internalType": "uint24", "name": "fee", "type": "uint24"},
            {"internalType": "uint256", "name": "amountIn", "type": "uint256"},
            {"internalType": "uint160", "name": "sqrtPriceLimitX96", "type": "uint160"}
        ],
        "name": "quoteExactInputSingle",
        "outputs": [{"internalType": "uint256", "name": "amountOut", "type": "uint256"}],
        "stateMutability": "nonpayable",
        "type": "function"
    }
]

# Common stablecoin addresses on Ethereum
USDC_ADDRESS = "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48"
USDT_ADDRESS = "0xdAC17F958D2ee523a2206206994597C13D831ec7"
WETH_ADDRESS = "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2"


class UniswapV2(Exchange):
    """Uniswap V2 price fetcher."""

    def __init__(self, rpc_url: str, factory_address: str, router_address: str):
        """
        Initialize Uniswap V2 adapter.

        Args:
            rpc_url: Ethereum RPC URL
            factory_address: Uniswap V2 factory contract address
            router_address: Uniswap V2 router contract address
        """
        super().__init__("Uniswap V2", ExchangeType.DEX)
        self.w3 = Web3(Web3.HTTPProvider(rpc_url))
        self.factory_address = Web3.to_checksum_address(factory_address)
        self.router_address = Web3.to_checksum_address(router_address)
        self.factory = self.w3.eth.contract(address=self.factory_address, abi=FACTORY_ABI)

    async def is_available(self) -> bool:
        """Check if Uniswap V2 is available."""
        try:
            return self.w3.is_connected()
        except Exception:
            return False

    @retry_on_failure(max_retries=3, delay=1.0)
    async def get_price(self, token_address: str, token_symbol: str = "TOKEN", **kwargs) -> ExchangePrice:
        """
        Get token price from Uniswap V2.

        Args:
            token_address: Token contract address
            token_symbol: Token symbol
            **kwargs: Additional parameters

        Returns:
            ExchangePrice object
        """
        try:
            token_address = Web3.to_checksum_address(token_address)

            # Try USDC pair first, then USDT, then WETH
            quote_tokens = [
                (USDC_ADDRESS, "USDC", 6),
                (USDT_ADDRESS, "USDT", 6),
                (WETH_ADDRESS, "WETH", 18)
            ]

            for quote_addr, quote_symbol, quote_decimals in quote_tokens:
                try:
                    price = await self._get_pair_price(token_address, quote_addr, quote_decimals)
                    if price:
                        return ExchangePrice(
                            exchange_name=self.name,
                            exchange_type=self.exchange_type,
                            price=price,
                            token_symbol=token_symbol,
                            chain="Ethereum",
                            pair=f"{token_symbol}/{quote_symbol}"
                        )
                except Exception as e:
                    logger.debug(f"Failed to get {token_symbol}/{quote_symbol} price on Uniswap V2: {e}")
                    continue

            return self._create_error_price(token_symbol, "No liquid pairs found")

        except Exception as e:
            logger.error(f"Error getting Uniswap V2 price for {token_symbol}: {e}")
            return self._create_error_price(token_symbol, str(e))

    async def _get_pair_price(self, token_address: str, quote_address: str, quote_decimals: int) -> Optional[float]:
        """Get price from a specific pair."""
        # Get pair address
        pair_address = self.factory.functions.getPair(token_address, quote_address).call()

        if pair_address == "0x0000000000000000000000000000000000000000":
            return None

        # Get pair contract
        pair = self.w3.eth.contract(address=pair_address, abi=PAIR_ABI)

        # Get reserves
        reserves = pair.functions.getReserves().call()
        reserve0, reserve1, _ = reserves

        # Get token order
        token0 = pair.functions.token0().call()

        # Calculate price based on token order
        if token0.lower() == token_address.lower():
            # Token is token0
            price = (reserve1 / (10 ** quote_decimals)) / (reserve0 / (10 ** 18))
        else:
            # Token is token1
            price = (reserve0 / (10 ** quote_decimals)) / (reserve1 / (10 ** 18))

        # If quoted in WETH, multiply by ETH price (approximate)
        if quote_address == WETH_ADDRESS:
            # For simplicity, we'll return the ETH price
            # In production, you'd want to fetch the ETH/USD price
            pass

        return price if price > 0 else None


class UniswapV3(Exchange):
    """Uniswap V3 price fetcher."""

    # Common fee tiers (in basis points)
    FEE_TIERS = [100, 500, 3000, 10000]  # 0.01%, 0.05%, 0.3%, 1%

    def __init__(self, rpc_url: str, quoter_address: str):
        """
        Initialize Uniswap V3 adapter.

        Args:
            rpc_url: Ethereum RPC URL
            quoter_address: Uniswap V3 Quoter contract address
        """
        super().__init__("Uniswap V3", ExchangeType.DEX)
        self.w3 = Web3(Web3.HTTPProvider(rpc_url))
        self.quoter_address = Web3.to_checksum_address(quoter_address)
        self.quoter = self.w3.eth.contract(address=self.quoter_address, abi=QUOTER_V3_ABI)

    async def is_available(self) -> bool:
        """Check if Uniswap V3 is available."""
        try:
            return self.w3.is_connected()
        except Exception:
            return False

    @retry_on_failure(max_retries=3, delay=1.0)
    async def get_price(self, token_address: str, token_symbol: str = "TOKEN", **kwargs) -> ExchangePrice:
        """
        Get token price from Uniswap V3.

        Args:
            token_address: Token contract address
            token_symbol: Token symbol
            **kwargs: Additional parameters

        Returns:
            ExchangePrice object
        """
        try:
            token_address = Web3.to_checksum_address(token_address)

            # Try different stablecoin pairs
            quote_tokens = [
                (USDC_ADDRESS, "USDC", 6),
                (USDT_ADDRESS, "USDT", 6),
            ]

            amount_in = 10 ** 18  # 1 token with 18 decimals

            for quote_addr, quote_symbol, quote_decimals in quote_tokens:
                for fee_tier in self.FEE_TIERS:
                    try:
                        # Try to get quote
                        amount_out = self.quoter.functions.quoteExactInputSingle(
                            token_address,
                            quote_addr,
                            fee_tier,
                            amount_in,
                            0  # sqrtPriceLimitX96 = 0 means no limit
                        ).call()

                        if amount_out > 0:
                            price = amount_out / (10 ** quote_decimals)
                            return ExchangePrice(
                                exchange_name=self.name,
                                exchange_type=self.exchange_type,
                                price=price,
                                token_symbol=token_symbol,
                                chain="Ethereum",
                                pair=f"{token_symbol}/{quote_symbol}"
                            )
                    except Exception:
                        continue

            return self._create_error_price(token_symbol, "No liquid pools found")

        except Exception as e:
            logger.error(f"Error getting Uniswap V3 price for {token_symbol}: {e}")
            return self._create_error_price(token_symbol, str(e))
