"""
This module contains the logic for producing portfolio positions.
"""

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pandas as pd
import pandas_market_calendars as mcal
import yfinance as yf

MARKET_TIME_ZONE = ZoneInfo("America/New_York")


def _format_market_time(timestamp) -> str:
    """Format a timezone-aware timestamp in the NYSE timezone."""
    return timestamp.tz_convert(MARKET_TIME_ZONE).strftime("%H:%M %Z")


def produce_portfolio(portfolio_date: str, logger: object) -> pd.DataFrame:
    """
    Produce the portfolio that is long SPY if the price return is positive and short
    SPY if the price return is negative for the 1-day period ending at the portfolio
    time with 15 minute tolerance.

    Args:
        portfolio_date: The date for which to produce the portfolio in YYYY-MM-DD format.
        logger: Logger object for logging messages.

    Returns:
        A DataFrame containing the position with columns ['sym', 'wt'].

    Raises:
        ValueError: If the portfolio date is not a trading day or if data is not available.
    """

    # Get the NYSE schedule for the portfolio date.
    schedule = mcal.get_calendar("NYSE").schedule(
        start_date=portfolio_date, end_date=portfolio_date
    )
    if schedule.empty:
        logger.warning(f"No trading on {portfolio_date}.")
        raise ValueError(f"No trading on {portfolio_date}.")

    # Calculate the target time (10 minutes before market close).
    target_time = schedule.iloc[0]["market_close"] - timedelta(minutes=10)
    logger.info(
        f"Market close time for {portfolio_date}: "
        f"{_format_market_time(schedule.iloc[0]['market_close'])}"
    )
    logger.info(f"Target time for price: {_format_market_time(target_time)}")

    # Check if we're dealing with current date and if we're past the target time.
    portfolio_datetime = datetime.strptime(portfolio_date, "%Y-%m-%d")
    current_datetime = datetime.now(MARKET_TIME_ZONE)
    is_current_date = portfolio_datetime.date() == current_datetime.date()
    logger.info(f"Current time: {current_datetime.strftime('%Y-%m-%d %H:%M %Z')}")
    logger.info(f"Is current date: {is_current_date}")

    if is_current_date and current_datetime < target_time:
        error_message = (
            "Current time is before target time "
            f"({_format_market_time(target_time)})."
        )
        logger.error(error_message)
        raise ValueError(error_message)

    # Fetch and process SPY data.
    spy_ticker = yf.Ticker("SPY")

    # Get current price data.
    spy_data = spy_ticker.history(
        start=portfolio_date,
        end=current_datetime if is_current_date else target_time,
        interval="15m",
    )
    if spy_data.empty:
        error_message = f"No data available for SPY on {portfolio_date}."
        logger.error(error_message)
        raise ValueError(error_message)

    current_price = spy_data["Close"].iloc[-1]
    logger.info(f"Fetched {len(spy_data)} intraday records")
    logger.info(
        f"Current price: ${current_price:.2f} "
        f"(from {spy_data.index[-1].strftime('%Y-%m-%d %H:%M')})"
    )

    # Get prior day's close.
    prior_record = spy_ticker.history(
        start=portfolio_datetime - timedelta(days=10),
        end=portfolio_date,
        interval="1d",
    ).iloc[-1]
    logger.info(
        f"Prior day close: ${prior_record['Close']:.2f} "
        f"(from {prior_record.name.strftime('%Y-%m-%d')})"
    )

    # Calculate return and determine position.
    price_return = current_price / prior_record["Close"] - 1
    logger.info(f"Price return: {price_return:.2%}")
    position_weight = 1 if price_return > 0 else -1
    logger.info(f"Position weight: {position_weight}")

    # Create and return the position DataFrame.
    position_df = pd.DataFrame({"sym": ["SPY"], "wt": [position_weight]})
    logger.info(f"Generated portfolio:\n{position_df}")

    return position_df
