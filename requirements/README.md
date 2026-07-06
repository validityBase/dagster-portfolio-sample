# Python Requirements

Human-edited dependency inputs live in `requirements/src/`. Generated
hash-locked install files live in `requirements/lock/`.

Root `requirements.txt` and `requirements-dev.txt` are compatibility shims that
install the generated locks. Keep using them for local setup unless you need to
regenerate locks.

Do not edit files in `requirements/lock/` by hand. Regenerate them from the
repository root with Python 3.12:

```bash
python -m pip install --require-hashes -r requirements/lock/tools.txt
pip-compile --strip-extras --no-annotate --allow-unsafe --generate-hashes -o requirements/lock/tools.txt requirements/src/tools.in
pip-compile --strip-extras --no-annotate --allow-unsafe --generate-hashes -o requirements/lock/base.txt requirements/src/base.in
pip-compile --strip-extras --no-annotate --allow-unsafe --generate-hashes -o requirements/lock/dev.txt requirements/src/dev.in
```
