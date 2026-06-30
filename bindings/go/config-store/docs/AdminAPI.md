# \AdminAPI

All URIs are relative to *http://localhost*

Method | HTTP request | Description
------------- | ------------- | -------------
[**CacheStatusV1AdminCacheStatusGet**](AdminAPI.md#CacheStatusV1AdminCacheStatusGet) | **Get** /v1/admin/cache/status | Check cache service status
[**DeleteDeviceV1AdminDevicesDeviceUuidDelete**](AdminAPI.md#DeleteDeviceV1AdminDevicesDeviceUuidDelete) | **Delete** /v1/admin/devices/{device_uuid} | Permanently delete all configs for a device
[**GetStatsV1AdminStatsGet**](AdminAPI.md#GetStatsV1AdminStatsGet) | **Get** /v1/admin/stats | Get database statistics
[**ListDevicesV1AdminDevicesGet**](AdminAPI.md#ListDevicesV1AdminDevicesGet) | **Get** /v1/admin/devices | List all devices
[**SearchDevicesV1AdminDevicesSearchGet**](AdminAPI.md#SearchDevicesV1AdminDevicesSearchGet) | **Get** /v1/admin/devices/search | Search devices by name with latest config info
[**TestCacheLookupV1AdminCacheTestDeviceUuidGet**](AdminAPI.md#TestCacheLookupV1AdminCacheTestDeviceUuidGet) | **Get** /v1/admin/cache/test/{device_uuid} | Test cache lookup for a device



## CacheStatusV1AdminCacheStatusGet

> CacheStatusResponse CacheStatusV1AdminCacheStatusGet(ctx).Execute()

Check cache service status



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

	configuration := openapiclient.NewConfiguration()
	apiClient := openapiclient.NewAPIClient(configuration)
	resp, r, err := apiClient.AdminAPI.CacheStatusV1AdminCacheStatusGet(context.Background()).Execute()
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error when calling `AdminAPI.CacheStatusV1AdminCacheStatusGet``: %v\n", err)
		fmt.Fprintf(os.Stderr, "Full HTTP response: %v\n", r)
	}
	// response from `CacheStatusV1AdminCacheStatusGet`: CacheStatusResponse
	fmt.Fprintf(os.Stdout, "Response from `AdminAPI.CacheStatusV1AdminCacheStatusGet`: %v\n", resp)
}
```

### Path Parameters

This endpoint does not need any parameter.

### Other Parameters

Other parameters are passed through a pointer to a apiCacheStatusV1AdminCacheStatusGetRequest struct via the builder pattern


### Return type

[**CacheStatusResponse**](CacheStatusResponse.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints)
[[Back to Model list]](../README.md#documentation-for-models)
[[Back to README]](../README.md)


## DeleteDeviceV1AdminDevicesDeviceUuidDelete

> DeleteDeviceResponse DeleteDeviceV1AdminDevicesDeviceUuidDelete(ctx, deviceUuid).Execute()

Permanently delete all configs for a device



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

	configuration := openapiclient.NewConfiguration()
	apiClient := openapiclient.NewAPIClient(configuration)
	resp, r, err := apiClient.AdminAPI.DeleteDeviceV1AdminDevicesDeviceUuidDelete(context.Background(), deviceUuid).Execute()
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error when calling `AdminAPI.DeleteDeviceV1AdminDevicesDeviceUuidDelete``: %v\n", err)
		fmt.Fprintf(os.Stderr, "Full HTTP response: %v\n", r)
	}
	// response from `DeleteDeviceV1AdminDevicesDeviceUuidDelete`: DeleteDeviceResponse
	fmt.Fprintf(os.Stdout, "Response from `AdminAPI.DeleteDeviceV1AdminDevicesDeviceUuidDelete`: %v\n", resp)
}
```

### Path Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
**ctx** | **context.Context** | context for authentication, logging, cancellation, deadlines, tracing, etc.
**deviceUuid** | **string** |  | 

### Other Parameters

Other parameters are passed through a pointer to a apiDeleteDeviceV1AdminDevicesDeviceUuidDeleteRequest struct via the builder pattern


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------


### Return type

[**DeleteDeviceResponse**](DeleteDeviceResponse.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints)
[[Back to Model list]](../README.md#documentation-for-models)
[[Back to README]](../README.md)


## GetStatsV1AdminStatsGet

> StatsResponse GetStatsV1AdminStatsGet(ctx).Execute()

Get database statistics



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

	configuration := openapiclient.NewConfiguration()
	apiClient := openapiclient.NewAPIClient(configuration)
	resp, r, err := apiClient.AdminAPI.GetStatsV1AdminStatsGet(context.Background()).Execute()
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error when calling `AdminAPI.GetStatsV1AdminStatsGet``: %v\n", err)
		fmt.Fprintf(os.Stderr, "Full HTTP response: %v\n", r)
	}
	// response from `GetStatsV1AdminStatsGet`: StatsResponse
	fmt.Fprintf(os.Stdout, "Response from `AdminAPI.GetStatsV1AdminStatsGet`: %v\n", resp)
}
```

### Path Parameters

This endpoint does not need any parameter.

### Other Parameters

Other parameters are passed through a pointer to a apiGetStatsV1AdminStatsGetRequest struct via the builder pattern


### Return type

[**StatsResponse**](StatsResponse.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints)
[[Back to Model list]](../README.md#documentation-for-models)
[[Back to README]](../README.md)


## ListDevicesV1AdminDevicesGet

> []DeviceUUID ListDevicesV1AdminDevicesGet(ctx).Limit(limit).Offset(offset).Execute()

List all devices



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
	limit := int32(56) // int32 |  (optional) (default to 100)
	offset := int32(56) // int32 |  (optional) (default to 0)

	configuration := openapiclient.NewConfiguration()
	apiClient := openapiclient.NewAPIClient(configuration)
	resp, r, err := apiClient.AdminAPI.ListDevicesV1AdminDevicesGet(context.Background()).Limit(limit).Offset(offset).Execute()
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error when calling `AdminAPI.ListDevicesV1AdminDevicesGet``: %v\n", err)
		fmt.Fprintf(os.Stderr, "Full HTTP response: %v\n", r)
	}
	// response from `ListDevicesV1AdminDevicesGet`: []DeviceUUID
	fmt.Fprintf(os.Stdout, "Response from `AdminAPI.ListDevicesV1AdminDevicesGet`: %v\n", resp)
}
```

### Path Parameters



### Other Parameters

Other parameters are passed through a pointer to a apiListDevicesV1AdminDevicesGetRequest struct via the builder pattern


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **limit** | **int32** |  | [default to 100]
 **offset** | **int32** |  | [default to 0]

### Return type

[**[]DeviceUUID**](DeviceUUID.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints)
[[Back to Model list]](../README.md#documentation-for-models)
[[Back to README]](../README.md)


## SearchDevicesV1AdminDevicesSearchGet

> []DeviceLatestConfig SearchDevicesV1AdminDevicesSearchGet(ctx).Q(q).Limit(limit).FileType(fileType).IncludeInactive(includeInactive).Execute()

Search devices by name with latest config info



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
	q := "q_example" // string |  (optional)
	limit := int32(56) // int32 |  (optional) (default to 100)
	fileType := openapiclient.FileType("intended") // FileType |  (optional) (default to "intended")
	includeInactive := true // bool |  (optional) (default to false)

	configuration := openapiclient.NewConfiguration()
	apiClient := openapiclient.NewAPIClient(configuration)
	resp, r, err := apiClient.AdminAPI.SearchDevicesV1AdminDevicesSearchGet(context.Background()).Q(q).Limit(limit).FileType(fileType).IncludeInactive(includeInactive).Execute()
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error when calling `AdminAPI.SearchDevicesV1AdminDevicesSearchGet``: %v\n", err)
		fmt.Fprintf(os.Stderr, "Full HTTP response: %v\n", r)
	}
	// response from `SearchDevicesV1AdminDevicesSearchGet`: []DeviceLatestConfig
	fmt.Fprintf(os.Stdout, "Response from `AdminAPI.SearchDevicesV1AdminDevicesSearchGet`: %v\n", resp)
}
```

### Path Parameters



### Other Parameters

Other parameters are passed through a pointer to a apiSearchDevicesV1AdminDevicesSearchGetRequest struct via the builder pattern


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **q** | **string** |  | 
 **limit** | **int32** |  | [default to 100]
 **fileType** | [**FileType**](FileType.md) |  | [default to &quot;intended&quot;]
 **includeInactive** | **bool** |  | [default to false]

### Return type

[**[]DeviceLatestConfig**](DeviceLatestConfig.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints)
[[Back to Model list]](../README.md#documentation-for-models)
[[Back to README]](../README.md)


## TestCacheLookupV1AdminCacheTestDeviceUuidGet

> ResponseTestCacheLookupV1AdminCacheTestDeviceUuidGet TestCacheLookupV1AdminCacheTestDeviceUuidGet(ctx, deviceUuid).Execute()

Test cache lookup for a device



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

	configuration := openapiclient.NewConfiguration()
	apiClient := openapiclient.NewAPIClient(configuration)
	resp, r, err := apiClient.AdminAPI.TestCacheLookupV1AdminCacheTestDeviceUuidGet(context.Background(), deviceUuid).Execute()
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error when calling `AdminAPI.TestCacheLookupV1AdminCacheTestDeviceUuidGet``: %v\n", err)
		fmt.Fprintf(os.Stderr, "Full HTTP response: %v\n", r)
	}
	// response from `TestCacheLookupV1AdminCacheTestDeviceUuidGet`: ResponseTestCacheLookupV1AdminCacheTestDeviceUuidGet
	fmt.Fprintf(os.Stdout, "Response from `AdminAPI.TestCacheLookupV1AdminCacheTestDeviceUuidGet`: %v\n", resp)
}
```

### Path Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
**ctx** | **context.Context** | context for authentication, logging, cancellation, deadlines, tracing, etc.
**deviceUuid** | **string** |  | 

### Other Parameters

Other parameters are passed through a pointer to a apiTestCacheLookupV1AdminCacheTestDeviceUuidGetRequest struct via the builder pattern


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------


### Return type

[**ResponseTestCacheLookupV1AdminCacheTestDeviceUuidGet**](ResponseTestCacheLookupV1AdminCacheTestDeviceUuidGet.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints)
[[Back to Model list]](../README.md#documentation-for-models)
[[Back to README]](../README.md)

