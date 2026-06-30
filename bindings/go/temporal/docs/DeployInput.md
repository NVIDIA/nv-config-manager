# DeployInput

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**CommitConfirm** | Pointer to **bool** |  | [optional] [default to true]
**DeviceId** | **string** |  | 

## Methods

### NewDeployInput

`func NewDeployInput(deviceId string, ) *DeployInput`

NewDeployInput instantiates a new DeployInput object
This constructor will assign default values to properties that have it defined,
and makes sure properties required by API are set, but the set of arguments
will change when the set of required properties is changed

### NewDeployInputWithDefaults

`func NewDeployInputWithDefaults() *DeployInput`

NewDeployInputWithDefaults instantiates a new DeployInput object
This constructor will only assign default values to properties that have it defined,
but it doesn't guarantee that properties required by API are set

### GetCommitConfirm

`func (o *DeployInput) GetCommitConfirm() bool`

GetCommitConfirm returns the CommitConfirm field if non-nil, zero value otherwise.

### GetCommitConfirmOk

`func (o *DeployInput) GetCommitConfirmOk() (*bool, bool)`

GetCommitConfirmOk returns a tuple with the CommitConfirm field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetCommitConfirm

`func (o *DeployInput) SetCommitConfirm(v bool)`

SetCommitConfirm sets CommitConfirm field to given value.

### HasCommitConfirm

`func (o *DeployInput) HasCommitConfirm() bool`

HasCommitConfirm returns a boolean if a field has been set.

### GetDeviceId

`func (o *DeployInput) GetDeviceId() string`

GetDeviceId returns the DeviceId field if non-nil, zero value otherwise.

### GetDeviceIdOk

`func (o *DeployInput) GetDeviceIdOk() (*string, bool)`

GetDeviceIdOk returns a tuple with the DeviceId field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetDeviceId

`func (o *DeployInput) SetDeviceId(v string)`

SetDeviceId sets DeviceId field to given value.



[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


