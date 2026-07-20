/*
 * SPDX-FileCopyrightText: Copyright (c) 2024-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
 * SPDX-License-Identifier: Apache-2.0
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 * http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
import { FORBIDDEN_SITE_ID } from "./formData";

// Create unique forbidden device IDs for each platform
export const FORBIDDEN_DEVICE_IDS = {
  UFM: "FORBIDDEN-DEVICE-UFM",
  CUMULUS: "FORBIDDEN-DEVICE-CUMULUS",
  ARISTA: "FORBIDDEN-DEVICE-ARISTA",
  MLNX: "FORBIDDEN-DEVICE-MLNX",
};

export const DEVICES_LIST = {
  PDX01: [
    {
      id: "e9243d67-dad0-4f4b-9f6d-9cc977ff0023",
      name: "LEAF1-GP1-CIN1",
      tenant: "TenantB",
      status: "Active",
      platform: "Arista EOS",
    },
    {
      id: "0158d65b-4124-4987-93d5-10a0aff77d61",
      name: "LEAF1-GP1-CIN2",
      tenant: "TenantB",
      status: "Active",
      platform: "Arista EOS",
    },
    {
      id: "cb60e17a-b426-471f-a5c5-255f45368e7c",
      name: "LEAF1-GP1-CIN3",
      tenant: "TenantA",
      status: "Provisioned",
      platform: "Cumulus Linux",
    },
    {
      id: "510de8e8-9589-4517-b67c-70b9affa9b28",
      name: "LEAF2-GP1-CIN1",
      tenant: "TenantB",
      status: "Active",
      platform: "Arista EOS",
    },
    {
      id: "7ff67cec-4009-44d8-8f28-25e8a26764ec",
      name: "LEAF2-GP1-CIN2",
      tenant: "TenantA",
      status: "Provisioned",
      platform: "Cumulus Linux",
    },
    {
      id: "76984a54-3188-418b-8e03-0489355e19fc",
      name: "LEAF2-GP1-CIN3",
      tenant: "TenantB",
      status: "Active",
      platform: "Arista EOS",
    },
    {
      id: "f8788f54-d511-48f1-8f5e-c102de59f15f",
      name: "SPINE1-GP1-CIN1",
      tenant: "TenantB",
      status: "Active",
      platform: "Arista EOS",
    },
    {
      id: "32fdefda-df59-4285-9d6e-a1f220906a8d",
      name: "SPINE1-GP1-CIN2",
      tenant: "TenantA",
      status: "Provisioned",
      platform: "UFM",
      role: "UFM",
    },
    {
      id: "e768a90c-f868-4d92-9b4f-cefa57b15e91",
      name: "SPINE1-GP1-CIN3",
      tenant: "TenantB",
      status: "Active",
      platform: "Arista EOS",
    },
    {
      id: "6e2f4696-79ad-48c2-903c-0bdc51111d81",
      name: "core1-cg1-cp1-tan1",
      tenant: "TenantA",
      status: "Active",
      platform: "Cumulus Linux",
    },
    {
      id: "2ec651a7-2a1c-4a27-bac7-b0a06f8ef49c",
      name: "core1-cg2-cp1-tan1",
      tenant: "TenantB",
      status: "Provisioned",
      platform: "UFM",
      role: "UFM",
    },
    {
      id: "e4d8a939-7c4c-51a8-b080-eaeea62257c1",
      name: "leaf1-gp3-tan1",
      tenant: "TenantB",
      status: "Active",
      platform: "Arista EOS",
    },
    {
      id: "17b7ac16-bfd6-5c21-824e-5d0e712ecc43",
      name: "leaf2-gp3-tan1",
      tenant: "TenantA",
      status: "Provisioned",
      platform: "Cumulus Linux",
    },
    {
      id: "fa011c98-5c39-5d7d-a50e-fe6601f231d4",
      name: "leaf3-hss1-cp1-tan1",
      tenant: "TenantB",
      status: "Active",
      platform: "Arista EOS",
    },
    {
      id: "b2c0e516-f830-53ae-9a5a-f70b38333834",
      name: "leaf4-hss1-cp1-tan1",
      tenant: "TenantA",
      status: "Provisioned",
      platform: "UFM",
      role: "UFM",
    },
    {
      id: "fae22069-6833-4cf7-b5f7-92167e6abbb8",
      name: "leaf5-cno1-cp1-tan1",
      tenant: "TenantB",
      status: "Active",
      platform: "Arista EOS",
    },
    {
      id: "9d5b1b2f-7a06-4696-8aa5-7c85f56e0239",
      name: "leaf6-cno1-cp1-tan1",
      tenant: "TenantA",
      status: "Provisioned",
      platform: "Cumulus Linux",
    },
    {
      id: "ecb8db8a-7fe9-4654-83d9-d099d8a46c59",
      name: "spine1-cno1-cp1-tan1",
      tenant: "TenantB",
      status: "Active",
      platform: "Arista EOS",
    },
    {
      id: "26b4256a-4d96-5f76-8664-0072a1b30b6a",
      name: "spine1-gp3-tan1",
      tenant: "TenantA",
      status: "Provisioned",
      platform: "UFM",
      role: "UFM",
    },
    {
      id: "6a2b6815-3042-4c90-a7b8-0b61d9c2d601",
      name: "spine1-hss1-cp1-tan1",
      tenant: "TenantB",
      status: "Active",
      platform: "Arista EOS",
    },
    {
      id: "402eebf2-66b0-4873-9f34-16bcc5d3c01f",
      name: "spine2-cno1-cp1-tan1",
      tenant: "TenantA",
      status: "Provisioned",
      platform: "Cumulus Linux",
    },
    {
      id: "56f9b012-22b0-5c6b-ade8-ad3af277a4cb",
      name: "spine2-gp3-tan1",
      tenant: "TenantB",
      status: "Active",
      platform: "Arista EOS",
    },
    {
      id: "1052dba6-47f8-48ef-b879-f47ea2efc31d",
      name: "spine2-hss1-cp1-tan1",
      tenant: "TenantA",
      status: "Provisioned",
      platform: "UFM",
      role: "UFM",
    },
    {
      id: "67a4c2d6-0b61-4c90-a7b8-3042d9c26815",
      name: "infiniband-switch1",
      tenant: "TenantB",
      status: "Active",
      platform: "MLNX-OS",
    },
    {
      id: "9d5b1b2f-7c85-4696-8aa5-f56e02397a06",
      name: "infiniband-switch2",
      tenant: "TenantB",
      status: "Active",
      platform: "MLNX-OS",
    },
    {
      id: "ecb8db8a-d099-4654-83d9-d8a46c597fe9",
      name: "infiniband-switch3",
      tenant: "TenantA",
      status: "Provisioned",
      platform: "MLNX-OS",
    },
  ],
  RNO1: [
    {
      id: "ca22595f-7044-46d1-b760-63cac2f947b3",
      name: "m04-c10-core1-cg1-tan-lab1",
      tenant: "TenantB",
      status: "Active",
      platform: "Arista EOS",
    },
    {
      id: "0158d65b-4124-4987-93d5-10a0aff77d61",
      name: "m04-c10-core1-cg3-tan-lab1",
      tenant: "TenantB",
      status: "Active",
      platform: "Cumulus Linux",
    },
    {
      id: "0158d65b-4124-4987-93d5-10a0aff77d61",
      name: "m04-c10-core1-cg2-tan-lab1",
      tenant: "TenantB",
      status: "Active",
      platform: "UFM",
      role: "UFM",
    },
    {
      id: "ca22595f-63ca-46d1-b760-c2f947b37044",
      name: "infiniband-switch1",
      tenant: "TenantB",
      status: "Active",
      platform: "MLNX-OS",
    },
    {
      id: "0158d65b-10a0-4987-93d5-aff77d614124",
      name: "infiniband-switch2",
      tenant: "TenantA",
      status: "Provisioned",
      platform: "MLNX-OS",
    },
  ],
  [FORBIDDEN_SITE_ID]: [
    {
      id: FORBIDDEN_DEVICE_IDS.UFM,
      name: "FORBIDDEN-UFM-DEVICE",
      tenant: "TenantA",
      status: "Provisioned",
      platform: "UFM",
      role: "UFM",
    },
    {
      id: FORBIDDEN_DEVICE_IDS.CUMULUS,
      name: "FORBIDDEN-CUMULUS-DEVICE",
      tenant: "TenantA",
      status: "Provisioned",
      platform: "Cumulus Linux",
    },
    {
      id: FORBIDDEN_DEVICE_IDS.ARISTA,
      name: "FORBIDDEN-ARISTA-DEVICE",
      tenant: "TenantA",
      status: "Provisioned",
      platform: "Arista EOS",
    },
    {
      id: FORBIDDEN_DEVICE_IDS.MLNX,
      name: "FORBIDDEN-MLNX-DEVICE",
      tenant: "TenantA",
      status: "Provisioned",
      platform: "MLNX-OS",
    },
  ],
};
