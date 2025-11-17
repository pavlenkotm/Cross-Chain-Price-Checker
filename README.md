# Cross-Chain Price Checker

A powerful Python library and CLI tool for comparing cryptocurrency token prices across multiple decentralized exchanges (DEXs) and centralized exchanges (CEXs) to identify arbitrage opportunities.

## Features

- **Multi-Chain Support**: Compare prices across Ethereum, BSC, and Solana
- **DEX Integration**:
  - Uniswap V2 & V3 (Ethereum)
  - PancakeSwap V2 (BSC)
  - Raydium (Solana)
- **CEX Integration**:
  - Binance
  - Bybit
- **Automatic Token Resolution**: Uses CoinGecko API to resolve token addresses across chains
- **Arbitrage Detection**: Automatically identifies price differences and potential arbitrage opportunities
- **Beautiful CLI**: Rich terminal interface with formatted tables and color-coded results
- **Async Architecture**: Fast concurrent price fetching from all exchanges
- **Configurable**: Flexible YAML configuration for customizing exchanges and RPC endpoints

## Installation

### From Source

```bash
# Clone the repository
git clone https://github.com/pavlenkotm/Cross-Chain-Price-Checker.git
cd Cross-Chain-Price-Checker

# Create a virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install the package
pip install -e .
```

### Using pip (once published)

```bash
pip install cross-chain-price-checker
```

## Quick Start

### Command Line Usage

Check a single token price:

```bash
ccpc check SOL
```

Compare multiple tokens:

```bash
ccpc compare BTC ETH SOL
```

With custom configuration:

```bash
ccpc check ETH --config config.yaml
```

Enable verbose logging:

```bash
ccpc check BTC --verbose
```

### Python Library Usage

```python
import asyncio
from cross_chain_price_checker import PriceChecker

async def main():
    checker = PriceChecker()

    # Check a single token
    analysis = await checker.check_token_price("SOL")

    print(f"Average Price: ${analysis['avg_price']:.6f}")
    print(f"Spread: {analysis['spread_percent']:.2f}%")

    # Show arbitrage opportunities
    for opp in analysis['opportunities']:
        print(f"Buy on {opp.buy_exchange} at ${opp.buy_price:.6f}")
        print(f"Sell on {opp.sell_exchange} at ${opp.sell_price:.6f}")
        print(f"Potential Profit: {opp.potential_profit_percent:.2f}%")

    await checker.close()

asyncio.run(main())
```

## Configuration

### Environment Variables

Create a `.env` file (see `.env.example`):

```env
# RPC Endpoints
ETH_RPC_URL=https://eth.public-rpc.com
BSC_RPC_URL=https://bsc-dataseed.binance.org/
SOLANA_RPC_URL=https://api.mainnet-beta.solana.com

# API Keys (optional but recommended)
COINGECKO_API_KEY=your_api_key_here
BINANCE_API_KEY=your_api_key_here
BYBIT_API_KEY=your_api_key_here
```

### YAML Configuration

Create a `config.yaml` file (see `config.example.yaml`):

```yaml
rpc:
  ethereum: "https://eth.public-rpc.com"
  bsc: "https://bsc-dataseed.binance.org/"
  solana: "https://api.mainnet-beta.solana.com"

exchanges:
  dex:
    uniswap_v2:
      enabled: true
    uniswap_v3:
      enabled: true
    pancakeswap_v2:
      enabled: true
    raydium:
      enabled: true
  cex:
    binance:
      enabled: true
    bybit:
      enabled: true

comparison:
  min_price_difference_percent: 0.5
  timeout_seconds: 10
```

## Supported Exchanges

### Decentralized Exchanges (DEX)

| Exchange | Chain | Protocol | Status |
|----------|-------|----------|--------|
| Uniswap V2 | Ethereum | AMM | ✅ |
| Uniswap V3 | Ethereum | Concentrated Liquidity | ✅ |
| PancakeSwap V2 | BSC | AMM | ✅ |
| Raydium | Solana | AMM | ✅ |

### Centralized Exchanges (CEX)

| Exchange | Type | API Version | Status |
|----------|------|-------------|--------|
| Binance | Spot | V3 | ✅ |
| Bybit | Spot | V5 | ✅ |

## Output Example

```
╭─────────────── Statistics ───────────────╮
│ Valid Prices: 5 / 6                      │
│ Average Price: $142.345678               │
│ Min Price: $141.234567                   │
│ Max Price: $143.456789                   │
│ Spread: 1.57%                            │
╰──────────────────────────────────────────╯

╭────────────────── SOL Price Comparison ──────────────────╮
│ Exchange       │ Type │ Chain    │ Pair      │ Price     │
├────────────────┼──────┼──────────┼───────────┼───────────┤
│ Binance        │ CEX  │ N/A      │ SOL/USDT  │ $143.46   │
│ Bybit          │ CEX  │ N/A      │ SOL/USDT  │ $143.12   │
│ Raydium        │ DEX  │ Solana   │ SOL/USDC  │ $142.89   │
│ Uniswap V3     │ DEX  │ Ethereum │ SOL/USDC  │ $141.67   │
│ PancakeSwap V2 │ DEX  │ BSC      │ SOL/BUSD  │ $141.23   │
╰────────────────────────────────────────────────────────────╯

╭──────────────── Arbitrage Opportunities ────────────────╮
│ # │ Buy From       │ Sell To │ Profit %                │
├───┼────────────────┼─────────┼─────────────────────────┤
│ 1 │ PancakeSwap V2 │ Binance │ +1.58%                  │
│ 2 │ Uniswap V3     │ Binance │ +1.26%                  │
╰─────────────────────────────────────────────────────────╯
```

## Architecture

```
cross_chain_price_checker/
├── __init__.py              # Package initialization
├── config.py                # Configuration management
├── token_resolver.py        # CoinGecko token address resolver
├── price_checker.py         # Main orchestrator
├── utils.py                 # Utility functions
├── cli.py                   # CLI interface
└── exchanges/               # Exchange adapters
    ├── base.py              # Base exchange class
    ├── dex/                 # DEX implementations
    │   ├── uniswap.py
    │   ├── pancakeswap.py
    │   └── raydium.py
    └── cex/                 # CEX implementations
        ├── binance.py
        └── bybit.py
```

## How It Works

1. **Token Resolution**: Input token symbol is resolved to contract addresses on different chains using CoinGecko API
2. **Parallel Price Fetching**: Prices are fetched concurrently from all enabled exchanges
3. **Price Analysis**: Calculate statistics (min, max, average, spread)
4. **Arbitrage Detection**: Identify price differences exceeding the configured threshold
5. **Display**: Show results in a formatted table with color-coded differences

## Use Cases

- **Arbitrage Trading**: Identify price discrepancies across exchanges
- **Market Research**: Compare liquidity and prices across different platforms
- **Price Monitoring**: Track token prices in real-time across multiple sources
- **DeFi Analytics**: Analyze decentralized exchange pricing dynamics

## Performance Considerations

- Uses async/await for concurrent API calls
- Caches token addresses to reduce API calls
- Configurable timeouts and retry logic
- Rate limiting aware (respects exchange API limits)

## Limitations & Disclaimer

- **Gas Fees**: Arbitrage profits shown do not account for transaction fees, gas costs, or slippage
- **Execution Time**: By the time you execute a trade, prices may have changed
- **Liquidity**: Large orders may face slippage not reflected in quoted prices
- **No Financial Advice**: This tool is for informational purposes only

**Always do your own research and understand the risks before trading!**

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

### Adding New Exchanges

1. Create a new class inheriting from `Exchange`
2. Implement `get_price()` and `is_available()` methods
3. Add to the appropriate module (DEX or CEX)
4. Register in `PriceChecker._setup_exchanges()`

## Roadmap

- [ ] Add more DEXs (SushiSwap, Curve, Balancer)
- [ ] Add more CEXs (Kraken, OKX, KuCoin)
- [ ] Support for more chains (Polygon, Avalanche, Arbitrum)
- [ ] WebSocket support for real-time price updates
- [ ] Historical price tracking and charting
- [ ] Telegram bot integration
- [ ] Web UI dashboard
- [ ] Price alerts and notifications

## License

MIT License - see [LICENSE](LICENSE) file for details

## Acknowledgments

- Built with [Web3.py](https://github.com/ethereum/web3.py)
- CLI powered by [Rich](https://github.com/Textualize/rich) and [Typer](https://github.com/tiangolo/typer)
- Token data from [CoinGecko](https://www.coingecko.com/)

## Support

If you find this project useful, please consider giving it a star on GitHub!

For issues and questions, please use the [GitHub Issues](https://github.com/pavlenkotm/Cross-Chain-Price-Checker/issues) page.
