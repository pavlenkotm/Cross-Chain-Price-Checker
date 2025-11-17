"""Base classes for exchange adapters."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional
from enum import Enum


class ExchangeType(Enum):
    """Type of exchange."""
    DEX = "DEX"
    CEX = "CEX"


@dataclass
class ExchangePrice:
    """Price information from an exchange."""
    exchange_name: str
    exchange_type: ExchangeType
    price: Optional[float]
    token_symbol: str
    chain: Optional[str] = None
    pair: Optional[str] = None
    liquidity: Optional[float] = None
    error: Optional[str] = None

    @property
    def is_valid(self) -> bool:
        """Check if price is valid."""
        return self.price is not None and self.price > 0 and self.error is None

    def __repr__(self) -> str:
        if self.is_valid:
            return f"<{self.exchange_name}: ${self.price:.6f}>"
        return f"<{self.exchange_name}: Error - {self.error}>"


class Exchange(ABC):
    """Base class for all exchange adapters."""

    def __init__(self, name: str, exchange_type: ExchangeType):
        """
        Initialize exchange adapter.

        Args:
            name: Exchange name
            exchange_type: Type of exchange (DEX or CEX)
        """
        self.name = name
        self.exchange_type = exchange_type

    @abstractmethod
    async def get_price(self, token_address: str, **kwargs) -> ExchangePrice:
        """
        Get token price from exchange.

        Args:
            token_address: Token contract address or symbol
            **kwargs: Additional parameters specific to the exchange

        Returns:
            ExchangePrice object
        """
        pass

    @abstractmethod
    async def is_available(self) -> bool:
        """
        Check if exchange is available.

        Returns:
            True if exchange is accessible
        """
        pass

    def _create_error_price(self, token_symbol: str, error: str) -> ExchangePrice:
        """Create an ExchangePrice object for errors."""
        return ExchangePrice(
            exchange_name=self.name,
            exchange_type=self.exchange_type,
            price=None,
            token_symbol=token_symbol,
            error=error
        )
