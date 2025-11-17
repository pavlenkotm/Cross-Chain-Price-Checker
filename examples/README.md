# Examples

This directory contains example scripts demonstrating how to use the Cross-Chain Price Checker library.

## Basic Usage

Run the basic usage example:

```bash
python examples/basic_usage.py
```

This example demonstrates:
- Checking price for a single token
- Displaying price statistics
- Identifying arbitrage opportunities
- Checking multiple tokens at once

## Custom Configuration

You can create custom examples with specific configurations:

```python
import asyncio
from cross_chain_price_checker import PriceChecker
from cross_chain_price_checker.config import Config

async def main():
    # Create custom config
    config = Config(config_path="my_config.yaml")

    # Initialize checker with custom config
    checker = PriceChecker(config)

    # Check token price
    analysis = await checker.check_token_price("SOL")

    # Process results...

    await checker.close()

asyncio.run(main())
```

## Notes

- Make sure you have installed the package: `pip install -e .`
- Configure your RPC endpoints in `.env` for better performance
- The examples use CEX APIs which don't require authentication for public data
- DEX prices require RPC access to Ethereum, BSC, and Solana networks
