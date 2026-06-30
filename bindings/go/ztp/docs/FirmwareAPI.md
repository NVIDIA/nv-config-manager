# \FirmwareAPI

All URIs are relative to *http://localhost*

Method | HTTP request | Description
------------- | ------------- | -------------
[**LoadFirmwareChecksumV1FirmwarePlatformVersionChecksumGet**](FirmwareAPI.md#LoadFirmwareChecksumV1FirmwarePlatformVersionChecksumGet) | **Get** /v1/firmware/{platform}/{version}/checksum | Load Firmware Checksum
[**LoadFirmwareV1FirmwarePlatformVersionGet**](FirmwareAPI.md#LoadFirmwareV1FirmwarePlatformVersionGet) | **Get** /v1/firmware/{platform}/{version} | Load Firmware



## LoadFirmwareChecksumV1FirmwarePlatformVersionChecksumGet

> ChecksumResponse LoadFirmwareChecksumV1FirmwarePlatformVersionChecksumGet(ctx, platform, version).Execute()

Load Firmware Checksum



### Example

```go
package main

import (
	"context"
	"fmt"
	"os"
	openapiclient "github.com/nvidia/nv-config-manager/bindings/go/ztp"
)

func main() {
	platform := "platform_example" // string | 
	version := "version_example" // string | 

	configuration := openapiclient.NewConfiguration()
	apiClient := openapiclient.NewAPIClient(configuration)
	resp, r, err := apiClient.FirmwareAPI.LoadFirmwareChecksumV1FirmwarePlatformVersionChecksumGet(context.Background(), platform, version).Execute()
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error when calling `FirmwareAPI.LoadFirmwareChecksumV1FirmwarePlatformVersionChecksumGet``: %v\n", err)
		fmt.Fprintf(os.Stderr, "Full HTTP response: %v\n", r)
	}
	// response from `LoadFirmwareChecksumV1FirmwarePlatformVersionChecksumGet`: ChecksumResponse
	fmt.Fprintf(os.Stdout, "Response from `FirmwareAPI.LoadFirmwareChecksumV1FirmwarePlatformVersionChecksumGet`: %v\n", resp)
}
```

### Path Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
**ctx** | **context.Context** | context for authentication, logging, cancellation, deadlines, tracing, etc.
**platform** | **string** |  | 
**version** | **string** |  | 

### Other Parameters

Other parameters are passed through a pointer to a apiLoadFirmwareChecksumV1FirmwarePlatformVersionChecksumGetRequest struct via the builder pattern


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------



### Return type

[**ChecksumResponse**](ChecksumResponse.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints)
[[Back to Model list]](../README.md#documentation-for-models)
[[Back to README]](../README.md)


## LoadFirmwareV1FirmwarePlatformVersionGet

> LoadFirmwareV1FirmwarePlatformVersionGet(ctx, platform, version).Execute()

Load Firmware



### Example

```go
package main

import (
	"context"
	"fmt"
	"os"
	openapiclient "github.com/nvidia/nv-config-manager/bindings/go/ztp"
)

func main() {
	platform := "platform_example" // string | 
	version := "version_example" // string | 

	configuration := openapiclient.NewConfiguration()
	apiClient := openapiclient.NewAPIClient(configuration)
	r, err := apiClient.FirmwareAPI.LoadFirmwareV1FirmwarePlatformVersionGet(context.Background(), platform, version).Execute()
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error when calling `FirmwareAPI.LoadFirmwareV1FirmwarePlatformVersionGet``: %v\n", err)
		fmt.Fprintf(os.Stderr, "Full HTTP response: %v\n", r)
	}
}
```

### Path Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
**ctx** | **context.Context** | context for authentication, logging, cancellation, deadlines, tracing, etc.
**platform** | **string** |  | 
**version** | **string** |  | 

### Other Parameters

Other parameters are passed through a pointer to a apiLoadFirmwareV1FirmwarePlatformVersionGetRequest struct via the builder pattern


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------



### Return type

 (empty response body)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints)
[[Back to Model list]](../README.md#documentation-for-models)
[[Back to README]](../README.md)

