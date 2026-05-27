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
"""Node selector browser and reusable NodeSelectorPanel widget."""

from __future__ import annotations

from textual import work
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label, ListItem, ListView

# Labels that add no useful scheduling signal and clutter the browser.
_NOISE_LABELS: frozenset[str] = frozenset(
    {
        "beta.kubernetes.io/arch",
        "beta.kubernetes.io/os",
        "node.kubernetes.io/exclude-from-external-load-balancers",
        "kubernetes.io/arch",
        "kubernetes.io/os",
    }
)


class NodePickerModal(ModalScreen["tuple[str, str] | None"]):
    """Browse live cluster nodes and pick a label key=value to use as a node selector.

    Dismissed with ``(key, value)`` when a label is selected, or ``None`` on cancel.
    """

    BINDINGS = [("escape", "dismiss(None)", "Cancel")]

    DEFAULT_CSS = """
    NodePickerModal {
        align: center middle;
    }
    #node-picker-dialog {
        width: 90;
        max-height: 34;
        background: $surface;
        border: thick $primary;
        padding: 1 2;
    }
    #node-label-list {
        height: 24;
        border: solid $accent;
    }
    #node-picker-status {
        color: $text-muted;
        padding: 0 0 1 0;
    }
    """

    def compose(self) -> ComposeResult:
        with Vertical(id="node-picker-dialog"):
            yield Label("Browse Node Labels", classes="section-title")
            yield Label("Loading cluster nodes…", id="node-picker-status")
            yield ListView(id="node-label-list")
            yield Button("Cancel", id="node-picker-cancel")

    def on_mount(self) -> None:
        self._label_pairs: list[tuple[str, str, str]] = []  # (node_name, key, value)
        self._load_nodes()

    @work
    async def _load_nodes(self) -> None:
        status = self.query_one("#node-picker-status", Label)
        lst = self.query_one("#node-label-list", ListView)

        try:
            from kubernetes import client as k8s_client
            from kubernetes import config as k8s_config
            from kubernetes.config.config_exception import ConfigException

            try:
                k8s_config.load_kube_config()
            except ConfigException:
                status.update("No kubeconfig found — enter labels manually.")
                return

            v1 = k8s_client.CoreV1Api()
            nodes = sorted(v1.list_node().items, key=lambda n: n.metadata.name)
        except Exception as exc:
            status.update(f"Could not list nodes: {exc}")
            return

        pairs: list[tuple[str, str, str]] = []
        for node in nodes:
            name = node.metadata.name
            labels: dict[str, str] = dict(node.metadata.labels or {})
            # Hostname label first — most common selector.
            hostname_key = "kubernetes.io/hostname"
            if hostname_key in labels:
                pairs.append((name, hostname_key, labels[hostname_key]))
            for k in sorted(labels):
                if k != hostname_key and k not in _NOISE_LABELS:
                    pairs.append((name, k, labels[k]))

        if not pairs:
            status.update("No nodes found.")
            return

        self._label_pairs = pairs
        status.update("Click a label to add it as a node selector constraint:")
        for node_name, key, value in pairs:
            display = f"{node_name}  [{key} = {value!r}]"
            lst.append(ListItem(Label(display)))

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        idx = event.list_view.index
        if idx is not None and idx < len(self._label_pairs):
            _, key, value = self._label_pairs[idx]
            self.dismiss((key, value))

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "node-picker-cancel":
            self.dismiss(None)


class NodeSelectorPanel(Vertical):
    """Editable list of node selector key=value pairs with a live node browser.

    Usage::

        yield NodeSelectorPanel("tpl", config.content.template_plugins_config.node_selector)
        ...
        selector = self.query_one(NodeSelectorPanel).collect()
    """

    DEFAULT_CSS = """
    NodeSelectorPanel {
        height: auto;
    }
    NodeSelectorPanel .ns-row {
        height: auto;
    }
    NodeSelectorPanel .ns-list {
        height: auto;
    }
    NodeSelectorPanel .ns-row Input {
        width: 1fr;
    }
    NodeSelectorPanel .ns-row Button {
        width: auto;
        min-width: 10;
    }
    NodeSelectorPanel #ns-actions {
        height: auto;
        margin-bottom: 1;
    }
    """

    def __init__(self, prefix: str, initial: dict[str, str], **kwargs: object) -> None:
        super().__init__(**kwargs)
        self._prefix = prefix
        self._pairs: list[tuple[str, str]] = list(initial.items())

    def compose(self) -> ComposeResult:
        yield Label("Node Selector (optional)", classes="field-label")
        yield Label(
            "May be required on multi-node clusters without shared NFS/RWX storage.",
            classes="section-divider",
        )
        yield Label(
            "If a PVC is created as ReadWriteOnce, it can only mount on the node where it was first bound.",
            classes="field-label-compact",
        )
        yield Label(
            "Pin the pod to that node here, or leave empty on single-node or shared-storage clusters.",
            classes="field-label-compact",
        )
        with Horizontal(id="ns-actions"):
            yield Button("+ Add Label", id=f"{self._prefix}-ns-add", classes="add-button")
            yield Button("Browse Nodes", id=f"{self._prefix}-ns-browse", classes="add-button")
        yield Vertical(id=f"{self._prefix}-ns-list", classes="ns-list")

    def on_mount(self) -> None:
        self._rebuild()

    def set_selector(self, selector: dict[str, str]) -> None:
        """Replace the current pairs from a fresh config dict."""
        self._pairs = list(selector.items())
        self._rebuild()

    def collect(self) -> dict[str, str]:
        """Read current widget values and return a node selector dict."""
        result: dict[str, str] = {}
        for i in range(len(self._pairs)):
            try:
                k = self.query_one(f"#{self._prefix}-ns-{i}-key", Input).value.strip()
                v = self.query_one(f"#{self._prefix}-ns-{i}-val", Input).value.strip()
                if k:
                    result[k] = v
            except Exception:
                pass
        return result

    def _rebuild(self) -> None:
        container = self.query_one(f"#{self._prefix}-ns-list", Vertical)
        container.remove_children()
        for i, (k, v) in enumerate(self._pairs):
            key_inp = Input(
                value=k, placeholder="kubernetes.io/hostname", id=f"{self._prefix}-ns-{i}-key"
            )
            key_inp.styles.width = "1fr"
            val_inp = Input(value=v, placeholder="worker-01", id=f"{self._prefix}-ns-{i}-val")
            val_inp.styles.width = "1fr"
            btn = Button("Remove", variant="error", id=f"{self._prefix}-ns-{i}-remove")
            btn.styles.width = "auto"
            btn.styles.min_width = 10
            row = Horizontal(classes="ns-row")
            row.compose_add_child(key_inp)
            row.compose_add_child(val_inp)
            row.compose_add_child(btn)
            container.mount(row)

    def _collect_current(self) -> None:
        new_pairs: list[tuple[str, str]] = []
        for i in range(len(self._pairs)):
            try:
                k = self.query_one(f"#{self._prefix}-ns-{i}-key", Input).value.strip()
                v = self.query_one(f"#{self._prefix}-ns-{i}-val", Input).value.strip()
                new_pairs.append((k, v))
            except Exception:
                pass
        self._pairs = new_pairs

    def on_button_pressed(self, event: Button.Pressed) -> None:
        bid = event.button.id or ""
        if (
            not bid.startswith(f"{self._prefix}-ns-")
            and bid != f"{self._prefix}-ns-add"
            and bid != f"{self._prefix}-ns-browse"
        ):
            return
        event.stop()

        if bid == f"{self._prefix}-ns-add":
            self._collect_current()
            self._pairs.append(("", ""))
            self._rebuild()
        elif bid == f"{self._prefix}-ns-browse":
            self._open_node_picker()
        elif bid.endswith("-remove"):
            parts = bid.split("-")
            try:
                idx = int(parts[-2])
                self._collect_current()
                if 0 <= idx < len(self._pairs):
                    self._pairs.pop(idx)
                self._rebuild()
            except (ValueError, IndexError):
                pass

    @work
    async def _open_node_picker(self) -> None:
        result: tuple[str, str] | None = await self.app.push_screen_wait(NodePickerModal())
        if result is not None:
            key, value = result
            self._collect_current()
            self._pairs.append((key, value))
            self._rebuild()
