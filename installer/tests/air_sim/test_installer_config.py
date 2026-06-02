# SPDX-FileCopyrightText: Copyright (c) 2024-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Tests for AIR sim installer config generation."""

from __future__ import annotations

import json

from nv_config_manager_installer.air_sim.constants import (
    CONFIG_MANAGER_REMOTE_DIR,
    DEFAULT_AIR_DEMO_TEMPLATE_PLUGIN_PATH,
    PROJECT_ROOT,
)
from nv_config_manager_installer.air_sim.installer_config import (
    build_content_jobs,
    build_deploy_command,
    build_template_plugins,
    generate_air_sim_install_config,
)
from nv_config_manager_installer.air_sim.prebuilt_configs import load_prebuilt_config
from nv_config_manager_installer.air_sim.sim_config import SimConfig


def test_install_config_uses_mock_topology_with_paired_template_plugin() -> None:
    cfg = SimConfig(
        mock_blueprint="air_trial",
        deployment_name="demo",
        mock_topology_path="development/mock_topology",
    )

    install_config = generate_air_sim_install_config(
        cfg,
        site_name="air-demo",
        lb_allowed_prefixes=["172.18.255.0/24"],
    )

    content = install_config["content"]
    assert content["template_plugins"] == [
        {
            "path": (
                f"{CONFIG_MANAGER_REMOTE_DIR}/{DEFAULT_AIR_DEMO_TEMPLATE_PLUGIN_PATH.as_posix()}"
            )
        }
    ]
    assert content["jobs"] == [{"path": f"{CONFIG_MANAGER_REMOTE_DIR}/development/mock_topology"}]
    assert content["run_after_deploy"] == [
        {
            "job": "mock_topology.jobs.mock_topology_design.MockTopologyDesign",
            "input": json.dumps({"blueprint": "air_trial", "deployment_name": "demo"}),
        }
    ]
    assert "ingest" not in json.dumps(content).lower()


def test_build_content_jobs_appends_extra_jobs() -> None:
    cfg = SimConfig(
        run_mock_topology_job=True,
        mock_blueprint="air_superpod",
        deployment_name="demo",
        mock_topology_path="development/mock_topology",
        extra_job_paths=["development/custom_jobs"],
        extra_run_after_deploy=[{"job": "custom.jobs.RunDemo", "input": {"name": "demo"}}],
    )

    jobs, run_after_deploy = build_content_jobs(cfg)

    assert jobs == [
        {"path": f"{CONFIG_MANAGER_REMOTE_DIR}/development/mock_topology"},
        {"path": f"{CONFIG_MANAGER_REMOTE_DIR}/development/custom_jobs"},
    ]
    assert run_after_deploy[0]["job"] == (
        "mock_topology.jobs.mock_topology_design.MockTopologyDesign"
    )
    assert run_after_deploy[1] == {
        "job": "custom.jobs.RunDemo",
        "input": json.dumps({"name": "demo"}),
    }


def test_custom_jobs_do_not_infer_mock_topology() -> None:
    cfg = SimConfig(
        run_mock_topology_job=False,
        extra_job_paths=["/opt/custom/jobs"],
        extra_run_after_deploy=[{"job": "custom.jobs.RunDemo", "input": ""}],
    )

    jobs, run_after_deploy = build_content_jobs(cfg)

    assert jobs == [{"path": "/opt/custom/jobs"}]
    assert run_after_deploy == [{"job": "custom.jobs.RunDemo", "input": ""}]


def test_template_plugin_paths_are_included_without_generation() -> None:
    cfg = SimConfig(
        run_mock_topology_job=False,
        template_plugin_paths=[
            "development/template_plugins/demo",
            "/opt/external/template-plugin.tar.gz",
        ],
    )

    assert build_template_plugins(cfg) == [
        {"path": f"{CONFIG_MANAGER_REMOTE_DIR}/development/template_plugins/demo"},
        {"path": "/opt/external/template-plugin.tar.gz"},
    ]

    install_config = generate_air_sim_install_config(
        cfg,
        site_name="air-demo",
        lb_allowed_prefixes=["172.18.255.0/24"],
    )
    assert install_config["content"]["template_plugins"] == [
        {"path": f"{CONFIG_MANAGER_REMOTE_DIR}/development/template_plugins/demo"},
        {"path": "/opt/external/template-plugin.tar.gz"},
    ]


def test_prebuilt_demos_include_static_template_plugin() -> None:
    expected = DEFAULT_AIR_DEMO_TEMPLATE_PLUGIN_PATH.as_posix()

    for config_id in ("air-trial", "superpod"):
        cfg = load_prebuilt_config(config_id)
        assert cfg.template_plugin_paths == [expected]
        assert build_template_plugins(cfg) == [{"path": f"{CONFIG_MANAGER_REMOTE_DIR}/{expected}"}]


def test_default_superpod_mock_topology_includes_static_template_plugin() -> None:
    expected = DEFAULT_AIR_DEMO_TEMPLATE_PLUGIN_PATH.as_posix()

    cfg = SimConfig()

    assert cfg.mock_blueprint == "air_superpod"
    assert build_template_plugins(cfg) == [{"path": f"{CONFIG_MANAGER_REMOTE_DIR}/{expected}"}]


def test_demo_template_plugin_is_static_and_public_named() -> None:
    plugin_dir = PROJECT_ROOT / DEFAULT_AIR_DEMO_TEMPLATE_PLUGIN_PATH

    assert (plugin_dir / "pyproject.toml").is_file()
    assert not (plugin_dir / "scripts").exists()

    plugin_text = "\n".join(path.read_text() for path in plugin_dir.rglob("*") if path.is_file())
    assert "generate_template_plugin" not in plugin_text
    assert "kiwi" not in plugin_text.lower()
    assert 'dhcp_servers("nvcm", true)' in plugin_text
    assert "REDISTRIBUTE-CONNECTED" in plugin_text
    assert "OOB-SERVER-P2P" in plugin_text
    assert "source-ip: giaddress" in plugin_text


def test_public_air_deploy_command_uses_default_numpy_wheel_path() -> None:
    command = build_deploy_command(SimConfig(use_internal=False))

    assert "NVCM_NUMPY_FROM_SOURCE" not in command


def test_internal_air_deploy_command_uses_default_numpy_wheel_path() -> None:
    command = build_deploy_command(SimConfig(use_internal=True))

    assert "NVCM_NUMPY_FROM_SOURCE" not in command
