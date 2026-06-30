# \AdminAPI

All URIs are relative to *http://localhost*

Method | HTTP request | Description
------------- | ------------- | -------------
[**GetConsumerInfoV1AdminConsumersConsumerTypeGet**](AdminAPI.md#GetConsumerInfoV1AdminConsumersConsumerTypeGet) | **Get** /v1/admin/consumers/{consumer_type} | Get Consumer Info
[**ListConsumersV1AdminConsumersGet**](AdminAPI.md#ListConsumersV1AdminConsumersGet) | **Get** /v1/admin/consumers | List Consumers
[**ResetAllConsumersV1AdminConsumersResetAllDelete**](AdminAPI.md#ResetAllConsumersV1AdminConsumersResetAllDelete) | **Delete** /v1/admin/consumers/reset-all | Reset All Consumers
[**ResetConsumerV1AdminConsumersConsumerTypeResetDelete**](AdminAPI.md#ResetConsumerV1AdminConsumersConsumerTypeResetDelete) | **Delete** /v1/admin/consumers/{consumer_type}/reset | Reset Consumer



## GetConsumerInfoV1AdminConsumersConsumerTypeGet

> ConsumerInfo GetConsumerInfoV1AdminConsumersConsumerTypeGet(ctx, consumerType).Execute()

Get Consumer Info



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
	consumerType := openapiclient.ConsumerType("nautobot") // ConsumerType | 

	configuration := openapiclient.NewConfiguration()
	apiClient := openapiclient.NewAPIClient(configuration)
	resp, r, err := apiClient.AdminAPI.GetConsumerInfoV1AdminConsumersConsumerTypeGet(context.Background(), consumerType).Execute()
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error when calling `AdminAPI.GetConsumerInfoV1AdminConsumersConsumerTypeGet``: %v\n", err)
		fmt.Fprintf(os.Stderr, "Full HTTP response: %v\n", r)
	}
	// response from `GetConsumerInfoV1AdminConsumersConsumerTypeGet`: ConsumerInfo
	fmt.Fprintf(os.Stdout, "Response from `AdminAPI.GetConsumerInfoV1AdminConsumersConsumerTypeGet`: %v\n", resp)
}
```

### Path Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
**ctx** | **context.Context** | context for authentication, logging, cancellation, deadlines, tracing, etc.
**consumerType** | [**ConsumerType**](.md) |  | 

### Other Parameters

Other parameters are passed through a pointer to a apiGetConsumerInfoV1AdminConsumersConsumerTypeGetRequest struct via the builder pattern


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------


### Return type

[**ConsumerInfo**](ConsumerInfo.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints)
[[Back to Model list]](../README.md#documentation-for-models)
[[Back to README]](../README.md)


## ListConsumersV1AdminConsumersGet

> ConsumerListResponse ListConsumersV1AdminConsumersGet(ctx).Execute()

List Consumers



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

	configuration := openapiclient.NewConfiguration()
	apiClient := openapiclient.NewAPIClient(configuration)
	resp, r, err := apiClient.AdminAPI.ListConsumersV1AdminConsumersGet(context.Background()).Execute()
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error when calling `AdminAPI.ListConsumersV1AdminConsumersGet``: %v\n", err)
		fmt.Fprintf(os.Stderr, "Full HTTP response: %v\n", r)
	}
	// response from `ListConsumersV1AdminConsumersGet`: ConsumerListResponse
	fmt.Fprintf(os.Stdout, "Response from `AdminAPI.ListConsumersV1AdminConsumersGet`: %v\n", resp)
}
```

### Path Parameters

This endpoint does not need any parameter.

### Other Parameters

Other parameters are passed through a pointer to a apiListConsumersV1AdminConsumersGetRequest struct via the builder pattern


### Return type

[**ConsumerListResponse**](ConsumerListResponse.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints)
[[Back to Model list]](../README.md#documentation-for-models)
[[Back to README]](../README.md)


## ResetAllConsumersV1AdminConsumersResetAllDelete

> []ConsumerResetResponse ResetAllConsumersV1AdminConsumersResetAllDelete(ctx).Execute()

Reset All Consumers



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

	configuration := openapiclient.NewConfiguration()
	apiClient := openapiclient.NewAPIClient(configuration)
	resp, r, err := apiClient.AdminAPI.ResetAllConsumersV1AdminConsumersResetAllDelete(context.Background()).Execute()
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error when calling `AdminAPI.ResetAllConsumersV1AdminConsumersResetAllDelete``: %v\n", err)
		fmt.Fprintf(os.Stderr, "Full HTTP response: %v\n", r)
	}
	// response from `ResetAllConsumersV1AdminConsumersResetAllDelete`: []ConsumerResetResponse
	fmt.Fprintf(os.Stdout, "Response from `AdminAPI.ResetAllConsumersV1AdminConsumersResetAllDelete`: %v\n", resp)
}
```

### Path Parameters

This endpoint does not need any parameter.

### Other Parameters

Other parameters are passed through a pointer to a apiResetAllConsumersV1AdminConsumersResetAllDeleteRequest struct via the builder pattern


### Return type

[**[]ConsumerResetResponse**](ConsumerResetResponse.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints)
[[Back to Model list]](../README.md#documentation-for-models)
[[Back to README]](../README.md)


## ResetConsumerV1AdminConsumersConsumerTypeResetDelete

> ConsumerResetResponse ResetConsumerV1AdminConsumersConsumerTypeResetDelete(ctx, consumerType).Execute()

Reset Consumer



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
	consumerType := openapiclient.ConsumerType("nautobot") // ConsumerType | 

	configuration := openapiclient.NewConfiguration()
	apiClient := openapiclient.NewAPIClient(configuration)
	resp, r, err := apiClient.AdminAPI.ResetConsumerV1AdminConsumersConsumerTypeResetDelete(context.Background(), consumerType).Execute()
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error when calling `AdminAPI.ResetConsumerV1AdminConsumersConsumerTypeResetDelete``: %v\n", err)
		fmt.Fprintf(os.Stderr, "Full HTTP response: %v\n", r)
	}
	// response from `ResetConsumerV1AdminConsumersConsumerTypeResetDelete`: ConsumerResetResponse
	fmt.Fprintf(os.Stdout, "Response from `AdminAPI.ResetConsumerV1AdminConsumersConsumerTypeResetDelete`: %v\n", resp)
}
```

### Path Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
**ctx** | **context.Context** | context for authentication, logging, cancellation, deadlines, tracing, etc.
**consumerType** | [**ConsumerType**](.md) |  | 

### Other Parameters

Other parameters are passed through a pointer to a apiResetConsumerV1AdminConsumersConsumerTypeResetDeleteRequest struct via the builder pattern


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------


### Return type

[**ConsumerResetResponse**](ConsumerResetResponse.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints)
[[Back to Model list]](../README.md#documentation-for-models)
[[Back to README]](../README.md)

