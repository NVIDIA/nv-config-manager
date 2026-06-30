# BatchDeployInput

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**BatchDevices** | [**[]DeviceDiffData**](DeviceDiffData.md) |  | 
**BatchNumber** | Pointer to **NullableInt32** |  | [optional] 
**CommitConfirm** | Pointer to **bool** |  | [optional] [default to true]
**DiffGroup** | [**DiffGroup**](DiffGroup.md) |  | 
**ParentWorkflowId** | **string** |  | 

## Methods

### NewBatchDeployInput

`func NewBatchDeployInput(batchDevices []DeviceDiffData, diffGroup DiffGroup, parentWorkflowId string, ) *BatchDeployInput`

NewBatchDeployInput instantiates a new BatchDeployInput object
This constructor will assign default values to properties that have it defined,
and makes sure properties required by API are set, but the set of arguments
will change when the set of required properties is changed

### NewBatchDeployInputWithDefaults

`func NewBatchDeployInputWithDefaults() *BatchDeployInput`

NewBatchDeployInputWithDefaults instantiates a new BatchDeployInput object
This constructor will only assign default values to properties that have it defined,
but it doesn't guarantee that properties required by API are set

### GetBatchDevices

`func (o *BatchDeployInput) GetBatchDevices() []DeviceDiffData`

GetBatchDevices returns the BatchDevices field if non-nil, zero value otherwise.

### GetBatchDevicesOk

`func (o *BatchDeployInput) GetBatchDevicesOk() (*[]DeviceDiffData, bool)`

GetBatchDevicesOk returns a tuple with the BatchDevices field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetBatchDevices

`func (o *BatchDeployInput) SetBatchDevices(v []DeviceDiffData)`

SetBatchDevices sets BatchDevices field to given value.


### GetBatchNumber

`func (o *BatchDeployInput) GetBatchNumber() int32`

GetBatchNumber returns the BatchNumber field if non-nil, zero value otherwise.

### GetBatchNumberOk

`func (o *BatchDeployInput) GetBatchNumberOk() (*int32, bool)`

GetBatchNumberOk returns a tuple with the BatchNumber field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetBatchNumber

`func (o *BatchDeployInput) SetBatchNumber(v int32)`

SetBatchNumber sets BatchNumber field to given value.

### HasBatchNumber

`func (o *BatchDeployInput) HasBatchNumber() bool`

HasBatchNumber returns a boolean if a field has been set.

### SetBatchNumberNil

`func (o *BatchDeployInput) SetBatchNumberNil(b bool)`

 SetBatchNumberNil sets the value for BatchNumber to be an explicit nil

### UnsetBatchNumber
`func (o *BatchDeployInput) UnsetBatchNumber()`

UnsetBatchNumber ensures that no value is present for BatchNumber, not even an explicit nil
### GetCommitConfirm

`func (o *BatchDeployInput) GetCommitConfirm() bool`

GetCommitConfirm returns the CommitConfirm field if non-nil, zero value otherwise.

### GetCommitConfirmOk

`func (o *BatchDeployInput) GetCommitConfirmOk() (*bool, bool)`

GetCommitConfirmOk returns a tuple with the CommitConfirm field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetCommitConfirm

`func (o *BatchDeployInput) SetCommitConfirm(v bool)`

SetCommitConfirm sets CommitConfirm field to given value.

### HasCommitConfirm

`func (o *BatchDeployInput) HasCommitConfirm() bool`

HasCommitConfirm returns a boolean if a field has been set.

### GetDiffGroup

`func (o *BatchDeployInput) GetDiffGroup() DiffGroup`

GetDiffGroup returns the DiffGroup field if non-nil, zero value otherwise.

### GetDiffGroupOk

`func (o *BatchDeployInput) GetDiffGroupOk() (*DiffGroup, bool)`

GetDiffGroupOk returns a tuple with the DiffGroup field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetDiffGroup

`func (o *BatchDeployInput) SetDiffGroup(v DiffGroup)`

SetDiffGroup sets DiffGroup field to given value.


### GetParentWorkflowId

`func (o *BatchDeployInput) GetParentWorkflowId() string`

GetParentWorkflowId returns the ParentWorkflowId field if non-nil, zero value otherwise.

### GetParentWorkflowIdOk

`func (o *BatchDeployInput) GetParentWorkflowIdOk() (*string, bool)`

GetParentWorkflowIdOk returns a tuple with the ParentWorkflowId field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetParentWorkflowId

`func (o *BatchDeployInput) SetParentWorkflowId(v string)`

SetParentWorkflowId sets ParentWorkflowId field to given value.



[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


