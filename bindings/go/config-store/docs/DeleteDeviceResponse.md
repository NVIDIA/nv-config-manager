# DeleteDeviceResponse

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**DeletedVersions** | **int32** | Number of config versions deleted | 
**DeviceUuid** | **string** | Device UUID | 
**Message** | **string** | Human-readable result message | 

## Methods

### NewDeleteDeviceResponse

`func NewDeleteDeviceResponse(deletedVersions int32, deviceUuid string, message string, ) *DeleteDeviceResponse`

NewDeleteDeviceResponse instantiates a new DeleteDeviceResponse object
This constructor will assign default values to properties that have it defined,
and makes sure properties required by API are set, but the set of arguments
will change when the set of required properties is changed

### NewDeleteDeviceResponseWithDefaults

`func NewDeleteDeviceResponseWithDefaults() *DeleteDeviceResponse`

NewDeleteDeviceResponseWithDefaults instantiates a new DeleteDeviceResponse object
This constructor will only assign default values to properties that have it defined,
but it doesn't guarantee that properties required by API are set

### GetDeletedVersions

`func (o *DeleteDeviceResponse) GetDeletedVersions() int32`

GetDeletedVersions returns the DeletedVersions field if non-nil, zero value otherwise.

### GetDeletedVersionsOk

`func (o *DeleteDeviceResponse) GetDeletedVersionsOk() (*int32, bool)`

GetDeletedVersionsOk returns a tuple with the DeletedVersions field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetDeletedVersions

`func (o *DeleteDeviceResponse) SetDeletedVersions(v int32)`

SetDeletedVersions sets DeletedVersions field to given value.


### GetDeviceUuid

`func (o *DeleteDeviceResponse) GetDeviceUuid() string`

GetDeviceUuid returns the DeviceUuid field if non-nil, zero value otherwise.

### GetDeviceUuidOk

`func (o *DeleteDeviceResponse) GetDeviceUuidOk() (*string, bool)`

GetDeviceUuidOk returns a tuple with the DeviceUuid field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetDeviceUuid

`func (o *DeleteDeviceResponse) SetDeviceUuid(v string)`

SetDeviceUuid sets DeviceUuid field to given value.


### GetMessage

`func (o *DeleteDeviceResponse) GetMessage() string`

GetMessage returns the Message field if non-nil, zero value otherwise.

### GetMessageOk

`func (o *DeleteDeviceResponse) GetMessageOk() (*string, bool)`

GetMessageOk returns a tuple with the Message field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetMessage

`func (o *DeleteDeviceResponse) SetMessage(v string)`

SetMessage sets Message field to given value.



[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


