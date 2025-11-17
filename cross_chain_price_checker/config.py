"""Configuration management for Cross-Chain Price Checker."""

import os
import yaml
from pathlib import Path
from typing import Dict, Any, Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class Config:
    """Configuration manager for the price checker."""

    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize configuration.

        Args:
            config_path: Path to YAML configuration file. If None, uses default settings.
        """
        self.config_path = config_path
        self.config = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from file or use defaults."""
        if self.config_path and os.path.exists(self.config_path):
            with open(self.config_path, 'r') as f:
                return yaml.safe_load(f)
        return self._get_default_config()

    def _get_default_config(self) -> Dict[str, Any]:
        """Return default configuration."""
        return {
            'rpc': {
                'ethereum': os.getenv('ETH_RPC_URL', 'https://eth.public-rpc.com'),
                'bsc': os.getenv('BSC_RPC_URL', 'https://bsc-dataseed.binance.org/'),
                'solana': os.getenv('SOLANA_RPC_URL', 'https://api.mainnet-beta.solana.com'),
            },
            'api_keys': {
                'coingecko': os.getenv('COINGECKO_API_KEY', ''),
                'binance': os.getenv('BINANCE_API_KEY', ''),
                'bybit': os.getenv('BYBIT_API_KEY', ''),
            },
            'exchanges': {
                'dex': {
                    'uniswap_v2': {
                        'enabled': True,
                        'router': '0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D',
                        'factory': '0x5C69bEe701ef814a2B6a3EDD4B1652CB9cc5aA6f',
                    },
                    'uniswap_v3': {
                        'enabled': True,
                        'router': '0xE592427A0AEce92De3Edee1F18E0157C05861564',
                        'factory': '0x1F98431c8aD98523631AE4a59f267346ea31F984',
                        'quoter': '0xb27308f9F90D607463bb33eA1BeBb41C27CE5AB6',
                    },
                    'pancakeswap_v2': {
                        'enabled': True,
                        'router': '0x10ED43C718714eb63d5aA57B78B54704E256024E',
                        'factory': '0xcA143Ce32Fe78f1f7019d7d551a6402fC5350c73',
                    },
                    'raydium': {
                        'enabled': True,
                        'program_id': '675kPX9MHTjS2zt1qfr1NYHuzeLXfQM9H24wFSUt1Mp8',
                    },
                },
                'cex': {
                    'binance': {
                        'enabled': True,
                        'base_url': 'https://api.binance.com',
                    },
                    'bybit': {
                        'enabled': True,
                        'base_url': 'https://api.bybit.com',
                    },
                },
            },
            'comparison': {
                'min_price_difference_percent': 0.5,
                'timeout_seconds': 10,
                'max_retries': 3,
            },
            'display': {
                'show_all_exchanges': True,
                'sort_by': 'price_diff',
                'highlight_arbitrage': True,
            },
        }

    def get(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value by key.

        Args:
            key: Configuration key (supports dot notation, e.g., 'rpc.ethereum')
            default: Default value if key not found

        Returns:
            Configuration value
        """
        keys = key.split('.')
        value = self.config
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
            else:
                return default
            if value is None:
                return default
        return value

    def get_rpc_url(self, chain: str) -> str:
        """Get RPC URL for a specific chain."""
        return self.get(f'rpc.{chain}', '')

    def get_api_key(self, service: str) -> str:
        """Get API key for a specific service."""
        return self.get(f'api_keys.{service}', '')

    def is_exchange_enabled(self, exchange_type: str, exchange_name: str) -> bool:
        """Check if an exchange is enabled."""
        return self.get(f'exchanges.{exchange_type}.{exchange_name}.enabled', False)


# Global configuration instance
_config_instance: Optional[Config] = None


def get_config(config_path: Optional[str] = None) -> Config:
    """
    Get or create global configuration instance.

    Args:
        config_path: Path to configuration file

    Returns:
        Config instance
    """
    global _config_instance
    if _config_instance is None:
        _config_instance = Config(config_path)
    return _config_instance
