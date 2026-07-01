// SPDX-FileCopyrightText: Copyright (c) 2024-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: Apache-2.0

package clienttest

import (
	"context"
	"encoding/json"
	"io"
	"mime"
	"mime/multipart"
	"net/http"
	"strings"
	"testing"

	"github.com/nvidia/nv-config-manager/bindings/go/config-store"
	"github.com/nvidia/nv-config-manager/bindings/go/dhcp"
	"github.com/nvidia/nv-config-manager/bindings/go/render"
	"github.com/nvidia/nv-config-manager/bindings/go/ztp"
)

func TestGeneratedModelsRejectNullForRequiredFields(t *testing.T) {
	testCases := []struct {
		name    string
		payload string
		target  interface{}
	}{
		{name: "device UUID", payload: `{"uuid":null}`, target: &configstore.DeviceUUID{}},
		{name: "identity", payload: `{"roles":[],"user":null}`, target: &dhcp.WhoamiResponse{}},
		{name: "consumer list", payload: `{"consumers":null}`, target: &render.ConsumerListResponse{}},
	}

	for _, testCase := range testCases {
		t.Run(testCase.name, func(t *testing.T) {
			if err := json.Unmarshal([]byte(testCase.payload), testCase.target); err == nil {
				t.Fatal("json.Unmarshal() accepted null for a required non-nullable field")
			}
		})
	}
}

func TestGeneratedMultipartLengthIncludesClosingBoundary(t *testing.T) {
	configuration := ztp.NewConfiguration()
	configuration.Servers[0].URL = "https://example.test"
	configuration.HTTPClient = &http.Client{
		Transport: roundTripFunc(func(request *http.Request) (*http.Response, error) {
			body, err := io.ReadAll(request.Body)
			if err != nil {
				t.Fatalf("read multipart body: %v", err)
			}
			if request.ContentLength != int64(len(body)) {
				t.Errorf("Content-Length = %d, body length = %d", request.ContentLength, len(body))
			}

			_, parameters, err := mime.ParseMediaType(request.Header.Get("Content-Type"))
			if err != nil {
				t.Fatalf("parse Content-Type: %v", err)
			}
			form, err := multipart.NewReader(strings.NewReader(string(body)), parameters["boundary"]).ReadForm(1024)
			if err != nil {
				t.Fatalf("parse finalized multipart body: %v", err)
			}
			if got := form.Value["file"]; len(got) != 1 || got[0] != "contents" {
				t.Errorf("multipart file field = %q, want %q", got, []string{"contents"})
			}

			return &http.Response{
				StatusCode: http.StatusOK,
				Status:     "200 OK",
				Header:     http.Header{"Content-Type": []string{"application/json"}},
				Body:       io.NopCloser(strings.NewReader(`"ok"`)),
			}, nil
		}),
	}

	client := ztp.NewAPIClient(configuration)
	_, _, err := client.FilesAPI.UploadFileV1FilesPlatformVersionFilenamePost(
		context.Background(), "platform", "version", "filename",
	).Checksum("checksum").File("contents").Execute()
	if err != nil {
		t.Fatalf("Execute() error = %v", err)
	}
}

func TestGeneratedUnionRejectsNullAndEmptyValue(t *testing.T) {
	var location configstore.LocationInner
	if err := json.Unmarshal([]byte("null"), &location); err == nil {
		t.Fatal("json.Unmarshal() accepted null for a non-nullable union")
	}
	if _, err := json.Marshal(configstore.LocationInner{}); err == nil {
		t.Fatal("json.Marshal() accepted an empty non-nullable union")
	}
}
