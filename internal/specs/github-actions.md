# GitHub Actions

## Policy
- Third-party actions are pinned by full commit SHA for reproducibility.
- Shared vBase-owned actions and reusable workflows use `validityBase/vbase-github-actions` with reviewed release tags such as `@v1`.
- Workflow permissions should be explicit and minimal when compatible with the called action/workflow contract.
- Secrets must come from GitHub Secrets or deployment configuration, never from committed files or logs.

## Workflows

### `.github/workflows/pylint.yml`
- Runs on pushes and pull requests for all branches.
- Delegates to `validityBase/vbase-github-actions/.github/workflows/python-lint.yml@v1`.
- Installs `requirements/lock/dev.txt` with Python 3.12.
- Runs `pylint --fail-under=8.0 $(git ls-files '*.py')`.
- Uses the runner from `vars.RUNS_ON` when set, otherwise `ubuntu-latest`.

### `.github/workflows/python-dependency-locks.yml`
- Runs on pushes, pull requests, and manual dispatch.
- Installs `requirements/lock/tools.txt` with Python 3.12.
- Regenerates `requirements/lock/tools.txt`, `requirements/lock/base.txt`, and
  `requirements/lock/dev.txt`; the workflow fails if the committed lock files
  differ.
- Installs `requirements/lock/dev.txt` and runs `python -m pip check`.

### `.github/workflows/deploy.yml`
- Runs on pushes to `main` and `master`.
- Deploys to Dagster Cloud serverless production.
- Builds with Python 3.12.
- Uses pinned `dagster-io/dagster-cloud-action` actions.
- Uses `DAGSTER_CLOUD_API_TOKEN` and `ORGANIZATION_ID` from GitHub Secrets.
- Checks out `${{ github.head_ref || github.ref_name }}` for deploy paths that need repository files.

### `.github/workflows/branch_deployments.yml`
- Runs for pull request open, synchronize, reopen, and close events.
- Deploys or tears down Dagster Cloud branch deployments.
- Builds with Python 3.12.
- Uses pinned `dagster-io/dagster-cloud-action` actions.
- Uses `DAGSTER_CLOUD_API_TOKEN` and `ORGANIZATION_ID` from GitHub Secrets.
