"""
This asset is used to generate a position for the SPY ETF.
"""

import hashlib
import os
import time
from datetime import datetime, timezone
from typing import Optional

import boto3
from dagster import DailyPartitionsDefinition, asset, build_op_context
from dotenv import load_dotenv
from vbase_api import VBaseAPIClient, VBaseAPIError

from .portfolio_producer import MARKET_TIME_ZONE, produce_portfolio

# The vBase collection that receives stamps for individual portfolios.
PORTFOLIO_NAME = "TestPortfolio"
PORTFOLIO_DESCRIPTION = "Daily portfolio records produced by Dagster."
STAMP_TIMEOUT_SECONDS = 120
STAMP_POLL_INTERVAL_SECONDS = 5

# Define a daily partition for portfolio rebalancing.
# The portfolio rebalances daily starting from 2025-01-01.
partitions_def = DailyPartitionsDefinition(start_date="2025-01-01")


def _get_required_setting(name: str) -> str:
    """Return a non-empty environment setting or raise a helpful error."""
    value = os.getenv(name)
    if value is None or not value.strip():
        raise ValueError(f"{name} environment variable is not set.")
    return value.strip()


def _find_collection(client):
    """Return this sample's collection when it already exists."""
    return next(
        (
            item
            for item in client.get_collections()
            if item.name.casefold() == PORTFOLIO_NAME.casefold()
        ),
        None,
    )


def _get_or_create_collection(client):
    """Return this sample's collection, creating it when necessary."""
    collection = _find_collection(client)
    if collection is not None:
        return collection
    try:
        return client.create_collection(
            name=PORTFOLIO_NAME,
            description=PORTFOLIO_DESCRIPTION,
            is_pinned=True,
        )
    except VBaseAPIError:
        # Another first materialization may have created it concurrently.
        collection = _find_collection(client)
        if collection is not None:
            return collection
        raise


def _wait_for_stamp(client, created_receipt):
    """Wait for verification of the exact transaction just created."""
    deadline = time.monotonic() + STAMP_TIMEOUT_SECONDS
    while time.monotonic() < deadline:
        verification = client.verify_stamps(
            [created_receipt.object_cid],
            filter_by_user=True,
        )
        for receipt in verification.stamp_list:
            if (
                receipt.object_cid.lower() == created_receipt.object_cid.lower()
                and receipt.set_cid.lower() == created_receipt.set_cid.lower()
                and receipt.transaction_hash.lower()
                == created_receipt.transaction_hash.lower()
            ):
                return receipt
        time.sleep(STAMP_POLL_INTERVAL_SECONDS)
    raise TimeoutError(
        "Timed out waiting for vBase transaction "
        f"{created_receipt.transaction_hash}."
    )


def _stamp_portfolio(api_key: str, object_cid: str):
    """Stamp one portfolio CID and return its collection and verified receipt."""
    with VBaseAPIClient(api_key=api_key) as client:
        collection = _get_or_create_collection(client)
        stamp = client.create_stamp(
            data_cid=object_cid,
            collection_cid=collection.cid,
            store_stamped_file=False,
            idempotent=False,
        )
        created_receipt = stamp.commitment_receipt
        if created_receipt.object_cid.lower() != object_cid.lower():
            raise RuntimeError("vBase returned a different CID than the portfolio.")
        return collection, _wait_for_stamp(client, created_receipt)


def _get_portfolio_filename(
    partition_date: str,
    object_cid: str,
) -> str:
    """Build a stable, collision-resistant filename for one daily partition."""
    partition_datetime = datetime.strptime(partition_date, "%Y-%m-%d").replace(
        tzinfo=timezone.utc
    )
    # vBase portfolio tooling parses this canonical daily timestamp at the basename end.
    return (
        f"portfolio--partition-{partition_date}"
        f"--cid-{object_cid.lower()}"
        f"_{partition_datetime.strftime('%Y-%m-%d_%H-%M-%S%z')}.csv"
    )


@asset(partitions_def=partitions_def)
def portfolio_asset(context):
    """
    Generate, stamp, and store one SPY portfolio partition.
    """

    load_dotenv()
    api_key = _get_required_setting("VBASE_API_KEY")
    bucket = _get_required_setting("S3_BUCKET")
    folder = _get_required_setting("S3_FOLDER").strip("/")

    partition_date = context.asset_partition_key_for_output()
    context.log.info("Starting portfolio generation for %s", partition_date)

    portfolio_frame = produce_portfolio(partition_date, logger=context.log)
    context.log.info("%s: position_df = \n%s", partition_date, portfolio_frame)
    portfolio_bytes = portfolio_frame.to_csv(
        index=False,
        lineterminator="\n",
    ).encode("utf-8")
    object_cid = "0x" + hashlib.sha3_256(portfolio_bytes).hexdigest()

    # A repeated partition and CID can overwrite only the same exact object bytes.
    filename = _get_portfolio_filename(
        partition_date,
        object_cid,
    )
    object_key = f"{folder}/{filename}"
    s3_client = boto3.client("s3")
    context.log.info("Saving portfolio to s3://%s/%s", bucket, object_key)
    s3_client.put_object(
        Bucket=bucket,
        Key=object_key,
        Body=portfolio_bytes,
    )

    collection, verified_receipt = _stamp_portfolio(api_key, object_cid)

    context.add_output_metadata(
        {
            "S3 URI": f"s3://{bucket}/{object_key}",
            "vBase collection CID": collection.cid,
            "vBase object CID": verified_receipt.object_cid,
            "vBase transaction": verified_receipt.transaction_hash,
            "vBase timestamp": verified_receipt.timestamp,
        }
    )
    context.log.info(
        "Verified vBase transaction %s for %s",
        verified_receipt.transaction_hash,
        verified_receipt.object_cid,
    )


def debug_portfolio(date_str: Optional[str] = None) -> None:
    """
    Materialize the portfolio asset for a specific date or today's market date.

    Args:
        date_str: Optional date string in YYYY-MM-DD format. If None, uses today's
            date in the New York market timezone.
    """
    # Use the provided date or today's date in the market timezone.
    partition_date = date_str or datetime.now(MARKET_TIME_ZONE).strftime("%Y-%m-%d")

    # Create a context for debugging.
    context = build_op_context(partition_key=partition_date)

    # Materialize the asset.
    portfolio_asset(context)


if __name__ == "__main__":
    debug_portfolio()
