# Installation

## Requirements

- Nautobot >= 2.4.20, < 2.5.0
- Python >= 3.10

## Install

```bash
pip install nautobot-app-overlays
```

## Configure

Add to `nautobot_config.py`:

```python
PLUGINS = ["nautobot_app_overlays"]
```

## Migrate

```bash
nautobot-server migrate
```

## Restart Services

```bash
sudo systemctl restart nautobot nautobot-worker
```

## Verify

Navigate to **Multi-Tenancy** in the sidebar — you should see Overlays, VXLANs,
InfiniBand PKeys, and InfiniBand MKeys.

!!! note "Status Content Types"
    On first startup, the app automatically assigns the **Active**, **Planned**, and
    **Deprecated** statuses to all overlay model content types. This happens via the
    `nautobot_database_ready` signal and requires no manual steps.
