# DeviceLatestConfig

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**Active** | Pointer to **bool** | Whether the device is currently active in nv-config-manager | [optional] [default to true]
**LatestAuthor** | **string** | Author of latest change | 
**LatestMessage** | **string** | Commit message of latest change | 
**LatestUpdate** | **string** | Latest config update timestamp | 
**Name** | **string** | Device name | 
**Site** | **string** | Site name | 
**Uuid** | **string** | Device UUID | 

## Methods

### NewDeviceLatestConfig

`func NewDeviceLatestConfig(latestAuthor string, latestMessage string, latestUpdate string, name string, site string, uuid string, ) *DeviceLatestConfig`

NewDeviceLatestConfig instantiates a new DeviceLatestConfig object
This constructor will assign default values to properties that have it defined,
and makes sure properties required by API are set, but the set of arguments
will change when the set of required properties is changed

### NewDeviceLatestConfigWithDefaults

`func NewDeviceLatestConfigWithDefaults() *DeviceLatestConfig`

NewDeviceLatestConfigWithDefaults instantiates a new DeviceLatestConfig object
This constructor will only assign default values to properties that have it defined,
but it doesn't guarantee that properties required by API are set

### GetActive

`func (o *DeviceLatestConfig) GetActive() bool`

GetActive returns the Active field if non-nil, zero value otherwise.

### GetActiveOk

`func (o *DeviceLatestConfig) GetActiveOk() (*bool, bool)`

GetActiveOk returns a tuple with the Active field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetActive

`func (o *DeviceLatestConfig) SetActive(v bool)`

SetActive sets Active field to given value.

### HasActive

`func (o *DeviceLatestConfig) HasActive() bool`

HasActive returns a boolean if a field has been set.

### GetLatestAuthor

`func (o *DeviceLatestConfig) GetLatestAuthor() string`

GetLatestAuthor returns the LatestAuthor field if non-nil, zero value otherwise.

### GetLatestAuthorOk

`func (o *DeviceLatestConfig) GetLatestAuthorOk() (*string, bool)`

GetLatestAuthorOk returns a tuple with the LatestAuthor field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetLatestAuthor

`func (o *DeviceLatestConfig) SetLatestAuthor(v string)`

SetLatestAuthor sets LatestAuthor field to given value.


### GetLatestMessage

`func (o *DeviceLatestConfig) GetLatestMessage() string`

GetLatestMessage returns the LatestMessage field if non-nil, zero value otherwise.

### GetLatestMessageOk

`func (o *DeviceLatestConfig) GetLatestMessageOk() (*string, bool)`

GetLatestMessageOk returns a tuple with the LatestMessage field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetLatestMessage

`func (o *DeviceLatestConfig) SetLatestMessage(v string)`

SetLatestMessage sets LatestMessage field to given value.


### GetLatestUpdate

`func (o *DeviceLatestConfig) GetLatestUpdate() string`

GetLatestUpdate returns the LatestUpdate field if non-nil, zero value otherwise.

### GetLatestUpdateOk

`func (o *DeviceLatestConfig) GetLatestUpdateOk() (*string, bool)`

GetLatestUpdateOk returns a tuple with the LatestUpdate field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetLatestUpdate

`func (o *DeviceLatestConfig) SetLatestUpdate(v string)`

SetLatestUpdate sets LatestUpdate field to given value.


### GetName

`func (o *DeviceLatestConfig) GetName() string`

GetName returns the Name field if non-nil, zero value otherwise.

### GetNameOk

`func (o *DeviceLatestConfig) GetNameOk() (*string, bool)`

GetNameOk returns a tuple with the Name field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetName

`func (o *DeviceLatestConfig) SetName(v string)`

SetName sets Name field to given value.


### GetSite

`func (o *DeviceLatestConfig) GetSite() string`

GetSite returns the Site field if non-nil, zero value otherwise.

### GetSiteOk

`func (o *DeviceLatestConfig) GetSiteOk() (*string, bool)`

GetSiteOk returns a tuple with the Site field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetSite

`func (o *DeviceLatestConfig) SetSite(v string)`

SetSite sets Site field to given value.


### GetUuid

`func (o *DeviceLatestConfig) GetUuid() string`

GetUuid returns the Uuid field if non-nil, zero value otherwise.

### GetUuidOk

`func (o *DeviceLatestConfig) GetUuidOk() (*string, bool)`

GetUuidOk returns a tuple with the Uuid field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetUuid

`func (o *DeviceLatestConfig) SetUuid(v string)`

SetUuid sets Uuid field to given value.



[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


