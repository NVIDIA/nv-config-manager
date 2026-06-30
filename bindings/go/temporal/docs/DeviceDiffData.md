# DeviceDiffData

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**CommitId** | Pointer to **NullableString** |  | [optional] 
**Device** | [**NetworkDeviceData**](NetworkDeviceData.md) |  | 
**Diff** | Pointer to **NullableString** |  | [optional] 
**Error** | Pointer to **NullableString** |  | [optional] 
**IntendedConfig** | Pointer to **NullableString** |  | [optional] 

## Methods

### NewDeviceDiffData

`func NewDeviceDiffData(device NetworkDeviceData, ) *DeviceDiffData`

NewDeviceDiffData instantiates a new DeviceDiffData object
This constructor will assign default values to properties that have it defined,
and makes sure properties required by API are set, but the set of arguments
will change when the set of required properties is changed

### NewDeviceDiffDataWithDefaults

`func NewDeviceDiffDataWithDefaults() *DeviceDiffData`

NewDeviceDiffDataWithDefaults instantiates a new DeviceDiffData object
This constructor will only assign default values to properties that have it defined,
but it doesn't guarantee that properties required by API are set

### GetCommitId

`func (o *DeviceDiffData) GetCommitId() string`

GetCommitId returns the CommitId field if non-nil, zero value otherwise.

### GetCommitIdOk

`func (o *DeviceDiffData) GetCommitIdOk() (*string, bool)`

GetCommitIdOk returns a tuple with the CommitId field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetCommitId

`func (o *DeviceDiffData) SetCommitId(v string)`

SetCommitId sets CommitId field to given value.

### HasCommitId

`func (o *DeviceDiffData) HasCommitId() bool`

HasCommitId returns a boolean if a field has been set.

### SetCommitIdNil

`func (o *DeviceDiffData) SetCommitIdNil(b bool)`

 SetCommitIdNil sets the value for CommitId to be an explicit nil

### UnsetCommitId
`func (o *DeviceDiffData) UnsetCommitId()`

UnsetCommitId ensures that no value is present for CommitId, not even an explicit nil
### GetDevice

`func (o *DeviceDiffData) GetDevice() NetworkDeviceData`

GetDevice returns the Device field if non-nil, zero value otherwise.

### GetDeviceOk

`func (o *DeviceDiffData) GetDeviceOk() (*NetworkDeviceData, bool)`

GetDeviceOk returns a tuple with the Device field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetDevice

`func (o *DeviceDiffData) SetDevice(v NetworkDeviceData)`

SetDevice sets Device field to given value.


### GetDiff

`func (o *DeviceDiffData) GetDiff() string`

GetDiff returns the Diff field if non-nil, zero value otherwise.

### GetDiffOk

`func (o *DeviceDiffData) GetDiffOk() (*string, bool)`

GetDiffOk returns a tuple with the Diff field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetDiff

`func (o *DeviceDiffData) SetDiff(v string)`

SetDiff sets Diff field to given value.

### HasDiff

`func (o *DeviceDiffData) HasDiff() bool`

HasDiff returns a boolean if a field has been set.

### SetDiffNil

`func (o *DeviceDiffData) SetDiffNil(b bool)`

 SetDiffNil sets the value for Diff to be an explicit nil

### UnsetDiff
`func (o *DeviceDiffData) UnsetDiff()`

UnsetDiff ensures that no value is present for Diff, not even an explicit nil
### GetError

`func (o *DeviceDiffData) GetError() string`

GetError returns the Error field if non-nil, zero value otherwise.

### GetErrorOk

`func (o *DeviceDiffData) GetErrorOk() (*string, bool)`

GetErrorOk returns a tuple with the Error field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetError

`func (o *DeviceDiffData) SetError(v string)`

SetError sets Error field to given value.

### HasError

`func (o *DeviceDiffData) HasError() bool`

HasError returns a boolean if a field has been set.

### SetErrorNil

`func (o *DeviceDiffData) SetErrorNil(b bool)`

 SetErrorNil sets the value for Error to be an explicit nil

### UnsetError
`func (o *DeviceDiffData) UnsetError()`

UnsetError ensures that no value is present for Error, not even an explicit nil
### GetIntendedConfig

`func (o *DeviceDiffData) GetIntendedConfig() string`

GetIntendedConfig returns the IntendedConfig field if non-nil, zero value otherwise.

### GetIntendedConfigOk

`func (o *DeviceDiffData) GetIntendedConfigOk() (*string, bool)`

GetIntendedConfigOk returns a tuple with the IntendedConfig field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetIntendedConfig

`func (o *DeviceDiffData) SetIntendedConfig(v string)`

SetIntendedConfig sets IntendedConfig field to given value.

### HasIntendedConfig

`func (o *DeviceDiffData) HasIntendedConfig() bool`

HasIntendedConfig returns a boolean if a field has been set.

### SetIntendedConfigNil

`func (o *DeviceDiffData) SetIntendedConfigNil(b bool)`

 SetIntendedConfigNil sets the value for IntendedConfig to be an explicit nil

### UnsetIntendedConfig
`func (o *DeviceDiffData) UnsetIntendedConfig()`

UnsetIntendedConfig ensures that no value is present for IntendedConfig, not even an explicit nil

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


