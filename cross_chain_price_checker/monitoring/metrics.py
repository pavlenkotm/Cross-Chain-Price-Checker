"""Prometheus metrics collector."""

from prometheus_client import Counter, Histogram, Gauge, CollectorRegistry
from typing import Optional


class MetricsCollector:
    """Collect and expose Prometheus metrics."""

    def __init__(self, registry: Optional[CollectorRegistry] = None):
        """Initialize metrics collector."""
        self.registry = registry or CollectorRegistry()

        # Request metrics
        self.api_requests = Counter(
            'ccpc_api_requests_total',
            'Total API requests',
            ['method', 'endpoint', 'status'],
            registry=self.registry
        )

        self.api_request_duration = Histogram(
            'ccpc_api_request_duration_seconds',
            'API request duration',
            ['method', 'endpoint'],
            registry=self.registry
        )

        # Price fetch metrics
        self.price_fetches = Counter(
            'ccpc_price_fetches_total',
            'Total price fetches',
            ['exchange', 'status'],
            registry=self.registry
        )

        self.price_fetch_duration = Histogram(
            'ccpc_price_fetch_duration_seconds',
            'Price fetch duration',
            ['exchange'],
            registry=self.registry
        )

        # Exchange health metrics
        self.exchange_availability = Gauge(
            'ccpc_exchange_available',
            'Exchange availability (1=available, 0=unavailable)',
            ['exchange'],
            registry=self.registry
        )

        self.exchange_response_time = Gauge(
            'ccpc_exchange_response_time_ms',
            'Exchange response time in milliseconds',
            ['exchange'],
            registry=self.registry
        )

        # Arbitrage metrics
        self.arbitrage_opportunities = Counter(
            'ccpc_arbitrage_opportunities_total',
            'Total arbitrage opportunities detected',
            ['token', 'buy_exchange', 'sell_exchange'],
            registry=self.registry
        )

        self.arbitrage_profit_percent = Histogram(
            'ccpc_arbitrage_profit_percent',
            'Arbitrage profit percentage',
            ['token'],
            registry=self.registry
        )

        # Database metrics
        self.db_queries = Counter(
            'ccpc_db_queries_total',
            'Total database queries',
            ['operation', 'table'],
            registry=self.registry
        )

        self.db_query_duration = Histogram(
            'ccpc_db_query_duration_seconds',
            'Database query duration',
            ['operation', 'table'],
            registry=self.registry
        )

        # Alert metrics
        self.alerts_triggered = Counter(
            'ccpc_alerts_triggered_total',
            'Total alerts triggered',
            ['type', 'token'],
            registry=self.registry
        )

    def record_api_request(self, method: str, endpoint: str, status: int):
        """Record API request."""
        self.api_requests.labels(method=method, endpoint=endpoint, status=status).inc()

    def record_price_fetch(self, exchange: str, success: bool):
        """Record price fetch attempt."""
        status = 'success' if success else 'failure'
        self.price_fetches.labels(exchange=exchange, status=status).inc()

    def update_exchange_health(self, exchange: str, available: bool, response_time: float):
        """Update exchange health metrics."""
        self.exchange_availability.labels(exchange=exchange).set(1 if available else 0)
        self.exchange_response_time.labels(exchange=exchange).set(response_time)

    def record_arbitrage_opportunity(self, token: str, buy_exchange: str, sell_exchange: str, profit_percent: float):
        """Record arbitrage opportunity."""
        self.arbitrage_opportunities.labels(
            token=token,
            buy_exchange=buy_exchange,
            sell_exchange=sell_exchange
        ).inc()
        self.arbitrage_profit_percent.labels(token=token).observe(profit_percent)

    def record_db_query(self, operation: str, table: str):
        """Record database query."""
        self.db_queries.labels(operation=operation, table=table).inc()

    def record_alert_triggered(self, alert_type: str, token: str):
        """Record alert trigger."""
        self.alerts_triggered.labels(type=alert_type, token=token).inc()


# Global metrics instance
_metrics_instance: Optional[MetricsCollector] = None


def get_metrics() -> MetricsCollector:
    """Get or create global metrics instance."""
    global _metrics_instance
    if _metrics_instance is None:
        _metrics_instance = MetricsCollector()
    return _metrics_instance
