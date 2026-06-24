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
import useDevices from "./useDevices";

interface UseUfmDevicesProps {
  site: string;
}

// UFM appliances are unmanaged and carry a non-switch platform, so they come
// from the dedicated /v1/parameter/ufm-device endpoint rather than the generic
// device query used for switches.
const useUfmDevices = ({ site }: UseUfmDevicesProps) =>
  useDevices({
    site,
    filterParams: site ? [["site", site]] : [],
    path: "/v1/parameter/ufm-device",
  });

export default useUfmDevices;
