"""Trading simulator for backtesting strategies."""

from typing import List, Dict, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass
from loguru import logger

from ..database import get_db, PriceHistory, Trade
from sqlalchemy import select, and_


@dataclass
class SimulationResult:
    """Results from a trading simulation."""
    initial_balance: float
    final_balance: float
    total_profit: float
    profit_percent: float
    trades_executed: int
    winning_trades: int
    losing_trades: int
    avg_profit_per_trade: float
    max_drawdown: float
    sharpe_ratio: float


class TradingSimulator:
    """Simulate trading strategies using historical data."""

    def __init__(self, initial_balance: float = 10000.0, fee_percent: float = 0.1):
        """
        Initialize trading simulator.

        Args:
            initial_balance: Starting capital in USD
            fee_percent: Trading fee percentage (default: 0.1%)
        """
        self.initial_balance = initial_balance
        self.current_balance = initial_balance
        self.fee_percent = fee_percent
        self.positions: Dict[str, float] = {}  # token -> amount
        self.trades: List[Dict] = []

    async def get_historical_prices(
        self,
        token: str,
        exchange: str,
        start_time: datetime,
        end_time: datetime,
    ) -> List[PriceHistory]:
        """
        Get historical prices from database.

        Args:
            token: Token symbol
            exchange: Exchange name
            start_time: Start datetime
            end_time: End datetime

        Returns:
            List of PriceHistory records
        """
        db = get_db()

        async for session in db.get_session():
            query = (
                select(PriceHistory)
                .where(
                    and_(
                        PriceHistory.token_symbol == token.upper(),
                        PriceHistory.exchange_name == exchange,
                        PriceHistory.timestamp >= start_time,
                        PriceHistory.timestamp <= end_time,
                    )
                )
                .order_by(PriceHistory.timestamp.asc())
            )

            result = await session.execute(query)
            return list(result.scalars().all())

    def buy(self, token: str, amount: float, price: float, timestamp: datetime) -> bool:
        """
        Simulate buying a token.

        Args:
            token: Token symbol
            amount: Amount to buy
            price: Price per token
            timestamp: Trade timestamp

        Returns:
            True if trade was successful
        """
        cost = amount * price
        fee = cost * (self.fee_percent / 100)
        total_cost = cost + fee

        if total_cost > self.current_balance:
            logger.warning(f"Insufficient balance for buy: need ${total_cost:.2f}, have ${self.current_balance:.2f}")
            return False

        self.current_balance -= total_cost
        self.positions[token] = self.positions.get(token, 0) + amount

        self.trades.append({
            "type": "buy",
            "token": token,
            "amount": amount,
            "price": price,
            "fee": fee,
            "timestamp": timestamp,
            "balance": self.current_balance,
        })

        logger.debug(f"BUY: {amount} {token} @ ${price:.6f} (fee: ${fee:.2f})")
        return True

    def sell(self, token: str, amount: float, price: float, timestamp: datetime) -> bool:
        """
        Simulate selling a token.

        Args:
            token: Token symbol
            amount: Amount to sell
            price: Price per token
            timestamp: Trade timestamp

        Returns:
            True if trade was successful
        """
        if self.positions.get(token, 0) < amount:
            logger.warning(f"Insufficient {token} for sell: need {amount}, have {self.positions.get(token, 0)}")
            return False

        revenue = amount * price
        fee = revenue * (self.fee_percent / 100)
        net_revenue = revenue - fee

        self.current_balance += net_revenue
        self.positions[token] -= amount

        if self.positions[token] == 0:
            del self.positions[token]

        self.trades.append({
            "type": "sell",
            "token": token,
            "amount": amount,
            "price": price,
            "fee": fee,
            "timestamp": timestamp,
            "balance": self.current_balance,
        })

        logger.debug(f"SELL: {amount} {token} @ ${price:.6f} (fee: ${fee:.2f})")
        return True

    def get_portfolio_value(self, current_prices: Dict[str, float]) -> float:
        """
        Calculate total portfolio value.

        Args:
            current_prices: Dictionary of token -> price

        Returns:
            Total portfolio value in USD
        """
        total = self.current_balance

        for token, amount in self.positions.items():
            if token in current_prices:
                total += amount * current_prices[token]

        return total

    def calculate_results(self) -> SimulationResult:
        """
        Calculate simulation results.

        Returns:
            SimulationResult object
        """
        total_profit = self.current_balance - self.initial_balance
        profit_percent = (total_profit / self.initial_balance) * 100

        winning_trades = 0
        losing_trades = 0
        profits = []

        # Calculate per-trade profits (simplified - matching buys with sells)
        for i, trade in enumerate(self.trades):
            if trade['type'] == 'sell' and i > 0:
                # Find corresponding buy
                for prev_trade in reversed(self.trades[:i]):
                    if prev_trade['type'] == 'buy' and prev_trade['token'] == trade['token']:
                        profit = (trade['price'] - prev_trade['price']) * trade['amount']
                        profit -= trade['fee'] + prev_trade['fee']
                        profits.append(profit)

                        if profit > 0:
                            winning_trades += 1
                        else:
                            losing_trades += 1
                        break

        avg_profit = sum(profits) / len(profits) if profits else 0

        # Calculate max drawdown
        max_balance = self.initial_balance
        max_drawdown = 0

        for trade in self.trades:
            balance = trade['balance']
            max_balance = max(max_balance, balance)
            drawdown = (max_balance - balance) / max_balance * 100
            max_drawdown = max(max_drawdown, drawdown)

        # Simplified Sharpe ratio (assuming 0% risk-free rate)
        import statistics
        sharpe_ratio = 0
        if len(profits) > 1:
            avg_return = statistics.mean(profits)
            std_return = statistics.stdev(profits)
            if std_return > 0:
                sharpe_ratio = avg_return / std_return

        return SimulationResult(
            initial_balance=self.initial_balance,
            final_balance=self.current_balance,
            total_profit=total_profit,
            profit_percent=profit_percent,
            trades_executed=len(self.trades),
            winning_trades=winning_trades,
            losing_trades=losing_trades,
            avg_profit_per_trade=avg_profit,
            max_drawdown=max_drawdown,
            sharpe_ratio=sharpe_ratio,
        )

    def reset(self):
        """Reset simulator to initial state."""
        self.current_balance = self.initial_balance
        self.positions = {}
        self.trades = []
