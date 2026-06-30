# SiteCableValidationInput

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**DeviceTypeIds** | Pointer to **[]string** |  | [optional] [default to {}]
**RaiseForInvalid** | Pointer to **bool** |  | [optional] [default to false]
**Roles** | Pointer to **[]string** |  | [optional] [default to {"tan-bbr", "cin-core", "cin-spine", "cin-leaf", "tan-core", "tan-spine", "tan-leaf", "smn-core", "smn-spine", "smn-leaf", "smn-aggleaf"}]
**Site** | **string** |  | 
**Status** | Pointer to **[]string** |  | [optional] [default to {"active", "provisioning"}]
**Tenant** | Pointer to **string** |  | [optional] [default to "nsv"]

## Methods

### NewSiteCableValidationInput

`func NewSiteCableValidationInput(site string, ) *SiteCableValidationInput`

NewSiteCableValidationInput instantiates a new SiteCableValidationInput object
This constructor will assign default values to properties that have it defined,
and makes sure properties required by API are set, but the set of arguments
will change when the set of required properties is changed

### NewSiteCableValidationInputWithDefaults

`func NewSiteCableValidationInputWithDefaults() *SiteCableValidationInput`

NewSiteCableValidationInputWithDefaults instantiates a new SiteCableValidationInput object
This constructor will only assign default values to properties that have it defined,
but it doesn't guarantee that properties required by API are set

### GetDeviceTypeIds

`func (o *SiteCableValidationInput) GetDeviceTypeIds() []string`

GetDeviceTypeIds returns the DeviceTypeIds field if non-nil, zero value otherwise.

### GetDeviceTypeIdsOk

`func (o *SiteCableValidationInput) GetDeviceTypeIdsOk() (*[]string, bool)`

GetDeviceTypeIdsOk returns a tuple with the DeviceTypeIds field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetDeviceTypeIds

`func (o *SiteCableValidationInput) SetDeviceTypeIds(v []string)`

SetDeviceTypeIds sets DeviceTypeIds field to given value.

### HasDeviceTypeIds

`func (o *SiteCableValidationInput) HasDeviceTypeIds() bool`

HasDeviceTypeIds returns a boolean if a field has been set.

### GetRaiseForInvalid

`func (o *SiteCableValidationInput) GetRaiseForInvalid() bool`

GetRaiseForInvalid returns the RaiseForInvalid field if non-nil, zero value otherwise.

### GetRaiseForInvalidOk

`func (o *SiteCableValidationInput) GetRaiseForInvalidOk() (*bool, bool)`

GetRaiseForInvalidOk returns a tuple with the RaiseForInvalid field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetRaiseForInvalid

`func (o *SiteCableValidationInput) SetRaiseForInvalid(v bool)`

SetRaiseForInvalid sets RaiseForInvalid field to given value.

### HasRaiseForInvalid

`func (o *SiteCableValidationInput) HasRaiseForInvalid() bool`

HasRaiseForInvalid returns a boolean if a field has been set.

### GetRoles

`func (o *SiteCableValidationInput) GetRoles() []string`

GetRoles returns the Roles field if non-nil, zero value otherwise.

### GetRolesOk

`func (o *SiteCableValidationInput) GetRolesOk() (*[]string, bool)`

GetRolesOk returns a tuple with the Roles field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetRoles

`func (o *SiteCableValidationInput) SetRoles(v []string)`

SetRoles sets Roles field to given value.

### HasRoles

`func (o *SiteCableValidationInput) HasRoles() bool`

HasRoles returns a boolean if a field has been set.

### GetSite

`func (o *SiteCableValidationInput) GetSite() string`

GetSite returns the Site field if non-nil, zero value otherwise.

### GetSiteOk

`func (o *SiteCableValidationInput) GetSiteOk() (*string, bool)`

GetSiteOk returns a tuple with the Site field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetSite

`func (o *SiteCableValidationInput) SetSite(v string)`

SetSite sets Site field to given value.


### GetStatus

`func (o *SiteCableValidationInput) GetStatus() []string`

GetStatus returns the Status field if non-nil, zero value otherwise.

### GetStatusOk

`func (o *SiteCableValidationInput) GetStatusOk() (*[]string, bool)`

GetStatusOk returns a tuple with the Status field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetStatus

`func (o *SiteCableValidationInput) SetStatus(v []string)`

SetStatus sets Status field to given value.

### HasStatus

`func (o *SiteCableValidationInput) HasStatus() bool`

HasStatus returns a boolean if a field has been set.

### GetTenant

`func (o *SiteCableValidationInput) GetTenant() string`

GetTenant returns the Tenant field if non-nil, zero value otherwise.

### GetTenantOk

`func (o *SiteCableValidationInput) GetTenantOk() (*string, bool)`

GetTenantOk returns a tuple with the Tenant field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetTenant

`func (o *SiteCableValidationInput) SetTenant(v string)`

SetTenant sets Tenant field to given value.

### HasTenant

`func (o *SiteCableValidationInput) HasTenant() bool`

HasTenant returns a boolean if a field has been set.


[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


