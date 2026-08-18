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
- Installs `requirements/dev.txt` with Python 3.12.
- Runs `pylint --fail-under=8.0 $(git ls-files '*.py')`.
- Uses the runner from `vars.RUNS_ON` when set, otherwise `ubuntu-latest`.

### `.github/workflows/python-dependency-locks.yml`
- Runs on pushes to all branch names, pull requests, and manual dispatch.
- Installs `requirements/tools.txt` with Python 3.12.
- Regenerates `requirements/tools.txt`, `requirements/base.txt`, and
  `requirements/dev.txt`; the workflow fails if the committed lock files
  differ.
- Installs `requirements/dev.txt` and runs `python -m pip check`.

### `.github/workflows/deploy.yml`
- Runs on pushes to `main` and `master`.
- Deploys to Dagster Cloud serverless production.
- Builds with Python 3.12.
- Copies `requirements/base.txt` over `project-repo/requirements.txt`
  before Python Executable deploys so the Dagster PEX builder receives a flat
  hash-locked requirements file.
- Uses pinned `dagster-io/dagster-cloud-action` actions.
- Uses `DAGSTER_CLOUD_API_TOKEN` and `ORGANIZATION_ID` from GitHub Secrets.
- Checks out `${{ github.head_ref || github.ref_name }}` for deploy paths that need repository files.

### `.github/workflows/branch_deployments.yml`
- Runs for pull request open, synchronize, reopen, and close events.
- Deploys or tears down Dagster Cloud branch deployments.
- Builds with Python 3.12.
- Grants `contents: read`, `issues: write`, and `pull-requests: write` so the
  Dagster Cloud action can check out code and update pull request comments.
- Copies `requirements/base.txt` over `project-repo/requirements.txt`
  before Python Executable deploys so the Dagster PEX builder receives a flat
  hash-locked requirements file.
- Uses pinned `dagster-io/dagster-cloud-action` actions.
- Uses `DAGSTER_CLOUD_API_TOKEN` and `ORGANIZATION_ID` from GitHub Secrets.
