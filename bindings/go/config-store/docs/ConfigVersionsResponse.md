# ConfigVersionsResponse

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**Device** | Pointer to [**NullableDeviceMetadata**](DeviceMetadata.md) |  | [optional] 
**DeviceUuid** | **string** | Device UUID | 
**Filename** | **string** | File name | 
**Versions** | [**[]ConfigVersionResponse**](ConfigVersionResponse.md) | List of versions | 

## Methods

### NewConfigVersionsResponse

`func NewConfigVersionsResponse(deviceUuid string, filename string, versions []ConfigVersionResponse, ) *ConfigVersionsResponse`

NewConfigVersionsResponse instantiates a new ConfigVersionsResponse object
This constructor will assign default values to properties that have it defined,
and makes sure properties required by API are set, but the set of arguments
will change when the set of required properties is changed

### NewConfigVersionsResponseWithDefaults

`func NewConfigVersionsResponseWithDefaults() *ConfigVersionsResponse`

NewConfigVersionsResponseWithDefaults instantiates a new ConfigVersionsResponse object
This constructor will only assign default values to properties that have it defined,
but it doesn't guarantee that properties required by API are set

### GetDevice

`func (o *ConfigVersionsResponse) GetDevice() DeviceMetadata`

GetDevice returns the Device field if non-nil, zero value otherwise.

### GetDeviceOk

`func (o *ConfigVersionsResponse) GetDeviceOk() (*DeviceMetadata, bool)`

GetDeviceOk returns a tuple with the Device field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetDevice

`func (o *ConfigVersionsResponse) SetDevice(v DeviceMetadata)`

SetDevice sets Device field to given value.

### HasDevice

`func (o *ConfigVersionsResponse) HasDevice() bool`

HasDevice returns a boolean if a field has been set.

### SetDeviceNil

`func (o *ConfigVersionsResponse) SetDeviceNil(b bool)`

 SetDeviceNil sets the value for Device to be an explicit nil

### UnsetDevice
`func (o *ConfigVersionsResponse) UnsetDevice()`

UnsetDevice ensures that no value is present for Device, not even an explicit nil
### GetDeviceUuid

`func (o *ConfigVersionsResponse) GetDeviceUuid() string`

GetDeviceUuid returns the DeviceUuid field if non-nil, zero value otherwise.

### GetDeviceUuidOk

`func (o *ConfigVersionsResponse) GetDeviceUuidOk() (*string, bool)`

GetDeviceUuidOk returns a tuple with the DeviceUuid field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetDeviceUuid

`func (o *ConfigVersionsResponse) SetDeviceUuid(v string)`

SetDeviceUuid sets DeviceUuid field to given value.


### GetFilename

`func (o *ConfigVersionsResponse) GetFilename() string`

GetFilename returns the Filename field if non-nil, zero value otherwise.

### GetFilenameOk

`func (o *ConfigVersionsResponse) GetFilenameOk() (*string, bool)`

GetFilenameOk returns a tuple with the Filename field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetFilename

`func (o *ConfigVersionsResponse) SetFilename(v string)`

SetFilename sets Filename field to given value.


### GetVersions

`func (o *ConfigVersionsResponse) GetVersions() []ConfigVersionResponse`

GetVersions returns the Versions field if non-nil, zero value otherwise.

### GetVersionsOk

`func (o *ConfigVersionsResponse) GetVersionsOk() (*[]ConfigVersionResponse, bool)`

GetVersionsOk returns a tuple with the Versions field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetVersions

`func (o *ConfigVersionsResponse) SetVersions(v []ConfigVersionResponse)`

SetVersions sets Versions field to given value.



[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


