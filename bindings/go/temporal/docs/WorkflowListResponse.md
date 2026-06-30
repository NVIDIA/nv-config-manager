# WorkflowListResponse

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**NextPageToken** | **NullableString** |  | 
**PageCount** | **int32** |  | 
**TotalCount** | **int32** |  | 
**Workflows** | [**[]WorkflowSummaryResponse**](WorkflowSummaryResponse.md) |  | 

## Methods

### NewWorkflowListResponse

`func NewWorkflowListResponse(nextPageToken NullableString, pageCount int32, totalCount int32, workflows []WorkflowSummaryResponse, ) *WorkflowListResponse`

NewWorkflowListResponse instantiates a new WorkflowListResponse object
This constructor will assign default values to properties that have it defined,
and makes sure properties required by API are set, but the set of arguments
will change when the set of required properties is changed

### NewWorkflowListResponseWithDefaults

`func NewWorkflowListResponseWithDefaults() *WorkflowListResponse`

NewWorkflowListResponseWithDefaults instantiates a new WorkflowListResponse object
This constructor will only assign default values to properties that have it defined,
but it doesn't guarantee that properties required by API are set

### GetNextPageToken

`func (o *WorkflowListResponse) GetNextPageToken() string`

GetNextPageToken returns the NextPageToken field if non-nil, zero value otherwise.

### GetNextPageTokenOk

`func (o *WorkflowListResponse) GetNextPageTokenOk() (*string, bool)`

GetNextPageTokenOk returns a tuple with the NextPageToken field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetNextPageToken

`func (o *WorkflowListResponse) SetNextPageToken(v string)`

SetNextPageToken sets NextPageToken field to given value.


### SetNextPageTokenNil

`func (o *WorkflowListResponse) SetNextPageTokenNil(b bool)`

 SetNextPageTokenNil sets the value for NextPageToken to be an explicit nil

### UnsetNextPageToken
`func (o *WorkflowListResponse) UnsetNextPageToken()`

UnsetNextPageToken ensures that no value is present for NextPageToken, not even an explicit nil
### GetPageCount

`func (o *WorkflowListResponse) GetPageCount() int32`

GetPageCount returns the PageCount field if non-nil, zero value otherwise.

### GetPageCountOk

`func (o *WorkflowListResponse) GetPageCountOk() (*int32, bool)`

GetPageCountOk returns a tuple with the PageCount field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetPageCount

`func (o *WorkflowListResponse) SetPageCount(v int32)`

SetPageCount sets PageCount field to given value.


### GetTotalCount

`func (o *WorkflowListResponse) GetTotalCount() int32`

GetTotalCount returns the TotalCount field if non-nil, zero value otherwise.

### GetTotalCountOk

`func (o *WorkflowListResponse) GetTotalCountOk() (*int32, bool)`

GetTotalCountOk returns a tuple with the TotalCount field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetTotalCount

`func (o *WorkflowListResponse) SetTotalCount(v int32)`

SetTotalCount sets TotalCount field to given value.


### GetWorkflows

`func (o *WorkflowListResponse) GetWorkflows() []WorkflowSummaryResponse`

GetWorkflows returns the Workflows field if non-nil, zero value otherwise.

### GetWorkflowsOk

`func (o *WorkflowListResponse) GetWorkflowsOk() (*[]WorkflowSummaryResponse, bool)`

GetWorkflowsOk returns a tuple with the Workflows field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetWorkflows

`func (o *WorkflowListResponse) SetWorkflows(v []WorkflowSummaryResponse)`

SetWorkflows sets Workflows field to given value.



[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


