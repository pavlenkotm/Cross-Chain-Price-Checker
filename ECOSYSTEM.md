# Cross-Chain Price Checker - Complete Ecosystem

## Overview

Cross-Chain Price Checker has evolved into a comprehensive ecosystem for cryptocurrency price tracking, arbitrage detection, and automated trading across multiple blockchains and exchanges.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     User Interfaces                         │
├────────┬──────────┬──────────┬──────────┬──────────────────┤
│  CLI   │ REST API │ WebSocket│ Telegram │    Discord       │
│        │          │          │   Bot    │      Bot         │
└────┬───┴─────┬────┴────┬─────┴─────┬────┴────────┬─────────┘
     │         │         │           │             │
     └─────────┴─────────┴───────────┴─────────────┘
                          │
          ┌───────────────┴───────────────┐
          │     Core Services              │
          ├───────────────────────────────┤
          │  • Price Checker              │
          │  • Token Resolver             │
          │  • Arbitrage Detector         │
          │  • Trading Simulator          │
          │  • Alert System               │
          │  • Portfolio Tracker          │
          └───────┬───────────────────┬───┘
                  │                   │
      ┌───────────┴──────┐   ┌────────┴────────┐
      │   Exchanges      │   │   Monitoring    │
      ├──────────────────┤   ├─────────────────┤
      │ DEX:             │   │ • Health Check  │
      │ • Uniswap V2/V3  │   │ • Metrics       │
      │ • PancakeSwap    │   │ • Prometheus    │
      │ • Raydium        │   │ • Grafana       │
      │                  │   └─────────────────┘
      │ CEX:             │
      │ • Binance        │   ┌─────────────────┐
      │ • Bybit          │   │   Data Layer    │
      │ • Kraken         │   ├─────────────────┤
      │ • OKX            │   │ • PostgreSQL    │
      └──────────────────┘   │ • Redis Cache   │
                             └─────────────────┘
```

## Components

### 1. Core Library (`cross_chain_price_checker/`)

#### Price Checker (`price_checker.py`)
- Main orchestrator for price fetching
- Concurrent price collection from all exchanges
- Arbitrage opportunity detection
- Price comparison and statistics

#### Token Resolver (`token_resolver.py`)
- CoinGecko API integration
- Token address resolution across chains
- Metadata caching

#### Configuration (`config.py`)
- YAML and environment variable support
- Exchange enable/disable
- RPC endpoint management

### 2. Exchange Adapters (`exchanges/`)

#### DEX Adapters
- **Uniswap V2** (`dex/uniswap.py`)
  - Ethereum mainnet
  - Pair-based pricing

- **Uniswap V3** (`dex/uniswap.py`)
  - Concentrated liquidity pools
  - Multiple fee tiers

- **PancakeSwap V2** (`dex/pancakeswap.py`)
  - BSC/BNB Chain
  - BEP-20 tokens

- **Raydium** (`dex/raydium.py`)
  - Solana blockchain
  - SPL token support

#### CEX Adapters
- **Binance** (`cex/binance.py`)
- **Bybit** (`cex/bybit.py`)
- **Kraken** (`cex/kraken.py`)
- **OKX** (`cex/okx.py`)

### 3. REST API Server (`api/`)

**Endpoints:**

```
GET  /api/v1/prices/current/{token}        - Get current prices
GET  /api/v1/prices/history/{token}        - Get historical prices
POST /api/v1/prices/compare                - Compare multiple tokens

GET  /api/v1/exchanges/                    - List all exchanges
GET  /api/v1/exchanges/{name}              - Get exchange status

POST /api/v1/alerts/                       - Create price alert
GET  /api/v1/alerts/user/{user_id}         - Get user alerts
DELETE /api/v1/alerts/{id}                 - Delete alert

POST /api/v1/portfolio/                    - Add to portfolio
GET  /api/v1/portfolio/user/{user_id}      - Get portfolio
POST /api/v1/portfolio/trades              - Record trade

GET  /api/v1/analytics/price-stats/{token} - Price statistics
GET  /api/v1/analytics/arbitrage-stats     - Arbitrage stats
GET  /api/v1/analytics/trending            - Trending opportunities

WS   /api/v1/ws/prices                     - Real-time price stream
```

### 4. WebSocket (`api/routes/websocket.py`)

Real-time price streaming with subscriptions:

```javascript
// Connect
ws = new WebSocket('ws://localhost:8000/api/v1/ws/prices');

// Subscribe to token
ws.send(JSON.stringify({
  action: 'subscribe',
  token: 'SOL'
}));

// Receive updates
ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log(data.token, data.data.avg_price);
};
```

### 5. Telegram Bot (`bots/telegram_bot.py`)

**Commands:**
- `/start` - Welcome message
- `/price <token>` - Get current price
- `/compare <tokens>` - Compare tokens
- `/alert <token> <price>` - Set price alert
- `/alerts` - View active alerts
- `/portfolio` - View portfolio

### 6. Discord Bot (`bots/discord_bot.py`)

**Commands:**
- `!price <token>` - Get current price
- `!compare <tokens>` - Compare tokens
- `!trending` - Show trending opportunities

### 7. Database Layer (`database/`)

**Models:**
- `PriceHistory` - Historical price data
- `TokenInfo` - Token metadata
- `ExchangeStatus` - Exchange health monitoring
- `Alert` - Price alerts
- `Portfolio` - User holdings
- `Trade` - Trade execution history
- `ArbitrageOpportunityLog` - Detected opportunities

### 8. Monitoring System (`monitoring/`)

#### Health Checker (`health_checker.py`)
- Continuous exchange availability monitoring
- Response time tracking
- Error logging and alerting

#### Metrics Collector (`metrics.py`)
- Prometheus metrics
- API request tracking
- Price fetch statistics
- Arbitrage opportunity metrics

### 9. Trading System (`trading/`)

#### Trading Simulator (`simulator.py`)
- Backtest trading strategies
- Performance metrics (Sharpe ratio, max drawdown)
- Transaction cost simulation

#### Strategies (`strategy.py`)
- **SimpleArbitrageStrategy** - Buy low, sell high
- **MomentumStrategy** - Trend following
- Extensible framework for custom strategies

## Deployment

### Docker Compose (Recommended)

```bash
# Start full stack
docker-compose up -d

# Start with bots
docker-compose --profile bots up -d

# Start with monitoring
docker-compose --profile monitoring up -d

# View logs
docker-compose logs -f api
```

### Manual Deployment

```bash
# 1. Setup
./scripts/setup.sh

# 2. Run API server
./scripts/run_api.sh

# 3. Run bots (optional)
./scripts/run_bots.sh

# 4. Run health checker
python -m cross_chain_price_checker.monitoring.health_checker
```

### Kubernetes (Production)

```bash
# Apply manifests
kubectl apply -f k8s/

# Scale API pods
kubectl scale deployment ccpc-api --replicas=3

# Check status
kubectl get pods -l app=ccpc
```

## Configuration

### Environment Variables

```bash
# Database
DATABASE_URL=postgresql://user:pass@localhost/ccpc

# RPC Endpoints
ETH_RPC_URL=https://eth.llamarpc.com
BSC_RPC_URL=https://bsc-dataseed.binance.org/
SOLANA_RPC_URL=https://api.mainnet-beta.solana.com

# API Keys
COINGECKO_API_KEY=your_key
TELEGRAM_BOT_TOKEN=your_token
DISCORD_BOT_TOKEN=your_token
```

### YAML Configuration

```yaml
# config.yaml
exchanges:
  dex:
    uniswap_v2:
      enabled: true
    raydium:
      enabled: false  # Disable specific exchanges

  cex:
    binance:
      enabled: true

comparison:
  min_price_difference_percent: 0.5
  timeout_seconds: 10
```

## Monitoring

### Prometheus Metrics

Available at `http://localhost:9090`

Key metrics:
- `ccpc_price_fetches_total` - Total price fetches
- `ccpc_exchange_available` - Exchange availability
- `ccpc_arbitrage_opportunities_total` - Opportunities detected
- `ccpc_api_requests_total` - API request count

### Grafana Dashboards

Available at `http://localhost:3000` (admin/admin)

Pre-configured dashboards:
- Price Comparison Overview
- Exchange Health
- Arbitrage Opportunities
- API Performance

## Development

### Adding a New Exchange

1. Create adapter class:

```python
# cross_chain_price_checker/exchanges/cex/new_exchange.py
from ..base import Exchange, ExchangePrice, ExchangeType

class NewExchange(Exchange):
    def __init__(self):
        super().__init__("New Exchange", ExchangeType.CEX)

    async def get_price(self, token_symbol: str, **kwargs) -> ExchangePrice:
        # Implementation
        pass
```

2. Register in `price_checker.py`:

```python
if self.config.is_exchange_enabled('cex', 'new_exchange'):
    self.exchanges.append(NewExchange())
```

3. Add to configuration:

```yaml
exchanges:
  cex:
    new_exchange:
      enabled: true
      base_url: "https://api.example.com"
```

### Running Tests

```bash
# Run all tests
pytest

# With coverage
pytest --cov=cross_chain_price_checker

# Specific test file
pytest tests/test_price_checker.py

# With verbose output
pytest -v
```

### Code Quality

```bash
# Format code
black cross_chain_price_checker

# Check style
flake8 cross_chain_price_checker

# Type checking
mypy cross_chain_price_checker
```

## Performance

### Optimization Tips

1. **Use Redis Caching**
   ```python
   REDIS_URL=redis://localhost:6379
   ```

2. **Database Connection Pooling**
   ```python
   DATABASE_URL=postgresql://...?pool_size=20&max_overflow=40
   ```

3. **Concurrent Price Fetching**
   - All exchanges queried in parallel
   - Typical response time: 2-5 seconds for all exchanges

4. **Rate Limiting**
   - CoinGecko: 50 calls/minute (free tier)
   - CEX APIs: Varies by exchange
   - Use API keys for higher limits

## Security

### Best Practices

1. **Never commit secrets**
   ```bash
   # Use .env file (gitignored)
   cp .env.example .env
   ```

2. **API Authentication** (Coming soon)
   ```python
   # JWT tokens for API access
   headers = {"Authorization": f"Bearer {token}"}
   ```

3. **Database Security**
   ```bash
   # Use strong passwords
   # Enable SSL connections
   DATABASE_URL=postgresql://...?sslmode=require
   ```

4. **Rate Limiting**
   ```python
   # API rate limiting enabled by default
   # 100 requests per minute per IP
   ```

## Roadmap

### Phase 1: Core Enhancement
- [x] Multi-chain support (ETH, BSC, Solana)
- [x] Multiple DEX/CEX integrations
- [x] Real-time price tracking
- [x] Arbitrage detection

### Phase 2: Ecosystem
- [x] REST API
- [x] WebSocket support
- [x] Telegram bot
- [x] Discord bot
- [x] Database persistence
- [x] Health monitoring

### Phase 3: Advanced Features
- [x] Trading simulator
- [x] Portfolio tracking
- [x] Alert system
- [ ] Automated trading (with safeguards)
- [ ] Machine learning price prediction

### Phase 4: Scale & Performance
- [x] Docker containerization
- [x] CI/CD pipeline
- [ ] Kubernetes deployment
- [ ] Load balancing
- [ ] Multi-region support

### Phase 5: User Experience
- [ ] Web dashboard (React/Vue)
- [ ] Mobile app
- [ ] Advanced charting
- [ ] Social features

## License

MIT License - see LICENSE file

## Support

- GitHub Issues: https://github.com/pavlenkotm/Cross-Chain-Price-Checker/issues
- Documentation: https://docs.example.com
- Discord Community: https://discord.gg/example

## Contributors

Made with ❤️ by the Cross-Chain Price Checker team
