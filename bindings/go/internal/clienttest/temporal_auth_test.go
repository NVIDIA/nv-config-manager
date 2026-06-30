// SPDX-FileCopyrightText: Copyright (c) 2024-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: Apache-2.0
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
// http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

package clienttest

import (
	"context"
	"io"
	"net/http"
	"strings"
	"testing"

	temporal "github.com/nvidia/nv-config-manager/bindings/go/temporal"
)

type roundTripFunc func(*http.Request) (*http.Response, error)

func (fn roundTripFunc) RoundTrip(request *http.Request) (*http.Response, error) {
	return fn(request)
}

func TestTemporalClientAppliesBearerToken(t *testing.T) {
	t.Parallel()

	var authorizationHeader string
	configuration := temporal.NewConfiguration()
	configuration.Servers[0].URL = "https://example.test"
	configuration.HTTPClient = &http.Client{
		Transport: roundTripFunc(func(request *http.Request) (*http.Response, error) {
			authorizationHeader = request.Header.Get("Authorization")
			return &http.Response{
				StatusCode: http.StatusOK,
				Header:     make(http.Header),
				Body:       io.NopCloser(strings.NewReader("{}")),
			}, nil
		}),
	}
	client := temporal.NewAPIClient(configuration)
	ctx := context.WithValue(context.Background(), temporal.ContextAccessToken, "test-token")

	_, _, _ = client.WorkflowAPI.GetWorkflowsV1WorkflowGet(ctx).Execute()

	if authorizationHeader != "Bearer test-token" {
		t.Errorf("authorization header = %q, want %q", authorizationHeader, "Bearer test-token")
	}
}
