# Nautobot NVIDIA Config Manager

This is the bundled Nautobot app for NVIDIA Config Manager. It is vendored as a standalone Python project so the deployment image can consume it through a local `uv` path source and release automation can publish it independently from the larger deployment package.

The import package is `nv_config_manager`; the distribution package is `nautobot-nv-config-manager`.
