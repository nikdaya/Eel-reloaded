# Eel Developers

## Setting up your environment

In order to start developing with Eel you'll need to checkout the code, set up a development and testing environment, and check that everything is in order.

**Python 3.12 or later is required.**

### Clone the repository
```bash
git clone git@github.com:python-eel/Eel.git
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

This installs Eel's runtime dependencies (`starlette`, `uvicorn`) plus all test dependencies.

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
