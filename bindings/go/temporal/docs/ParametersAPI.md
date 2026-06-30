# \ParametersAPI

All URIs are relative to *http://localhost*

Method | HTTP request | Description
------------- | ------------- | -------------
[**GetDeviceIdByNameV1ParameterDeviceIdGet**](ParametersAPI.md#GetDeviceIdByNameV1ParameterDeviceIdGet) | **Get** /v1/parameter/device-id | Get Device ID by Name
[**GetDevicePasswordUsersV1ParameterDeviceDeviceIdPasswordUsersGet**](ParametersAPI.md#GetDevicePasswordUsersV1ParameterDeviceDeviceIdPasswordUsersGet) | **Get** /v1/parameter/device/{device_id}/password_users | Get Device Password Users
[**GetDeviceSecretsV1ParameterDeviceDeviceIdSecretsGet**](ParametersAPI.md#GetDeviceSecretsV1ParameterDeviceDeviceIdSecretsGet) | **Get** /v1/parameter/device/{device_id}/secrets | Get Device Secrets
[**GetDeviceUsersWithVersionsV1ParameterDeviceDeviceIdSecretTypesGet**](ParametersAPI.md#GetDeviceUsersWithVersionsV1ParameterDeviceDeviceIdSecretTypesGet) | **Get** /v1/parameter/device/{device_id}/secret_types | Get Secret Types for Device
[**GetDevicesV1ParameterDeviceGet**](ParametersAPI.md#GetDevicesV1ParameterDeviceGet) | **Get** /v1/parameter/device | Get Devices
[**GetDiagnosticsCommandsV1ParameterDiagnosticsCommandsGet**](ParametersAPI.md#GetDiagnosticsCommandsV1ParameterDiagnosticsCommandsGet) | **Get** /v1/parameter/diagnostics/commands | Get Diagnostics Commands
[**GetLocationsV1ParameterLocationGet**](ParametersAPI.md#GetLocationsV1ParameterLocationGet) | **Get** /v1/parameter/location | Get Locations
[**GetNamespaceTagsV1ParameterNamespaceTagGet**](ParametersAPI.md#GetNamespaceTagsV1ParameterNamespaceTagGet) | **Get** /v1/parameter/namespace-tag | Get Namespace Tags
[**GetRolesV1ParameterRoleGet**](ParametersAPI.md#GetRolesV1ParameterRoleGet) | **Get** /v1/parameter/role | Get Roles
[**GetSitesV1ParameterSiteGet**](ParametersAPI.md#GetSitesV1ParameterSiteGet) | **Get** /v1/parameter/site | Get Sites
[**GetStatusesV1ParameterStatusGet**](ParametersAPI.md#GetStatusesV1ParameterStatusGet) | **Get** /v1/parameter/status | Get Statuses
[**GetTenantsV1ParameterTenantGet**](ParametersAPI.md#GetTenantsV1ParameterTenantGet) | **Get** /v1/parameter/tenant | Get Tenants



## GetDeviceIdByNameV1ParameterDeviceIdGet

> Device GetDeviceIdByNameV1ParameterDeviceIdGet(ctx).DeviceName(deviceName).Execute()

Get Device ID by Name



### Example

```go
package main

import (
	"context"
	"fmt"
	"os"
	openapiclient "github.com/nvidia/nv-config-manager/bindings/go/temporal"
)

func main() {
	deviceName := "deviceName_example" // string | 

	configuration := openapiclient.NewConfiguration()
	apiClient := openapiclient.NewAPIClient(configuration)
	resp, r, err := apiClient.ParametersAPI.GetDeviceIdByNameV1ParameterDeviceIdGet(context.Background()).DeviceName(deviceName).Execute()
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error when calling `ParametersAPI.GetDeviceIdByNameV1ParameterDeviceIdGet``: %v\n", err)
		fmt.Fprintf(os.Stderr, "Full HTTP response: %v\n", r)
	}
	// response from `GetDeviceIdByNameV1ParameterDeviceIdGet`: Device
	fmt.Fprintf(os.Stdout, "Response from `ParametersAPI.GetDeviceIdByNameV1ParameterDeviceIdGet`: %v\n", resp)
}
```

### Path Parameters



### Other Parameters

Other parameters are passed through a pointer to a apiGetDeviceIdByNameV1ParameterDeviceIdGetRequest struct via the builder pattern


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **deviceName** | **string** |  | 

### Return type

[**Device**](Device.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints)
[[Back to Model list]](../README.md#documentation-for-models)
[[Back to README]](../README.md)


## GetDevicePasswordUsersV1ParameterDeviceDeviceIdPasswordUsersGet

> []Secret GetDevicePasswordUsersV1ParameterDeviceDeviceIdPasswordUsersGet(ctx, deviceId).Execute()

Get Device Password Users



### Example

```go
package main

import (
	"context"
	"fmt"
	"os"
	openapiclient "github.com/nvidia/nv-config-manager/bindings/go/temporal"
)

func main() {
	deviceId := "deviceId_example" // string | 

	configuration := openapiclient.NewConfiguration()
	apiClient := openapiclient.NewAPIClient(configuration)
	resp, r, err := apiClient.ParametersAPI.GetDevicePasswordUsersV1ParameterDeviceDeviceIdPasswordUsersGet(context.Background(), deviceId).Execute()
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error when calling `ParametersAPI.GetDevicePasswordUsersV1ParameterDeviceDeviceIdPasswordUsersGet``: %v\n", err)
		fmt.Fprintf(os.Stderr, "Full HTTP response: %v\n", r)
	}
	// response from `GetDevicePasswordUsersV1ParameterDeviceDeviceIdPasswordUsersGet`: []Secret
	fmt.Fprintf(os.Stdout, "Response from `ParametersAPI.GetDevicePasswordUsersV1ParameterDeviceDeviceIdPasswordUsersGet`: %v\n", resp)
}
```

### Path Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
**ctx** | **context.Context** | context for authentication, logging, cancellation, deadlines, tracing, etc.
**deviceId** | **string** |  | 

### Other Parameters

Other parameters are passed through a pointer to a apiGetDevicePasswordUsersV1ParameterDeviceDeviceIdPasswordUsersGetRequest struct via the builder pattern


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------


### Return type

[**[]Secret**](Secret.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints)
[[Back to Model list]](../README.md#documentation-for-models)
[[Back to README]](../README.md)


## GetDeviceSecretsV1ParameterDeviceDeviceIdSecretsGet

> []Secret GetDeviceSecretsV1ParameterDeviceDeviceIdSecretsGet(ctx, deviceId).Execute()

Get Device Secrets



### Example

```go
package main

import (
	"context"
	"fmt"
	"os"
	openapiclient "github.com/nvidia/nv-config-manager/bindings/go/temporal"
)

func main() {
	deviceId := "deviceId_example" // string | 

	configuration := openapiclient.NewConfiguration()
	apiClient := openapiclient.NewAPIClient(configuration)
	resp, r, err := apiClient.ParametersAPI.GetDeviceSecretsV1ParameterDeviceDeviceIdSecretsGet(context.Background(), deviceId).Execute()
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error when calling `ParametersAPI.GetDeviceSecretsV1ParameterDeviceDeviceIdSecretsGet``: %v\n", err)
		fmt.Fprintf(os.Stderr, "Full HTTP response: %v\n", r)
	}
	// response from `GetDeviceSecretsV1ParameterDeviceDeviceIdSecretsGet`: []Secret
	fmt.Fprintf(os.Stdout, "Response from `ParametersAPI.GetDeviceSecretsV1ParameterDeviceDeviceIdSecretsGet`: %v\n", resp)
}
```

### Path Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
**ctx** | **context.Context** | context for authentication, logging, cancellation, deadlines, tracing, etc.
**deviceId** | **string** |  | 

### Other Parameters

Other parameters are passed through a pointer to a apiGetDeviceSecretsV1ParameterDeviceDeviceIdSecretsGetRequest struct via the builder pattern


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------


### Return type

[**[]Secret**](Secret.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints)
[[Back to Model list]](../README.md#documentation-for-models)
[[Back to README]](../README.md)


## GetDeviceUsersWithVersionsV1ParameterDeviceDeviceIdSecretTypesGet

> []*string GetDeviceUsersWithVersionsV1ParameterDeviceDeviceIdSecretTypesGet(ctx, deviceId).Execute()

Get Secret Types for Device



### Example

```go
package main

import (
	"context"
	"fmt"
	"os"
	openapiclient "github.com/nvidia/nv-config-manager/bindings/go/temporal"
)

func main() {
	deviceId := "deviceId_example" // string | 

	configuration := openapiclient.NewConfiguration()
	apiClient := openapiclient.NewAPIClient(configuration)
	resp, r, err := apiClient.ParametersAPI.GetDeviceUsersWithVersionsV1ParameterDeviceDeviceIdSecretTypesGet(context.Background(), deviceId).Execute()
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error when calling `ParametersAPI.GetDeviceUsersWithVersionsV1ParameterDeviceDeviceIdSecretTypesGet``: %v\n", err)
		fmt.Fprintf(os.Stderr, "Full HTTP response: %v\n", r)
	}
	// response from `GetDeviceUsersWithVersionsV1ParameterDeviceDeviceIdSecretTypesGet`: []*string
	fmt.Fprintf(os.Stdout, "Response from `ParametersAPI.GetDeviceUsersWithVersionsV1ParameterDeviceDeviceIdSecretTypesGet`: %v\n", resp)
}
```

### Path Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
**ctx** | **context.Context** | context for authentication, logging, cancellation, deadlines, tracing, etc.
**deviceId** | **string** |  | 

### Other Parameters

Other parameters are passed through a pointer to a apiGetDeviceUsersWithVersionsV1ParameterDeviceDeviceIdSecretTypesGetRequest struct via the builder pattern


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------


### Return type

**[]*string**

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints)
[[Back to Model list]](../README.md#documentation-for-models)
[[Back to README]](../README.md)


## GetDevicesV1ParameterDeviceGet

> []Device GetDevicesV1ParameterDeviceGet(ctx).Site(site).Status(status).Role(role).Tenant(tenant).DeviceTypeId(deviceTypeId).Manufacturer(manufacturer).Platform(platform).ManagedOnly(managedOnly).Execute()

Get Devices



### Example

```go
package main

import (
	"context"
	"fmt"
	"os"
	openapiclient "github.com/nvidia/nv-config-manager/bindings/go/temporal"
)

func main() {
	site := []*string{"Inner_example"} // []*string |  (optional)
	status := []string{"Inner_example"} // []string |  (optional)
	role := []string{"Inner_example"} // []string |  (optional)
	tenant := []string{"Inner_example"} // []string |  (optional)
	deviceTypeId := []string{"Inner_example"} // []string |  (optional)
	manufacturer := []string{"Inner_example"} // []string |  (optional)
	platform := []string{"Inner_example"} // []string |  (optional)
	managedOnly := true // bool | Limit to NVIDIA Config Manager-managed devices (optional) (default to false)

	configuration := openapiclient.NewConfiguration()
	apiClient := openapiclient.NewAPIClient(configuration)
	resp, r, err := apiClient.ParametersAPI.GetDevicesV1ParameterDeviceGet(context.Background()).Site(site).Status(status).Role(role).Tenant(tenant).DeviceTypeId(deviceTypeId).Manufacturer(manufacturer).Platform(platform).ManagedOnly(managedOnly).Execute()
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error when calling `ParametersAPI.GetDevicesV1ParameterDeviceGet``: %v\n", err)
		fmt.Fprintf(os.Stderr, "Full HTTP response: %v\n", r)
	}
	// response from `GetDevicesV1ParameterDeviceGet`: []Device
	fmt.Fprintf(os.Stdout, "Response from `ParametersAPI.GetDevicesV1ParameterDeviceGet`: %v\n", resp)
}
```

### Path Parameters



### Other Parameters

Other parameters are passed through a pointer to a apiGetDevicesV1ParameterDeviceGetRequest struct via the builder pattern


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **site** | **[]string** |  | 
 **status** | **[]string** |  | 
 **role** | **[]string** |  | 
 **tenant** | **[]string** |  | 
 **deviceTypeId** | **[]string** |  | 
 **manufacturer** | **[]string** |  | 
 **platform** | **[]string** |  | 
 **managedOnly** | **bool** | Limit to NVIDIA Config Manager-managed devices | [default to false]

### Return type

[**[]Device**](Device.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints)
[[Back to Model list]](../README.md#documentation-for-models)
[[Back to README]](../README.md)


## GetDiagnosticsCommandsV1ParameterDiagnosticsCommandsGet

> []CommandEntry GetDiagnosticsCommandsV1ParameterDiagnosticsCommandsGet(ctx).Platform(platform).Execute()

Get Diagnostics Commands



### Example

```go
package main

import (
	"context"
	"fmt"
	"os"
	openapiclient "github.com/nvidia/nv-config-manager/bindings/go/temporal"
)

func main() {
	platform := []string{"Inner_example"} // []string |  (optional)

	configuration := openapiclient.NewConfiguration()
	apiClient := openapiclient.NewAPIClient(configuration)
	resp, r, err := apiClient.ParametersAPI.GetDiagnosticsCommandsV1ParameterDiagnosticsCommandsGet(context.Background()).Platform(platform).Execute()
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error when calling `ParametersAPI.GetDiagnosticsCommandsV1ParameterDiagnosticsCommandsGet``: %v\n", err)
		fmt.Fprintf(os.Stderr, "Full HTTP response: %v\n", r)
	}
	// response from `GetDiagnosticsCommandsV1ParameterDiagnosticsCommandsGet`: []CommandEntry
	fmt.Fprintf(os.Stdout, "Response from `ParametersAPI.GetDiagnosticsCommandsV1ParameterDiagnosticsCommandsGet`: %v\n", resp)
}
```

### Path Parameters



### Other Parameters

Other parameters are passed through a pointer to a apiGetDiagnosticsCommandsV1ParameterDiagnosticsCommandsGetRequest struct via the builder pattern


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **platform** | **[]string** |  | 

### Return type

[**[]CommandEntry**](CommandEntry.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints)
[[Back to Model list]](../README.md#documentation-for-models)
[[Back to README]](../README.md)


## GetLocationsV1ParameterLocationGet

> []Location GetLocationsV1ParameterLocationGet(ctx).LocationType(locationType).Execute()

Get Locations



### Example

```go
package main

import (
	"context"
	"fmt"
	"os"
	openapiclient "github.com/nvidia/nv-config-manager/bindings/go/temporal"
)

func main() {
	locationType := []string{"Inner_example"} // []string |  (optional)

	configuration := openapiclient.NewConfiguration()
	apiClient := openapiclient.NewAPIClient(configuration)
	resp, r, err := apiClient.ParametersAPI.GetLocationsV1ParameterLocationGet(context.Background()).LocationType(locationType).Execute()
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error when calling `ParametersAPI.GetLocationsV1ParameterLocationGet``: %v\n", err)
		fmt.Fprintf(os.Stderr, "Full HTTP response: %v\n", r)
	}
	// response from `GetLocationsV1ParameterLocationGet`: []Location
	fmt.Fprintf(os.Stdout, "Response from `ParametersAPI.GetLocationsV1ParameterLocationGet`: %v\n", resp)
}
```

### Path Parameters



### Other Parameters

Other parameters are passed through a pointer to a apiGetLocationsV1ParameterLocationGetRequest struct via the builder pattern


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **locationType** | **[]string** |  | 

### Return type

[**[]Location**](Location.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints)
[[Back to Model list]](../README.md#documentation-for-models)
[[Back to README]](../README.md)


## GetNamespaceTagsV1ParameterNamespaceTagGet

> []Tag GetNamespaceTagsV1ParameterNamespaceTagGet(ctx).Location(location).Execute()

Get Namespace Tags



### Example

```go
package main

import (
	"context"
	"fmt"
	"os"
	openapiclient "github.com/nvidia/nv-config-manager/bindings/go/temporal"
)

func main() {
	location := "location_example" // string | Limit to namespace tags at this location (optional)

	configuration := openapiclient.NewConfiguration()
	apiClient := openapiclient.NewAPIClient(configuration)
	resp, r, err := apiClient.ParametersAPI.GetNamespaceTagsV1ParameterNamespaceTagGet(context.Background()).Location(location).Execute()
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error when calling `ParametersAPI.GetNamespaceTagsV1ParameterNamespaceTagGet``: %v\n", err)
		fmt.Fprintf(os.Stderr, "Full HTTP response: %v\n", r)
	}
	// response from `GetNamespaceTagsV1ParameterNamespaceTagGet`: []Tag
	fmt.Fprintf(os.Stdout, "Response from `ParametersAPI.GetNamespaceTagsV1ParameterNamespaceTagGet`: %v\n", resp)
}
```

### Path Parameters



### Other Parameters

Other parameters are passed through a pointer to a apiGetNamespaceTagsV1ParameterNamespaceTagGetRequest struct via the builder pattern


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **location** | **string** | Limit to namespace tags at this location | 

### Return type

[**[]Tag**](Tag.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints)
[[Back to Model list]](../README.md#documentation-for-models)
[[Back to README]](../README.md)


## GetRolesV1ParameterRoleGet

> []Role GetRolesV1ParameterRoleGet(ctx).ManagedOnly(managedOnly).Execute()

Get Roles



### Example

```go
package main

import (
	"context"
	"fmt"
	"os"
	openapiclient "github.com/nvidia/nv-config-manager/bindings/go/temporal"
)

func main() {
	managedOnly := true // bool | Limit to roles with managed devices (optional) (default to false)

	configuration := openapiclient.NewConfiguration()
	apiClient := openapiclient.NewAPIClient(configuration)
	resp, r, err := apiClient.ParametersAPI.GetRolesV1ParameterRoleGet(context.Background()).ManagedOnly(managedOnly).Execute()
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error when calling `ParametersAPI.GetRolesV1ParameterRoleGet``: %v\n", err)
		fmt.Fprintf(os.Stderr, "Full HTTP response: %v\n", r)
	}
	// response from `GetRolesV1ParameterRoleGet`: []Role
	fmt.Fprintf(os.Stdout, "Response from `ParametersAPI.GetRolesV1ParameterRoleGet`: %v\n", resp)
}
```

### Path Parameters



### Other Parameters

Other parameters are passed through a pointer to a apiGetRolesV1ParameterRoleGetRequest struct via the builder pattern


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **managedOnly** | **bool** | Limit to roles with managed devices | [default to false]

### Return type

[**[]Role**](Role.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints)
[[Back to Model list]](../README.md#documentation-for-models)
[[Back to README]](../README.md)


## GetSitesV1ParameterSiteGet

> []Location GetSitesV1ParameterSiteGet(ctx).Execute()

Get Sites



### Example

```go
package main

import (
	"context"
	"fmt"
	"os"
	openapiclient "github.com/nvidia/nv-config-manager/bindings/go/temporal"
)

func main() {

	configuration := openapiclient.NewConfiguration()
	apiClient := openapiclient.NewAPIClient(configuration)
	resp, r, err := apiClient.ParametersAPI.GetSitesV1ParameterSiteGet(context.Background()).Execute()
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error when calling `ParametersAPI.GetSitesV1ParameterSiteGet``: %v\n", err)
		fmt.Fprintf(os.Stderr, "Full HTTP response: %v\n", r)
	}
	// response from `GetSitesV1ParameterSiteGet`: []Location
	fmt.Fprintf(os.Stdout, "Response from `ParametersAPI.GetSitesV1ParameterSiteGet`: %v\n", resp)
}
```

### Path Parameters

This endpoint does not need any parameter.

### Other Parameters

Other parameters are passed through a pointer to a apiGetSitesV1ParameterSiteGetRequest struct via the builder pattern


### Return type

[**[]Location**](Location.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints)
[[Back to Model list]](../README.md#documentation-for-models)
[[Back to README]](../README.md)


## GetStatusesV1ParameterStatusGet

> []Status GetStatusesV1ParameterStatusGet(ctx).ContentType(contentType).Execute()

Get Statuses



### Example

```go
package main

import (
	"context"
	"fmt"
	"os"
	openapiclient "github.com/nvidia/nv-config-manager/bindings/go/temporal"
)

func main() {
	contentType := "contentType_example" // string | Filter by content type (e.g. dcim.device, circuits.circuit) (optional)

	configuration := openapiclient.NewConfiguration()
	apiClient := openapiclient.NewAPIClient(configuration)
	resp, r, err := apiClient.ParametersAPI.GetStatusesV1ParameterStatusGet(context.Background()).ContentType(contentType).Execute()
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error when calling `ParametersAPI.GetStatusesV1ParameterStatusGet``: %v\n", err)
		fmt.Fprintf(os.Stderr, "Full HTTP response: %v\n", r)
	}
	// response from `GetStatusesV1ParameterStatusGet`: []Status
	fmt.Fprintf(os.Stdout, "Response from `ParametersAPI.GetStatusesV1ParameterStatusGet`: %v\n", resp)
}
```

### Path Parameters



### Other Parameters

Other parameters are passed through a pointer to a apiGetStatusesV1ParameterStatusGetRequest struct via the builder pattern


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **contentType** | **string** | Filter by content type (e.g. dcim.device, circuits.circuit) | 

### Return type

[**[]Status**](Status.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints)
[[Back to Model list]](../README.md#documentation-for-models)
[[Back to README]](../README.md)


## GetTenantsV1ParameterTenantGet

> []Tenant GetTenantsV1ParameterTenantGet(ctx).ManagedOnly(managedOnly).Execute()

Get Tenants



### Example

```go
package main

import (
	"context"
	"fmt"
	"os"
	openapiclient "github.com/nvidia/nv-config-manager/bindings/go/temporal"
)

func main() {
	managedOnly := true // bool | Limit to tenants with managed devices (optional) (default to false)

	configuration := openapiclient.NewConfiguration()
	apiClient := openapiclient.NewAPIClient(configuration)
	resp, r, err := apiClient.ParametersAPI.GetTenantsV1ParameterTenantGet(context.Background()).ManagedOnly(managedOnly).Execute()
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error when calling `ParametersAPI.GetTenantsV1ParameterTenantGet``: %v\n", err)
		fmt.Fprintf(os.Stderr, "Full HTTP response: %v\n", r)
	}
	// response from `GetTenantsV1ParameterTenantGet`: []Tenant
	fmt.Fprintf(os.Stdout, "Response from `ParametersAPI.GetTenantsV1ParameterTenantGet`: %v\n", resp)
}
```

### Path Parameters



### Other Parameters

Other parameters are passed through a pointer to a apiGetTenantsV1ParameterTenantGetRequest struct via the builder pattern


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **managedOnly** | **bool** | Limit to tenants with managed devices | [default to false]

### Return type

[**[]Tenant**](Tenant.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints)
[[Back to Model list]](../README.md#documentation-for-models)
[[Back to README]](../README.md)

