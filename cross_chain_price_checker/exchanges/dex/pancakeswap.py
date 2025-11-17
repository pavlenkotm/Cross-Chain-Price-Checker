"""PancakeSwap V2 price fetcher."""

from typing import Optional
from web3 import Web3
from loguru import logger

from ..base import Exchange, ExchangePrice, ExchangeType
from ...utils import retry_on_failure


# Minimal ABI for getting reserves
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

# Common stablecoin addresses on BSC
BUSD_ADDRESS = "0xe9e7CEA3DedcA5984780Bafc599bD69ADd087D56"
USDT_ADDRESS = "0x55d398326f99059fF775485246999027B3197955"
USDC_ADDRESS = "0x8AC76a51cc950d9822D68b83fE1Ad97B32Cd580d"
WBNB_ADDRESS = "0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c"


class PancakeSwapV2(Exchange):
    """PancakeSwap V2 price fetcher."""

    def __init__(self, rpc_url: str, factory_address: str, router_address: str):
        """
        Initialize PancakeSwap V2 adapter.

        Args:
            rpc_url: BSC RPC URL
            factory_address: PancakeSwap V2 factory contract address
            router_address: PancakeSwap V2 router contract address
        """
        super().__init__("PancakeSwap V2", ExchangeType.DEX)
        self.w3 = Web3(Web3.HTTPProvider(rpc_url))
        self.factory_address = Web3.to_checksum_address(factory_address)
        self.router_address = Web3.to_checksum_address(router_address)
        self.factory = self.w3.eth.contract(address=self.factory_address, abi=FACTORY_ABI)

    async def is_available(self) -> bool:
        """Check if PancakeSwap V2 is available."""
        try:
            return self.w3.is_connected()
        except Exception:
            return False

    @retry_on_failure(max_retries=3, delay=1.0)
    async def get_price(self, token_address: str, token_symbol: str = "TOKEN", **kwargs) -> ExchangePrice:
        """
        Get token price from PancakeSwap V2.

        Args:
            token_address: Token contract address on BSC
            token_symbol: Token symbol
            **kwargs: Additional parameters

        Returns:
            ExchangePrice object
        """
        try:
            token_address = Web3.to_checksum_address(token_address)

            # Try BUSD pair first, then USDT, then USDC, then WBNB
            quote_tokens = [
                (BUSD_ADDRESS, "BUSD", 18),
                (USDT_ADDRESS, "USDT", 18),
                (USDC_ADDRESS, "USDC", 18),
                (WBNB_ADDRESS, "WBNB", 18)
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
                            chain="BSC",
                            pair=f"{token_symbol}/{quote_symbol}"
                        )
                except Exception as e:
                    logger.debug(f"Failed to get {token_symbol}/{quote_symbol} price on PancakeSwap: {e}")
                    continue

            return self._create_error_price(token_symbol, "No liquid pairs found")

        except Exception as e:
            logger.error(f"Error getting PancakeSwap V2 price for {token_symbol}: {e}")
            return self._create_error_price(token_symbol, str(e))

    async def _get_pair_price(self, token_address: str, quote_address: str, quote_decimals: int) -> Optional[float]:
        """Get price from a specific pair."""
        try:
            # Get pair address
            pair_address = self.factory.functions.getPair(token_address, quote_address).call()

            if pair_address == "0x0000000000000000000000000000000000000000":
                return None

            # Get pair contract
            pair = self.w3.eth.contract(address=pair_address, abi=PAIR_ABI)

            # Get reserves
            reserves = pair.functions.getReserves().call()
            reserve0, reserve1, _ = reserves

            if reserve0 == 0 or reserve1 == 0:
                return None

            # Get token order
            token0 = pair.functions.token0().call()

            # Calculate price based on token order
            if token0.lower() == token_address.lower():
                # Token is token0
                price = (reserve1 / (10 ** quote_decimals)) / (reserve0 / (10 ** 18))
            else:
                # Token is token1
                price = (reserve0 / (10 ** quote_decimals)) / (reserve1 / (10 ** 18))

            return price if price > 0 else None

        except Exception as e:
            logger.debug(f"Error getting pair price: {e}")
            return None
