# \CodecAPI

All URIs are relative to *http://localhost*

Method | HTTP request | Description
------------- | ------------- | -------------
[**DecodeV1CodecDecodePost**](CodecAPI.md#DecodeV1CodecDecodePost) | **Post** /v1/codec/decode | Decode payloads
[**EncodeV1CodecEncodePost**](CodecAPI.md#EncodeV1CodecEncodePost) | **Post** /v1/codec/encode | Encode payloads



## DecodeV1CodecDecodePost

> map[string]interface{} DecodeV1CodecDecodePost(ctx).Execute()

Decode payloads



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
	resp, r, err := apiClient.CodecAPI.DecodeV1CodecDecodePost(context.Background()).Execute()
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error when calling `CodecAPI.DecodeV1CodecDecodePost``: %v\n", err)
		fmt.Fprintf(os.Stderr, "Full HTTP response: %v\n", r)
	}
	// response from `DecodeV1CodecDecodePost`: map[string]interface{}
	fmt.Fprintf(os.Stdout, "Response from `CodecAPI.DecodeV1CodecDecodePost`: %v\n", resp)
}
```

### Path Parameters

This endpoint does not need any parameter.

### Other Parameters

Other parameters are passed through a pointer to a apiDecodeV1CodecDecodePostRequest struct via the builder pattern


### Return type

**map[string]interface{}**

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints)
[[Back to Model list]](../README.md#documentation-for-models)
[[Back to README]](../README.md)


## EncodeV1CodecEncodePost

> map[string]interface{} EncodeV1CodecEncodePost(ctx).Execute()

Encode payloads



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
	resp, r, err := apiClient.CodecAPI.EncodeV1CodecEncodePost(context.Background()).Execute()
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error when calling `CodecAPI.EncodeV1CodecEncodePost``: %v\n", err)
		fmt.Fprintf(os.Stderr, "Full HTTP response: %v\n", r)
	}
	// response from `EncodeV1CodecEncodePost`: map[string]interface{}
	fmt.Fprintf(os.Stdout, "Response from `CodecAPI.EncodeV1CodecEncodePost`: %v\n", resp)
}
```

### Path Parameters

This endpoint does not need any parameter.

### Other Parameters

Other parameters are passed through a pointer to a apiEncodeV1CodecEncodePostRequest struct via the builder pattern


### Return type

**map[string]interface{}**

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints)
[[Back to Model list]](../README.md#documentation-for-models)
[[Back to README]](../README.md)

