# \DefaultAPI

All URIs are relative to *http://localhost*

Method | HTTP request | Description
------------- | ------------- | -------------
[**FlushCacheAdminCacheDelete**](DefaultAPI.md#FlushCacheAdminCacheDelete) | **Delete** /admin/cache | Flush Cache
[**GetConfigConfigGet**](DefaultAPI.md#GetConfigConfigGet) | **Get** /config | Get Config
[**HealthcheckHealthcheckGet**](DefaultAPI.md#HealthcheckHealthcheckGet) | **Get** /healthcheck | Healthcheck
[**WhoamiWhoamiGet**](DefaultAPI.md#WhoamiWhoamiGet) | **Get** /whoami | Current User Info



## FlushCacheAdminCacheDelete

> map[string]string FlushCacheAdminCacheDelete(ctx).IpVersion(ipVersion).Execute()

Flush Cache



### Example

```go
package main

import (
	"context"
	"fmt"
	"os"
	openapiclient "github.com/nvidia/nv-config-manager/bindings/go/dhcp"
)

func main() {
	ipVersion := int32(56) // int32 |  (optional) (default to 4)

	configuration := openapiclient.NewConfiguration()
	apiClient := openapiclient.NewAPIClient(configuration)
	resp, r, err := apiClient.DefaultAPI.FlushCacheAdminCacheDelete(context.Background()).IpVersion(ipVersion).Execute()
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error when calling `DefaultAPI.FlushCacheAdminCacheDelete``: %v\n", err)
		fmt.Fprintf(os.Stderr, "Full HTTP response: %v\n", r)
	}
	// response from `FlushCacheAdminCacheDelete`: map[string]string
	fmt.Fprintf(os.Stdout, "Response from `DefaultAPI.FlushCacheAdminCacheDelete`: %v\n", resp)
}
```

### Path Parameters



### Other Parameters

Other parameters are passed through a pointer to a apiFlushCacheAdminCacheDeleteRequest struct via the builder pattern


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **ipVersion** | **int32** |  | [default to 4]

### Return type

**map[string]string**

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints)
[[Back to Model list]](../README.md#documentation-for-models)
[[Back to README]](../README.md)


## GetConfigConfigGet

> interface{} GetConfigConfigGet(ctx).IpVersion(ipVersion).Execute()

Get Config



### Example

```go
package main

import (
	"context"
	"fmt"
	"os"
	openapiclient "github.com/nvidia/nv-config-manager/bindings/go/dhcp"
)

func main() {
	ipVersion := int32(56) // int32 |  (optional) (default to 4)

	configuration := openapiclient.NewConfiguration()
	apiClient := openapiclient.NewAPIClient(configuration)
	resp, r, err := apiClient.DefaultAPI.GetConfigConfigGet(context.Background()).IpVersion(ipVersion).Execute()
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error when calling `DefaultAPI.GetConfigConfigGet``: %v\n", err)
		fmt.Fprintf(os.Stderr, "Full HTTP response: %v\n", r)
	}
	// response from `GetConfigConfigGet`: interface{}
	fmt.Fprintf(os.Stdout, "Response from `DefaultAPI.GetConfigConfigGet`: %v\n", resp)
}
```

### Path Parameters



### Other Parameters

Other parameters are passed through a pointer to a apiGetConfigConfigGetRequest struct via the builder pattern


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **ipVersion** | **int32** |  | [default to 4]

### Return type

**interface{}**

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints)
[[Back to Model list]](../README.md#documentation-for-models)
[[Back to README]](../README.md)


## HealthcheckHealthcheckGet

> string HealthcheckHealthcheckGet(ctx).Execute()

Healthcheck



### Example

```go
package main

import (
	"context"
	"fmt"
	"os"
	openapiclient "github.com/nvidia/nv-config-manager/bindings/go/dhcp"
)

func main() {

	configuration := openapiclient.NewConfiguration()
	apiClient := openapiclient.NewAPIClient(configuration)
	resp, r, err := apiClient.DefaultAPI.HealthcheckHealthcheckGet(context.Background()).Execute()
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error when calling `DefaultAPI.HealthcheckHealthcheckGet``: %v\n", err)
		fmt.Fprintf(os.Stderr, "Full HTTP response: %v\n", r)
	}
	// response from `HealthcheckHealthcheckGet`: string
	fmt.Fprintf(os.Stdout, "Response from `DefaultAPI.HealthcheckHealthcheckGet`: %v\n", resp)
}
```

### Path Parameters

This endpoint does not need any parameter.

### Other Parameters

Other parameters are passed through a pointer to a apiHealthcheckHealthcheckGetRequest struct via the builder pattern


### Return type

**string**

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints)
[[Back to Model list]](../README.md#documentation-for-models)
[[Back to README]](../README.md)


## WhoamiWhoamiGet

> WhoamiResponse WhoamiWhoamiGet(ctx).Execute()

Current User Info



### Example

```go
package main

import (
	"context"
	"fmt"
	"os"
	openapiclient "github.com/nvidia/nv-config-manager/bindings/go/dhcp"
)

func main() {

	configuration := openapiclient.NewConfiguration()
	apiClient := openapiclient.NewAPIClient(configuration)
	resp, r, err := apiClient.DefaultAPI.WhoamiWhoamiGet(context.Background()).Execute()
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error when calling `DefaultAPI.WhoamiWhoamiGet``: %v\n", err)
		fmt.Fprintf(os.Stderr, "Full HTTP response: %v\n", r)
	}
	// response from `WhoamiWhoamiGet`: WhoamiResponse
	fmt.Fprintf(os.Stdout, "Response from `DefaultAPI.WhoamiWhoamiGet`: %v\n", resp)
}
```

### Path Parameters

This endpoint does not need any parameter.

### Other Parameters

Other parameters are passed through a pointer to a apiWhoamiWhoamiGetRequest struct via the builder pattern


### Return type

[**WhoamiResponse**](WhoamiResponse.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints)
[[Back to Model list]](../README.md#documentation-for-models)
[[Back to README]](../README.md)

