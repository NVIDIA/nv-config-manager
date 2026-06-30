# CacheTestFoundResponse

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**DeviceName** | **string** | Device name | 
**DeviceUuid** | **string** | Device UUID | 
**Found** | Pointer to **bool** | Whether device was found | [optional] [default to true]
**Platform** | **NullableString** |  | 
**Site** | **string** | Site name | 

## Methods

### NewCacheTestFoundResponse

`func NewCacheTestFoundResponse(deviceName string, deviceUuid string, platform NullableString, site string, ) *CacheTestFoundResponse`

NewCacheTestFoundResponse instantiates a new CacheTestFoundResponse object
This constructor will assign default values to properties that have it defined,
and makes sure properties required by API are set, but the set of arguments
will change when the set of required properties is changed

### NewCacheTestFoundResponseWithDefaults

`func NewCacheTestFoundResponseWithDefaults() *CacheTestFoundResponse`

NewCacheTestFoundResponseWithDefaults instantiates a new CacheTestFoundResponse object
This constructor will only assign default values to properties that have it defined,
but it doesn't guarantee that properties required by API are set

### GetDeviceName

`func (o *CacheTestFoundResponse) GetDeviceName() string`

GetDeviceName returns the DeviceName field if non-nil, zero value otherwise.

### GetDeviceNameOk

`func (o *CacheTestFoundResponse) GetDeviceNameOk() (*string, bool)`

GetDeviceNameOk returns a tuple with the DeviceName field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetDeviceName

`func (o *CacheTestFoundResponse) SetDeviceName(v string)`

SetDeviceName sets DeviceName field to given value.


### GetDeviceUuid

`func (o *CacheTestFoundResponse) GetDeviceUuid() string`

GetDeviceUuid returns the DeviceUuid field if non-nil, zero value otherwise.

### GetDeviceUuidOk

`func (o *CacheTestFoundResponse) GetDeviceUuidOk() (*string, bool)`

GetDeviceUuidOk returns a tuple with the DeviceUuid field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetDeviceUuid

`func (o *CacheTestFoundResponse) SetDeviceUuid(v string)`

SetDeviceUuid sets DeviceUuid field to given value.


### GetFound

`func (o *CacheTestFoundResponse) GetFound() bool`

GetFound returns the Found field if non-nil, zero value otherwise.

### GetFoundOk

`func (o *CacheTestFoundResponse) GetFoundOk() (*bool, bool)`

GetFoundOk returns a tuple with the Found field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetFound

`func (o *CacheTestFoundResponse) SetFound(v bool)`

SetFound sets Found field to given value.

### HasFound

`func (o *CacheTestFoundResponse) HasFound() bool`

HasFound returns a boolean if a field has been set.

### GetPlatform

`func (o *CacheTestFoundResponse) GetPlatform() string`

GetPlatform returns the Platform field if non-nil, zero value otherwise.

### GetPlatformOk

`func (o *CacheTestFoundResponse) GetPlatformOk() (*string, bool)`

GetPlatformOk returns a tuple with the Platform field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetPlatform

`func (o *CacheTestFoundResponse) SetPlatform(v string)`

SetPlatform sets Platform field to given value.


### SetPlatformNil

`func (o *CacheTestFoundResponse) SetPlatformNil(b bool)`

 SetPlatformNil sets the value for Platform to be an explicit nil

### UnsetPlatform
`func (o *CacheTestFoundResponse) UnsetPlatform()`

UnsetPlatform ensures that no value is present for Platform, not even an explicit nil
### GetSite

`func (o *CacheTestFoundResponse) GetSite() string`

GetSite returns the Site field if non-nil, zero value otherwise.

### GetSiteOk

`func (o *CacheTestFoundResponse) GetSiteOk() (*string, bool)`

GetSiteOk returns a tuple with the Site field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetSite

`func (o *CacheTestFoundResponse) SetSite(v string)`

SetSite sets Site field to given value.



[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


