"""Health monitoring system for exchanges and services."""

import asyncio
from datetime import datetime
from typing import List, Dict
from loguru import logger

from ..database import get_db, ExchangeStatus
from ..price_checker import PriceChecker
from sqlalchemy import select


class HealthChecker:
    """Monitor exchange health and availability."""

    def __init__(self, check_interval: int = 300):
        """
        Initialize health checker.

        Args:
            check_interval: Interval between health checks in seconds (default: 5 minutes)
        """
        self.check_interval = check_interval
        self.checker = PriceChecker()
        self.running = False

    async def check_exchange_health(self, exchange) -> Dict:
        """
        Check health of a single exchange.

        Args:
            exchange: Exchange instance

        Returns:
            Health status dictionary
        """
        start_time = asyncio.get_event_loop().time()

        try:
            is_available = await exchange.is_available()
            response_time = (asyncio.get_event_loop().time() - start_time) * 1000  # Convert to ms

            return {
                "name": exchange.name,
                "type": exchange.exchange_type.value,
                "is_available": is_available,
                "response_time_ms": response_time,
                "error": None,
            }

        except Exception as e:
            response_time = (asyncio.get_event_loop().time() - start_time) * 1000

            return {
                "name": exchange.name,
                "type": exchange.exchange_type.value,
                "is_available": False,
                "response_time_ms": response_time,
                "error": str(e),
            }

    async def check_all_exchanges(self) -> List[Dict]:
        """
        Check health of all exchanges.

        Returns:
            List of health status dictionaries
        """
        logger.info("Running health check for all exchanges...")

        tasks = [
            self.check_exchange_health(exchange)
            for exchange in self.checker.exchanges
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Filter out exceptions
        health_status = []
        for result in results:
            if isinstance(result, dict):
                health_status.append(result)
            elif isinstance(result, Exception):
                logger.error(f"Health check error: {result}")

        return health_status

    async def update_database(self, health_results: List[Dict]):
        """
        Update database with health check results.

        Args:
            health_results: List of health status dictionaries
        """
        db = get_db()

        async for session in db.get_session():
            for result in health_results:
                # Check if exchange status exists
                query = select(ExchangeStatus).where(
                    ExchangeStatus.exchange_name == result['name']
                )
                db_result = await session.execute(query)
                status = db_result.scalar_one_or_none()

                if status:
                    # Update existing
                    status.is_available = result['is_available']
                    status.last_check = datetime.utcnow()
                    status.response_time_ms = result['response_time_ms']

                    if result['is_available']:
                        status.last_success = datetime.utcnow()
                        status.error_count = 0
                        status.last_error = None
                    else:
                        status.error_count += 1
                        status.last_error = result['error']

                else:
                    # Create new
                    status = ExchangeStatus(
                        exchange_name=result['name'],
                        exchange_type=result['type'],
                        is_available=result['is_available'],
                        last_check=datetime.utcnow(),
                        last_success=datetime.utcnow() if result['is_available'] else None,
                        response_time_ms=result['response_time_ms'],
                        error_count=0 if result['is_available'] else 1,
                        last_error=result['error'],
                    )
                    session.add(status)

        logger.info(f"Updated health status for {len(health_results)} exchanges")

    async def run_continuous_monitoring(self):
        """Run continuous health monitoring."""
        self.running = True
        logger.info(f"Starting continuous health monitoring (interval: {self.check_interval}s)")

        while self.running:
            try:
                health_results = await self.check_all_exchanges()
                await self.update_database(health_results)

                # Log summary
                available = sum(1 for r in health_results if r['is_available'])
                logger.info(
                    f"Health check complete: {available}/{len(health_results)} exchanges available"
                )

            except Exception as e:
                logger.error(f"Error in health monitoring: {e}")

            await asyncio.sleep(self.check_interval)

    def stop(self):
        """Stop continuous monitoring."""
        self.running = False
        logger.info("Stopping health monitoring")

    async def close(self):
        """Clean up resources."""
        self.stop()
        await self.checker.close()


async def main():
    """Run health checker as standalone service."""
    checker = HealthChecker(check_interval=300)  # 5 minutes

    try:
        await checker.run_continuous_monitoring()
    except KeyboardInterrupt:
        logger.info("Health checker interrupted")
    finally:
        await checker.close()


if __name__ == "__main__":
    asyncio.run(main())
