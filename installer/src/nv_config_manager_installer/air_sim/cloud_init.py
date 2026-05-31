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
"""Cloud-init generation for nvcm-air-simulation."""

from __future__ import annotations

import logging
import shlex
import textwrap
from typing import Any
from urllib.parse import quote, urlsplit, urlunsplit

import yaml

from nv_config_manager_installer.air_sim.constants import (
    CONFIG_MANAGER_NAMESPACE,
    CONFIG_MANAGER_REMOTE_DIR,
    _BlockStyleDumper,
)

LOG = logging.getLogger(__name__)


def _repo_url_with_optional_token(repo_url: str, git_token: str | None) -> str:
    """Return *repo_url* with HTTPS credentials only when a token is supplied."""
    token = (git_token or "").strip()
    if not token:
        return repo_url

    parts = urlsplit(repo_url)
    if parts.scheme not in {"http", "https"}:
        return repo_url

    host = parts.netloc.rsplit("@", 1)[-1]
    username = "x-access-token" if "github.com" in host.lower() else "oauth2"
    netloc = f"{username}:{quote(token, safe='')}@{host}"
    return urlunsplit((parts.scheme, netloc, parts.path, parts.query, parts.fragment))


# ==============================================================================
# Cloud-init setup script template
# ==============================================================================
# Placeholders (__VARNAME__) are substituted at generation time.
# This runs as root during cloud-init, so no sudo needed.

_SETUP_SCRIPT_TEMPLATE = textwrap.dedent("""\
    #!/bin/bash
    set -euo pipefail
    exec > >(tee -a /var/log/nvcm-setup.log) 2>&1
    export HOME=/root

    DEPLOY_SIZE=__DEPLOY_SIZE__
    INTERNAL_IP=__INTERNAL_IP__
    INTERNAL_MAC=__INTERNAL_MAC__
    OOB_SWITCH_GW=__OOB_SWITCH_GW__
    BGP_ASN=__BGP_ASN__
    BGP_PASSWORD=__BGP_PASSWORD__
    RELAY_RETURN_NETWORKS=(__RELAY_RETURN_NETWORKS__)
    echo "========================================"
    echo "  NVCM AIR Setup"
    echo "========================================"
    echo "Started: $(date)"
    echo "Deploy size: $DEPLOY_SIZE"
    echo ""

    # ==========================================================================
    # PREREQUISITES
    # ==========================================================================
    export DEBIAN_FRONTEND=noninteractive
    APT_OPTS='-o Dpkg::Options::=--force-confdef -o Dpkg::Options::=--force-confold'

    echo ">>> Waiting for cloud-init apt lock..."
    for i in $(seq 1 120); do
        fuser /var/lib/dpkg/lock-frontend >/dev/null 2>&1 || break
        sleep 5
    done
    echo ">>> Lock released."

    echo ">>> Updating system packages..."
    apt-get update && apt-get $APT_OPTS upgrade -y

    echo ">>> Installing Docker..."
    if ! command -v docker &>/dev/null; then
        apt-get $APT_OPTS install -y ca-certificates curl gnupg
        install -m 0755 -d /etc/apt/keyrings
        curl -fsSL https://download.docker.com/linux/ubuntu/gpg \\
            | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
        chmod a+r /etc/apt/keyrings/docker.gpg
        . /etc/os-release
        echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \\
            https://download.docker.com/linux/ubuntu $VERSION_CODENAME stable" \\
            > /etc/apt/sources.list.d/docker.list
        apt-get update
        apt-get $APT_OPTS install -y docker-ce docker-ce-cli containerd.io \\
            docker-buildx-plugin docker-compose-plugin
        usermod -aG docker nvcm
    else
        echo "  Docker already installed"
    fi

    echo ">>> Installing kubectl..."
    if ! command -v kubectl &>/dev/null; then
        curl -LO "https://dl.k8s.io/release/$(curl -Ls \\
            https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
        install -o root -g root -m 0755 kubectl /usr/local/bin/kubectl
        rm -f kubectl
    fi

    echo ">>> Installing Helm..."
    if ! command -v helm &>/dev/null; then
        curl -fsSL https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 \\
            | bash
    fi

    echo ">>> Installing Kind..."
    if ! command -v kind &>/dev/null; then
        curl -Lo /usr/local/bin/kind \\
            https://kind.sigs.k8s.io/dl/v0.25.0/kind-linux-amd64
        chmod +x /usr/local/bin/kind
    fi

    echo ">>> Installing uv..."
    if ! command -v uv &>/dev/null; then
        curl -LsSf https://astral.sh/uv/install.sh \\
            | env UV_INSTALL_DIR=/usr/local/bin sh
    fi

    echo ">>> Installing dev tools..."
    apt-get $APT_OPTS install -y git jq htop yq \\
        isc-dhcp-relay sshpass
    systemctl disable isc-dhcp-relay
    systemctl stop isc-dhcp-relay

    # ==========================================================================
    # SYSTEM LIMITS
    # ==========================================================================
    echo ">>> Configuring system limits..."
    if ! grep -q "fs.inotify.max_user_watches" /etc/sysctl.conf 2>/dev/null; then
        cat >> /etc/sysctl.conf <<'SYSCTL'
    fs.inotify.max_user_watches=1048576
    fs.inotify.max_user_instances=8192
    fs.file-max=2097152
    SYSCTL
        sysctl -p
    fi

    # ==========================================================================
    # INTERNAL NETWORK (resolve by MAC)
    # ==========================================================================
    echo ">>> Configuring internal network (MAC: $INTERNAL_MAC)..."
    INT_IFACE=$(ip -o link | grep -i "$INTERNAL_MAC" \\
        | awk -F': ' '{print $2}' | head -1)
    if [[ -n "$INT_IFACE" ]]; then
        echo "  Resolved internal interface: $INT_IFACE"
        ip addr flush dev "$INT_IFACE" 2>/dev/null || true
        ip addr add "$INTERNAL_IP" dev "$INT_IFACE" 2>/dev/null || true
        ip link set "$INT_IFACE" up
        INTERNAL_NETWORK=$(echo "$INTERNAL_IP" | sed 's|\\.[0-9]*/|.0/|')
        ip route add "$INTERNAL_NETWORK" dev "$INT_IFACE" 2>/dev/null || true
        for _rr_net in "${RELAY_RETURN_NETWORKS[@]}"; do
            ip route replace "$_rr_net" via "$OOB_SWITCH_GW" \\
                dev "$INT_IFACE" 2>/dev/null || true
        done
    else
        echo "  WARNING: Could not find interface with MAC $INTERNAL_MAC"
    fi

    # ==========================================================================
    # KIND CLUSTER
    # ==========================================================================
    echo ">>> Creating Kind cluster..."
    kind delete cluster --name nvcm 2>/dev/null || true
    kind create cluster --name nvcm --config /opt/kind-config.yaml --wait 5m
    echo "  Kind cluster created"

    echo ">>> Setting up kubeconfig for nvcm..."
    mkdir -p /home/nvcm/.kube
    kind get kubeconfig --name nvcm > /home/nvcm/.kube/config
    chown -R nvcm:nvcm /home/nvcm/.kube

    # ==========================================================================
    # METALLB
    # ==========================================================================
    echo ">>> Installing MetalLB..."
    helm repo add metallb https://metallb.github.io/metallb 2>/dev/null || true
    helm repo update
    helm upgrade --install metallb metallb/metallb \\
        --namespace metallb-system \\
        --create-namespace \\
        --set frr-k8s.prometheus.serviceMonitor.enabled=false \\
        --wait

    kubectl wait --for=condition=ready pod -n metallb-system \\
        -l app.kubernetes.io/component=controller --timeout=120s

    KIND_SUBNET=$(docker network inspect kind \\
        -f '{{range .IPAM.Config}}{{.Subnet}} {{end}}' 2>/dev/null \\
        | grep -oE '([0-9]+\\.){3}[0-9]+/[0-9]+' | head -1)
    if [[ -n "$KIND_SUBNET" ]]; then
        KIND_PREFIX=$(echo "$KIND_SUBNET" | cut -d'.' -f1-2)
        METALLB_RANGE="${KIND_PREFIX}.255.200-${KIND_PREFIX}.255.220"
    else
        METALLB_RANGE="172.18.255.200-172.18.255.220"
    fi

    kubectl apply -f - <<METALLB_EOF
    apiVersion: metallb.io/v1beta1
    kind: IPAddressPool
    metadata:
      name: kind-pool
      namespace: metallb-system
    spec:
      addresses:
      - ${METALLB_RANGE}
    ---
    apiVersion: metallb.io/v1beta1
    kind: L2Advertisement
    metadata:
      name: kind-l2
      namespace: metallb-system
    METALLB_EOF

    echo "  MetalLB configured with range: $METALLB_RANGE"
    echo "$METALLB_RANGE" > /home/nvcm/.nvcm-metallb-range
    chown nvcm:nvcm /home/nvcm/.nvcm-metallb-range

    CONTROL_PLANE=$(kubectl get nodes \\
        -l node-role.kubernetes.io/control-plane \\
        -o jsonpath='{.items[0].metadata.name}')
    kubectl taint nodes "$CONTROL_PLANE" \\
        node-role.kubernetes.io/control-plane:NoSchedule- 2>/dev/null || true

    # IP forwarding
    echo ">>> Configuring IP forwarding..."
    grep -q "net.ipv4.ip_forward=1" /etc/sysctl.conf || \\
        echo "net.ipv4.ip_forward=1" >> /etc/sysctl.conf
    sysctl -w net.ipv4.ip_forward=1
    iptables -t nat -C POSTROUTING -d 172.18.0.0/16 -j MASQUERADE \\
        2>/dev/null || \\
        iptables -t nat -A POSTROUTING -d 172.18.0.0/16 -j MASQUERADE

    # ==========================================================================
    # FRR (BGP peering with OOB switch)
    # ==========================================================================
    echo ">>> Installing FRR for BGP peering with OOB switch..."
    curl -s https://deb.frrouting.org/frr/keys.gpg \\
        | tee /usr/share/keyrings/frrouting.gpg >/dev/null
    FRRVER="frr-stable"
    echo "deb [signed-by=/usr/share/keyrings/frrouting.gpg] \\
        https://deb.frrouting.org/frr $(lsb_release -s -c) $FRRVER" \\
        | tee /etc/apt/sources.list.d/frr.list
    apt-get update -qq && apt-get install -y -qq frr frr-pythontools \\
        2>/dev/null

    sed -i 's/^bgpd=no/bgpd=yes/' /etc/frr/daemons

    if [[ -n "${KIND_PREFIX:-}" ]]; then
        FRR_METALLB_PREFIX="${KIND_PREFIX}.255.0/24"
    else
        FRR_METALLB_PREFIX="172.18.255.0/24"
    fi

    BRIDGE_ID=$(docker network inspect kind \\
        -f '{{.Id}}' 2>/dev/null | cut -c1-12)
    ip route add "$FRR_METALLB_PREFIX" dev "br-${BRIDGE_ID}" \\
        2>/dev/null || true

    cat > /etc/frr/frr.conf << FRREOF
    frr version 10
    frr defaults traditional
    hostname oob-mgmt-server
    log syslog informational
    service integrated-vtysh-config
    !
    ip prefix-list PL-METALLB seq 10 permit ${FRR_METALLB_PREFIX}
    ip prefix-list PL-METALLB seq 9999 deny any
    !
    route-map RM-EXPORT permit 10
     match ip address prefix-list PL-METALLB
    route-map RM-EXPORT deny 9999
    !
    router bgp ${BGP_ASN}
     bgp router-id __ZTP_URL_HOST__
     no bgp ebgp-requires-policy
     neighbor ${OOB_SWITCH_GW} remote-as external
     !
     address-family ipv4 unicast
      redistribute kernel route-map RM-EXPORT
      neighbor ${OOB_SWITCH_GW} route-map RM-EXPORT out
     exit-address-family
    !
    FRREOF

    systemctl enable frr
    systemctl restart frr
    echo "  FRR BGP configured: ASN ${BGP_ASN}, neighbor ${OOB_SWITCH_GW}"
    echo "  Advertising ${FRR_METALLB_PREFIX}"

    # ==========================================================================
    # REFRESH KUBECONFIG FOR NVCM USER
    # ==========================================================================
    echo ">>> Setting up kubeconfig for nvcm..."
    mkdir -p /home/nvcm/.kube
    kind get kubeconfig --name nvcm > /home/nvcm/.kube/config
    chown -R nvcm:nvcm /home/nvcm/.kube

    # ==========================================================================
    # CLONE REPOSITORIES
    # ==========================================================================
    echo ">>> Ensuring /home/nvcm ownership..."
    chown nvcm:nvcm /home/nvcm

    echo ">>> Cloning repositories..."
    __CLONE_COMMANDS__

    # ==========================================================================
    # DONE
    # ==========================================================================
    echo ""
    echo "========================================"
    echo "  NVCM AIR Setup Complete!"
    echo "========================================"
    echo "Finished: $(date)"
    echo ""
    echo "Cluster status:"
    kubectl get nodes -o wide
    echo ""
    echo "Next step: run nv-config-manager-installer deploy"
    echo "  sudo KUBECONFIG=/home/nvcm/.kube/config uv run \\\\"
    echo "    --directory /home/nvcm/nv-config-manager \\\\"
    echo "    --project /home/nvcm/nv-config-manager/installer \\\\"
    echo "    nv-config-manager-installer deploy /home/nvcm/nv-config-manager-install.yaml \\\\"
    echo "    --chart-dir /home/nvcm/nv-config-manager/deploy/helm \\\\"
    echo "    --kind-cluster nvcm \\\\"
    echo "    --install-envoy-gateway --install-cnpg-operator --install-cert-manager"
""")


def generate_kind_config(deploy_size: str) -> str:
    """Generate a single-node Kind cluster config.

    A single control-plane node avoids MetalLB L2 / pod affinity
    issues where traffic lands on a different node than the pod.
    """
    if deploy_size == "medium":
        mem_system = "2Gi"
        mem_kube = "2Gi"
        eviction = "memory.available<1Gi"
    else:
        mem_system = "1Gi"
        mem_kube = "1Gi"
        eviction = "memory.available<500Mi"

    cp_patch = (
        "kind: InitConfiguration\n"
        "nodeRegistration:\n"
        "  kubeletExtraArgs:\n"
        f"    system-reserved: cpu=50m,memory={mem_system}\n"
        f"    kube-reserved: cpu=50m,memory={mem_kube}\n"
        f"    eviction-hard: {eviction}\n"
    )

    port_mappings = [
        {"containerPort": 30080, "hostPort": 80, "protocol": "TCP"},
        {"containerPort": 30443, "hostPort": 443, "protocol": "TCP"},
    ]
    nodes: list[dict[str, Any]] = [
        {
            "role": "control-plane",
            "extraPortMappings": port_mappings,
            "kubeadmConfigPatches": [cp_patch],
        },
    ]

    config = {
        "kind": "Cluster",
        "apiVersion": "kind.x-k8s.io/v1alpha4",
        "nodes": nodes,
    }
    return yaml.dump(
        config,
        Dumper=_BlockStyleDumper,
        default_flow_style=False,
        sort_keys=False,
    )


def generate_setup_script(
    *,
    deploy_size: str,
    git_token: str | None,
    config_manager_repo: str,
    config_manager_ref: str,
    internal_ip: str,
    internal_mac: str,
    site_name: str,
    oob_gateway: str | None,
    lb_allowed_prefixes: str,
    relay_return_networks: str,
    bgp_asn: str,
) -> str:
    """Build the full OOB-server setup bash script from the template.

    Substitutes placeholder tokens in ``_SETUP_SCRIPT_TEMPLATE`` with
    concrete values so the script can run unattended via cloud-init.
    """
    config_manager_auth = _repo_url_with_optional_token(config_manager_repo, git_token)

    def _quote_shell_words(words: str) -> str:
        return " ".join(shlex.quote(word) for word in words.split())

    clone_lines = (
        f'su - nvcm -c "git clone -b {shlex.quote(config_manager_ref)}'
        f' {shlex.quote(config_manager_auth)} {shlex.quote(CONFIG_MANAGER_REMOTE_DIR)}"'
    )

    script = _SETUP_SCRIPT_TEMPLATE
    script = script.replace("__DEPLOY_SIZE__", shlex.quote(deploy_size))
    script = script.replace("__INTERNAL_IP__", shlex.quote(internal_ip))
    script = script.replace("__INTERNAL_MAC__", shlex.quote(internal_mac))
    ztp_url_host = internal_ip.split("/")[0]
    script = script.replace("__ZTP_URL_HOST__", ztp_url_host)
    script = script.replace("__SITE_NAME__", site_name)
    script = script.replace("__CONFIG_MANAGER_NAMESPACE__", CONFIG_MANAGER_NAMESPACE)
    script = script.replace("__OOB_SWITCH_GW__", shlex.quote(oob_gateway or "UNSET"))
    script = script.replace("__LB_ALLOWED_PREFIXES__", _quote_shell_words(lb_allowed_prefixes))
    script = script.replace("__RELAY_RETURN_NETWORKS__", _quote_shell_words(relay_return_networks))
    script = script.replace("__BGP_ASN__", shlex.quote(bgp_asn))
    script = script.replace("__CLONE_COMMANDS__", clone_lines)
    return script


def generate_server_cloud_init(
    *,
    internal_mac: str,
    git_token: str | None = None,
    config_manager_repo: str = "",
    config_manager_ref: str = "main",
    deploy_size: str = "medium",
    internal_ip: str,
    site_name: str,
    oob_gateway: str | None,
    lb_allowed_prefixes: str = "0.0.0.0/0",
    relay_return_networks: str = "",
    bgp_asn: str = "4266000000",
) -> str:
    """Generate cloud-init user-data for the oob-mgmt-server.

    eth0 is the AIR exit interface (auto-DHCP by AIR, no config needed).
    eth1 is the internal OOB interface configured here with a static IP
    matched by MAC address.

    When *config_manager_repo* is supplied, produces a full-setup cloud-init that
    installs all prerequisites, creates a Kind cluster with MetalLB, clones the
    nv-config-manager repository. ``git_token`` is optional and is only embedded in
    the clone URL when set, which keeps public GitHub clones tokenless by
    default while still allowing private forks.
    """
    netplan_yaml = yaml.dump(
        {
            "network": {
                "version": 2,
                "ethernets": {
                    "eth1-internal": {
                        "match": {"macaddress": internal_mac},
                        "dhcp4": False,
                        "addresses": [internal_ip],
                        "optional": True,
                    },
                },
            }
        },
        Dumper=_BlockStyleDumper,
        default_flow_style=False,
        sort_keys=False,
    )

    write_files: list[dict[str, Any]] = [
        {
            "path": "/etc/netplan/99-air-config.yaml",
            "permissions": "0600",
            "content": netplan_yaml,
        },
        {
            "path": "/etc/sudoers.d/99-nvcm-nopasswd",
            "content": "nvcm ALL=(ALL) NOPASSWD:ALL\n",
        },
    ]

    runcmd: list[list[str]] = [
        ["netplan", "apply"],
    ]

    if config_manager_repo:
        setup_script = generate_setup_script(
            deploy_size=deploy_size,
            git_token=git_token,
            config_manager_repo=config_manager_repo,
            config_manager_ref=config_manager_ref,
            internal_ip=internal_ip,
            internal_mac=internal_mac,
            site_name=site_name,
            oob_gateway=oob_gateway,
            lb_allowed_prefixes=lb_allowed_prefixes,
            relay_return_networks=relay_return_networks,
            bgp_asn=bgp_asn,
        )
        kind_config = generate_kind_config(deploy_size)

        write_files.extend(
            [
                {
                    "path": "/opt/nvcm-setup.sh",
                    "permissions": "0755",
                    "content": setup_script,
                },
                {
                    "path": "/opt/kind-config.yaml",
                    "content": kind_config,
                },
            ]
        )
        runcmd.append(["bash", "/opt/nvcm-setup.sh"])

    cloud_config: dict[str, Any] = {
        "users": [
            {
                "name": "nvcm",
                "gecos": "NVCM Demo User",
                "groups": "sudo,adm",
                "shell": "/bin/bash",
                "lock_passwd": False,
                "passwd": (
                    "$6$nvcmsalt$lHuZ5gth0uLkQEy.uz47oeG85XNZwA8AIHmFEKf98ZBs0S4b5M69JX2DyqQKTD05Hlek39poAyNJgN1J.0A.y/"
                ),
            },
        ],
        "ssh_pwauth": True,
        "chpasswd": {"expire": False},
        "write_files": write_files,
        "runcmd": runcmd,
    }

    return "#cloud-config\n" + yaml.dump(
        cloud_config,
        Dumper=_BlockStyleDumper,
        default_flow_style=False,
        sort_keys=False,
    )
