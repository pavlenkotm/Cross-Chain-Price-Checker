"""
Basic usage example for Cross-Chain Price Checker.

This script demonstrates how to use the library to check token prices
and identify arbitrage opportunities.
"""

import asyncio
from cross_chain_price_checker import PriceChecker


async def check_single_token():
    """Example: Check price for a single token."""
    print("=" * 60)
    print("Example 1: Checking SOL price")
    print("=" * 60)

    checker = PriceChecker()

    try:
        # Check SOL price
        analysis = await checker.check_token_price("SOL")

        # Display results
        if analysis.get('valid_count', 0) > 0:
            print(f"\nToken: SOL")
            print(f"Valid Prices: {analysis['valid_count']} / {analysis['count']}")
            print(f"Average Price: ${analysis['avg_price']:.6f}")
            print(f"Min Price: ${analysis['min_price']:.6f}")
            print(f"Max Price: ${analysis['max_price']:.6f}")
            print(f"Spread: {analysis['spread_percent']:.2f}%")

            # Show all prices
            print("\nPrices by Exchange:")
            for price in analysis['prices']:
                if price.is_valid:
                    print(f"  {price.exchange_name:20} ${price.price:12.6f} ({price.pair})")
                else:
                    print(f"  {price.exchange_name:20} Error: {price.error}")

            # Show arbitrage opportunities
            opportunities = analysis.get('opportunities', [])
            if opportunities:
                print(f"\nArbitrage Opportunities Found: {len(opportunities)}")
                for i, opp in enumerate(opportunities[:5], 1):  # Show top 5
                    print(f"\n  Opportunity #{i}:")
                    print(f"    Buy:  {opp.buy_exchange} at ${opp.buy_price:.6f}")
                    print(f"    Sell: {opp.sell_exchange} at ${opp.sell_price:.6f}")
                    print(f"    Potential Profit: +{opp.potential_profit_percent:.2f}%")
            else:
                print("\nNo significant arbitrage opportunities found.")
        else:
            print("No valid prices found!")

    finally:
        await checker.close()


async def check_multiple_tokens():
    """Example: Check prices for multiple tokens."""
    print("\n" + "=" * 60)
    print("Example 2: Checking multiple tokens")
    print("=" * 60)

    checker = PriceChecker()

    try:
        # Check multiple tokens
        tokens = ["BTC", "ETH"]
        results = await checker.check_multiple_tokens(tokens)

        for token in tokens:
            analysis = results.get(token, {})

            if 'error' in analysis:
                print(f"\n{token}: Error - {analysis['error']}")
                continue

            if analysis.get('valid_count', 0) > 0:
                print(f"\n{token}:")
                print(f"  Average: ${analysis['avg_price']:.6f}")
                print(f"  Spread: {analysis['spread_percent']:.2f}%")

                # Show best arbitrage opportunity
                opportunities = analysis.get('opportunities', [])
                if opportunities:
                    best = opportunities[0]
                    print(f"  Best Arbitrage: {best.potential_profit_percent:.2f}% "
                          f"({best.buy_exchange} → {best.sell_exchange})")

    finally:
        await checker.close()


async def main():
    """Run all examples."""
    print("\nCross-Chain Price Checker - Usage Examples")
    print("=" * 60)

    # Example 1: Single token
    await check_single_token()

    # Example 2: Multiple tokens
    await check_multiple_tokens()

    print("\n" + "=" * 60)
    print("Examples completed!")
    print("=" * 60)


if __name__ == "__main__":
    # Run the examples
    asyncio.run(main())
