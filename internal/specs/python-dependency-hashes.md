# Python Dependency Hashes

This repository is a deployable Dagster sample project. Runtime and development
installs are terminal environments owned by this repository, so generated
requirements files use pip hash-checking mode for reproducibility.

Lock files are generated with Python 3.12 for CI and Dagster Cloud deployment
parity.

## Files

- `requirements/base.in` is the human-edited runtime dependency input.
- `requirements/dev.in` is the human-edited development/lint input and
  includes `base.in`.
- `requirements/tools.in` is the human-edited lock-regeneration tooling
  input.
- `requirements/base.txt`, `requirements/dev.txt`, and
  `requirements/tools.txt` are generated with hashes and must not be edited
  by hand.
- Root `requirements.txt` and `requirements-dev.txt` are compatibility shims
  that install the generated runtime and development locks.

## Developer Workflow

Install the pinned lock-generation tooling before regenerating locks:

```bash
python -m pip install --require-hashes -r requirements/tools.txt
```

Regenerate locks from the repository root:

```bash
pip-compile --strip-extras --no-annotate --allow-unsafe --generate-hashes -o requirements/tools.txt requirements/tools.in
pip-compile --strip-extras --no-annotate --allow-unsafe --generate-hashes -o requirements/base.txt requirements/base.in
pip-compile --strip-extras --no-annotate --allow-unsafe --generate-hashes -o requirements/dev.txt requirements/dev.in
```

## CI Contract

`.github/workflows/python-dependency-locks.yml` regenerates the lock files and
fails if generated files differ from committed files. The lint workflow installs
`requirements/dev.txt` before running pylint.
