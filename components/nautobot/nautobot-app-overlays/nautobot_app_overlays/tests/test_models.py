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

"""Tests for Overlays models."""

from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.test import TestCase
from nautobot.dcim.models import Device, DeviceType, Location, LocationType, Manufacturer
from nautobot.extras.models import Role, Status
from nautobot.ipam.models import Namespace
from nautobot.tenancy.models import Tenant

from nautobot_app_overlays.choices import (
    IsolationTypeChoices,
    PKeyMembershipTypeChoices,
    VNITypeChoices,
)
from nautobot_app_overlays.models import VXLAN, InfiniBandMKey, InfiniBandPKey, Overlay, OverlayAssignment
from nautobot_app_overlays.tests.fixtures import get_or_create_status_for_model


class OverlayModelTest(TestCase):
    """Test cases for Overlay model."""

    @classmethod
    def setUpTestData(cls):
        """Set up test data."""
        cls.status = get_or_create_status_for_model(Overlay)
        cls.tenant = Tenant.objects.create(name="Test Tenant")
        cls.location_type = LocationType.objects.create(name="Site")
        cls.location = Location.objects.create(
            name="Test Site",
            location_type=cls.location_type,
            status=Status.objects.get_for_model(Location).first(),
        )

    def test_create_overlay(self):
        """Test creating an Overlay."""
        overlay = Overlay.objects.create(
            name="Test Overlay",
            tenant=self.tenant,
            location=self.location,
            isolation_type=IsolationTypeChoices.VXLAN_EVPN,
            status=self.status,
        )
        self.assertEqual(str(overlay), "Test Overlay")
        self.assertEqual(overlay.tenant, self.tenant)
        self.assertEqual(overlay.location, self.location)

    def test_unique_name_per_location(self):
        """Test that overlay names must be unique within a location."""
        Overlay.objects.create(
            name="Unique Overlay",
            tenant=self.tenant,
            location=self.location,
            isolation_type=IsolationTypeChoices.NVLINK_PARTITION,
            status=self.status,
        )
        with self.assertRaises(Exception):
            Overlay.objects.create(
                name="Unique Overlay",
                tenant=self.tenant,
                location=self.location,
                isolation_type=IsolationTypeChoices.NVLINK_PARTITION,
                status=self.status,
            )

    def test_isolation_type_immutable_with_assignments(self):
        """Test that isolation_type cannot be changed when assignments exist."""
        overlay = Overlay.objects.create(
            name="Immutable Type Overlay",
            tenant=self.tenant,
            location=self.location,
            isolation_type=IsolationTypeChoices.VXLAN_EVPN,
            status=self.status,
        )
        assignment_status = get_or_create_status_for_model(OverlayAssignment)
        manufacturer = Manufacturer.objects.create(name="Test Mfr Immut")
        device_type = DeviceType.objects.create(model="Test DT Immut", manufacturer=manufacturer)
        role, _ = Role.objects.get_or_create(name="Test Role Immut")
        role.content_types.add(ContentType.objects.get_for_model(Device))
        device = Device.objects.create(
            name="Test Device for Immutability",
            device_type=device_type,
            role=role,
            location=self.location,
            status=Status.objects.get_for_model(Device).first(),
        )
        ct = ContentType.objects.get_for_model(Device)
        OverlayAssignment.objects.create(
            overlay=overlay,
            assigned_object_type=ct,
            assigned_object_id=device.pk,
            status=assignment_status,
        )

        overlay.isolation_type = IsolationTypeChoices.IB_PKEY
        with self.assertRaises(ValidationError):
            overlay.full_clean()


class VXLANModelTest(TestCase):
    """Test cases for VXLAN model."""

    @classmethod
    def setUpTestData(cls):
        """Set up test data."""
        cls.status = get_or_create_status_for_model(VXLAN)
        cls.namespace = Namespace.objects.first() or Namespace.objects.create(name="Test Namespace")

    def test_create_vxlan(self):
        """Test creating a VXLAN."""
        vxlan = VXLAN.objects.create(
            vnid=10001,
            name="Test VXLAN",
            namespace=self.namespace,
            status=self.status,
        )
        self.assertEqual(str(vxlan), "Test VXLAN (VNI: 10001)")

    def test_vnid_range_validation(self):
        """Test VNI range validation."""
        vxlan = VXLAN(vnid=16777215, name="Max VNI", namespace=self.namespace, status=self.status)
        vxlan.full_clean()

        with self.assertRaises(Exception):
            vxlan = VXLAN(vnid=16777216, name="Invalid VNI", namespace=self.namespace, status=self.status)
            vxlan.full_clean()

    def test_vni_type_l2(self):
        """Test creating an L2 VNI."""
        vxlan = VXLAN.objects.create(
            vnid=2001,
            name="L2 VXLAN",
            vni_type=VNITypeChoices.L2_VNI,
            namespace=self.namespace,
            status=self.status,
        )
        self.assertEqual(vxlan.vni_type, VNITypeChoices.L2_VNI)

    def test_vni_type_l3(self):
        """Test creating an L3 VNI for symmetric IRB."""
        vxlan = VXLAN.objects.create(
            vnid=2000,
            name="L3 VNI for OOB VRF",
            vni_type=VNITypeChoices.L3_VNI,
            namespace=self.namespace,
            status=self.status,
        )
        self.assertEqual(vxlan.vni_type, VNITypeChoices.L3_VNI)

    def test_vni_type_defaults_to_l2(self):
        """Test that vni_type defaults to L2 VNI."""
        vxlan = VXLAN.objects.create(
            vnid=3000,
            name="Default VNI Type",
            namespace=self.namespace,
            status=self.status,
        )
        self.assertEqual(vxlan.vni_type, VNITypeChoices.L2_VNI)


class InfiniBandPKeyModelTest(TestCase):
    """Test cases for InfiniBandPKey model."""

    @classmethod
    def setUpTestData(cls):
        """Set up test data."""
        cls.status = get_or_create_status_for_model(InfiniBandPKey)

    def test_create_pkey(self):
        """Test creating an InfiniBandPKey."""
        pkey = InfiniBandPKey.objects.create(
            pkey="0x8001",
            name="Test PKey",
            membership_type=PKeyMembershipTypeChoices.FULL,
            status=self.status,
        )
        self.assertEqual(str(pkey), "Test PKey (0x8001)")
        self.assertEqual(pkey.membership_type, PKeyMembershipTypeChoices.FULL)

    def test_pkey_format_validator_accepts_valid_values(self):
        """Test that valid PKey hex values pass validation."""
        for valid in ("0x8001", "0x0001", "0xFFFF", "0x1"):
            pkey = InfiniBandPKey(pkey=valid, name=f"PKey {valid}", status=self.status)
            pkey.full_clean()  # should not raise

    def test_pkey_format_validator_rejects_invalid_values(self):
        """Test that invalid PKey values fail validation."""
        for invalid in ("8001", "0x8001X", "0xGGGG", "0x1234567"):
            pkey = InfiniBandPKey(pkey=invalid, name=f"PKey {invalid}", status=self.status)
            with self.assertRaises(ValidationError, msg=f"Expected ValidationError for pkey={invalid!r}"):
                pkey.full_clean()


class InfiniBandMKeyModelTest(TestCase):
    """Test cases for InfiniBandMKey model."""

    @classmethod
    def setUpTestData(cls):
        """Set up test data."""
        cls.status = get_or_create_status_for_model(InfiniBandMKey)
        cls.overlay_status = get_or_create_status_for_model(Overlay)
        cls.tenant = Tenant.objects.create(name="MKey Test Tenant")
        cls.location_type = LocationType.objects.create(name="MKey Site Type")
        cls.location = Location.objects.create(
            name="MKey Test Site",
            location_type=cls.location_type,
            status=Status.objects.get_for_model(Location).first(),
        )
        cls.mkey_overlay = Overlay.objects.create(
            name="MKey Overlay",
            tenant=cls.tenant,
            location=cls.location,
            isolation_type=IsolationTypeChoices.IB_MKEY,
            status=cls.overlay_status,
        )
        cls.ib_pkey_overlay = Overlay.objects.create(
            name="PKey Overlay for MKey Test",
            tenant=cls.tenant,
            location=cls.location,
            isolation_type=IsolationTypeChoices.IB_PKEY,
            status=cls.overlay_status,
        )

    def test_create_mkey(self):
        """Test creating an InfiniBandMKey."""
        mkey = InfiniBandMKey.objects.create(
            name="Test MKey",
            mkey_value="0x0000000000a12c30",
            status=self.status,
        )
        self.assertEqual(str(mkey), "Test MKey (0x0000000000a12c30)")

    def test_mkey_value_validator_accepts_valid_values(self):
        """Test that valid MKey hex values pass validation."""
        for valid in ("0x1", "0xABCDEF0123456789", "0x0000000000a12c30"):
            mkey = InfiniBandMKey(name=f"MK {valid}", mkey_value=valid, status=self.status)
            mkey.full_clean()

    def test_mkey_value_validator_rejects_invalid_values(self):
        """Test that invalid MKey values fail validation."""
        for invalid in ("deadbeef", "0x", "0xGGGG", "0x0000000000a12c300000"):
            mkey = InfiniBandMKey(name=f"MK {invalid}", mkey_value=invalid, status=self.status)
            with self.assertRaises(ValidationError, msg=f"Expected ValidationError for mkey_value={invalid!r}"):
                mkey.full_clean()

    def test_protect_bits_range(self):
        """Test that protect_bits is validated to 0-3."""
        for valid in (0, 1, 2, 3):
            mkey = InfiniBandMKey(name=f"MK pb{valid}", mkey_value="0x1", protect_bits=valid, status=self.status)
            mkey.full_clean()

        for invalid in (-1, 4):
            mkey = InfiniBandMKey(name=f"MK pb{invalid}", mkey_value="0x1", protect_bits=invalid, status=self.status)
            with self.assertRaises(ValidationError):
                mkey.full_clean()

    def test_mkey_lease_period_max(self):
        """Test that mkey_lease_period is validated to <= 65535."""
        valid = InfiniBandMKey(name="MK lease ok", mkey_value="0x1", mkey_lease_period=65535, status=self.status)
        valid.full_clean()

        invalid = InfiniBandMKey(name="MK lease bad", mkey_value="0x1", mkey_lease_period=65536, status=self.status)
        with self.assertRaises(ValidationError):
            invalid.full_clean()

    def test_mkey_requires_ib_mkey_overlay(self):
        """Test that MKeys can only be associated with IB MKey overlays."""
        mkey_valid = InfiniBandMKey(
            name="Valid MKey",
            mkey_value="0x0000000000a12c30",
            overlay=self.mkey_overlay,
            status=self.status,
        )
        mkey_valid.full_clean()  # should not raise

        mkey_invalid = InfiniBandMKey(
            name="Invalid MKey",
            mkey_value="0x0000000000a12c31",
            overlay=self.ib_pkey_overlay,
            status=self.status,
        )
        with self.assertRaises(ValidationError) as ctx:
            mkey_invalid.full_clean()
        self.assertIn("IB MKey", str(ctx.exception))

    def test_mkey_without_overlay_valid(self):
        """Test that MKeys without an overlay are valid."""
        mkey = InfiniBandMKey(
            name="No Overlay MKey",
            mkey_value="0x1",
            overlay=None,
            status=self.status,
        )
        mkey.full_clean()  # should not raise

    def test_mkey_global_seed_validator(self):
        """Test that mkey_global_seed accepts valid hex or empty string."""
        valid_seeds = ("", "0x1", "0xABCDEF0123456789")
        for seed in valid_seeds:
            mkey = InfiniBandMKey(name=f"MK seed {seed!r}", mkey_value="0x1", mkey_global_seed=seed, status=self.status)
            mkey.full_clean()

        invalid_seed = "not_hex"
        mkey = InfiniBandMKey(name="MK bad seed", mkey_value="0x1", mkey_global_seed=invalid_seed, status=self.status)
        with self.assertRaises(ValidationError):
            mkey.full_clean()


class IsolationTypeConstraintsTest(TestCase):
    """Test cases for isolation type constraints."""

    @classmethod
    def setUpTestData(cls):
        """Set up test data for constraint tests."""
        cls.overlay_status = get_or_create_status_for_model(Overlay)
        cls.vxlan_status = get_or_create_status_for_model(VXLAN)
        cls.pkey_status = get_or_create_status_for_model(InfiniBandPKey)
        cls.tenant = Tenant.objects.create(name="Constraint Test Tenant")
        cls.location_type = LocationType.objects.create(name="Constraint Test Site Type")
        cls.location = Location.objects.create(
            name="Constraint Test Site",
            location_type=cls.location_type,
            status=Status.objects.get_for_model(Location).first(),
        )
        cls.namespace = Namespace.objects.first() or Namespace.objects.create(name="Test Namespace")

        cls.vxlan_overlay = Overlay.objects.create(
            name="VXLAN Overlay",
            tenant=cls.tenant,
            location=cls.location,
            isolation_type=IsolationTypeChoices.VXLAN_EVPN,
            status=cls.overlay_status,
        )
        cls.ib_overlay = Overlay.objects.create(
            name="IB Overlay",
            tenant=cls.tenant,
            location=cls.location,
            isolation_type=IsolationTypeChoices.IB_PKEY,
            status=cls.overlay_status,
        )
        cls.nmx_overlay = Overlay.objects.create(
            name="NMX Overlay",
            tenant=cls.tenant,
            location=cls.location,
            isolation_type=IsolationTypeChoices.NVLINK_PARTITION,
            status=cls.overlay_status,
        )
        cls.mkey_overlay = Overlay.objects.create(
            name="MKey Overlay",
            tenant=cls.tenant,
            location=cls.location,
            isolation_type=IsolationTypeChoices.IB_MKEY,
            status=cls.overlay_status,
        )
        cls.spectrum_x_overlay = Overlay.objects.create(
            name="Spectrum X Overlay",
            tenant=cls.tenant,
            location=cls.location,
            isolation_type=IsolationTypeChoices.SPECTRUM_X_VRF,
            status=cls.overlay_status,
        )

    def test_vxlan_accepts_vxlan_evpn_overlay(self):
        """Test that VXLANs can be associated with VXLAN/EVPN overlays."""
        vxlan = VXLAN(
            vnid=10001,
            name="Valid VXLAN",
            namespace=self.namespace,
            overlay=self.vxlan_overlay,
            status=self.vxlan_status,
        )
        vxlan.full_clean()  # Should not raise

    def test_vxlan_accepts_spectrum_x_overlay(self):
        """Test that VXLANs can be associated with Spectrum X overlays."""
        vxlan = VXLAN(
            vnid=10010,
            name="Spectrum X VXLAN",
            namespace=self.namespace,
            overlay=self.spectrum_x_overlay,
            status=self.vxlan_status,
        )
        vxlan.full_clean()  # Should not raise

    def test_vxlan_rejects_incompatible_overlay(self):
        """Test that VXLANs cannot be associated with non-VXLAN overlay types."""
        vxlan_invalid = VXLAN(
            vnid=10002,
            name="Invalid VXLAN",
            namespace=self.namespace,
            overlay=self.ib_overlay,
            status=self.vxlan_status,
        )
        with self.assertRaises(ValidationError) as context:
            vxlan_invalid.full_clean()
        self.assertIn("VXLAN", str(context.exception))

    def test_pkey_requires_ib_pkey_overlay(self):
        """Test that PKeys can only be associated with IB PKey overlays."""
        pkey = InfiniBandPKey(
            pkey="0x8001",
            name="Valid PKey",
            overlay=self.ib_overlay,
            status=self.pkey_status,
        )
        pkey.full_clean()  # Should not raise

        pkey_invalid = InfiniBandPKey(
            pkey="0x8002",
            name="Invalid PKey",
            overlay=self.vxlan_overlay,
            status=self.pkey_status,
        )
        with self.assertRaises(Exception) as context:
            pkey_invalid.full_clean()
        self.assertIn("IB PKey", str(context.exception))

    def test_vxlan_without_overlay_valid(self):
        """Test that VXLANs without an overlay are valid."""
        vxlan = VXLAN(
            vnid=10003,
            name="No Overlay VXLAN",
            namespace=self.namespace,
            overlay=None,
            status=self.vxlan_status,
        )
        vxlan.full_clean()  # Should not raise

    def test_pkey_without_overlay_valid(self):
        """Test that PKeys without an overlay are valid."""
        pkey = InfiniBandPKey(
            pkey="0x8003",
            name="No Overlay PKey",
            overlay=None,
            status=self.pkey_status,
        )
        pkey.full_clean()  # Should not raise

    def test_ib_mkey_choice_exists(self):
        """Test that IB_MKEY is a valid isolation type choice."""
        overlay = Overlay(
            name="MKey Choice Test",
            tenant=self.tenant,
            location=self.location,
            isolation_type=IsolationTypeChoices.IB_MKEY,
            status=self.overlay_status,
        )
        overlay.full_clean()  # Should not raise
