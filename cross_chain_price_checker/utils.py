"""Utility functions for Cross-Chain Price Checker."""

import asyncio
from typing import Any, Callable, TypeVar, Optional
from functools import wraps
from loguru import logger

T = TypeVar('T')


def retry_on_failure(max_retries: int = 3, delay: float = 1.0):
    """
    Decorator to retry a function on failure.

    Args:
        max_retries: Maximum number of retry attempts
        delay: Delay between retries in seconds
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_retries):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_retries - 1:
                        logger.warning(
                            f"Attempt {attempt + 1}/{max_retries} failed for {func.__name__}: {e}. Retrying..."
                        )
                        await asyncio.sleep(delay * (attempt + 1))
                    else:
                        logger.error(f"All {max_retries} attempts failed for {func.__name__}: {e}")
            raise last_exception

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_retries - 1:
                        logger.warning(
                            f"Attempt {attempt + 1}/{max_retries} failed for {func.__name__}: {e}. Retrying..."
                        )
                        import time
                        time.sleep(delay * (attempt + 1))
                    else:
                        logger.error(f"All {max_retries} attempts failed for {func.__name__}: {e}")
            raise last_exception

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator


def format_price(price: Optional[float], decimals: int = 6) -> str:
    """
    Format price for display.

    Args:
        price: Price value
        decimals: Number of decimal places

    Returns:
        Formatted price string
    """
    if price is None:
        return "N/A"
    if price == 0:
        return "0.00"

    # For very small numbers, use scientific notation
    if price < 0.000001:
        return f"{price:.2e}"

    # For normal numbers, use fixed decimal places
    return f"${price:.{decimals}f}"


def calculate_price_difference(price1: float, price2: float) -> float:
    """
    Calculate percentage difference between two prices.

    Args:
        price1: First price
        price2: Second price

    Returns:
        Percentage difference (positive if price1 > price2)
    """
    if price2 == 0:
        return 0.0
    return ((price1 - price2) / price2) * 100


def get_price_color(diff_percent: float, threshold: float = 0.5) -> str:
    """
    Get color code for price difference.

    Args:
        diff_percent: Price difference percentage
        threshold: Threshold for highlighting

    Returns:
        Color name for Rich formatting
    """
    abs_diff = abs(diff_percent)
    if abs_diff >= threshold * 3:
        return "bright_red" if diff_percent > 0 else "bright_green"
    elif abs_diff >= threshold * 2:
        return "red" if diff_percent > 0 else "green"
    elif abs_diff >= threshold:
        return "yellow"
    return "white"


class AsyncCache:
    """Simple async cache for API results."""

    def __init__(self, ttl: int = 60):
        """
        Initialize cache.

        Args:
            ttl: Time-to-live in seconds
        """
        self.ttl = ttl
        self._cache = {}
        self._timestamps = {}

    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache if not expired."""
        import time
        if key in self._cache:
            if time.time() - self._timestamps[key] < self.ttl:
                return self._cache[key]
            else:
                del self._cache[key]
                del self._timestamps[key]
        return None

    async def set(self, key: str, value: Any):
        """Set value in cache."""
        import time
        self._cache[key] = value
        self._timestamps[key] = time.time()

    def clear(self):
        """Clear all cache."""
        self._cache.clear()
        self._timestamps.clear()
