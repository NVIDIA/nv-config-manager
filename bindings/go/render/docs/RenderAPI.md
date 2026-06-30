# \RenderAPI

All URIs are relative to *http://localhost*

Method | HTTP request | Description
------------- | ------------- | -------------
[**RenderAllV1RenderAllPost**](RenderAPI.md#RenderAllV1RenderAllPost) | **Post** /v1/render/all | Render All
[**RenderBatchV1RenderBatchPost**](RenderAPI.md#RenderBatchV1RenderBatchPost) | **Post** /v1/render/batch | Render Batch
[**RenderV1RenderDeviceUuidRenderPost**](RenderAPI.md#RenderV1RenderDeviceUuidRenderPost) | **Post** /v1/render/{device_uuid}/render | Render



## RenderAllV1RenderAllPost

> BulkRenderResponse RenderAllV1RenderAllPost(ctx).RenderRequest(renderRequest).Execute()

Render All



### Example

```go
package main

import (
	"context"
	"fmt"
	"os"
	openapiclient "github.com/nvidia/nv-config-manager/bindings/go/render"
)

func main() {
	renderRequest := *openapiclient.NewRenderRequest() // RenderRequest |  (optional)

	configuration := openapiclient.NewConfiguration()
	apiClient := openapiclient.NewAPIClient(configuration)
	resp, r, err := apiClient.RenderAPI.RenderAllV1RenderAllPost(context.Background()).RenderRequest(renderRequest).Execute()
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error when calling `RenderAPI.RenderAllV1RenderAllPost``: %v\n", err)
		fmt.Fprintf(os.Stderr, "Full HTTP response: %v\n", r)
	}
	// response from `RenderAllV1RenderAllPost`: BulkRenderResponse
	fmt.Fprintf(os.Stdout, "Response from `RenderAPI.RenderAllV1RenderAllPost`: %v\n", resp)
}
```

### Path Parameters



### Other Parameters

Other parameters are passed through a pointer to a apiRenderAllV1RenderAllPostRequest struct via the builder pattern


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **renderRequest** | [**RenderRequest**](RenderRequest.md) |  | 

### Return type

[**BulkRenderResponse**](BulkRenderResponse.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: application/json
- **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints)
[[Back to Model list]](../README.md#documentation-for-models)
[[Back to README]](../README.md)


## RenderBatchV1RenderBatchPost

> BulkRenderResponse RenderBatchV1RenderBatchPost(ctx).BatchRenderRequest(batchRenderRequest).Execute()

Render Batch



### Example

```go
package main

import (
	"context"
	"fmt"
	"os"
	openapiclient "github.com/nvidia/nv-config-manager/bindings/go/render"
)

func main() {
	batchRenderRequest := *openapiclient.NewBatchRenderRequest([]string{"DeviceUuids_example"}) // BatchRenderRequest | 

	configuration := openapiclient.NewConfiguration()
	apiClient := openapiclient.NewAPIClient(configuration)
	resp, r, err := apiClient.RenderAPI.RenderBatchV1RenderBatchPost(context.Background()).BatchRenderRequest(batchRenderRequest).Execute()
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error when calling `RenderAPI.RenderBatchV1RenderBatchPost``: %v\n", err)
		fmt.Fprintf(os.Stderr, "Full HTTP response: %v\n", r)
	}
	// response from `RenderBatchV1RenderBatchPost`: BulkRenderResponse
	fmt.Fprintf(os.Stdout, "Response from `RenderAPI.RenderBatchV1RenderBatchPost`: %v\n", resp)
}
```

### Path Parameters



### Other Parameters

Other parameters are passed through a pointer to a apiRenderBatchV1RenderBatchPostRequest struct via the builder pattern


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **batchRenderRequest** | [**BatchRenderRequest**](BatchRenderRequest.md) |  | 

### Return type

[**BulkRenderResponse**](BulkRenderResponse.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: application/json
- **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints)
[[Back to Model list]](../README.md#documentation-for-models)
[[Back to README]](../README.md)


## RenderV1RenderDeviceUuidRenderPost

> RenderResponse RenderV1RenderDeviceUuidRenderPost(ctx, deviceUuid).RenderRequest(renderRequest).Execute()

Render



### Example

```go
package main

import (
	"context"
	"fmt"
	"os"
	openapiclient "github.com/nvidia/nv-config-manager/bindings/go/render"
)

func main() {
	deviceUuid := "deviceUuid_example" // string | 
	renderRequest := *openapiclient.NewRenderRequest() // RenderRequest |  (optional)

	configuration := openapiclient.NewConfiguration()
	apiClient := openapiclient.NewAPIClient(configuration)
	resp, r, err := apiClient.RenderAPI.RenderV1RenderDeviceUuidRenderPost(context.Background(), deviceUuid).RenderRequest(renderRequest).Execute()
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error when calling `RenderAPI.RenderV1RenderDeviceUuidRenderPost``: %v\n", err)
		fmt.Fprintf(os.Stderr, "Full HTTP response: %v\n", r)
	}
	// response from `RenderV1RenderDeviceUuidRenderPost`: RenderResponse
	fmt.Fprintf(os.Stdout, "Response from `RenderAPI.RenderV1RenderDeviceUuidRenderPost`: %v\n", resp)
}
```

### Path Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
**ctx** | **context.Context** | context for authentication, logging, cancellation, deadlines, tracing, etc.
**deviceUuid** | **string** |  | 

### Other Parameters

Other parameters are passed through a pointer to a apiRenderV1RenderDeviceUuidRenderPostRequest struct via the builder pattern


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------

 **renderRequest** | [**RenderRequest**](RenderRequest.md) |  | 

### Return type

[**RenderResponse**](RenderResponse.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: application/json
- **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints)
[[Back to Model list]](../README.md#documentation-for-models)
[[Back to README]](../README.md)

