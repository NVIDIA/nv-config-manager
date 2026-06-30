# BatchConfigResponse

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**Created** | [**[]ConfigVersionResponse**](ConfigVersionResponse.md) | Successfully created/updated files | 
**Skipped** | Pointer to **[]string** | Paths that had no changes | [optional] 

## Methods

### NewBatchConfigResponse

`func NewBatchConfigResponse(created []ConfigVersionResponse, ) *BatchConfigResponse`

NewBatchConfigResponse instantiates a new BatchConfigResponse object
This constructor will assign default values to properties that have it defined,
and makes sure properties required by API are set, but the set of arguments
will change when the set of required properties is changed

### NewBatchConfigResponseWithDefaults

`func NewBatchConfigResponseWithDefaults() *BatchConfigResponse`

NewBatchConfigResponseWithDefaults instantiates a new BatchConfigResponse object
This constructor will only assign default values to properties that have it defined,
but it doesn't guarantee that properties required by API are set

### GetCreated

`func (o *BatchConfigResponse) GetCreated() []ConfigVersionResponse`

GetCreated returns the Created field if non-nil, zero value otherwise.

### GetCreatedOk

`func (o *BatchConfigResponse) GetCreatedOk() (*[]ConfigVersionResponse, bool)`

GetCreatedOk returns a tuple with the Created field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetCreated

`func (o *BatchConfigResponse) SetCreated(v []ConfigVersionResponse)`

SetCreated sets Created field to given value.


### GetSkipped

`func (o *BatchConfigResponse) GetSkipped() []string`

GetSkipped returns the Skipped field if non-nil, zero value otherwise.

### GetSkippedOk

`func (o *BatchConfigResponse) GetSkippedOk() (*[]string, bool)`

GetSkippedOk returns a tuple with the Skipped field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetSkipped

`func (o *BatchConfigResponse) SetSkipped(v []string)`

SetSkipped sets Skipped field to given value.

### HasSkipped

`func (o *BatchConfigResponse) HasSkipped() bool`

HasSkipped returns a boolean if a field has been set.


[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


