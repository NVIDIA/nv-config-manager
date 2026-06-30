# \FilesAPI

All URIs are relative to *http://localhost*

Method | HTTP request | Description
------------- | ------------- | -------------
[**ListAllFilesV1FilesGet**](FilesAPI.md#ListAllFilesV1FilesGet) | **Get** /v1/files/ | List All Files
[**ListFilesV1FilesPlatformVersionGet**](FilesAPI.md#ListFilesV1FilesPlatformVersionGet) | **Get** /v1/files/{platform}/{version}/ | List Files
[**LoadChecksumV1FilesPlatformVersionFilenameChecksumGet**](FilesAPI.md#LoadChecksumV1FilesPlatformVersionFilenameChecksumGet) | **Get** /v1/files/{platform}/{version}/{filename}/checksum | Load Checksum
[**LoadObjectV1FilesPlatformVersionFilenameGet**](FilesAPI.md#LoadObjectV1FilesPlatformVersionFilenameGet) | **Get** /v1/files/{platform}/{version}/{filename} | Load Object
[**UploadFileV1FilesPlatformVersionFilenamePost**](FilesAPI.md#UploadFileV1FilesPlatformVersionFilenamePost) | **Post** /v1/files/{platform}/{version}/{filename} | Upload File



## ListAllFilesV1FilesGet

> []ObjectInfo ListAllFilesV1FilesGet(ctx).Execute()

List All Files



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

	configuration := openapiclient.NewConfiguration()
	apiClient := openapiclient.NewAPIClient(configuration)
	resp, r, err := apiClient.FilesAPI.ListAllFilesV1FilesGet(context.Background()).Execute()
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error when calling `FilesAPI.ListAllFilesV1FilesGet``: %v\n", err)
		fmt.Fprintf(os.Stderr, "Full HTTP response: %v\n", r)
	}
	// response from `ListAllFilesV1FilesGet`: []ObjectInfo
	fmt.Fprintf(os.Stdout, "Response from `FilesAPI.ListAllFilesV1FilesGet`: %v\n", resp)
}
```

### Path Parameters

This endpoint does not need any parameter.

### Other Parameters

Other parameters are passed through a pointer to a apiListAllFilesV1FilesGetRequest struct via the builder pattern


### Return type

[**[]ObjectInfo**](ObjectInfo.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints)
[[Back to Model list]](../README.md#documentation-for-models)
[[Back to README]](../README.md)


## ListFilesV1FilesPlatformVersionGet

> []FileInfo ListFilesV1FilesPlatformVersionGet(ctx, platform, version).Execute()

List Files



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
	resp, r, err := apiClient.FilesAPI.ListFilesV1FilesPlatformVersionGet(context.Background(), platform, version).Execute()
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error when calling `FilesAPI.ListFilesV1FilesPlatformVersionGet``: %v\n", err)
		fmt.Fprintf(os.Stderr, "Full HTTP response: %v\n", r)
	}
	// response from `ListFilesV1FilesPlatformVersionGet`: []FileInfo
	fmt.Fprintf(os.Stdout, "Response from `FilesAPI.ListFilesV1FilesPlatformVersionGet`: %v\n", resp)
}
```

### Path Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
**ctx** | **context.Context** | context for authentication, logging, cancellation, deadlines, tracing, etc.
**platform** | **string** |  | 
**version** | **string** |  | 

### Other Parameters

Other parameters are passed through a pointer to a apiListFilesV1FilesPlatformVersionGetRequest struct via the builder pattern


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------



### Return type

[**[]FileInfo**](FileInfo.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints)
[[Back to Model list]](../README.md#documentation-for-models)
[[Back to README]](../README.md)


## LoadChecksumV1FilesPlatformVersionFilenameChecksumGet

> ChecksumResponse LoadChecksumV1FilesPlatformVersionFilenameChecksumGet(ctx, platform, version, filename).Execute()

Load Checksum



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
	filename := "filename_example" // string | 

	configuration := openapiclient.NewConfiguration()
	apiClient := openapiclient.NewAPIClient(configuration)
	resp, r, err := apiClient.FilesAPI.LoadChecksumV1FilesPlatformVersionFilenameChecksumGet(context.Background(), platform, version, filename).Execute()
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error when calling `FilesAPI.LoadChecksumV1FilesPlatformVersionFilenameChecksumGet``: %v\n", err)
		fmt.Fprintf(os.Stderr, "Full HTTP response: %v\n", r)
	}
	// response from `LoadChecksumV1FilesPlatformVersionFilenameChecksumGet`: ChecksumResponse
	fmt.Fprintf(os.Stdout, "Response from `FilesAPI.LoadChecksumV1FilesPlatformVersionFilenameChecksumGet`: %v\n", resp)
}
```

### Path Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
**ctx** | **context.Context** | context for authentication, logging, cancellation, deadlines, tracing, etc.
**platform** | **string** |  | 
**version** | **string** |  | 
**filename** | **string** |  | 

### Other Parameters

Other parameters are passed through a pointer to a apiLoadChecksumV1FilesPlatformVersionFilenameChecksumGetRequest struct via the builder pattern


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


## LoadObjectV1FilesPlatformVersionFilenameGet

> LoadObjectV1FilesPlatformVersionFilenameGet(ctx, platform, version, filename).Execute()

Load Object



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
	filename := "filename_example" // string | 

	configuration := openapiclient.NewConfiguration()
	apiClient := openapiclient.NewAPIClient(configuration)
	r, err := apiClient.FilesAPI.LoadObjectV1FilesPlatformVersionFilenameGet(context.Background(), platform, version, filename).Execute()
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error when calling `FilesAPI.LoadObjectV1FilesPlatformVersionFilenameGet``: %v\n", err)
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
**filename** | **string** |  | 

### Other Parameters

Other parameters are passed through a pointer to a apiLoadObjectV1FilesPlatformVersionFilenameGetRequest struct via the builder pattern


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


## UploadFileV1FilesPlatformVersionFilenamePost

> string UploadFileV1FilesPlatformVersionFilenamePost(ctx, platform, version, filename).Checksum(checksum).File(file).Overwrite(overwrite).FirmwareImage(firmwareImage).Execute()

Upload File



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
	filename := "filename_example" // string | 
	checksum := "checksum_example" // string | 
	file := "file_example" // string | 
	overwrite := true // bool |  (optional) (default to false)
	firmwareImage := true // bool |  (optional) (default to false)

	configuration := openapiclient.NewConfiguration()
	apiClient := openapiclient.NewAPIClient(configuration)
	resp, r, err := apiClient.FilesAPI.UploadFileV1FilesPlatformVersionFilenamePost(context.Background(), platform, version, filename).Checksum(checksum).File(file).Overwrite(overwrite).FirmwareImage(firmwareImage).Execute()
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error when calling `FilesAPI.UploadFileV1FilesPlatformVersionFilenamePost``: %v\n", err)
		fmt.Fprintf(os.Stderr, "Full HTTP response: %v\n", r)
	}
	// response from `UploadFileV1FilesPlatformVersionFilenamePost`: string
	fmt.Fprintf(os.Stdout, "Response from `FilesAPI.UploadFileV1FilesPlatformVersionFilenamePost`: %v\n", resp)
}
```

### Path Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
**ctx** | **context.Context** | context for authentication, logging, cancellation, deadlines, tracing, etc.
**platform** | **string** |  | 
**version** | **string** |  | 
**filename** | **string** |  | 

### Other Parameters

Other parameters are passed through a pointer to a apiUploadFileV1FilesPlatformVersionFilenamePostRequest struct via the builder pattern


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------



 **checksum** | **string** |  | 
 **file** | **string** |  | 
 **overwrite** | **bool** |  | [default to false]
 **firmwareImage** | **bool** |  | [default to false]

### Return type

**string**

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: multipart/form-data
- **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints)
[[Back to Model list]](../README.md#documentation-for-models)
[[Back to README]](../README.md)

