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
"""Integration tests for NVIDIA Config Manager.

These tests run against a live Kubernetes cluster with NVIDIA Config Manager deployed.
They can be run in CI after deploying to a Kind cluster, or locally
against any running NVIDIA Config Manager environment.

All traffic is routed through the Envoy Gateway to validate the full
routing and gateway configuration, including TLS and hostname-based routing.

Usage:
    # Run integration tests through Envoy Gateway
    pytest src/tests/integration/ -v

    # Run with custom namespace
    pytest src/tests/integration/ -v --nv-config-manager-namespace nv-config-manager

    # Run with custom base hostname
    pytest src/tests/integration/ -v --base-hostname config-manager.example.com

    # Local Kind runs require config-manager.local hostnames to resolve to the
    # host port exposed by deploy/kind-config.yaml.
    # Example /etc/hosts entry:
    # 127.0.0.1 config-manager.local render.config-manager.local ztp.config-manager.local dhcp.config-manager.local workflow.config-manager.local temporal.config-manager.local nautobot.config-manager.local config-store.config-manager.local
"""
