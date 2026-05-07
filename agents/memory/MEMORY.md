# Agent Memory

## GitHub Actions
- Third-party GitHub Actions are pinned to full commit SHAs.
- vBase-owned shared actions and reusable workflows use reviewed `validityBase/vbase-github-actions` version tags.
- Pylint delegates to `validityBase/vbase-github-actions/.github/workflows/python-lint.yml@v1`.
- Pylint installs `requirements.txt` with Python 3.11 and runs `pylint --fail-under=8.0 $(git ls-files '*.py')`.
- The old local `.github/actions/setup-python-deps` action was removed after pylint moved to the shared reusable workflow.
- Dagster Cloud deploy workflows use pinned `dagster-io/dagster-cloud-action` actions and require `DAGSTER_CLOUD_API_TOKEN` plus `ORGANIZATION_ID`.
