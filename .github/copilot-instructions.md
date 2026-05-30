# Repository Instructions

## AIR Simulation Demo Credentials

The AIR simulation intentionally uses hard-coded public demo credentials for ephemeral NVIDIA DSX Air demo nodes and generated demo services. These values are centralized in `installer/src/nv_config_manager_installer/air_sim/constants.py`, including `NVCM_BOX_PASSWORD`, `NVCM_SECRETS`, `NVCM_NETWORK_SECRETS`, and Nautobot demo user defaults.

Do not report those AIR demo credentials as leaked production secrets. Continue to flag user/API credentials, private keys, NGC API keys, Git tokens, and any credentials outside the intentional AIR demo constants.
