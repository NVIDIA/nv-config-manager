# DeviceCableValidationInput

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**Device** | Pointer to [**NullableNetworkDeviceData**](NetworkDeviceData.md) |  | [optional] 
**DeviceId** | **string** |  | 
**IgnoreNoNeighbor** | Pointer to **bool** |  | [optional] [default to false]

## Methods

### NewDeviceCableValidationInput

`func NewDeviceCableValidationInput(deviceId string, ) *DeviceCableValidationInput`

NewDeviceCableValidationInput instantiates a new DeviceCableValidationInput object
This constructor will assign default values to properties that have it defined,
and makes sure properties required by API are set, but the set of arguments
will change when the set of required properties is changed

### NewDeviceCableValidationInputWithDefaults

`func NewDeviceCableValidationInputWithDefaults() *DeviceCableValidationInput`

NewDeviceCableValidationInputWithDefaults instantiates a new DeviceCableValidationInput object
This constructor will only assign default values to properties that have it defined,
but it doesn't guarantee that properties required by API are set

### GetDevice

`func (o *DeviceCableValidationInput) GetDevice() NetworkDeviceData`

GetDevice returns the Device field if non-nil, zero value otherwise.

### GetDeviceOk

`func (o *DeviceCableValidationInput) GetDeviceOk() (*NetworkDeviceData, bool)`

GetDeviceOk returns a tuple with the Device field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetDevice

`func (o *DeviceCableValidationInput) SetDevice(v NetworkDeviceData)`

SetDevice sets Device field to given value.

### HasDevice

`func (o *DeviceCableValidationInput) HasDevice() bool`

HasDevice returns a boolean if a field has been set.

### SetDeviceNil

`func (o *DeviceCableValidationInput) SetDeviceNil(b bool)`

 SetDeviceNil sets the value for Device to be an explicit nil

### UnsetDevice
`func (o *DeviceCableValidationInput) UnsetDevice()`

UnsetDevice ensures that no value is present for Device, not even an explicit nil
### GetDeviceId

`func (o *DeviceCableValidationInput) GetDeviceId() string`

GetDeviceId returns the DeviceId field if non-nil, zero value otherwise.

### GetDeviceIdOk

`func (o *DeviceCableValidationInput) GetDeviceIdOk() (*string, bool)`

GetDeviceIdOk returns a tuple with the DeviceId field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetDeviceId

`func (o *DeviceCableValidationInput) SetDeviceId(v string)`

SetDeviceId sets DeviceId field to given value.


### GetIgnoreNoNeighbor

`func (o *DeviceCableValidationInput) GetIgnoreNoNeighbor() bool`

GetIgnoreNoNeighbor returns the IgnoreNoNeighbor field if non-nil, zero value otherwise.

### GetIgnoreNoNeighborOk

`func (o *DeviceCableValidationInput) GetIgnoreNoNeighborOk() (*bool, bool)`

GetIgnoreNoNeighborOk returns a tuple with the IgnoreNoNeighbor field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetIgnoreNoNeighbor

`func (o *DeviceCableValidationInput) SetIgnoreNoNeighbor(v bool)`

SetIgnoreNoNeighbor sets IgnoreNoNeighbor field to given value.

### HasIgnoreNoNeighbor

`func (o *DeviceCableValidationInput) HasIgnoreNoNeighbor() bool`

HasIgnoreNoNeighbor returns a boolean if a field has been set.


[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


