# Python Requirements

Human-edited dependency inputs (`*.in`) and generated hash-locked install files
(`*.txt`) live together in `requirements/` so Dependabot can update
pip-compile pairs.

Root `requirements.txt` and `requirements-dev.txt` are compatibility shims that
install the generated locks. Keep using them for local setup unless you need to
regenerate locks.

Do not edit generated `*.txt` files by hand. Regenerate them from the
repository root with Python 3.12:

```bash
python -m pip install --require-hashes -r requirements/tools.txt
pip-compile --strip-extras --no-annotate --allow-unsafe --generate-hashes -o requirements/tools.txt requirements/tools.in
pip-compile --strip-extras --no-annotate --allow-unsafe --generate-hashes -o requirements/base.txt requirements/base.in
pip-compile --strip-extras --no-annotate --allow-unsafe --generate-hashes -o requirements/dev.txt requirements/dev.in
```
