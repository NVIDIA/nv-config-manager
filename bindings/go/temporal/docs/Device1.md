# Device1

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
**Position** | Pointer to **int32** |  | [optional] 
**PrimaryIp4** | **string** |  | 
**PrimaryIp6** | **string** |  | 
**Rack** | Pointer to **string** |  | [optional] 
**RenderEnabled** | Pointer to **bool** |  | [optional] [default to false]
**Role** | **string** |  | 
**Site** | **string** |  | 
**ZtpEnabled** | Pointer to **bool** |  | [optional] [default to false]

## Methods

### NewDevice1

`func NewDevice1(deviceType string, id string, name string, platform Platform, primaryIp4 string, primaryIp6 string, role string, site string, ) *Device1`

NewDevice1 instantiates a new Device1 object
This constructor will assign default values to properties that have it defined,
and makes sure properties required by API are set, but the set of arguments
will change when the set of required properties is changed

### NewDevice1WithDefaults

`func NewDevice1WithDefaults() *Device1`

NewDevice1WithDefaults instantiates a new Device1 object
This constructor will only assign default values to properties that have it defined,
but it doesn't guarantee that properties required by API are set

### GetBackupEnabled

`func (o *Device1) GetBackupEnabled() bool`

GetBackupEnabled returns the BackupEnabled field if non-nil, zero value otherwise.

### GetBackupEnabledOk

`func (o *Device1) GetBackupEnabledOk() (*bool, bool)`

GetBackupEnabledOk returns a tuple with the BackupEnabled field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetBackupEnabled

`func (o *Device1) SetBackupEnabled(v bool)`

SetBackupEnabled sets BackupEnabled field to given value.

### HasBackupEnabled

`func (o *Device1) HasBackupEnabled() bool`

HasBackupEnabled returns a boolean if a field has been set.

### GetConfigContext

`func (o *Device1) GetConfigContext() map[string]interface{}`

GetConfigContext returns the ConfigContext field if non-nil, zero value otherwise.

### GetConfigContextOk

`func (o *Device1) GetConfigContextOk() (*map[string]interface{}, bool)`

GetConfigContextOk returns a tuple with the ConfigContext field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetConfigContext

`func (o *Device1) SetConfigContext(v map[string]interface{})`

SetConfigContext sets ConfigContext field to given value.

### HasConfigContext

`func (o *Device1) HasConfigContext() bool`

HasConfigContext returns a boolean if a field has been set.

### GetDeployEnabled

`func (o *Device1) GetDeployEnabled() bool`

GetDeployEnabled returns the DeployEnabled field if non-nil, zero value otherwise.

### GetDeployEnabledOk

`func (o *Device1) GetDeployEnabledOk() (*bool, bool)`

GetDeployEnabledOk returns a tuple with the DeployEnabled field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetDeployEnabled

`func (o *Device1) SetDeployEnabled(v bool)`

SetDeployEnabled sets DeployEnabled field to given value.

### HasDeployEnabled

`func (o *Device1) HasDeployEnabled() bool`

HasDeployEnabled returns a boolean if a field has been set.

### GetDeviceType

`func (o *Device1) GetDeviceType() string`

GetDeviceType returns the DeviceType field if non-nil, zero value otherwise.

### GetDeviceTypeOk

`func (o *Device1) GetDeviceTypeOk() (*string, bool)`

GetDeviceTypeOk returns a tuple with the DeviceType field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetDeviceType

`func (o *Device1) SetDeviceType(v string)`

SetDeviceType sets DeviceType field to given value.


### GetId

`func (o *Device1) GetId() string`

GetId returns the Id field if non-nil, zero value otherwise.

### GetIdOk

`func (o *Device1) GetIdOk() (*string, bool)`

GetIdOk returns a tuple with the Id field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetId

`func (o *Device1) SetId(v string)`

SetId sets Id field to given value.


### GetName

`func (o *Device1) GetName() string`

GetName returns the Name field if non-nil, zero value otherwise.

### GetNameOk

`func (o *Device1) GetNameOk() (*string, bool)`

GetNameOk returns a tuple with the Name field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetName

`func (o *Device1) SetName(v string)`

SetName sets Name field to given value.


### GetPlatform

`func (o *Device1) GetPlatform() Platform`

GetPlatform returns the Platform field if non-nil, zero value otherwise.

### GetPlatformOk

`func (o *Device1) GetPlatformOk() (*Platform, bool)`

GetPlatformOk returns a tuple with the Platform field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetPlatform

`func (o *Device1) SetPlatform(v Platform)`

SetPlatform sets Platform field to given value.


### GetPosition

`func (o *Device1) GetPosition() int32`

GetPosition returns the Position field if non-nil, zero value otherwise.

### GetPositionOk

`func (o *Device1) GetPositionOk() (*int32, bool)`

GetPositionOk returns a tuple with the Position field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetPosition

`func (o *Device1) SetPosition(v int32)`

SetPosition sets Position field to given value.

### HasPosition

`func (o *Device1) HasPosition() bool`

HasPosition returns a boolean if a field has been set.

### GetPrimaryIp4

`func (o *Device1) GetPrimaryIp4() string`

GetPrimaryIp4 returns the PrimaryIp4 field if non-nil, zero value otherwise.

### GetPrimaryIp4Ok

`func (o *Device1) GetPrimaryIp4Ok() (*string, bool)`

GetPrimaryIp4Ok returns a tuple with the PrimaryIp4 field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetPrimaryIp4

`func (o *Device1) SetPrimaryIp4(v string)`

SetPrimaryIp4 sets PrimaryIp4 field to given value.


### GetPrimaryIp6

`func (o *Device1) GetPrimaryIp6() string`

GetPrimaryIp6 returns the PrimaryIp6 field if non-nil, zero value otherwise.

### GetPrimaryIp6Ok

`func (o *Device1) GetPrimaryIp6Ok() (*string, bool)`

GetPrimaryIp6Ok returns a tuple with the PrimaryIp6 field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetPrimaryIp6

`func (o *Device1) SetPrimaryIp6(v string)`

SetPrimaryIp6 sets PrimaryIp6 field to given value.


### GetRack

`func (o *Device1) GetRack() string`

GetRack returns the Rack field if non-nil, zero value otherwise.

### GetRackOk

`func (o *Device1) GetRackOk() (*string, bool)`

GetRackOk returns a tuple with the Rack field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetRack

`func (o *Device1) SetRack(v string)`

SetRack sets Rack field to given value.

### HasRack

`func (o *Device1) HasRack() bool`

HasRack returns a boolean if a field has been set.

### GetRenderEnabled

`func (o *Device1) GetRenderEnabled() bool`

GetRenderEnabled returns the RenderEnabled field if non-nil, zero value otherwise.

### GetRenderEnabledOk

`func (o *Device1) GetRenderEnabledOk() (*bool, bool)`

GetRenderEnabledOk returns a tuple with the RenderEnabled field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetRenderEnabled

`func (o *Device1) SetRenderEnabled(v bool)`

SetRenderEnabled sets RenderEnabled field to given value.

### HasRenderEnabled

`func (o *Device1) HasRenderEnabled() bool`

HasRenderEnabled returns a boolean if a field has been set.

### GetRole

`func (o *Device1) GetRole() string`

GetRole returns the Role field if non-nil, zero value otherwise.

### GetRoleOk

`func (o *Device1) GetRoleOk() (*string, bool)`

GetRoleOk returns a tuple with the Role field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetRole

`func (o *Device1) SetRole(v string)`

SetRole sets Role field to given value.


### GetSite

`func (o *Device1) GetSite() string`

GetSite returns the Site field if non-nil, zero value otherwise.

### GetSiteOk

`func (o *Device1) GetSiteOk() (*string, bool)`

GetSiteOk returns a tuple with the Site field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetSite

`func (o *Device1) SetSite(v string)`

SetSite sets Site field to given value.


### GetZtpEnabled

`func (o *Device1) GetZtpEnabled() bool`

GetZtpEnabled returns the ZtpEnabled field if non-nil, zero value otherwise.

### GetZtpEnabledOk

`func (o *Device1) GetZtpEnabledOk() (*bool, bool)`

GetZtpEnabledOk returns a tuple with the ZtpEnabled field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetZtpEnabled

`func (o *Device1) SetZtpEnabled(v bool)`

SetZtpEnabled sets ZtpEnabled field to given value.

### HasZtpEnabled

`func (o *Device1) HasZtpEnabled() bool`

HasZtpEnabled returns a boolean if a field has been set.


[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


