# CacheTestNotFoundResponse

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**DeviceUuid** | **string** | Device UUID | 
**Found** | Pointer to **bool** | Whether device was found | [optional] [default to false]
**Message** | **string** | Not found message | 

## Methods

### NewCacheTestNotFoundResponse

`func NewCacheTestNotFoundResponse(deviceUuid string, message string, ) *CacheTestNotFoundResponse`

NewCacheTestNotFoundResponse instantiates a new CacheTestNotFoundResponse object
This constructor will assign default values to properties that have it defined,
and makes sure properties required by API are set, but the set of arguments
will change when the set of required properties is changed

### NewCacheTestNotFoundResponseWithDefaults

`func NewCacheTestNotFoundResponseWithDefaults() *CacheTestNotFoundResponse`

NewCacheTestNotFoundResponseWithDefaults instantiates a new CacheTestNotFoundResponse object
This constructor will only assign default values to properties that have it defined,
but it doesn't guarantee that properties required by API are set

### GetDeviceUuid

`func (o *CacheTestNotFoundResponse) GetDeviceUuid() string`

GetDeviceUuid returns the DeviceUuid field if non-nil, zero value otherwise.

### GetDeviceUuidOk

`func (o *CacheTestNotFoundResponse) GetDeviceUuidOk() (*string, bool)`

GetDeviceUuidOk returns a tuple with the DeviceUuid field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetDeviceUuid

`func (o *CacheTestNotFoundResponse) SetDeviceUuid(v string)`

SetDeviceUuid sets DeviceUuid field to given value.


### GetFound

`func (o *CacheTestNotFoundResponse) GetFound() bool`

GetFound returns the Found field if non-nil, zero value otherwise.

### GetFoundOk

`func (o *CacheTestNotFoundResponse) GetFoundOk() (*bool, bool)`

GetFoundOk returns a tuple with the Found field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetFound

`func (o *CacheTestNotFoundResponse) SetFound(v bool)`

SetFound sets Found field to given value.

### HasFound

`func (o *CacheTestNotFoundResponse) HasFound() bool`

HasFound returns a boolean if a field has been set.

### GetMessage

`func (o *CacheTestNotFoundResponse) GetMessage() string`

GetMessage returns the Message field if non-nil, zero value otherwise.

### GetMessageOk

`func (o *CacheTestNotFoundResponse) GetMessageOk() (*string, bool)`

GetMessageOk returns a tuple with the Message field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetMessage

`func (o *CacheTestNotFoundResponse) SetMessage(v string)`

SetMessage sets Message field to given value.



[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


