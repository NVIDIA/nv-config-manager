# \DeviceAPI

All URIs are relative to *http://localhost*

Method | HTTP request | Description
------------- | ------------- | -------------
[**LoadBootscriptV1DeviceDeviceUuidBootScriptGet**](DeviceAPI.md#LoadBootscriptV1DeviceDeviceUuidBootScriptGet) | **Get** /v1/device/{device_uuid}/boot-script | Load Bootscript
[**LoadConfigurationV1DeviceDeviceUuidConfigConfigletGet**](DeviceAPI.md#LoadConfigurationV1DeviceDeviceUuidConfigConfigletGet) | **Get** /v1/device/{device_uuid}/config/{configlet} | Load Configuration
[**LoadFirmwareChecksumV1DeviceDeviceUuidFirmwareChecksumGet**](DeviceAPI.md#LoadFirmwareChecksumV1DeviceDeviceUuidFirmwareChecksumGet) | **Get** /v1/device/{device_uuid}/firmware/checksum | Load Firmware Checksum
[**LoadFirmwareV1DeviceDeviceUuidFirmwareGet**](DeviceAPI.md#LoadFirmwareV1DeviceDeviceUuidFirmwareGet) | **Get** /v1/device/{device_uuid}/firmware | Load Firmware
[**LoadFirmwareV1DeviceDeviceUuidOnieGet**](DeviceAPI.md#LoadFirmwareV1DeviceDeviceUuidOnieGet) | **Get** /v1/device/{device_uuid}/onie | Load Firmware
[**MarkProvisionedV1DeviceDeviceUuidProvisionedPost**](DeviceAPI.md#MarkProvisionedV1DeviceDeviceUuidProvisionedPost) | **Post** /v1/device/{device_uuid}/provisioned | Mark Provisioned
[**ValidateSerialV1DeviceDeviceUuidValidateSerialPost**](DeviceAPI.md#ValidateSerialV1DeviceDeviceUuidValidateSerialPost) | **Post** /v1/device/{device_uuid}/validate_serial | Validate Serial



## LoadBootscriptV1DeviceDeviceUuidBootScriptGet

> string LoadBootscriptV1DeviceDeviceUuidBootScriptGet(ctx, deviceUuid).Execute()

Load Bootscript



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
	deviceUuid := "deviceUuid_example" // string | 

	configuration := openapiclient.NewConfiguration()
	apiClient := openapiclient.NewAPIClient(configuration)
	resp, r, err := apiClient.DeviceAPI.LoadBootscriptV1DeviceDeviceUuidBootScriptGet(context.Background(), deviceUuid).Execute()
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error when calling `DeviceAPI.LoadBootscriptV1DeviceDeviceUuidBootScriptGet``: %v\n", err)
		fmt.Fprintf(os.Stderr, "Full HTTP response: %v\n", r)
	}
	// response from `LoadBootscriptV1DeviceDeviceUuidBootScriptGet`: string
	fmt.Fprintf(os.Stdout, "Response from `DeviceAPI.LoadBootscriptV1DeviceDeviceUuidBootScriptGet`: %v\n", resp)
}
```

### Path Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
**ctx** | **context.Context** | context for authentication, logging, cancellation, deadlines, tracing, etc.
**deviceUuid** | **string** |  | 

### Other Parameters

Other parameters are passed through a pointer to a apiLoadBootscriptV1DeviceDeviceUuidBootScriptGetRequest struct via the builder pattern


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------


### Return type

**string**

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: text/plain, application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints)
[[Back to Model list]](../README.md#documentation-for-models)
[[Back to README]](../README.md)


## LoadConfigurationV1DeviceDeviceUuidConfigConfigletGet

> string LoadConfigurationV1DeviceDeviceUuidConfigConfigletGet(ctx, deviceUuid, configlet).Execute()

Load Configuration



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
	deviceUuid := "deviceUuid_example" // string | 
	configlet := "configlet_example" // string | 

	configuration := openapiclient.NewConfiguration()
	apiClient := openapiclient.NewAPIClient(configuration)
	resp, r, err := apiClient.DeviceAPI.LoadConfigurationV1DeviceDeviceUuidConfigConfigletGet(context.Background(), deviceUuid, configlet).Execute()
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error when calling `DeviceAPI.LoadConfigurationV1DeviceDeviceUuidConfigConfigletGet``: %v\n", err)
		fmt.Fprintf(os.Stderr, "Full HTTP response: %v\n", r)
	}
	// response from `LoadConfigurationV1DeviceDeviceUuidConfigConfigletGet`: string
	fmt.Fprintf(os.Stdout, "Response from `DeviceAPI.LoadConfigurationV1DeviceDeviceUuidConfigConfigletGet`: %v\n", resp)
}
```

### Path Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
**ctx** | **context.Context** | context for authentication, logging, cancellation, deadlines, tracing, etc.
**deviceUuid** | **string** |  | 
**configlet** | **string** |  | 

### Other Parameters

Other parameters are passed through a pointer to a apiLoadConfigurationV1DeviceDeviceUuidConfigConfigletGetRequest struct via the builder pattern


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------



### Return type

**string**

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: text/plain, application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints)
[[Back to Model list]](../README.md#documentation-for-models)
[[Back to README]](../README.md)


## LoadFirmwareChecksumV1DeviceDeviceUuidFirmwareChecksumGet

> ChecksumResponse LoadFirmwareChecksumV1DeviceDeviceUuidFirmwareChecksumGet(ctx, deviceUuid).Execute()

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
	deviceUuid := "deviceUuid_example" // string | 

	configuration := openapiclient.NewConfiguration()
	apiClient := openapiclient.NewAPIClient(configuration)
	resp, r, err := apiClient.DeviceAPI.LoadFirmwareChecksumV1DeviceDeviceUuidFirmwareChecksumGet(context.Background(), deviceUuid).Execute()
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error when calling `DeviceAPI.LoadFirmwareChecksumV1DeviceDeviceUuidFirmwareChecksumGet``: %v\n", err)
		fmt.Fprintf(os.Stderr, "Full HTTP response: %v\n", r)
	}
	// response from `LoadFirmwareChecksumV1DeviceDeviceUuidFirmwareChecksumGet`: ChecksumResponse
	fmt.Fprintf(os.Stdout, "Response from `DeviceAPI.LoadFirmwareChecksumV1DeviceDeviceUuidFirmwareChecksumGet`: %v\n", resp)
}
```

### Path Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
**ctx** | **context.Context** | context for authentication, logging, cancellation, deadlines, tracing, etc.
**deviceUuid** | **string** |  | 

### Other Parameters

Other parameters are passed through a pointer to a apiLoadFirmwareChecksumV1DeviceDeviceUuidFirmwareChecksumGetRequest struct via the builder pattern


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


## LoadFirmwareV1DeviceDeviceUuidFirmwareGet

> LoadFirmwareV1DeviceDeviceUuidFirmwareGet(ctx, deviceUuid).Execute()

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
	deviceUuid := "deviceUuid_example" // string | 

	configuration := openapiclient.NewConfiguration()
	apiClient := openapiclient.NewAPIClient(configuration)
	r, err := apiClient.DeviceAPI.LoadFirmwareV1DeviceDeviceUuidFirmwareGet(context.Background(), deviceUuid).Execute()
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error when calling `DeviceAPI.LoadFirmwareV1DeviceDeviceUuidFirmwareGet``: %v\n", err)
		fmt.Fprintf(os.Stderr, "Full HTTP response: %v\n", r)
	}
}
```

### Path Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
**ctx** | **context.Context** | context for authentication, logging, cancellation, deadlines, tracing, etc.
**deviceUuid** | **string** |  | 

### Other Parameters

Other parameters are passed through a pointer to a apiLoadFirmwareV1DeviceDeviceUuidFirmwareGetRequest struct via the builder pattern


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


## LoadFirmwareV1DeviceDeviceUuidOnieGet

> string LoadFirmwareV1DeviceDeviceUuidOnieGet(ctx, deviceUuid).Execute()

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
	deviceUuid := "deviceUuid_example" // string | 

	configuration := openapiclient.NewConfiguration()
	apiClient := openapiclient.NewAPIClient(configuration)
	resp, r, err := apiClient.DeviceAPI.LoadFirmwareV1DeviceDeviceUuidOnieGet(context.Background(), deviceUuid).Execute()
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error when calling `DeviceAPI.LoadFirmwareV1DeviceDeviceUuidOnieGet``: %v\n", err)
		fmt.Fprintf(os.Stderr, "Full HTTP response: %v\n", r)
	}
	// response from `LoadFirmwareV1DeviceDeviceUuidOnieGet`: string
	fmt.Fprintf(os.Stdout, "Response from `DeviceAPI.LoadFirmwareV1DeviceDeviceUuidOnieGet`: %v\n", resp)
}
```

### Path Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
**ctx** | **context.Context** | context for authentication, logging, cancellation, deadlines, tracing, etc.
**deviceUuid** | **string** |  | 

### Other Parameters

Other parameters are passed through a pointer to a apiLoadFirmwareV1DeviceDeviceUuidOnieGetRequest struct via the builder pattern


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------


### Return type

**string**

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: text/plain, application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints)
[[Back to Model list]](../README.md#documentation-for-models)
[[Back to README]](../README.md)


## MarkProvisionedV1DeviceDeviceUuidProvisionedPost

> string MarkProvisionedV1DeviceDeviceUuidProvisionedPost(ctx, deviceUuid).Execute()

Mark Provisioned



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
	deviceUuid := "deviceUuid_example" // string | 

	configuration := openapiclient.NewConfiguration()
	apiClient := openapiclient.NewAPIClient(configuration)
	resp, r, err := apiClient.DeviceAPI.MarkProvisionedV1DeviceDeviceUuidProvisionedPost(context.Background(), deviceUuid).Execute()
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error when calling `DeviceAPI.MarkProvisionedV1DeviceDeviceUuidProvisionedPost``: %v\n", err)
		fmt.Fprintf(os.Stderr, "Full HTTP response: %v\n", r)
	}
	// response from `MarkProvisionedV1DeviceDeviceUuidProvisionedPost`: string
	fmt.Fprintf(os.Stdout, "Response from `DeviceAPI.MarkProvisionedV1DeviceDeviceUuidProvisionedPost`: %v\n", resp)
}
```

### Path Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
**ctx** | **context.Context** | context for authentication, logging, cancellation, deadlines, tracing, etc.
**deviceUuid** | **string** |  | 

### Other Parameters

Other parameters are passed through a pointer to a apiMarkProvisionedV1DeviceDeviceUuidProvisionedPostRequest struct via the builder pattern


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------


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


## ValidateSerialV1DeviceDeviceUuidValidateSerialPost

> string ValidateSerialV1DeviceDeviceUuidValidateSerialPost(ctx, deviceUuid).ValidateSerialBody(validateSerialBody).Execute()

Validate Serial



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
	deviceUuid := "deviceUuid_example" // string | 
	validateSerialBody := *openapiclient.NewValidateSerialBody("Serial_example") // ValidateSerialBody | 

	configuration := openapiclient.NewConfiguration()
	apiClient := openapiclient.NewAPIClient(configuration)
	resp, r, err := apiClient.DeviceAPI.ValidateSerialV1DeviceDeviceUuidValidateSerialPost(context.Background(), deviceUuid).ValidateSerialBody(validateSerialBody).Execute()
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error when calling `DeviceAPI.ValidateSerialV1DeviceDeviceUuidValidateSerialPost``: %v\n", err)
		fmt.Fprintf(os.Stderr, "Full HTTP response: %v\n", r)
	}
	// response from `ValidateSerialV1DeviceDeviceUuidValidateSerialPost`: string
	fmt.Fprintf(os.Stdout, "Response from `DeviceAPI.ValidateSerialV1DeviceDeviceUuidValidateSerialPost`: %v\n", resp)
}
```

### Path Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
**ctx** | **context.Context** | context for authentication, logging, cancellation, deadlines, tracing, etc.
**deviceUuid** | **string** |  | 

### Other Parameters

Other parameters are passed through a pointer to a apiValidateSerialV1DeviceDeviceUuidValidateSerialPostRequest struct via the builder pattern


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------

 **validateSerialBody** | [**ValidateSerialBody**](ValidateSerialBody.md) |  | 

### Return type

**string**

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: application/json
- **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints)
[[Back to Model list]](../README.md#documentation-for-models)
[[Back to README]](../README.md)

