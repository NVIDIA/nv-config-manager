# DeviceMetadata

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**LastUpdated** | Pointer to **NullableTime** |  | [optional] 
**Name** | **string** | Device name | 
**NautobotUrl** | Pointer to **NullableString** |  | [optional] 
**Platform** | Pointer to **NullableString** |  | [optional] 
**PrimaryIp4** | Pointer to **NullableString** |  | [optional] 
**Rack** | Pointer to **NullableString** |  | [optional] 
**Role** | Pointer to **NullableString** |  | [optional] 
**Site** | **string** | Site name | 

## Methods

### NewDeviceMetadata

`func NewDeviceMetadata(name string, site string, ) *DeviceMetadata`

NewDeviceMetadata instantiates a new DeviceMetadata object
This constructor will assign default values to properties that have it defined,
and makes sure properties required by API are set, but the set of arguments
will change when the set of required properties is changed

### NewDeviceMetadataWithDefaults

`func NewDeviceMetadataWithDefaults() *DeviceMetadata`

NewDeviceMetadataWithDefaults instantiates a new DeviceMetadata object
This constructor will only assign default values to properties that have it defined,
but it doesn't guarantee that properties required by API are set

### GetLastUpdated

`func (o *DeviceMetadata) GetLastUpdated() time.Time`

GetLastUpdated returns the LastUpdated field if non-nil, zero value otherwise.

### GetLastUpdatedOk

`func (o *DeviceMetadata) GetLastUpdatedOk() (*time.Time, bool)`

GetLastUpdatedOk returns a tuple with the LastUpdated field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetLastUpdated

`func (o *DeviceMetadata) SetLastUpdated(v time.Time)`

SetLastUpdated sets LastUpdated field to given value.

### HasLastUpdated

`func (o *DeviceMetadata) HasLastUpdated() bool`

HasLastUpdated returns a boolean if a field has been set.

### SetLastUpdatedNil

`func (o *DeviceMetadata) SetLastUpdatedNil(b bool)`

 SetLastUpdatedNil sets the value for LastUpdated to be an explicit nil

### UnsetLastUpdated
`func (o *DeviceMetadata) UnsetLastUpdated()`

UnsetLastUpdated ensures that no value is present for LastUpdated, not even an explicit nil
### GetName

`func (o *DeviceMetadata) GetName() string`

GetName returns the Name field if non-nil, zero value otherwise.

### GetNameOk

`func (o *DeviceMetadata) GetNameOk() (*string, bool)`

GetNameOk returns a tuple with the Name field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetName

`func (o *DeviceMetadata) SetName(v string)`

SetName sets Name field to given value.


### GetNautobotUrl

`func (o *DeviceMetadata) GetNautobotUrl() string`

GetNautobotUrl returns the NautobotUrl field if non-nil, zero value otherwise.

### GetNautobotUrlOk

`func (o *DeviceMetadata) GetNautobotUrlOk() (*string, bool)`

GetNautobotUrlOk returns a tuple with the NautobotUrl field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetNautobotUrl

`func (o *DeviceMetadata) SetNautobotUrl(v string)`

SetNautobotUrl sets NautobotUrl field to given value.

### HasNautobotUrl

`func (o *DeviceMetadata) HasNautobotUrl() bool`

HasNautobotUrl returns a boolean if a field has been set.

### SetNautobotUrlNil

`func (o *DeviceMetadata) SetNautobotUrlNil(b bool)`

 SetNautobotUrlNil sets the value for NautobotUrl to be an explicit nil

### UnsetNautobotUrl
`func (o *DeviceMetadata) UnsetNautobotUrl()`

UnsetNautobotUrl ensures that no value is present for NautobotUrl, not even an explicit nil
### GetPlatform

`func (o *DeviceMetadata) GetPlatform() string`

GetPlatform returns the Platform field if non-nil, zero value otherwise.

### GetPlatformOk

`func (o *DeviceMetadata) GetPlatformOk() (*string, bool)`

GetPlatformOk returns a tuple with the Platform field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetPlatform

`func (o *DeviceMetadata) SetPlatform(v string)`

SetPlatform sets Platform field to given value.

### HasPlatform

`func (o *DeviceMetadata) HasPlatform() bool`

HasPlatform returns a boolean if a field has been set.

### SetPlatformNil

`func (o *DeviceMetadata) SetPlatformNil(b bool)`

 SetPlatformNil sets the value for Platform to be an explicit nil

### UnsetPlatform
`func (o *DeviceMetadata) UnsetPlatform()`

UnsetPlatform ensures that no value is present for Platform, not even an explicit nil
### GetPrimaryIp4

`func (o *DeviceMetadata) GetPrimaryIp4() string`

GetPrimaryIp4 returns the PrimaryIp4 field if non-nil, zero value otherwise.

### GetPrimaryIp4Ok

`func (o *DeviceMetadata) GetPrimaryIp4Ok() (*string, bool)`

GetPrimaryIp4Ok returns a tuple with the PrimaryIp4 field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetPrimaryIp4

`func (o *DeviceMetadata) SetPrimaryIp4(v string)`

SetPrimaryIp4 sets PrimaryIp4 field to given value.

### HasPrimaryIp4

`func (o *DeviceMetadata) HasPrimaryIp4() bool`

HasPrimaryIp4 returns a boolean if a field has been set.

### SetPrimaryIp4Nil

`func (o *DeviceMetadata) SetPrimaryIp4Nil(b bool)`

 SetPrimaryIp4Nil sets the value for PrimaryIp4 to be an explicit nil

### UnsetPrimaryIp4
`func (o *DeviceMetadata) UnsetPrimaryIp4()`

UnsetPrimaryIp4 ensures that no value is present for PrimaryIp4, not even an explicit nil
### GetRack

`func (o *DeviceMetadata) GetRack() string`

GetRack returns the Rack field if non-nil, zero value otherwise.

### GetRackOk

`func (o *DeviceMetadata) GetRackOk() (*string, bool)`

GetRackOk returns a tuple with the Rack field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetRack

`func (o *DeviceMetadata) SetRack(v string)`

SetRack sets Rack field to given value.

### HasRack

`func (o *DeviceMetadata) HasRack() bool`

HasRack returns a boolean if a field has been set.

### SetRackNil

`func (o *DeviceMetadata) SetRackNil(b bool)`

 SetRackNil sets the value for Rack to be an explicit nil

### UnsetRack
`func (o *DeviceMetadata) UnsetRack()`

UnsetRack ensures that no value is present for Rack, not even an explicit nil
### GetRole

`func (o *DeviceMetadata) GetRole() string`

GetRole returns the Role field if non-nil, zero value otherwise.

### GetRoleOk

`func (o *DeviceMetadata) GetRoleOk() (*string, bool)`

GetRoleOk returns a tuple with the Role field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetRole

`func (o *DeviceMetadata) SetRole(v string)`

SetRole sets Role field to given value.

### HasRole

`func (o *DeviceMetadata) HasRole() bool`

HasRole returns a boolean if a field has been set.

### SetRoleNil

`func (o *DeviceMetadata) SetRoleNil(b bool)`

 SetRoleNil sets the value for Role to be an explicit nil

### UnsetRole
`func (o *DeviceMetadata) UnsetRole()`

UnsetRole ensures that no value is present for Role, not even an explicit nil
### GetSite

`func (o *DeviceMetadata) GetSite() string`

GetSite returns the Site field if non-nil, zero value otherwise.

### GetSiteOk

`func (o *DeviceMetadata) GetSiteOk() (*string, bool)`

GetSiteOk returns a tuple with the Site field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetSite

`func (o *DeviceMetadata) SetSite(v string)`

SetSite sets Site field to given value.



[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


