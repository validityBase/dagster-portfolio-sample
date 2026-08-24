"""Behavior tests for the Dagster portfolio asset."""

import importlib
import os
import sys
import unittest
from datetime import datetime
from types import ModuleType, SimpleNamespace
from unittest.mock import patch
from zoneinfo import ZoneInfo

PORTFOLIO_BYTES = b"sym,wt\nSPY,1\n"
PORTFOLIO_CID = "0xdda8e4685a737a3416f2fd57cd287e0e8b14400459105372ab5135c0210765e1"


class FakeVBaseAPIError(Exception):
    """Represent an API error raised by the public client."""


class FakeLog:  # pylint: disable=too-few-public-methods
    """Collect log calls without depending on Dagster internals."""

    def info(self, *args, **kwargs):
        """Accept one informational log call."""
        del args, kwargs


class FakeContext:  # pylint: disable=too-few-public-methods
    """Expose the asset context behavior used by the sample."""

    def __init__(self):
        self.log = FakeLog()
        self.metadata = None

    def asset_partition_key_for_output(self):
        """Return the partition selected for materialization."""
        return "2026-08-21"

    def add_output_metadata(self, metadata):
        """Capture metadata emitted by the asset."""
        self.metadata = metadata


class FakePortfolioFrame:  # pylint: disable=too-few-public-methods
    """Return one stable CSV record for hashing and storage assertions."""

    def to_csv(self, *, index, lineterminator="\n"):
        """Return a known-good stable CSV representation."""
        if index or lineterminator != "\n":
            raise AssertionError("The portfolio must use stable CSV serialization.")
        return PORTFOLIO_BYTES.decode("utf-8")


class FakeS3Client:  # pylint: disable=too-few-public-methods
    """Capture S3 writes at the boto3 boundary."""

    def __init__(self):
        self.put_calls = []

    def put_object(self, **kwargs):
        """Capture one S3 object write."""
        self.put_calls.append(kwargs)


class FailingS3Client:  # pylint: disable=too-few-public-methods
    """Fail every S3 write to exercise materialization recovery ordering."""

    def put_object(self, **kwargs):
        """Raise before a portfolio can be persisted."""
        del kwargs
        raise RuntimeError("S3 write failed")


class FakeVBaseAPIClient:
    """Capture vBase API calls and return one verified stamp."""

    instances = []
    return_existing_collection = True

    def __init__(self, api_key):
        self.api_key = api_key
        self.create_collection_calls = []
        self.create_stamp_calls = []
        self.verify_calls = []
        self.collection = SimpleNamespace(
            name="TestPortfolio",
            cid="0xcollection",
        )
        self.created_receipt = SimpleNamespace(
            object_cid=PORTFOLIO_CID,
            set_cid=self.collection.cid,
            user_address="0xowner",
            transaction_hash="0xtransaction",
            timestamp="2026-08-24T12:00:00Z",
        )
        self.stale_receipt = SimpleNamespace(
            object_cid=PORTFOLIO_CID,
            set_cid=self.collection.cid,
            user_address="0xowner",
            transaction_hash="0xolder-transaction",
            timestamp="2026-08-24T11:00:00Z",
        )
        self.__class__.instances.append(self)

    def __enter__(self):
        """Return this fake as a context-managed client."""
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        """Accept context manager exit details."""
        del exc_type, exc_value, traceback

    def get_collections(self):
        """Return the existing sample collection."""
        return [self.collection] if self.return_existing_collection else []

    def create_collection(self, **kwargs):
        """Capture creation of the sample collection."""
        self.create_collection_calls.append(kwargs)
        return self.collection

    def create_stamp(self, **kwargs):
        """Capture a stamp request and return its receipt."""
        self.create_stamp_calls.append(kwargs)
        return SimpleNamespace(commitment_receipt=self.created_receipt)

    def verify_stamps(self, cids, filter_by_user=False):
        """Capture verification and return stale and exact receipts."""
        self.verify_calls.append((cids, filter_by_user))
        return SimpleNamespace(stamp_list=[self.stale_receipt, self.created_receipt])


def _identity_asset(*args, **kwargs):
    """Replace Dagster's decorator while preserving the asset function seam."""
    del args, kwargs

    def decorator(function):
        return function

    return decorator


def _load_portfolio_asset_module(s3_client):
    """Load the asset with deterministic external service boundaries."""
    dagster_module = ModuleType("dagster")
    dagster_module.DailyPartitionsDefinition = lambda **kwargs: kwargs
    dagster_module.Definitions = lambda **kwargs: kwargs
    dagster_module.ScheduleDefinition = lambda **kwargs: kwargs
    dagster_module.asset = _identity_asset
    dagster_module.build_op_context = lambda **kwargs: kwargs
    dagster_module.define_asset_job = lambda *args, **kwargs: (args, kwargs)

    boto3_module = ModuleType("boto3")
    boto3_module.client = lambda service_name: (
        s3_client
        if service_name == "s3"
        else (_ for _ in ()).throw(AssertionError(service_name))
    )

    dotenv_module = ModuleType("dotenv")
    dotenv_module.load_dotenv = lambda: None

    vbase_api_module = ModuleType("vbase_api")
    vbase_api_module.VBaseAPIError = FakeVBaseAPIError
    vbase_api_module.VBaseAPIClient = FakeVBaseAPIClient

    producer_module = ModuleType("dagster_pipelines.assets.portfolio_producer")
    producer_module.MARKET_TIME_ZONE = ZoneInfo("America/New_York")
    producer_module.produce_portfolio = lambda partition_date, logger: (
        FakePortfolioFrame()
    )

    module_name = "dagster_pipelines.assets.portfolio_asset"
    sys.modules.pop(module_name, None)
    with patch.dict(
        sys.modules,
        {
            "boto3": boto3_module,
            "dagster": dagster_module,
            "dotenv": dotenv_module,
            "vbase_api": vbase_api_module,
            "dagster_pipelines.assets.portfolio_producer": producer_module,
        },
    ):
        return importlib.import_module(module_name)


class PortfolioAssetTests(unittest.TestCase):
    """Verify the public materialization behavior with service fakes."""

    def setUp(self):
        FakeVBaseAPIClient.instances.clear()
        FakeVBaseAPIClient.return_existing_collection = True

    def test_materialization_stamps_and_stores_the_same_portfolio_bytes(self):
        """Stamp the CID of the exact bytes written to the configured bucket."""
        s3_client = FakeS3Client()
        portfolio_asset_module = _load_portfolio_asset_module(s3_client)
        context = FakeContext()
        environment = {
            "VBASE_API_KEY": "test-api-key",
            "S3_BUCKET": "test-bucket",
            "S3_FOLDER": "test-prefix",
        }

        with patch.dict(os.environ, environment, clear=True):
            portfolio_asset_module.portfolio_asset(context)

        client = FakeVBaseAPIClient.instances[0]
        self.assertEqual(client.api_key, "test-api-key")
        self.assertEqual(client.create_collection_calls, [])
        self.assertEqual(
            client.create_stamp_calls,
            [
                {
                    "data_cid": PORTFOLIO_CID,
                    "collection_cid": "0xcollection",
                    "store_stamped_file": False,
                    "idempotent": False,
                }
            ],
        )
        self.assertEqual(client.verify_calls, [([PORTFOLIO_CID], True)])
        self.assertEqual(len(s3_client.put_calls), 1)
        self.assertEqual(s3_client.put_calls[0]["Bucket"], "test-bucket")
        self.assertEqual(
            s3_client.put_calls[0]["Key"],
            "test-prefix/portfolio--partition-2026-08-21"
            f"--cid-{PORTFOLIO_CID}_2026-08-21_00-00-00+0000.csv",
        )
        self.assertEqual(s3_client.put_calls[0]["Body"], PORTFOLIO_BYTES)
        self.assertEqual(context.metadata["vBase object CID"], PORTFOLIO_CID)
        self.assertEqual(
            context.metadata["vBase transaction"],
            "0xtransaction",
        )

    def test_s3_failure_does_not_create_a_vbase_stamp(self):
        """Do not stamp a portfolio that was not persisted successfully."""
        portfolio_asset_module = _load_portfolio_asset_module(FailingS3Client())
        environment = {
            "VBASE_API_KEY": "test-api-key",
            "S3_BUCKET": "test-bucket",
            "S3_FOLDER": "test-prefix",
        }

        with (
            patch.dict(os.environ, environment, clear=True),
            self.assertRaisesRegex(RuntimeError, "S3 write failed"),
        ):
            portfolio_asset_module.portfolio_asset(FakeContext())

        self.assertEqual(FakeVBaseAPIClient.instances, [])

    def test_first_materialization_creates_the_sample_collection(self):
        """Create and pin the collection when the account has none."""
        FakeVBaseAPIClient.return_existing_collection = False
        s3_client = FakeS3Client()
        portfolio_asset_module = _load_portfolio_asset_module(s3_client)
        environment = {
            "VBASE_API_KEY": "test-api-key",
            "S3_BUCKET": "test-bucket",
            "S3_FOLDER": "test-prefix",
        }

        with patch.dict(os.environ, environment, clear=True):
            portfolio_asset_module.portfolio_asset(FakeContext())

        client = FakeVBaseAPIClient.instances[0]
        self.assertEqual(
            client.create_collection_calls,
            [
                {
                    "name": "TestPortfolio",
                    "description": "Daily portfolio records produced by Dagster.",
                    "is_pinned": True,
                }
            ],
        )

    def test_collection_creation_recovers_from_a_concurrent_create(self):
        """Reuse the collection created by another first materialization."""
        portfolio_asset_module = _load_portfolio_asset_module(FakeS3Client())
        collection = SimpleNamespace(name="TestPortfolio", cid="0xcollection")

        class ConcurrentCollectionClient:
            """Expose an empty first read and the winning collection afterward."""

            def __init__(self):
                self.get_calls = 0
                self.create_calls = []

            def get_collections(self):
                """Return the winning collection only after the failed create."""
                self.get_calls += 1
                return [] if self.get_calls == 1 else [collection]

            def create_collection(self, **kwargs):
                """Represent losing the concurrent create race."""
                self.create_calls.append(kwargs)
                raise FakeVBaseAPIError("Collection already exists")

        client = ConcurrentCollectionClient()

        # pylint: disable=protected-access
        result = portfolio_asset_module._get_or_create_collection(client)

        self.assertIs(result, collection)
        self.assertEqual(client.get_calls, 2)
        self.assertEqual(
            client.create_calls,
            [
                {
                    "name": "TestPortfolio",
                    "description": "Daily portfolio records produced by Dagster.",
                    "is_pinned": True,
                }
            ],
        )

    def test_collection_creation_preserves_unresolved_api_errors(self):
        """Do not hide an API failure when no concurrent collection exists."""
        portfolio_asset_module = _load_portfolio_asset_module(FakeS3Client())
        api_error = FakeVBaseAPIError("Service unavailable")

        class FailedCollectionClient:
            """Return no collection before or after a failed create."""

            def get_collections(self):
                """Return no concurrently created collection."""
                return []

            def create_collection(self, **kwargs):
                """Raise the original unrelated API failure."""
                del kwargs
                raise api_error

        with self.assertRaises(FakeVBaseAPIError) as raised:
            # pylint: disable=protected-access
            portfolio_asset_module._get_or_create_collection(FailedCollectionClient())

        self.assertIs(raised.exception, api_error)

    def test_debug_default_uses_the_new_york_market_date(self):
        """Select the New York date when the host's calendar is already ahead."""
        portfolio_asset_module = _load_portfolio_asset_module(FakeS3Client())

        class FixedDatetime(datetime):
            """Represent 00:30 UTC while New York is still on the prior date."""

            @classmethod
            def now(cls, tz=None):
                if tz is None:
                    return cls(2026, 8, 25, 0, 30)
                return cls(2026, 8, 24, 20, 30, tzinfo=tz)

        with (
            patch.object(portfolio_asset_module, "datetime", FixedDatetime),
            patch.object(portfolio_asset_module, "portfolio_asset") as materialize,
        ):
            portfolio_asset_module.debug_portfolio()

        materialize.assert_called_once_with({"partition_key": "2026-08-24"})


if __name__ == "__main__":
    unittest.main()
