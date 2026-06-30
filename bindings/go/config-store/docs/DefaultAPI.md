# \DefaultAPI

All URIs are relative to *http://localhost*

Method | HTTP request | Description
------------- | ------------- | -------------
[**WhoamiWhoamiGet**](DefaultAPI.md#WhoamiWhoamiGet) | **Get** /whoami | Current User Info



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
	openapiclient "github.com/nvidia/nv-config-manager/bindings/go/config-store"
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

