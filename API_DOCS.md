# API Documentation

## Base URL

```
http://localhost:8000/api/v1
```

## Authentication

Currently, the API is open. Authentication will be added in future versions.

## Endpoints

### Prices

#### Get Current Prices

```http
GET /prices/current/{token}
```

**Parameters:**
- `token` (path): Token symbol (e.g., "SOL", "BTC")

**Response:**
```json
{
  "token": "SOL",
  "prices": [
    {
      "exchange": "Binance",
      "type": "CEX",
      "price": 142.35,
      "pair": "SOL/USDT",
      "valid": true
    }
  ],
  "statistics": {
    "avg_price": 142.25,
    "min_price": 141.50,
    "max_price": 143.00,
    "spread_percent": 1.06
  },
  "arbitrage_opportunities": [
    {
      "buy_exchange": "PancakeSwap V2",
      "sell_exchange": "Binance",
      "buy_price": 141.50,
      "sell_price": 143.00,
      "profit_percent": 1.06
    }
  ]
}
```

#### Get Historical Prices

```http
GET /prices/history/{token}?exchange=Binance&hours=24&limit=100
```

**Parameters:**
- `token` (path): Token symbol
- `exchange` (query, optional): Filter by exchange
- `hours` (query): Hours to look back (1-720)
- `limit` (query): Max records (1-1000)

#### Compare Tokens

```http
POST /prices/compare
Content-Type: application/json

["BTC", "ETH", "SOL"]
```

### Exchanges

#### List All Exchanges

```http
GET /exchanges/
```

#### Get Exchange Status

```http
GET /exchanges/{exchange_name}
```

### Alerts

#### Create Alert

```http
POST /alerts/
Content-Type: application/json

{
  "user_id": "telegram_12345",
  "token_symbol": "SOL",
  "alert_type": "price_above",
  "threshold": 150.0,
  "notification_channel": "telegram"
}
```

#### Get User Alerts

```http
GET /alerts/user/{user_id}?active_only=true
```

#### Delete Alert

```http
DELETE /alerts/{alert_id}
```

### Portfolio

#### Add to Portfolio

```http
POST /portfolio/
Content-Type: application/json

{
  "user_id": "user_123",
  "token_symbol": "SOL",
  "amount": 10.5,
  "avg_buy_price": 140.00,
  "exchange_name": "Binance"
}
```

#### Get User Portfolio

```http
GET /portfolio/user/{user_id}
```

**Response includes current prices and P&L:**
```json
[
  {
    "token_symbol": "SOL",
    "amount": 10.5,
    "avg_buy_price": 140.00,
    "current_price": 142.35,
    "current_value": 1494.68,
    "profit_loss": 24.68,
    "profit_loss_percent": 1.68
  }
]
```

### Analytics

#### Get Price Statistics

```http
GET /analytics/price-stats/{token}?hours=24
```

#### Get Arbitrage Statistics

```http
GET /analytics/arbitrage-stats/{token}?hours=24
```

#### Get Trending Opportunities

```http
GET /analytics/trending?limit=10
```

### WebSocket

#### Price Streaming

```
WS /ws/prices
```

**Subscribe to token:**
```json
{
  "action": "subscribe",
  "token": "SOL"
}
```

**Unsubscribe:**
```json
{
  "action": "unsubscribe",
  "token": "SOL"
}
```

**Ping:**
```json
{
  "action": "ping"
}
```

**Server messages:**
```json
{
  "type": "price_update",
  "token": "SOL",
  "data": {
    "avg_price": 142.35,
    "spread_percent": 1.06,
    "opportunities": 3,
    "timestamp": 1234567890
  }
}
```

## Error Handling

All errors follow this format:

```json
{
  "detail": "Error message here"
}
```

**Status Codes:**
- `200` - Success
- `400` - Bad Request
- `404` - Not Found
- `500` - Internal Server Error

## Rate Limiting

- Default: 100 requests per minute per IP
- WebSocket: Unlimited connections, updates every 30 seconds

## Examples

### cURL

```bash
# Get current price
curl http://localhost:8000/api/v1/prices/current/SOL

# Create alert
curl -X POST http://localhost:8000/api/v1/alerts/ \
  -H "Content-Type: application/json" \
  -d '{"user_id":"user1","token_symbol":"SOL","alert_type":"price_above","threshold":150}'
```

### Python

```python
import requests

# Get prices
response = requests.get('http://localhost:8000/api/v1/prices/current/SOL')
data = response.json()
print(f"Average price: ${data['statistics']['avg_price']:.2f}")

# Create alert
alert = {
    "user_id": "user1",
    "token_symbol": "SOL",
    "alert_type": "price_above",
    "threshold": 150.0
}
response = requests.post('http://localhost:8000/api/v1/alerts/', json=alert)
```

### JavaScript

```javascript
// Fetch prices
fetch('http://localhost:8000/api/v1/prices/current/SOL')
  .then(res => res.json())
  .then(data => {
    console.log('Avg price:', data.statistics.avg_price);
  });

// WebSocket
const ws = new WebSocket('ws://localhost:8000/api/v1/ws/prices');
ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log(data);
};
```
