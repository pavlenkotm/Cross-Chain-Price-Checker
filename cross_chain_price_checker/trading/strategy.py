"""Trading strategies for simulation and automation."""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional
from datetime import datetime
from loguru import logger


class Strategy(ABC):
    """Base class for trading strategies."""

    def __init__(self, name: str):
        """
        Initialize strategy.

        Args:
            name: Strategy name
        """
        self.name = name

    @abstractmethod
    async def should_buy(
        self,
        token: str,
        current_price: float,
        prices: Dict[str, float],
        timestamp: datetime,
    ) -> Optional[tuple[str, float]]:
        """
        Determine if should buy.

        Args:
            token: Token symbol
            current_price: Current price
            prices: All current prices by exchange
            timestamp: Current timestamp

        Returns:
            Tuple of (exchange, amount) if should buy, None otherwise
        """
        pass

    @abstractmethod
    async def should_sell(
        self,
        token: str,
        held_amount: float,
        current_price: float,
        prices: Dict[str, float],
        timestamp: datetime,
    ) -> Optional[tuple[str, float]]:
        """
        Determine if should sell.

        Args:
            token: Token symbol
            held_amount: Amount currently held
            current_price: Current price
            prices: All current prices by exchange
            timestamp: Current timestamp

        Returns:
            Tuple of (exchange, amount) if should sell, None otherwise
        """
        pass


class SimpleArbitrageStrategy(Strategy):
    """Simple arbitrage strategy - buy low, sell high across exchanges."""

    def __init__(
        self,
        min_profit_percent: float = 1.0,
        max_position_percent: float = 10.0,
    ):
        """
        Initialize arbitrage strategy.

        Args:
            min_profit_percent: Minimum profit percentage to execute trade
            max_position_percent: Maximum percentage of balance to use per position
        """
        super().__init__("Simple Arbitrage")
        self.min_profit_percent = min_profit_percent
        self.max_position_percent = max_position_percent

    async def should_buy(
        self,
        token: str,
        current_price: float,
        prices: Dict[str, float],
        timestamp: datetime,
    ) -> Optional[tuple[str, float]]:
        """Buy on the lowest priced exchange if arbitrage opportunity exists."""

        if not prices:
            return None

        # Find min and max prices
        min_price = min(prices.values())
        max_price = max(prices.values())

        # Calculate potential profit
        profit_percent = ((max_price - min_price) / min_price) * 100

        if profit_percent >= self.min_profit_percent:
            # Find exchange with lowest price
            buy_exchange = min(prices.items(), key=lambda x: x[1])[0]

            # Calculate amount to buy (simplified - fixed percentage of balance)
            # In real implementation, would calculate based on current balance
            amount = 1.0  # Placeholder

            logger.info(
                f"Arbitrage opportunity: Buy {token} on {buy_exchange} at ${min_price:.6f}, "
                f"sell at ${max_price:.6f} for {profit_percent:.2f}% profit"
            )

            return (buy_exchange, amount)

        return None

    async def should_sell(
        self,
        token: str,
        held_amount: float,
        current_price: float,
        prices: Dict[str, float],
        timestamp: datetime,
    ) -> Optional[tuple[str, float]]:
        """Sell on the highest priced exchange."""

        if not prices or held_amount <= 0:
            return None

        # Find highest price
        max_price = max(prices.values())
        sell_exchange = max(prices.items(), key=lambda x: x[1])[0]

        # For simplicity, sell all holdings
        return (sell_exchange, held_amount)


class MomentumStrategy(Strategy):
    """Momentum-based trading strategy."""

    def __init__(
        self,
        lookback_periods: int = 10,
        buy_threshold: float = 2.0,
        sell_threshold: float = -1.0,
    ):
        """
        Initialize momentum strategy.

        Args:
            lookback_periods: Number of periods to look back for momentum
            buy_threshold: Price increase % to trigger buy
            sell_threshold: Price decrease % to trigger sell
        """
        super().__init__("Momentum")
        self.lookback_periods = lookback_periods
        self.buy_threshold = buy_threshold
        self.sell_threshold = sell_threshold
        self.price_history: Dict[str, List[float]] = {}

    async def should_buy(
        self,
        token: str,
        current_price: float,
        prices: Dict[str, float],
        timestamp: datetime,
    ) -> Optional[tuple[str, float]]:
        """Buy if price momentum is positive."""

        # Update price history
        if token not in self.price_history:
            self.price_history[token] = []

        self.price_history[token].append(current_price)

        # Keep only lookback periods
        self.price_history[token] = self.price_history[token][-self.lookback_periods:]

        if len(self.price_history[token]) < self.lookback_periods:
            return None  # Not enough history

        # Calculate momentum
        first_price = self.price_history[token][0]
        momentum = ((current_price - first_price) / first_price) * 100

        if momentum >= self.buy_threshold:
            # Buy on any available exchange
            exchange = list(prices.keys())[0] if prices else None
            if exchange:
                return (exchange, 1.0)

        return None

    async def should_sell(
        self,
        token: str,
        held_amount: float,
        current_price: float,
        prices: Dict[str, float],
        timestamp: datetime,
    ) -> Optional[tuple[str, float]]:
        """Sell if momentum turns negative."""

        if token not in self.price_history or len(self.price_history[token]) < self.lookback_periods:
            return None

        # Calculate momentum
        first_price = self.price_history[token][0]
        momentum = ((current_price - first_price) / first_price) * 100

        if momentum <= self.sell_threshold:
            # Sell on any available exchange
            exchange = list(prices.keys())[0] if prices else None
            if exchange:
                return (exchange, held_amount)

        return None
