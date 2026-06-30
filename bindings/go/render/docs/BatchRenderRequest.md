# BatchRenderRequest

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**CommitMessage** | Pointer to **NullableString** |  | [optional] 
**DeviceUuids** | **[]string** |  | 
**MaxConcurrency** | Pointer to **int32** |  | [optional] [default to 20]

## Methods

### NewBatchRenderRequest

`func NewBatchRenderRequest(deviceUuids []string, ) *BatchRenderRequest`

NewBatchRenderRequest instantiates a new BatchRenderRequest object
This constructor will assign default values to properties that have it defined,
and makes sure properties required by API are set, but the set of arguments
will change when the set of required properties is changed

### NewBatchRenderRequestWithDefaults

`func NewBatchRenderRequestWithDefaults() *BatchRenderRequest`

NewBatchRenderRequestWithDefaults instantiates a new BatchRenderRequest object
This constructor will only assign default values to properties that have it defined,
but it doesn't guarantee that properties required by API are set

### GetCommitMessage

`func (o *BatchRenderRequest) GetCommitMessage() string`

GetCommitMessage returns the CommitMessage field if non-nil, zero value otherwise.

### GetCommitMessageOk

`func (o *BatchRenderRequest) GetCommitMessageOk() (*string, bool)`

GetCommitMessageOk returns a tuple with the CommitMessage field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetCommitMessage

`func (o *BatchRenderRequest) SetCommitMessage(v string)`

SetCommitMessage sets CommitMessage field to given value.

### HasCommitMessage

`func (o *BatchRenderRequest) HasCommitMessage() bool`

HasCommitMessage returns a boolean if a field has been set.

### SetCommitMessageNil

`func (o *BatchRenderRequest) SetCommitMessageNil(b bool)`

 SetCommitMessageNil sets the value for CommitMessage to be an explicit nil

### UnsetCommitMessage
`func (o *BatchRenderRequest) UnsetCommitMessage()`

UnsetCommitMessage ensures that no value is present for CommitMessage, not even an explicit nil
### GetDeviceUuids

`func (o *BatchRenderRequest) GetDeviceUuids() []string`

GetDeviceUuids returns the DeviceUuids field if non-nil, zero value otherwise.

### GetDeviceUuidsOk

`func (o *BatchRenderRequest) GetDeviceUuidsOk() (*[]string, bool)`

GetDeviceUuidsOk returns a tuple with the DeviceUuids field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetDeviceUuids

`func (o *BatchRenderRequest) SetDeviceUuids(v []string)`

SetDeviceUuids sets DeviceUuids field to given value.


### GetMaxConcurrency

`func (o *BatchRenderRequest) GetMaxConcurrency() int32`

GetMaxConcurrency returns the MaxConcurrency field if non-nil, zero value otherwise.

### GetMaxConcurrencyOk

`func (o *BatchRenderRequest) GetMaxConcurrencyOk() (*int32, bool)`

GetMaxConcurrencyOk returns a tuple with the MaxConcurrency field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetMaxConcurrency

`func (o *BatchRenderRequest) SetMaxConcurrency(v int32)`

SetMaxConcurrency sets MaxConcurrency field to given value.

### HasMaxConcurrency

`func (o *BatchRenderRequest) HasMaxConcurrency() bool`

HasMaxConcurrency returns a boolean if a field has been set.


[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


