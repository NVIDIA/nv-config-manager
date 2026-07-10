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
"""ZTP Service configuration screen."""

from __future__ import annotations

from textual import work
from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Button, Checkbox, Input, Label, RadioButton, RadioSet, Select
from textual_fspicker import FileOpen

from nv_config_manager_installer.schema import (
    NVConfigManagerInstallConfig,
    ZTPOSImage,
    ZTPStorageType,
)
from nv_config_manager_installer.tui.screens.node_picker import NodeSelectorPanel

_ZTP_PLATFORMS: list[tuple[str, str]] = [
    ("Cumulus Linux", "cumulus-linux"),
    ("Arista EOS", "arista-eos"),
    ("NV-OS", "nv-os"),
    ("MLNX-OS", "mlnx-os"),
]

_W_ZTP_FILE = "#ztp-storage-file"


class ZTPScreen(Container):
    """ZTP Service: toggle, storage, OS image catalogue, and node scheduling."""

    def __init__(self, config: NVConfigManagerInstallConfig, **kwargs: object) -> None:
        super().__init__(**kwargs)
        self._config = config

    def compose(self) -> ComposeResult:
        zs = self._config.infrastructure.ztp_storage
        yield Label("OS Images", classes="section-title")
        yield Label("─" * 40, classes="section-divider")

        yield Label("Storage Type", classes="field-label")
        with RadioSet(id="ztp-storage-type"):
            yield RadioButton(
                "S3",
                value=zs.type == ZTPStorageType.S3,
                id="ztp-storage-s3",
            )
            yield RadioButton(
                "File (PVC)",
                value=zs.type == ZTPStorageType.FILE,
                id="ztp-storage-file",
            )

        with Container(id="ztp-s3-fields"):
            yield Checkbox(
                "Use Rook Ceph object storage",
                value=zs.s3_ceph.enabled,
                id="ztp-s3-ceph-enabled",
            )
            with Container(id="ztp-s3-bucket-fields"):
                yield Label("S3 Bucket", classes="field-label")
                yield Input(
                    value=zs.s3_bucket,
                    placeholder="ngc-network-firmware-images",
                    id="ztp-s3-bucket",
                )
            with Container(id="ztp-s3-endpoint-fields"):
                yield Label("S3 Endpoint", classes="field-label")
                yield Input(
                    value=zs.s3_endpoint,
                    placeholder="https://s3.example.com",
                    id="ztp-s3-endpoint",
                )
            with Container(id="ztp-s3-region-fields"):
                yield Label("AWS S3 Region (IRSA, optional)", classes="field-label")
                yield Input(
                    value=zs.s3_region,
                    placeholder="us-west-2",
                    id="ztp-s3-region",
                )
            with Container(id="ztp-s3-ceph-fields"):
                yield Label("Ceph ObjectBucketClaim Storage Class", classes="field-label")
                yield Input(
                    value=zs.s3_ceph.object_bucket_claim.storage_class_name,
                    placeholder="ceph-object-store",
                    id="ztp-s3-ceph-storage-class",
                )

        with Container(id="ztp-file-fields"):
            yield Label("PVC Name", classes="field-label")
            yield Input(value=zs.pvc_name, placeholder="ztp-os-images", id="ztp-pvc-name")
            yield Label("PVC Size", classes="field-label")
            yield Input(value=zs.pvc_size, placeholder="10Gi", id="ztp-pvc-size")
            yield Label("Storage Class (optional)", classes="field-label")
            yield Input(value=zs.storage_class, placeholder="", id="ztp-storage-class")
            yield Label("PVC Access Mode", classes="field-label")
            with RadioSet(id="ztp-access-mode"):
                yield RadioButton(
                    "ReadWriteOnce  (single-node, no NFS required)",
                    value=zs.access_mode != "ReadWriteMany",
                    id="ztp-access-rwo",
                )
                yield RadioButton(
                    "ReadWriteMany  (multi-node, requires NFS or RWX storage class)",
                    value=zs.access_mode == "ReadWriteMany",
                    id="ztp-access-rwx",
                )

        with Container(id="ztp-file-only-fields"):
            yield Label("OS Images", classes="field-label")
            yield Button("+ Add Image", id="ztp-img-add", classes="add-button")
            with Horizontal(classes="ztp-img-header"):
                hdr_plat = Label("Platform")
                hdr_plat.styles.width = "1fr"
                yield hdr_plat
                hdr_ver = Label("Version")
                hdr_ver.styles.width = "1fr"
                yield hdr_ver
                hdr_path = Label("File Path")
                hdr_path.styles.width = "2fr"
                yield hdr_path
                hdr_spacer = Label("")
                hdr_spacer.styles.width = 15
                yield hdr_spacer
            yield Vertical(id="ztp-img-list")

            yield NodeSelectorPanel("ztp", zs.node_selector, id="ztp-node-selector")

    def on_mount(self) -> None:
        self._toggle_storage_fields()
        self._rebuild_image_rows()

    def on_radio_set_changed(self, event: RadioSet.Changed) -> None:
        if event.radio_set.id == "ztp-storage-type":
            self._toggle_storage_fields()

    def on_checkbox_changed(self, event: Checkbox.Changed) -> None:
        if event.checkbox.id == "ztp-s3-ceph-enabled":
            self._toggle_storage_fields()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        bid = event.button.id or ""
        if bid == "ztp-img-add":
            self._collect_images()
            self._config.infrastructure.ztp_storage.os_images.append(ZTPOSImage())
            self._rebuild_image_rows()
        elif bid.startswith("ztp-img-") and bid.endswith("-browse"):
            self._pick_image(int(bid.split("-")[2]))
        elif bid.startswith("ztp-img-") and bid.endswith("-remove"):
            self._handle_image_remove(bid)

    def _handle_image_remove(self, bid: str) -> None:
        self._collect_images()
        try:
            idx = int(bid.split("-")[2])
            images = self._config.infrastructure.ztp_storage.os_images
            if 0 <= idx < len(images):
                images.pop(idx)
        except (ValueError, IndexError):
            pass
        self._rebuild_image_rows()

    @work
    async def _pick_image(self, idx: int) -> None:
        picked = await self.app.push_screen_wait(FileOpen(title="Select OS Image"))
        if picked is not None:
            try:
                self.query_one(f"#ztp-img-{idx}-path", Input).value = str(picked)
            except LookupError:
                pass

    def _toggle_storage_fields(self) -> None:
        is_file = self.query_one(_W_ZTP_FILE, RadioButton).value
        ceph_enabled = False
        try:
            ceph_enabled = self.query_one("#ztp-s3-ceph-enabled", Checkbox).value
        except LookupError:
            pass
        self.query_one("#ztp-file-fields").display = is_file
        self.query_one("#ztp-s3-fields").display = not is_file
        self.query_one("#ztp-s3-bucket-fields").display = not is_file
        self.query_one("#ztp-s3-endpoint-fields").display = not is_file and not ceph_enabled
        self.query_one("#ztp-s3-region-fields").display = not is_file and not ceph_enabled
        self.query_one("#ztp-s3-ceph-fields").display = not is_file and ceph_enabled
        self.query_one("#ztp-file-only-fields").display = is_file

    def _rebuild_image_rows(self) -> None:
        container = self.query_one("#ztp-img-list", Vertical)
        container.remove_children()
        for i, img in enumerate(self._config.infrastructure.ztp_storage.os_images):
            plat_kwargs: dict = {
                "options": [(label, slug) for label, slug in _ZTP_PLATFORMS],
                "allow_blank": True,
                "prompt": "Select platform",
                "id": f"ztp-img-{i}-platform",
            }
            if img.platform:
                plat_kwargs["value"] = img.platform
            plat = Select(**plat_kwargs)
            plat.styles.width = "1fr"
            ver = Input(value=img.version, placeholder="5.14.0", id=f"ztp-img-{i}-version")
            ver.styles.width = "1fr"
            path_inp = Input(
                value=img.path, placeholder="/path/to/firmware.bin", id=f"ztp-img-{i}-path"
            )
            path_inp.styles.width = "2fr"
            browse = Button("...", id=f"ztp-img-{i}-browse")
            browse.styles.width = "auto"
            browse.styles.min_width = 5
            btn = Button("Remove", variant="error", id=f"ztp-img-{i}-remove")
            btn.styles.width = "auto"
            btn.styles.min_width = 10
            row = Horizontal(classes="account-title-row")
            row.compose_add_child(plat)
            row.compose_add_child(ver)
            row.compose_add_child(path_inp)
            row.compose_add_child(browse)
            row.compose_add_child(btn)
            container.mount(row)

    def _collect_images(self) -> None:
        images: list[ZTPOSImage] = []
        for i in range(len(self._config.infrastructure.ztp_storage.os_images)):
            try:
                sel = self.query_one(f"#ztp-img-{i}-platform", Select)
                platform = str(sel.value) if sel.value is not Select.BLANK else ""
                version = self.query_one(f"#ztp-img-{i}-version", Input).value.strip()
                path = self.query_one(f"#ztp-img-{i}-path", Input).value.strip()
                if path:
                    images.append(ZTPOSImage(platform=platform, version=version, path=path))
            except LookupError:
                pass
        self._config.infrastructure.ztp_storage.os_images = images

    def write_to_config(self, config: NVConfigManagerInstallConfig) -> None:
        self._collect_images()
        zs = config.infrastructure.ztp_storage
        zs.type = (
            ZTPStorageType.FILE
            if self.query_one(_W_ZTP_FILE, RadioButton).value
            else ZTPStorageType.S3
        )
        zs.s3_ceph.enabled = self.query_one("#ztp-s3-ceph-enabled", Checkbox).value
        zs.s3_bucket = self.query_one("#ztp-s3-bucket", Input).value
        if zs.s3_ceph.enabled:
            zs.s3_endpoint = ""
            zs.s3_region = ""
        else:
            zs.s3_endpoint = self.query_one("#ztp-s3-endpoint", Input).value
            zs.s3_region = self.query_one("#ztp-s3-region", Input).value
        zs.s3_ceph.object_bucket_claim.storage_class_name = self.query_one(
            "#ztp-s3-ceph-storage-class", Input
        ).value
        zs.pvc_name = self.query_one("#ztp-pvc-name", Input).value
        zs.pvc_size = self.query_one("#ztp-pvc-size", Input).value
        zs.storage_class = self.query_one("#ztp-storage-class", Input).value
        zs.access_mode = (
            "ReadWriteMany"
            if self.query_one("#ztp-access-rwx", RadioButton).value
            else "ReadWriteOnce"
        )
        zs.os_images = list(self._config.infrastructure.ztp_storage.os_images)
        try:
            zs.node_selector = self.query_one("#ztp-node-selector", NodeSelectorPanel).collect()
        except Exception:
            pass

    def sync_from_config(self, config: NVConfigManagerInstallConfig) -> None:
        self._config = config
        zs = config.infrastructure.ztp_storage
        try:
            self.query_one("#ztp-storage-s3", RadioButton).value = zs.type == ZTPStorageType.S3
            self.query_one(_W_ZTP_FILE, RadioButton).value = zs.type == ZTPStorageType.FILE
            self.query_one("#ztp-s3-bucket", Input).value = zs.s3_bucket
            self.query_one("#ztp-s3-endpoint", Input).value = zs.s3_endpoint
            self.query_one("#ztp-s3-region", Input).value = zs.s3_region
            self.query_one("#ztp-s3-ceph-enabled", Checkbox).value = zs.s3_ceph.enabled
            self.query_one(
                "#ztp-s3-ceph-storage-class", Input
            ).value = zs.s3_ceph.object_bucket_claim.storage_class_name
            self.query_one("#ztp-pvc-name", Input).value = zs.pvc_name
            self.query_one("#ztp-pvc-size", Input).value = zs.pvc_size
            self.query_one("#ztp-storage-class", Input).value = zs.storage_class
            self.query_one("#ztp-access-rwo", RadioButton).value = zs.access_mode != "ReadWriteMany"
            self.query_one("#ztp-access-rwx", RadioButton).value = zs.access_mode == "ReadWriteMany"
            self.query_one("#ztp-node-selector", NodeSelectorPanel).set_selector(zs.node_selector)
        except Exception:
            pass
        self._config.infrastructure.ztp_storage.os_images = list(zs.os_images)
        self._rebuild_image_rows()
        self._toggle_storage_fields()

    def get_status(self, config: NVConfigManagerInstallConfig) -> str:
        return "[*]" if config.services.ztp else "[ ]"
