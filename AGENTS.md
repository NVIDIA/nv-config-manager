# Agent Instructions

## Python Imports

All imports MUST be placed at the top of the file, following standard Python conventions (stdlib, third-party, local). Do NOT place imports inside functions, methods, or conditional blocks.

The only exception is when a top-level import would cause a **circular dependency**. In that case, add a brief comment explaining why.

```python
# Correct — imports at the top
from datetime import UTC, datetime

from kubernetes.client import CoreV1Api

from nv_config_manager_installer.schema import NVConfigManagerInstallConfig


def do_something():
    v1 = CoreV1Api()
    ...

# Wrong — import buried inside a function
def do_something():
    from kubernetes.client import CoreV1Api
    v1 = CoreV1Api()
    ...

# Exception — circular dependency with comment
def get_app():
    from nv_config_manager_installer.tui.app import NVConfigManagerApp  # avoid circular import
    return NVConfigManagerApp()
```

## Python Tooling

Always use `uv run` to execute Python tools and utilities (ruff, pytest, mypy, etc.) inside this repository. Do NOT invoke them directly or via `python -m`.

```bash
# Correct
uv run ruff check src/
uv run ruff format src/
uv run pytest tests/
uv run mypy src/

# Wrong
ruff check src/
python -m ruff check src/
python -m pytest tests/
```

## Helm Charts (`deploy/helm/`)

When running `helm template` for testing or dry-run validation, always use `values-ci.yaml`:

```bash
helm template test . --values values-ci.yaml
```

Do NOT use `values.yaml` alone — it requires secrets/vault paths that aren't populated outside of a real deployment.

To test with the observability stack enabled, layer `values-observability.yaml` on top:

```bash
helm template test . --values values-ci.yaml --values values-observability.yaml
```
