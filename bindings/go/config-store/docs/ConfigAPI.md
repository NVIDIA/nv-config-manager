# \ConfigAPI

All URIs are relative to *http://localhost*

Method | HTTP request | Description
------------- | ------------- | -------------
[**BatchCreateConfigsV1ConfigDeviceUuidBatchPost**](ConfigAPI.md#BatchCreateConfigsV1ConfigDeviceUuidBatchPost) | **Post** /v1/config/{device_uuid}/batch | Batch create/update config files
[**CreateConfigV1ConfigDeviceUuidFilenamePost**](ConfigAPI.md#CreateConfigV1ConfigDeviceUuidFilenamePost) | **Post** /v1/config/{device_uuid}/{filename} | Create or update a config file
[**GetConfigV1ConfigDeviceUuidFilenameGet**](ConfigAPI.md#GetConfigV1ConfigDeviceUuidFilenameGet) | **Get** /v1/config/{device_uuid}/{filename} | Get a config file
[**GetDeviceConfigsV1ConfigDeviceDeviceUuidGet**](ConfigAPI.md#GetDeviceConfigsV1ConfigDeviceDeviceUuidGet) | **Get** /v1/config/device/{device_uuid} | Get all configs for a device
[**GetDiffV1ConfigDeviceUuidFilenameDiffGet**](ConfigAPI.md#GetDiffV1ConfigDeviceUuidFilenameDiffGet) | **Get** /v1/config/{device_uuid}/{filename}/diff | Get diff between two versions
[**ListVersionsV1ConfigDeviceUuidFilenameVersionsGet**](ConfigAPI.md#ListVersionsV1ConfigDeviceUuidFilenameVersionsGet) | **Get** /v1/config/{device_uuid}/{filename}/versions | List all versions of a config file



## BatchCreateConfigsV1ConfigDeviceUuidBatchPost

> BatchConfigResponse BatchCreateConfigsV1ConfigDeviceUuidBatchPost(ctx, deviceUuid).BatchConfigRequest(batchConfigRequest).Execute()

Batch create/update config files



### Example

```go
package main

import (
	"context"
	"fmt"
	"os"
	openapiclient "github.com/nvidia/nv-config-manager/bindings/go/config-store"
)

func main() {
	deviceUuid := "38400000-8cf0-11bd-b23e-10b96e4ef00d" // string | 
	batchConfigRequest := *openapiclient.NewBatchConfigRequest([]openapiclient.BatchConfigItem{*openapiclient.NewBatchConfigItem("Author_example", "CommitMessage_example", "Content_example", "Filename_example")}) // BatchConfigRequest | 

	configuration := openapiclient.NewConfiguration()
	apiClient := openapiclient.NewAPIClient(configuration)
	resp, r, err := apiClient.ConfigAPI.BatchCreateConfigsV1ConfigDeviceUuidBatchPost(context.Background(), deviceUuid).BatchConfigRequest(batchConfigRequest).Execute()
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error when calling `ConfigAPI.BatchCreateConfigsV1ConfigDeviceUuidBatchPost``: %v\n", err)
		fmt.Fprintf(os.Stderr, "Full HTTP response: %v\n", r)
	}
	// response from `BatchCreateConfigsV1ConfigDeviceUuidBatchPost`: BatchConfigResponse
	fmt.Fprintf(os.Stdout, "Response from `ConfigAPI.BatchCreateConfigsV1ConfigDeviceUuidBatchPost`: %v\n", resp)
}
```

### Path Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
**ctx** | **context.Context** | context for authentication, logging, cancellation, deadlines, tracing, etc.
**deviceUuid** | **string** |  | 

### Other Parameters

Other parameters are passed through a pointer to a apiBatchCreateConfigsV1ConfigDeviceUuidBatchPostRequest struct via the builder pattern


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------

 **batchConfigRequest** | [**BatchConfigRequest**](BatchConfigRequest.md) |  | 

### Return type

[**BatchConfigResponse**](BatchConfigResponse.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: application/json
- **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints)
[[Back to Model list]](../README.md#documentation-for-models)
[[Back to README]](../README.md)


## CreateConfigV1ConfigDeviceUuidFilenamePost

> ConfigResponse CreateConfigV1ConfigDeviceUuidFilenamePost(ctx, deviceUuid, filename).ConfigCreateRequest(configCreateRequest).Execute()

Create or update a config file



### Example

```go
package main

import (
	"context"
	"fmt"
	"os"
	openapiclient "github.com/nvidia/nv-config-manager/bindings/go/config-store"
)

func main() {
	deviceUuid := "38400000-8cf0-11bd-b23e-10b96e4ef00d" // string | 
	filename := "filename_example" // string | 
	configCreateRequest := *openapiclient.NewConfigCreateRequest("Author_example", "CommitMessage_example", "Content_example") // ConfigCreateRequest | 

	configuration := openapiclient.NewConfiguration()
	apiClient := openapiclient.NewAPIClient(configuration)
	resp, r, err := apiClient.ConfigAPI.CreateConfigV1ConfigDeviceUuidFilenamePost(context.Background(), deviceUuid, filename).ConfigCreateRequest(configCreateRequest).Execute()
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error when calling `ConfigAPI.CreateConfigV1ConfigDeviceUuidFilenamePost``: %v\n", err)
		fmt.Fprintf(os.Stderr, "Full HTTP response: %v\n", r)
	}
	// response from `CreateConfigV1ConfigDeviceUuidFilenamePost`: ConfigResponse
	fmt.Fprintf(os.Stdout, "Response from `ConfigAPI.CreateConfigV1ConfigDeviceUuidFilenamePost`: %v\n", resp)
}
```

### Path Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
**ctx** | **context.Context** | context for authentication, logging, cancellation, deadlines, tracing, etc.
**deviceUuid** | **string** |  | 
**filename** | **string** |  | 

### Other Parameters

Other parameters are passed through a pointer to a apiCreateConfigV1ConfigDeviceUuidFilenamePostRequest struct via the builder pattern


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------


 **configCreateRequest** | [**ConfigCreateRequest**](ConfigCreateRequest.md) |  | 

### Return type

[**ConfigResponse**](ConfigResponse.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: application/json
- **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints)
[[Back to Model list]](../README.md#documentation-for-models)
[[Back to README]](../README.md)


## GetConfigV1ConfigDeviceUuidFilenameGet

> ConfigResponse GetConfigV1ConfigDeviceUuidFilenameGet(ctx, deviceUuid, filename).FileType(fileType).Version(version).Execute()

Get a config file



### Example

```go
package main

import (
	"context"
	"fmt"
	"os"
	openapiclient "github.com/nvidia/nv-config-manager/bindings/go/config-store"
)

func main() {
	deviceUuid := "38400000-8cf0-11bd-b23e-10b96e4ef00d" // string | 
	filename := "filename_example" // string | 
	fileType := openapiclient.FileType("intended") // FileType |  (optional) (default to "intended")
	version := int32(56) // int32 |  (optional)

	configuration := openapiclient.NewConfiguration()
	apiClient := openapiclient.NewAPIClient(configuration)
	resp, r, err := apiClient.ConfigAPI.GetConfigV1ConfigDeviceUuidFilenameGet(context.Background(), deviceUuid, filename).FileType(fileType).Version(version).Execute()
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error when calling `ConfigAPI.GetConfigV1ConfigDeviceUuidFilenameGet``: %v\n", err)
		fmt.Fprintf(os.Stderr, "Full HTTP response: %v\n", r)
	}
	// response from `GetConfigV1ConfigDeviceUuidFilenameGet`: ConfigResponse
	fmt.Fprintf(os.Stdout, "Response from `ConfigAPI.GetConfigV1ConfigDeviceUuidFilenameGet`: %v\n", resp)
}
```

### Path Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
**ctx** | **context.Context** | context for authentication, logging, cancellation, deadlines, tracing, etc.
**deviceUuid** | **string** |  | 
**filename** | **string** |  | 

### Other Parameters

Other parameters are passed through a pointer to a apiGetConfigV1ConfigDeviceUuidFilenameGetRequest struct via the builder pattern


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------


 **fileType** | [**FileType**](FileType.md) |  | [default to &quot;intended&quot;]
 **version** | **int32** |  | 

### Return type

[**ConfigResponse**](ConfigResponse.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints)
[[Back to Model list]](../README.md#documentation-for-models)
[[Back to README]](../README.md)


## GetDeviceConfigsV1ConfigDeviceDeviceUuidGet

> []ConfigResponse GetDeviceConfigsV1ConfigDeviceDeviceUuidGet(ctx, deviceUuid).FileType(fileType).Execute()

Get all configs for a device



### Example

```go
package main

import (
	"context"
	"fmt"
	"os"
	openapiclient "github.com/nvidia/nv-config-manager/bindings/go/config-store"
)

func main() {
	deviceUuid := "38400000-8cf0-11bd-b23e-10b96e4ef00d" // string | 
	fileType := openapiclient.FileType("intended") // FileType |  (optional)

	configuration := openapiclient.NewConfiguration()
	apiClient := openapiclient.NewAPIClient(configuration)
	resp, r, err := apiClient.ConfigAPI.GetDeviceConfigsV1ConfigDeviceDeviceUuidGet(context.Background(), deviceUuid).FileType(fileType).Execute()
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error when calling `ConfigAPI.GetDeviceConfigsV1ConfigDeviceDeviceUuidGet``: %v\n", err)
		fmt.Fprintf(os.Stderr, "Full HTTP response: %v\n", r)
	}
	// response from `GetDeviceConfigsV1ConfigDeviceDeviceUuidGet`: []ConfigResponse
	fmt.Fprintf(os.Stdout, "Response from `ConfigAPI.GetDeviceConfigsV1ConfigDeviceDeviceUuidGet`: %v\n", resp)
}
```

### Path Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
**ctx** | **context.Context** | context for authentication, logging, cancellation, deadlines, tracing, etc.
**deviceUuid** | **string** |  | 

### Other Parameters

Other parameters are passed through a pointer to a apiGetDeviceConfigsV1ConfigDeviceDeviceUuidGetRequest struct via the builder pattern


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------

 **fileType** | [**FileType**](FileType.md) |  | 

### Return type

[**[]ConfigResponse**](ConfigResponse.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints)
[[Back to Model list]](../README.md#documentation-for-models)
[[Back to README]](../README.md)


## GetDiffV1ConfigDeviceUuidFilenameDiffGet

> DiffResponse GetDiffV1ConfigDeviceUuidFilenameDiffGet(ctx, deviceUuid, filename).FromVersion(fromVersion).ToVersion(toVersion).FileType(fileType).Execute()

Get diff between two versions



### Example

```go
package main

import (
	"context"
	"fmt"
	"os"
	openapiclient "github.com/nvidia/nv-config-manager/bindings/go/config-store"
)

func main() {
	deviceUuid := "38400000-8cf0-11bd-b23e-10b96e4ef00d" // string | 
	filename := "filename_example" // string | 
	fromVersion := int32(56) // int32 | 
	toVersion := int32(56) // int32 | 
	fileType := openapiclient.FileType("intended") // FileType |  (optional) (default to "intended")

	configuration := openapiclient.NewConfiguration()
	apiClient := openapiclient.NewAPIClient(configuration)
	resp, r, err := apiClient.ConfigAPI.GetDiffV1ConfigDeviceUuidFilenameDiffGet(context.Background(), deviceUuid, filename).FromVersion(fromVersion).ToVersion(toVersion).FileType(fileType).Execute()
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error when calling `ConfigAPI.GetDiffV1ConfigDeviceUuidFilenameDiffGet``: %v\n", err)
		fmt.Fprintf(os.Stderr, "Full HTTP response: %v\n", r)
	}
	// response from `GetDiffV1ConfigDeviceUuidFilenameDiffGet`: DiffResponse
	fmt.Fprintf(os.Stdout, "Response from `ConfigAPI.GetDiffV1ConfigDeviceUuidFilenameDiffGet`: %v\n", resp)
}
```

### Path Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
**ctx** | **context.Context** | context for authentication, logging, cancellation, deadlines, tracing, etc.
**deviceUuid** | **string** |  | 
**filename** | **string** |  | 

### Other Parameters

Other parameters are passed through a pointer to a apiGetDiffV1ConfigDeviceUuidFilenameDiffGetRequest struct via the builder pattern


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------


 **fromVersion** | **int32** |  | 
 **toVersion** | **int32** |  | 
 **fileType** | [**FileType**](FileType.md) |  | [default to &quot;intended&quot;]

### Return type

[**DiffResponse**](DiffResponse.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints)
[[Back to Model list]](../README.md#documentation-for-models)
[[Back to README]](../README.md)


## ListVersionsV1ConfigDeviceUuidFilenameVersionsGet

> ConfigVersionsResponse ListVersionsV1ConfigDeviceUuidFilenameVersionsGet(ctx, deviceUuid, filename).FileType(fileType).Limit(limit).Execute()

List all versions of a config file



### Example

```go
package main

import (
	"context"
	"fmt"
	"os"
	openapiclient "github.com/nvidia/nv-config-manager/bindings/go/config-store"
)

func main() {
	deviceUuid := "38400000-8cf0-11bd-b23e-10b96e4ef00d" // string | 
	filename := "filename_example" // string | 
	fileType := openapiclient.FileType("intended") // FileType |  (optional) (default to "intended")
	limit := int32(56) // int32 |  (optional) (default to 100)

	configuration := openapiclient.NewConfiguration()
	apiClient := openapiclient.NewAPIClient(configuration)
	resp, r, err := apiClient.ConfigAPI.ListVersionsV1ConfigDeviceUuidFilenameVersionsGet(context.Background(), deviceUuid, filename).FileType(fileType).Limit(limit).Execute()
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error when calling `ConfigAPI.ListVersionsV1ConfigDeviceUuidFilenameVersionsGet``: %v\n", err)
		fmt.Fprintf(os.Stderr, "Full HTTP response: %v\n", r)
	}
	// response from `ListVersionsV1ConfigDeviceUuidFilenameVersionsGet`: ConfigVersionsResponse
	fmt.Fprintf(os.Stdout, "Response from `ConfigAPI.ListVersionsV1ConfigDeviceUuidFilenameVersionsGet`: %v\n", resp)
}
```

### Path Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
**ctx** | **context.Context** | context for authentication, logging, cancellation, deadlines, tracing, etc.
**deviceUuid** | **string** |  | 
**filename** | **string** |  | 

### Other Parameters

Other parameters are passed through a pointer to a apiListVersionsV1ConfigDeviceUuidFilenameVersionsGetRequest struct via the builder pattern


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------


 **fileType** | [**FileType**](FileType.md) |  | [default to &quot;intended&quot;]
 **limit** | **int32** |  | [default to 100]

### Return type

[**ConfigVersionsResponse**](ConfigVersionsResponse.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints)
[[Back to Model list]](../README.md#documentation-for-models)
[[Back to README]](../README.md)

