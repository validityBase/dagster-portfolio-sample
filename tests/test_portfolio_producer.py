"""Behavior tests for portfolio production timing."""

import unittest
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import Mock, patch
from zoneinfo import ZoneInfo

import pandas as pd

from dagster_pipelines.assets import portfolio_producer


class FixedDatetime(datetime):
    """Return an instant whose UTC and New York calendar dates differ."""

    @classmethod
    def now(cls, tz=None):
        fixed_utc = cls(2026, 8, 22, 0, 5, tzinfo=timezone.utc)
        if tz is None:
            return fixed_utc.replace(tzinfo=None)
        return fixed_utc.astimezone(tz)


class FakeTicker:  # pylint: disable=too-few-public-methods
    """Return deterministic prices and capture the intraday end time."""

    def __init__(self):
        self.intraday_end = None

    def history(self, *, start, end, interval):
        """Return one intraday or prior-close data frame."""
        del start
        if interval == "15m":
            self.intraday_end = end
            return pd.DataFrame(
                {"Close": [101.0]},
                index=[pd.Timestamp("2026-08-21T20:00:00Z")],
            )
        return pd.DataFrame(
            {"Close": [100.0]},
            index=[pd.Timestamp("2026-08-20T20:00:00Z")],
        )


class PortfolioProducerTests(unittest.TestCase):
    """Verify that market-time decisions are independent of machine timezone."""

    def test_current_partition_uses_new_york_calendar_date(self):
        """Treat late New York evening as the selected trading date."""
        market_calendar = Mock()
        market_calendar.schedule.return_value = pd.DataFrame(
            {"market_close": [pd.Timestamp("2026-08-21T20:00:00Z")]}
        )
        ticker = FakeTicker()
        logger = SimpleNamespace(
            info=Mock(),
            warning=Mock(),
            error=Mock(),
        )

        with (
            patch.object(portfolio_producer, "datetime", FixedDatetime),
            patch.object(
                portfolio_producer.mcal,
                "get_calendar",
                return_value=market_calendar,
            ),
            patch.object(portfolio_producer.yf, "Ticker", return_value=ticker),
        ):
            portfolio_producer.produce_portfolio("2026-08-21", logger)

        self.assertEqual(
            ticker.intraday_end,
            FixedDatetime.now(ZoneInfo("America/New_York")),
        )
        info_messages = [call.args[0] for call in logger.info.call_args_list]
        self.assertIn(
            "Market close time for 2026-08-21: 16:00 EDT",
            info_messages,
        )
        self.assertIn("Target time for price: 15:50 EDT", info_messages)


if __name__ == "__main__":
    unittest.main()
