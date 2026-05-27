from unittest.mock import patch

import pytest


@pytest.fixture(autouse=True)
def _skip_inotify_check():
    with patch("nv_config_manager_installer.deployer.Deployer._check_inotify_limits"):
        yield
