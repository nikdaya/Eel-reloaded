# Eel-reloaded Developers

## Setting up your environment

In order to start developing with Eel-reloaded you'll need to check out the code, set up a development and testing environment, and verify that everything is in order.

**Python 3.12 or later is required.**

### Clone the repository
```bash
git clone https://github.com/nikdaya/Eel-reloaded.git
cd Eel-reloaded
```

### Create a virtual environment

```bash
python3 -m venv venv
source venv/bin/activate          # Linux / macOS
venv\Scripts\Activate.ps1         # Windows (PowerShell)
```

**Note**: `venv` is listed in the `.gitignore` file so it's the recommended virtual environment name.

### Install project requirements

The recommended way is to install the package in editable mode with the test extras:

```bash
pip install --upgrade pip setuptools wheel
pip install --no-build-isolation -e ".[jinja2]"
pip install -r requirements-test.txt
pip install -r requirements-meta.txt   # optional: tox
```

This installs Eel-reloaded's runtime dependencies (`starlette`, `uvicorn`) plus all test dependencies.

The editable install still exposes the runtime package as `import eel`, but the distribution metadata is `eel-reloaded`.

### (Recommended) Run Automated Tests

Tox is configured to run tests against each supported Python version (3.12+).
Integration tests require [Chrome](https://www.google.com/chrome) and a matching [ChromeDriver](https://chromedriver.chromium.org/home) on your PATH.

#### Running Tests

Quick unit-test run (no browser needed):

```bash
pytest tests/unit/
```

Full tox matrix (requires multiple Python versions installed):

```bash
tox
```

Single environment:

```bash
tox -e py312
```

### Verified local runbook (Python 3.12)

If your machine has multiple Python versions, use explicit 3.12 commands to avoid
accidentally running tests on unsupported interpreters.

Windows (PowerShell):

```bash
py -3.12 -m pip install --upgrade pip
py -3.12 -m pip install -e ".[jinja2]"
py -3.12 -m pip install -r requirements-test.txt
py -3.12 -m pytest tests/unit -q
py -3.12 -m pytest tests/integration -q
```

Alternative explicit interpreter path (Windows):

```bash
C:/Users/<you>/AppData/Local/Programs/Python/Python312/python.exe -m pytest tests/unit -q
```

Notes:

- Keep the project installed in editable mode (`-e`) so tests use workspace code.
- Integration tests require Chrome on the machine.

## Release and tagging policy

Use semantic version tags in the form `vMAJOR.MINOR.PATCH` (for example `v0.19.0`).

Versioning rules:

- `MAJOR`: incompatible API changes
- `MINOR`: backward-compatible features
- `PATCH`: backward-compatible fixes/docs/packaging updates

Before creating a release tag:

1. Update `version` in `pyproject.toml`.
2. Add/update the matching heading in `CHANGELOG.md`.
3. Ensure tests pass (`pytest tests/unit/` and optionally `tox`).
4. Commit those changes.
5. Create an annotated tag:

```bash
git tag -a v0.19.0 -m "Release v0.19.0"
git push origin main
git push origin v0.19.0
```

Backfilling old tags:

- If a historical release exists in the changelog but no tag exists, create the tag at the commit that introduced that release version metadata.
- Prefer annotated tags (`git tag -a`) over lightweight tags.
- Do not reuse/move a published tag.
