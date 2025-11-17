"""Command-line interface for Cross-Chain Price Checker."""

import asyncio
import sys
from pathlib import Path
from typing import Optional, List

import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich import box
from loguru import logger

from .price_checker import PriceChecker
from .config import get_config, Config
from .utils import format_price, get_price_color

# Initialize CLI
app = typer.Typer(
    name="ccpc",
    help="Cross-Chain Price Checker - Compare token prices across DEXs and CEXs",
    add_completion=False
)
console = Console()

# Configure logger
logger.remove()
logger.add(
    sys.stderr,
    format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
    level="INFO"
)


def create_price_table(analysis: dict, token: str) -> Table:
    """
    Create a Rich table for displaying prices.

    Args:
        analysis: Analysis dictionary from PriceChecker
        token: Token symbol

    Returns:
        Rich Table object
    """
    table = Table(
        title=f"[bold cyan]{token} Price Comparison[/bold cyan]",
        box=box.ROUNDED,
        show_header=True,
        header_style="bold magenta"
    )

    table.add_column("Exchange", style="cyan", no_wrap=True)
    table.add_column("Type", style="yellow", no_wrap=True)
    table.add_column("Chain", style="blue")
    table.add_column("Pair", style="white")
    table.add_column("Price", style="green", justify="right")
    table.add_column("Diff %", justify="right")
    table.add_column("Status", justify="center")

    prices = analysis.get('prices', [])
    avg_price = analysis.get('avg_price', 0)

    # Sort prices by value
    valid_prices = [p for p in prices if p.is_valid]
    invalid_prices = [p for p in prices if not p.is_valid]
    valid_prices.sort(key=lambda x: x.price, reverse=True)

    # Add valid prices
    for price in valid_prices:
        diff_percent = ((price.price - avg_price) / avg_price) * 100 if avg_price > 0 else 0
        color = get_price_color(diff_percent, threshold=0.5)

        diff_str = f"[{color}]{diff_percent:+.2f}%[/{color}]"
        price_str = f"[green]{format_price(price.price)}[/green]"

        table.add_row(
            price.exchange_name,
            price.exchange_type.value,
            price.chain or "N/A",
            price.pair or "N/A",
            price_str,
            diff_str,
            "[green]✓[/green]"
        )

    # Add failed prices
    for price in invalid_prices:
        table.add_row(
            price.exchange_name,
            price.exchange_type.value,
            price.chain or "N/A",
            "N/A",
            "[red]Failed[/red]",
            "[red]N/A[/red]",
            "[red]✗[/red]"
        )

    return table


def create_stats_panel(analysis: dict) -> Panel:
    """
    Create a panel with price statistics.

    Args:
        analysis: Analysis dictionary

    Returns:
        Rich Panel object
    """
    if analysis.get('valid_count', 0) == 0:
        return Panel(
            "[red]No valid prices found[/red]",
            title="[bold]Statistics[/bold]",
            border_style="red"
        )

    min_price = analysis.get('min_price', 0)
    max_price = analysis.get('max_price', 0)
    avg_price = analysis.get('avg_price', 0)
    spread = analysis.get('spread_percent', 0)

    stats_text = f"""
[cyan]Valid Prices:[/cyan] {analysis.get('valid_count', 0)} / {analysis.get('count', 0)}
[green]Average Price:[/green] {format_price(avg_price)}
[blue]Min Price:[/blue] {format_price(min_price)}
[yellow]Max Price:[/yellow] {format_price(max_price)}
[magenta]Spread:[/magenta] {spread:.2f}%
"""

    return Panel(
        stats_text.strip(),
        title="[bold]Statistics[/bold]",
        border_style="cyan",
        box=box.ROUNDED
    )


def create_arbitrage_table(opportunities: list) -> Optional[Table]:
    """
    Create a table for arbitrage opportunities.

    Args:
        opportunities: List of ArbitrageOpportunity objects

    Returns:
        Rich Table object or None if no opportunities
    """
    if not opportunities:
        return None

    table = Table(
        title="[bold red]Arbitrage Opportunities[/bold red]",
        box=box.DOUBLE,
        show_header=True,
        header_style="bold red"
    )

    table.add_column("#", style="dim", width=3)
    table.add_column("Buy From", style="green")
    table.add_column("Buy Price", style="green", justify="right")
    table.add_column("Sell To", style="red")
    table.add_column("Sell Price", style="red", justify="right")
    table.add_column("Profit %", style="yellow bold", justify="right")

    for idx, opp in enumerate(opportunities[:10], 1):  # Show top 10
        profit_color = "bright_green" if opp.potential_profit_percent >= 2 else "yellow"

        table.add_row(
            str(idx),
            opp.buy_exchange,
            format_price(opp.buy_price),
            opp.sell_exchange,
            format_price(opp.sell_price),
            f"[{profit_color}]+{opp.potential_profit_percent:.2f}%[/{profit_color}]"
        )

    return table


@app.command()
def check(
    token: str = typer.Argument(..., help="Token symbol or name (e.g., SOL, BTC, Ethereum)"),
    config_file: Optional[Path] = typer.Option(None, "--config", "-c", help="Path to configuration file"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose logging"),
):
    """
    Check token price across multiple exchanges and identify arbitrage opportunities.
    """
    if verbose:
        logger.remove()
        logger.add(sys.stderr, level="DEBUG")

    async def run():
        # Load configuration
        config = get_config(str(config_file) if config_file else None)

        # Initialize price checker
        checker = PriceChecker(config)

        # Fetch prices with progress indicator
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task(f"Fetching prices for {token}...", total=None)

            try:
                analysis = await checker.check_token_price(token)
            finally:
                await checker.close()
                progress.remove_task(task)

        # Display results
        if 'error' in analysis:
            console.print(f"[red]Error:[/red] {analysis['error']}")
            return

        # Show statistics
        console.print()
        console.print(create_stats_panel(analysis))
        console.print()

        # Show price table
        console.print(create_price_table(analysis, token.upper()))
        console.print()

        # Show arbitrage opportunities
        opportunities = analysis.get('opportunities', [])
        if opportunities:
            arb_table = create_arbitrage_table(opportunities)
            if arb_table:
                console.print(arb_table)
                console.print()
                console.print(
                    f"[yellow]Found {len(opportunities)} arbitrage opportunities![/yellow]"
                )
        else:
            console.print("[dim]No significant arbitrage opportunities found.[/dim]")

        console.print()

    # Run async function
    asyncio.run(run())


@app.command()
def compare(
    tokens: List[str] = typer.Argument(..., help="Token symbols to compare (space-separated)"),
    config_file: Optional[Path] = typer.Option(None, "--config", "-c", help="Path to configuration file"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose logging"),
):
    """
    Compare prices for multiple tokens.
    """
    if verbose:
        logger.remove()
        logger.add(sys.stderr, level="DEBUG")

    async def run():
        # Load configuration
        config = get_config(str(config_file) if config_file else None)

        # Initialize price checker
        checker = PriceChecker(config)

        # Fetch prices for all tokens
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task(f"Fetching prices for {len(tokens)} tokens...", total=None)

            try:
                results = await checker.check_multiple_tokens(tokens)
            finally:
                await checker.close()
                progress.remove_task(task)

        # Display results for each token
        for token in tokens:
            analysis = results.get(token, {})

            if 'error' in analysis:
                console.print(f"\n[red]Error for {token}:[/red] {analysis['error']}")
                continue

            console.print()
            console.print(create_price_table(analysis, token.upper()))
            console.print()

    # Run async function
    asyncio.run(run())


@app.command()
def version():
    """Show version information."""
    from . import __version__
    console.print(f"[cyan]Cross-Chain Price Checker v{__version__}[/cyan]")


def main():
    """Main entry point."""
    try:
        app()
    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted by user[/yellow]")
        sys.exit(0)
    except Exception as e:
        console.print(f"\n[red]Error:[/red] {e}")
        if "--verbose" in sys.argv or "-v" in sys.argv:
            raise
        sys.exit(1)


if __name__ == "__main__":
    main()
