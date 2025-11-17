# Cross-Chain Price Checker

🚀 **A Complete Ecosystem for Cryptocurrency Price Tracking and Arbitrage Detection**

A comprehensive Python platform combining a powerful library, REST API, WebSocket server, Telegram/Discord bots, and trading simulator for comparing cryptocurrency prices across multiple blockchains and exchanges.

[![CI/CD](https://github.com/pavlenkotm/Cross-Chain-Price-Checker/workflows/CI/badge.svg)](https://github.com/pavlenkotm/Cross-Chain-Price-Checker/actions)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)

## ✨ Features

### Core Functionality
- 🌐 **Multi-Chain Support**: Ethereum, BSC (BNB Chain), Solana
- 💱 **8+ Exchange Integrations**:
  - **DEX**: Uniswap V2/V3, PancakeSwap V2, Raydium
  - **CEX**: Binance, Bybit, Kraken, OKX
- 🔍 **Automatic Token Resolution**: CoinGecko API integration
- ⚡ **Real-Time Arbitrage Detection**: Sub-second opportunity identification
- 📊 **Beautiful CLI**: Rich terminal interface with formatted tables

### Ecosystem Components
- 🌐 **REST API**: FastAPI-powered server with full CRUD operations
- 📡 **WebSocket Server**: Real-time price streaming
- 🤖 **Telegram Bot**: Interactive price checking and alerts
- 💬 **Discord Bot**: Community integration
- 📈 **Trading Simulator**: Backtest strategies with historical data
- 💼 **Portfolio Tracker**: Monitor holdings across exchanges
- 🔔 **Alert System**: Custom price and arbitrage notifications
- 📊 **Analytics Dashboard**: Prometheus + Grafana monitoring
- 🗄️ **Database Layer**: PostgreSQL with historical data tracking
- 🐳 **Docker Support**: Full containerized deployment

## 🚀 Installation

### Quick Start with Docker (Recommended)

```bash
# Clone the repository
git clone https://github.com/pavlenkotm/Cross-Chain-Price-Checker.git
cd Cross-Chain-Price-Checker

# Start the full stack
docker-compose up -d

# Access services:
# - API: http://localhost:8000/api/docs
# - WebSocket: ws://localhost:8000/api/v1/ws/prices
# - Grafana: http://localhost:3000 (admin/admin)
# - Prometheus: http://localhost:9090
```

### From Source

```bash
# Clone and setup
git clone https://github.com/pavlenkotm/Cross-Chain-Price-Checker.git
cd Cross-Chain-Price-Checker

# Run automated setup
./scripts/setup.sh

# Or manual installation:
python -m venv venv
source venv/bin/activate
pip install -r requirements-full.txt
pip install -e .
```

### Using pip (PyPI)

```bash
pip install cross-chain-price-checker

# Full installation with all features
pip install cross-chain-price-checker[full]
```

## 🎯 Quick Start

### 1. Command Line Interface

```bash
# Check single token
ccpc check SOL

# Compare multiple tokens
ccpc compare BTC ETH SOL

# With custom config
ccpc check ETH --config config.yaml --verbose
```

### 2. REST API

```bash
# Start API server
./scripts/run_api.sh

# Or with Docker
docker-compose up api

# Access interactive docs
open http://localhost:8000/api/docs
```

### 3. Telegram Bot

```bash
# Set your bot token
export TELEGRAM_BOT_TOKEN="your_token_here"

# Run bot
python -m cross_chain_price_checker.bots.telegram_bot

# Or with Docker
docker-compose --profile bots up telegram_bot
```

### 4. WebSocket Streaming

```javascript
const ws = new WebSocket('ws://localhost:8000/api/v1/ws/prices');

ws.onopen = () => {
  ws.send(JSON.stringify({
    action: 'subscribe',
    token: 'SOL'
  }));
};

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('Price update:', data);
};
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
