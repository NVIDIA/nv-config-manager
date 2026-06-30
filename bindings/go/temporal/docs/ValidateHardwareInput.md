# ValidateHardwareInput

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**DeviceTypeIds** | Pointer to **[]string** |  | [optional] [default to {}]
**RaiseForInvalid** | Pointer to **bool** |  | [optional] [default to false]
**Roles** | Pointer to **[]string** |  | [optional] [default to {}]
**Site** | **string** |  | 
**Status** | Pointer to **[]string** |  | [optional] [default to {}]
**Tenant** | **string** |  | 

## Methods

### NewValidateHardwareInput

`func NewValidateHardwareInput(site string, tenant string, ) *ValidateHardwareInput`

NewValidateHardwareInput instantiates a new ValidateHardwareInput object
This constructor will assign default values to properties that have it defined,
and makes sure properties required by API are set, but the set of arguments
will change when the set of required properties is changed

### NewValidateHardwareInputWithDefaults

`func NewValidateHardwareInputWithDefaults() *ValidateHardwareInput`

NewValidateHardwareInputWithDefaults instantiates a new ValidateHardwareInput object
This constructor will only assign default values to properties that have it defined,
but it doesn't guarantee that properties required by API are set

### GetDeviceTypeIds

`func (o *ValidateHardwareInput) GetDeviceTypeIds() []string`

GetDeviceTypeIds returns the DeviceTypeIds field if non-nil, zero value otherwise.

### GetDeviceTypeIdsOk

`func (o *ValidateHardwareInput) GetDeviceTypeIdsOk() (*[]string, bool)`

GetDeviceTypeIdsOk returns a tuple with the DeviceTypeIds field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetDeviceTypeIds

`func (o *ValidateHardwareInput) SetDeviceTypeIds(v []string)`

SetDeviceTypeIds sets DeviceTypeIds field to given value.

### HasDeviceTypeIds

`func (o *ValidateHardwareInput) HasDeviceTypeIds() bool`

HasDeviceTypeIds returns a boolean if a field has been set.

### GetRaiseForInvalid

`func (o *ValidateHardwareInput) GetRaiseForInvalid() bool`

GetRaiseForInvalid returns the RaiseForInvalid field if non-nil, zero value otherwise.

### GetRaiseForInvalidOk

`func (o *ValidateHardwareInput) GetRaiseForInvalidOk() (*bool, bool)`

GetRaiseForInvalidOk returns a tuple with the RaiseForInvalid field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetRaiseForInvalid

`func (o *ValidateHardwareInput) SetRaiseForInvalid(v bool)`

SetRaiseForInvalid sets RaiseForInvalid field to given value.

### HasRaiseForInvalid

`func (o *ValidateHardwareInput) HasRaiseForInvalid() bool`

HasRaiseForInvalid returns a boolean if a field has been set.

### GetRoles

`func (o *ValidateHardwareInput) GetRoles() []string`

GetRoles returns the Roles field if non-nil, zero value otherwise.

### GetRolesOk

`func (o *ValidateHardwareInput) GetRolesOk() (*[]string, bool)`

GetRolesOk returns a tuple with the Roles field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetRoles

`func (o *ValidateHardwareInput) SetRoles(v []string)`

SetRoles sets Roles field to given value.

### HasRoles

`func (o *ValidateHardwareInput) HasRoles() bool`

HasRoles returns a boolean if a field has been set.

### GetSite

`func (o *ValidateHardwareInput) GetSite() string`

GetSite returns the Site field if non-nil, zero value otherwise.

### GetSiteOk

`func (o *ValidateHardwareInput) GetSiteOk() (*string, bool)`

GetSiteOk returns a tuple with the Site field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetSite

`func (o *ValidateHardwareInput) SetSite(v string)`

SetSite sets Site field to given value.


### GetStatus

`func (o *ValidateHardwareInput) GetStatus() []string`

GetStatus returns the Status field if non-nil, zero value otherwise.

### GetStatusOk

`func (o *ValidateHardwareInput) GetStatusOk() (*[]string, bool)`

GetStatusOk returns a tuple with the Status field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetStatus

`func (o *ValidateHardwareInput) SetStatus(v []string)`

SetStatus sets Status field to given value.

### HasStatus

`func (o *ValidateHardwareInput) HasStatus() bool`

HasStatus returns a boolean if a field has been set.

### GetTenant

`func (o *ValidateHardwareInput) GetTenant() string`

GetTenant returns the Tenant field if non-nil, zero value otherwise.

### GetTenantOk

`func (o *ValidateHardwareInput) GetTenantOk() (*string, bool)`

GetTenantOk returns a tuple with the Tenant field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetTenant

`func (o *ValidateHardwareInput) SetTenant(v string)`

SetTenant sets Tenant field to given value.



[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


