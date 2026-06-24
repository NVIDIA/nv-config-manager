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
import { test, expect } from "@playwright/test";
import {
  shouldEnableMocks,
  MockGateInputs,
} from "../../src/mocks/shouldEnableMocks";

const baseInputs: MockGateInputs = {
  hasWindow: true,
  bypassWindowFlag: false,
  bypassEnvFlag: undefined,
  nodeEnv: "development",
};

test.describe("shouldEnableMocks", () => {
  test("enables mocks during next dev with no overrides", () => {
    expect(shouldEnableMocks(baseInputs)).toBe(true);
  });

  test("skips mocks during server-side rendering (no window)", () => {
    expect(shouldEnableMocks({ ...baseInputs, hasWindow: false })).toBe(false);
  });

  test("skips mocks outside development", () => {
    expect(shouldEnableMocks({ ...baseInputs, nodeEnv: "production" })).toBe(
      false
    );
    expect(shouldEnableMocks({ ...baseInputs, nodeEnv: "test" })).toBe(false);
    expect(shouldEnableMocks({ ...baseInputs, nodeEnv: undefined })).toBe(
      false
    );
  });

  test("skips mocks when window.BYPASS_MSW is set", () => {
    expect(
      shouldEnableMocks({ ...baseInputs, bypassWindowFlag: true })
    ).toBe(false);
  });

  test("skips mocks when NEXT_PUBLIC_BYPASS_MSW is truthy", () => {
    for (const value of ["true", "1", "yes", "on", "TRUE", " true "]) {
      expect(
        shouldEnableMocks({ ...baseInputs, bypassEnvFlag: value })
      ).toBe(false);
    }
  });

  test("keeps mocks enabled when NEXT_PUBLIC_BYPASS_MSW is falsy or absent", () => {
    for (const value of ["", "false", "0", "no", "off", undefined]) {
      expect(
        shouldEnableMocks({ ...baseInputs, bypassEnvFlag: value })
      ).toBe(true);
    }
  });
});
