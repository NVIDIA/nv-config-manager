# NetworkDeviceData

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**BackupEnabled** | Pointer to **bool** |  | [optional] [default to false]
**ConfigContext** | Pointer to **map[string]interface{}** |  | [optional] 
**DeployEnabled** | Pointer to **bool** |  | [optional] [default to false]
**DeviceType** | **string** |  | 
**Id** | **string** |  | 
**Name** | **string** |  | 
**Platform** | [**Platform**](Platform.md) |  | 
**Position** | Pointer to **NullableInt32** |  | [optional] 
**PrimaryIp4** | **NullableString** |  | 
**PrimaryIp6** | **NullableString** |  | 
**Rack** | Pointer to **NullableString** |  | [optional] 
**RenderEnabled** | Pointer to **bool** |  | [optional] [default to false]
**Role** | **string** |  | 
**Site** | **string** |  | 
**ZtpEnabled** | Pointer to **bool** |  | [optional] [default to false]

## Methods

### NewNetworkDeviceData

`func NewNetworkDeviceData(deviceType string, id string, name string, platform Platform, primaryIp4 NullableString, primaryIp6 NullableString, role string, site string, ) *NetworkDeviceData`

NewNetworkDeviceData instantiates a new NetworkDeviceData object
This constructor will assign default values to properties that have it defined,
and makes sure properties required by API are set, but the set of arguments
will change when the set of required properties is changed

### NewNetworkDeviceDataWithDefaults

`func NewNetworkDeviceDataWithDefaults() *NetworkDeviceData`

NewNetworkDeviceDataWithDefaults instantiates a new NetworkDeviceData object
This constructor will only assign default values to properties that have it defined,
but it doesn't guarantee that properties required by API are set

### GetBackupEnabled

`func (o *NetworkDeviceData) GetBackupEnabled() bool`

GetBackupEnabled returns the BackupEnabled field if non-nil, zero value otherwise.

### GetBackupEnabledOk

`func (o *NetworkDeviceData) GetBackupEnabledOk() (*bool, bool)`

GetBackupEnabledOk returns a tuple with the BackupEnabled field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetBackupEnabled

`func (o *NetworkDeviceData) SetBackupEnabled(v bool)`

SetBackupEnabled sets BackupEnabled field to given value.

### HasBackupEnabled

`func (o *NetworkDeviceData) HasBackupEnabled() bool`

HasBackupEnabled returns a boolean if a field has been set.

### GetConfigContext

`func (o *NetworkDeviceData) GetConfigContext() map[string]interface{}`

GetConfigContext returns the ConfigContext field if non-nil, zero value otherwise.

### GetConfigContextOk

`func (o *NetworkDeviceData) GetConfigContextOk() (*map[string]interface{}, bool)`

GetConfigContextOk returns a tuple with the ConfigContext field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetConfigContext

`func (o *NetworkDeviceData) SetConfigContext(v map[string]interface{})`

SetConfigContext sets ConfigContext field to given value.

### HasConfigContext

`func (o *NetworkDeviceData) HasConfigContext() bool`

HasConfigContext returns a boolean if a field has been set.

### SetConfigContextNil

`func (o *NetworkDeviceData) SetConfigContextNil(b bool)`

 SetConfigContextNil sets the value for ConfigContext to be an explicit nil

### UnsetConfigContext
`func (o *NetworkDeviceData) UnsetConfigContext()`

UnsetConfigContext ensures that no value is present for ConfigContext, not even an explicit nil
### GetDeployEnabled

`func (o *NetworkDeviceData) GetDeployEnabled() bool`

GetDeployEnabled returns the DeployEnabled field if non-nil, zero value otherwise.

### GetDeployEnabledOk

`func (o *NetworkDeviceData) GetDeployEnabledOk() (*bool, bool)`

GetDeployEnabledOk returns a tuple with the DeployEnabled field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetDeployEnabled

`func (o *NetworkDeviceData) SetDeployEnabled(v bool)`

SetDeployEnabled sets DeployEnabled field to given value.

### HasDeployEnabled

`func (o *NetworkDeviceData) HasDeployEnabled() bool`

HasDeployEnabled returns a boolean if a field has been set.

### GetDeviceType

`func (o *NetworkDeviceData) GetDeviceType() string`

GetDeviceType returns the DeviceType field if non-nil, zero value otherwise.

### GetDeviceTypeOk

`func (o *NetworkDeviceData) GetDeviceTypeOk() (*string, bool)`

GetDeviceTypeOk returns a tuple with the DeviceType field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetDeviceType

`func (o *NetworkDeviceData) SetDeviceType(v string)`

SetDeviceType sets DeviceType field to given value.


### GetId

`func (o *NetworkDeviceData) GetId() string`

GetId returns the Id field if non-nil, zero value otherwise.

### GetIdOk

`func (o *NetworkDeviceData) GetIdOk() (*string, bool)`

GetIdOk returns a tuple with the Id field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetId

`func (o *NetworkDeviceData) SetId(v string)`

SetId sets Id field to given value.


### GetName

`func (o *NetworkDeviceData) GetName() string`

GetName returns the Name field if non-nil, zero value otherwise.

### GetNameOk

`func (o *NetworkDeviceData) GetNameOk() (*string, bool)`

GetNameOk returns a tuple with the Name field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetName

`func (o *NetworkDeviceData) SetName(v string)`

SetName sets Name field to given value.


### GetPlatform

`func (o *NetworkDeviceData) GetPlatform() Platform`

GetPlatform returns the Platform field if non-nil, zero value otherwise.

### GetPlatformOk

`func (o *NetworkDeviceData) GetPlatformOk() (*Platform, bool)`

GetPlatformOk returns a tuple with the Platform field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetPlatform

`func (o *NetworkDeviceData) SetPlatform(v Platform)`

SetPlatform sets Platform field to given value.


### GetPosition

`func (o *NetworkDeviceData) GetPosition() int32`

GetPosition returns the Position field if non-nil, zero value otherwise.

### GetPositionOk

`func (o *NetworkDeviceData) GetPositionOk() (*int32, bool)`

GetPositionOk returns a tuple with the Position field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetPosition

`func (o *NetworkDeviceData) SetPosition(v int32)`

SetPosition sets Position field to given value.

### HasPosition

`func (o *NetworkDeviceData) HasPosition() bool`

HasPosition returns a boolean if a field has been set.

### SetPositionNil

`func (o *NetworkDeviceData) SetPositionNil(b bool)`

 SetPositionNil sets the value for Position to be an explicit nil

### UnsetPosition
`func (o *NetworkDeviceData) UnsetPosition()`

UnsetPosition ensures that no value is present for Position, not even an explicit nil
### GetPrimaryIp4

`func (o *NetworkDeviceData) GetPrimaryIp4() string`

GetPrimaryIp4 returns the PrimaryIp4 field if non-nil, zero value otherwise.

### GetPrimaryIp4Ok

`func (o *NetworkDeviceData) GetPrimaryIp4Ok() (*string, bool)`

GetPrimaryIp4Ok returns a tuple with the PrimaryIp4 field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetPrimaryIp4

`func (o *NetworkDeviceData) SetPrimaryIp4(v string)`

SetPrimaryIp4 sets PrimaryIp4 field to given value.


### SetPrimaryIp4Nil

`func (o *NetworkDeviceData) SetPrimaryIp4Nil(b bool)`

 SetPrimaryIp4Nil sets the value for PrimaryIp4 to be an explicit nil

### UnsetPrimaryIp4
`func (o *NetworkDeviceData) UnsetPrimaryIp4()`

UnsetPrimaryIp4 ensures that no value is present for PrimaryIp4, not even an explicit nil
### GetPrimaryIp6

`func (o *NetworkDeviceData) GetPrimaryIp6() string`

GetPrimaryIp6 returns the PrimaryIp6 field if non-nil, zero value otherwise.

### GetPrimaryIp6Ok

`func (o *NetworkDeviceData) GetPrimaryIp6Ok() (*string, bool)`

GetPrimaryIp6Ok returns a tuple with the PrimaryIp6 field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetPrimaryIp6

`func (o *NetworkDeviceData) SetPrimaryIp6(v string)`

SetPrimaryIp6 sets PrimaryIp6 field to given value.


### SetPrimaryIp6Nil

`func (o *NetworkDeviceData) SetPrimaryIp6Nil(b bool)`

 SetPrimaryIp6Nil sets the value for PrimaryIp6 to be an explicit nil

### UnsetPrimaryIp6
`func (o *NetworkDeviceData) UnsetPrimaryIp6()`

UnsetPrimaryIp6 ensures that no value is present for PrimaryIp6, not even an explicit nil
### GetRack

`func (o *NetworkDeviceData) GetRack() string`

GetRack returns the Rack field if non-nil, zero value otherwise.

### GetRackOk

`func (o *NetworkDeviceData) GetRackOk() (*string, bool)`

GetRackOk returns a tuple with the Rack field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetRack

`func (o *NetworkDeviceData) SetRack(v string)`

SetRack sets Rack field to given value.

### HasRack

`func (o *NetworkDeviceData) HasRack() bool`

HasRack returns a boolean if a field has been set.

### SetRackNil

`func (o *NetworkDeviceData) SetRackNil(b bool)`

 SetRackNil sets the value for Rack to be an explicit nil

### UnsetRack
`func (o *NetworkDeviceData) UnsetRack()`

UnsetRack ensures that no value is present for Rack, not even an explicit nil
### GetRenderEnabled

`func (o *NetworkDeviceData) GetRenderEnabled() bool`

GetRenderEnabled returns the RenderEnabled field if non-nil, zero value otherwise.

### GetRenderEnabledOk

`func (o *NetworkDeviceData) GetRenderEnabledOk() (*bool, bool)`

GetRenderEnabledOk returns a tuple with the RenderEnabled field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetRenderEnabled

`func (o *NetworkDeviceData) SetRenderEnabled(v bool)`

SetRenderEnabled sets RenderEnabled field to given value.

### HasRenderEnabled

`func (o *NetworkDeviceData) HasRenderEnabled() bool`

HasRenderEnabled returns a boolean if a field has been set.

### GetRole

`func (o *NetworkDeviceData) GetRole() string`

GetRole returns the Role field if non-nil, zero value otherwise.

### GetRoleOk

`func (o *NetworkDeviceData) GetRoleOk() (*string, bool)`

GetRoleOk returns a tuple with the Role field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetRole

`func (o *NetworkDeviceData) SetRole(v string)`

SetRole sets Role field to given value.


### GetSite

`func (o *NetworkDeviceData) GetSite() string`

GetSite returns the Site field if non-nil, zero value otherwise.

### GetSiteOk

`func (o *NetworkDeviceData) GetSiteOk() (*string, bool)`

GetSiteOk returns a tuple with the Site field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetSite

`func (o *NetworkDeviceData) SetSite(v string)`

SetSite sets Site field to given value.


### GetZtpEnabled

`func (o *NetworkDeviceData) GetZtpEnabled() bool`

GetZtpEnabled returns the ZtpEnabled field if non-nil, zero value otherwise.

### GetZtpEnabledOk

`func (o *NetworkDeviceData) GetZtpEnabledOk() (*bool, bool)`

GetZtpEnabledOk returns a tuple with the ZtpEnabled field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetZtpEnabled

`func (o *NetworkDeviceData) SetZtpEnabled(v bool)`

SetZtpEnabled sets ZtpEnabled field to given value.

### HasZtpEnabled

`func (o *NetworkDeviceData) HasZtpEnabled() bool`

HasZtpEnabled returns a boolean if a field has been set.


[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


