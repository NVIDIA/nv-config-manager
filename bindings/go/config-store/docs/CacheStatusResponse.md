# CacheStatusResponse

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**CacheTtl** | Pointer to **NullableInt32** |  | [optional] 
**Enabled** | **bool** | Whether cache service is enabled | 
**Message** | Pointer to **NullableString** |  | [optional] 
**NautobotConnected** | Pointer to **NullableBool** |  | [optional] 
**RedisConnected** | Pointer to **NullableBool** |  | [optional] 

## Methods

### NewCacheStatusResponse

`func NewCacheStatusResponse(enabled bool, ) *CacheStatusResponse`

NewCacheStatusResponse instantiates a new CacheStatusResponse object
This constructor will assign default values to properties that have it defined,
and makes sure properties required by API are set, but the set of arguments
will change when the set of required properties is changed

### NewCacheStatusResponseWithDefaults

`func NewCacheStatusResponseWithDefaults() *CacheStatusResponse`

NewCacheStatusResponseWithDefaults instantiates a new CacheStatusResponse object
This constructor will only assign default values to properties that have it defined,
but it doesn't guarantee that properties required by API are set

### GetCacheTtl

`func (o *CacheStatusResponse) GetCacheTtl() int32`

GetCacheTtl returns the CacheTtl field if non-nil, zero value otherwise.

### GetCacheTtlOk

`func (o *CacheStatusResponse) GetCacheTtlOk() (*int32, bool)`

GetCacheTtlOk returns a tuple with the CacheTtl field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetCacheTtl

`func (o *CacheStatusResponse) SetCacheTtl(v int32)`

SetCacheTtl sets CacheTtl field to given value.

### HasCacheTtl

`func (o *CacheStatusResponse) HasCacheTtl() bool`

HasCacheTtl returns a boolean if a field has been set.

### SetCacheTtlNil

`func (o *CacheStatusResponse) SetCacheTtlNil(b bool)`

 SetCacheTtlNil sets the value for CacheTtl to be an explicit nil

### UnsetCacheTtl
`func (o *CacheStatusResponse) UnsetCacheTtl()`

UnsetCacheTtl ensures that no value is present for CacheTtl, not even an explicit nil
### GetEnabled

`func (o *CacheStatusResponse) GetEnabled() bool`

GetEnabled returns the Enabled field if non-nil, zero value otherwise.

### GetEnabledOk

`func (o *CacheStatusResponse) GetEnabledOk() (*bool, bool)`

GetEnabledOk returns a tuple with the Enabled field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetEnabled

`func (o *CacheStatusResponse) SetEnabled(v bool)`

SetEnabled sets Enabled field to given value.


### GetMessage

`func (o *CacheStatusResponse) GetMessage() string`

GetMessage returns the Message field if non-nil, zero value otherwise.

### GetMessageOk

`func (o *CacheStatusResponse) GetMessageOk() (*string, bool)`

GetMessageOk returns a tuple with the Message field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetMessage

`func (o *CacheStatusResponse) SetMessage(v string)`

SetMessage sets Message field to given value.

### HasMessage

`func (o *CacheStatusResponse) HasMessage() bool`

HasMessage returns a boolean if a field has been set.

### SetMessageNil

`func (o *CacheStatusResponse) SetMessageNil(b bool)`

 SetMessageNil sets the value for Message to be an explicit nil

### UnsetMessage
`func (o *CacheStatusResponse) UnsetMessage()`

UnsetMessage ensures that no value is present for Message, not even an explicit nil
### GetNautobotConnected

`func (o *CacheStatusResponse) GetNautobotConnected() bool`

GetNautobotConnected returns the NautobotConnected field if non-nil, zero value otherwise.

### GetNautobotConnectedOk

`func (o *CacheStatusResponse) GetNautobotConnectedOk() (*bool, bool)`

GetNautobotConnectedOk returns a tuple with the NautobotConnected field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetNautobotConnected

`func (o *CacheStatusResponse) SetNautobotConnected(v bool)`

SetNautobotConnected sets NautobotConnected field to given value.

### HasNautobotConnected

`func (o *CacheStatusResponse) HasNautobotConnected() bool`

HasNautobotConnected returns a boolean if a field has been set.

### SetNautobotConnectedNil

`func (o *CacheStatusResponse) SetNautobotConnectedNil(b bool)`

 SetNautobotConnectedNil sets the value for NautobotConnected to be an explicit nil

### UnsetNautobotConnected
`func (o *CacheStatusResponse) UnsetNautobotConnected()`

UnsetNautobotConnected ensures that no value is present for NautobotConnected, not even an explicit nil
### GetRedisConnected

`func (o *CacheStatusResponse) GetRedisConnected() bool`

GetRedisConnected returns the RedisConnected field if non-nil, zero value otherwise.

### GetRedisConnectedOk

`func (o *CacheStatusResponse) GetRedisConnectedOk() (*bool, bool)`

GetRedisConnectedOk returns a tuple with the RedisConnected field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetRedisConnected

`func (o *CacheStatusResponse) SetRedisConnected(v bool)`

SetRedisConnected sets RedisConnected field to given value.

### HasRedisConnected

`func (o *CacheStatusResponse) HasRedisConnected() bool`

HasRedisConnected returns a boolean if a field has been set.

### SetRedisConnectedNil

`func (o *CacheStatusResponse) SetRedisConnectedNil(b bool)`

 SetRedisConnectedNil sets the value for RedisConnected to be an explicit nil

### UnsetRedisConnected
`func (o *CacheStatusResponse) UnsetRedisConnected()`

UnsetRedisConnected ensures that no value is present for RedisConnected, not even an explicit nil

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


