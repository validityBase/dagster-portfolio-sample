# Dagster Portfolio Sample

A public sample that uses Dagster to produce a daily SPY portfolio, stamp its
exact CSV bytes with the vBase API, and store those bytes in Amazon S3.

## Prerequisites

- Python 3.12 or later on macOS or Linux (Windows users should use WSL 2)
- A vBase account and API key from
  [Account Settings](https://app.vbase.com/profile/#account_settings)
- An Amazon S3 bucket where your AWS identity can write portfolio objects

The sample uses boto3's standard credential resolution. Local AWS profiles,
AWS IAM Identity Center, environment credentials, and IAM roles are supported;
static AWS keys are not required by the application.

## Quickstart

1. Clone the repository and create an isolated environment:

   ```bash
   git clone https://github.com/validityBase/dagster-portfolio-sample.git
   cd dagster-portfolio-sample
   python -m venv venv
   source venv/bin/activate
   ```

   On Windows, run these Linux commands inside WSL 2.

2. Install the reproducible dependencies for local development:

   ```bash
   python -m pip install --require-hashes -r requirements-dev.txt
   ```

3. Copy the example configuration and replace its placeholders:

   ```bash
   cp .env.example .env
   ```

   ```dotenv
   VBASE_API_KEY=your_vbase_api_key
   S3_BUCKET=your_bucket_name
   S3_FOLDER=your_portfolio_prefix
   ```

   `.env` is ignored by Git. For Dagster Cloud, configure the same values as
   deployment environment variables or secrets. Configure AWS credentials
   through your normal boto3 credential source.

4. Start Dagster:

   ```bash
   dagster dev
   ```

5. Open `http://localhost:3000`, select the `portfolio_asset`, choose a trading-day
   partition, and materialize it.

The selected date must be an NYSE trading day. A current-day partition can only
be materialized after the sample's target market time. Because yfinance limits
15-minute history to the most recent 60 days, select a trading-day partition
within that range.

## What the Asset Does

For each Dagster partition, the asset:

1. Produces a simple SPY position from market data.
2. Serializes the portfolio to stable UTF-8 CSV bytes.
3. Calculates the bytes' SHA3-256 content ID.
4. Creates or reuses the `TestPortfolio` vBase collection.
5. Stamps the content ID without uploading the portfolio data to vBase.
6. Verifies the exact vBase transaction returned by the stamp request.
7. Writes the same bytes to the configured S3 location, using the partition date
   and verified CID in the filename to prevent portfolio records from
   overwriting each other.
8. Adds the S3 URI, collection CID, object CID, transaction, and timestamp to
   the Dagster materialization metadata.

Each materialization requests a new vBase stamp, matching the original sample's
behavior. The vBase API also supports optional idempotent stamp requests;
applications can enable them with a window appropriate to their own retry and
partition semantics.

## Architecture

- [Portfolio producer](dagster_pipelines/assets/portfolio_producer.py) contains
  the reusable SPY strategy logic.
- [Portfolio asset](dagster_pipelines/assets/portfolio_asset.py) connects the
  producer to Dagster, vBase, and S3.
- [Portfolio schedule](dagster_pipelines/schedules/portfolio_schedule.py)
  materializes the asset on weekdays at 3:50 PM America/New_York time.

## Development

Install the development lock and run the local checks:

```bash
python -m pip install --require-hashes -r requirements-dev.txt
python -m unittest discover -s tests -v
pre-commit run --all-files
pylint --fail-under=8.0 $(git ls-files '*.py')
```

See [Python dependency hashes](internal/specs/python-dependency-hashes.md) for
the lock-file regeneration process.

Additional references:

- [vBase Python samples](https://github.com/validityBase/vbase-py-samples/tree/main/samples)
- [CSV portfolio producer](https://github.com/validityBase/vbase-py-samples/blob/main/samples/produce_portfolio_history_csv_s3.py)
- [CSV portfolio verifier](https://github.com/validityBase/vbase-py-samples/blob/main/samples/verify_portfolio_history_csv_s3.py)
- [Dagster 1.10 webserver and UI](https://release-1-10-21.archive.dagster-docs.io/guides/operate/webserver)

## License

This project is licensed under the Apache 2.0 License. See
[LICENSE.txt](LICENSE.txt).
