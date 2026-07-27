# Agent Memory

## GitHub Actions
- Third-party GitHub Actions are pinned to full commit SHAs.
- vBase-owned shared actions and reusable workflows use reviewed `validityBase/vbase-github-actions` version tags.
- Pylint delegates to `validityBase/vbase-github-actions/.github/workflows/python-lint.yml@v1`.
- Pylint installs `requirements/dev.txt` with Python 3.12 and runs `pylint --fail-under=8.0 $(git ls-files '*.py')`.
- Runtime and development dependency inputs live in `requirements/`; generated hash-locked install files live in `requirements/`.
- Root `requirements.txt` and `requirements-dev.txt` are compatibility shims for the generated runtime and development locks.
- Dagster Python Executable deploy steps copy `requirements/base.txt` over
  the checked-out root `requirements.txt` before invoking the PEX builder because
  the builder copies requirements to `/output` and cannot resolve nested `-r`
  paths from the root shim.
- The old local `.github/actions/setup-python-deps` action was removed after pylint moved to the shared reusable workflow.
- Dagster Cloud deploy workflows use pinned `dagster-io/dagster-cloud-action` actions and require `DAGSTER_CLOUD_API_TOKEN` plus `ORGANIZATION_ID`.
