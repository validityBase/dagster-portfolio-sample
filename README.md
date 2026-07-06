# Dagster Portfolio Sample

A sample project demonstrating how to build and validate a simple portfolio using Dagster and vBase. This project creates a daily portfolio that takes a long position in SPY if the price return is positive and a short position if negative.

## Quickstart Guide

1. Clone the repository:
```bash
git clone https://github.com/validityBase/dagster-portfolio-sample.git
cd dagster-portfolio-sample
```

2. Create and activate a virtual environment (recommended):
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install --require-hashes -r requirements.txt
```

For local development and linting, install the development lock:

```bash
pip install --require-hashes -r requirements-dev.txt
```

4. Set up environment variables:
Create a `.env` file in the project root with the following variables:
```bash
# vBase Configuration
VBASE_API_KEY=your_api_key_here           # API key for vBase authentication
VBASE_API_URL=your_api_url_here           # vBase API endpoint URL
VBASE_COMMITMENT_SERVICE_PRIVATE_KEY=your_private_key_here  # Private key for vBase commitment service

# AWS Configuration
AWS_ACCESS_KEY_ID=your_aws_access_key     # AWS access key for S3 operations
AWS_SECRET_ACCESS_KEY=your_aws_secret_key # AWS secret key for S3 operations
S3_BUCKET=your_bucket_name                # S3 bucket name for storing portfolio data
S3_FOLDER=your_folder_name                # S3 folder path within the bucket
```

For Dagster Cloud deployment, these variables should be set as secrets in your Dagster Cloud organization settings.

5. Run the Dagster development server:
```bash
dagster dev
```

6. Access the Dagster UI at `http://localhost:3000`

## Architecture

The project consists of several key components:

1. **[Portfolio Producer](dagster_pipelines/assets/portfolio_producer.py)**: Core logic for generating portfolio positions based on SPY price movements. This is the file that will be changed to define new portfolios and datasets.
2. **[Portfolio Asset](dagster_pipelines/assets/portfolio_asset.py)**: Dagster and vBase logic for managing the produced portfolio.

### Portfolio Producer

The portfolio producer is designed to be:
- **Reusable**: Can be called from different contexts (Dagster, standalone scripts, etc.)
- **Testable**: Has clear inputs and outputs
- **Loggable**: Includes comprehensive logging for debugging and monitoring

## Development

- The project uses Pylint for code quality checks (minimum score: 8.0)
- GitHub Actions automatically runs Pylint on all pushes and pull requests
- Pre-commit hooks are configured to run code quality checks before commits
- Python dependencies use human-edited inputs in `requirements/src/` and
  generated hash-locked install files in `requirements/lock/`

## Background

The following resources and examples can help you onboard to vBase, understand its architecture,
and get ready for building more complex infrastructure like this Dagster portfolio asset:

- **Onboard to vBase**: Create vBase accounts via our onboarding process. You would typically want two accounts -- one for testing and one for production. You can sign up for both accounts using https://app.vbase.com/accounts/signup/ and create `myusername-dev` and `myusername-prd` to make dev (sandbox) and eventually production stamps (commitments).

- **Review Basic Samples**: Study our samples in https://github.com/validityBase/vbase-py-samples/tree/main/samples, such as https://github.com/validityBase/vbase-py-samples/blob/main/samples/add_string_dataset_record.py and https://github.com/validityBase/vbase-py-samples/blob/main/samples/add_string_dataset_record_idempotent.py for stamping and verifying simple strings. These strings will be CSVs in the case of a portfolio asset. You should be able to run these with your `-dev` account for testing.

- **Explore Complex Examples**: Review and understand more complex examples like https://github.com/validityBase/vbase-py-samples/blob/main/samples/produce_portfolio_history_csv_s3.py and https://github.com/validityBase/vbase-py-samples/blob/main/samples/verify_portfolio_history_csv_s3.py. You can run and modify these to write and validate local files instead of S3 objects.

- **Learn Dagster**: Study Dagster (https://dagster.io/). An investment strategy can be implemented as a Dagster pipeline with a single asset that is produced (materialized) daily to read financial data, save the portfolio data, and stamp it. This pipeline is a more complex version of this sample: https://docs.dagster.io/getting-started/quickstart. For development, you can work through various Dagster demos using `dagster dev` as described here: https://docs.dagster.io/guides/deploy/deployment-options/running-dagster-locally.

## License

This project is licensed under the Apache 2.0 License - see the [LICENSE.txt](LICENSE.txt) file for details.
