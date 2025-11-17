"""
Cross-Chain Price Checker

A Python library for comparing token prices across multiple DEXs and CEXs
to identify arbitrage opportunities.
"""

__version__ = "0.1.0"
__author__ = "Cross-Chain Price Checker Contributors"

from .price_checker import PriceChecker
from .token_resolver import TokenResolver

__all__ = ["PriceChecker", "TokenResolver"]
