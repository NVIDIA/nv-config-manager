# SitePasswordRotationInput

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**Location** | **string** |  | 
**Roles** | Pointer to **[]string** |  | [optional] [default to {"TAN-Core", "TAN-Spine", "TAN-Leaf", "SMN-Core", "SMN-Spine", "SMN-Leaf", "SMN-Aggleaf"}]
**SelectedSecret** | **string** |  | 
**Status** | Pointer to **[]string** |  | [optional] [default to {"Active", "Provisioned"}]
**Tenant** | Pointer to **string** |  | [optional] [default to "NGC"]

## Methods

### NewSitePasswordRotationInput

`func NewSitePasswordRotationInput(location string, selectedSecret string, ) *SitePasswordRotationInput`

NewSitePasswordRotationInput instantiates a new SitePasswordRotationInput object
This constructor will assign default values to properties that have it defined,
and makes sure properties required by API are set, but the set of arguments
will change when the set of required properties is changed

### NewSitePasswordRotationInputWithDefaults

`func NewSitePasswordRotationInputWithDefaults() *SitePasswordRotationInput`

NewSitePasswordRotationInputWithDefaults instantiates a new SitePasswordRotationInput object
This constructor will only assign default values to properties that have it defined,
but it doesn't guarantee that properties required by API are set

### GetLocation

`func (o *SitePasswordRotationInput) GetLocation() string`

GetLocation returns the Location field if non-nil, zero value otherwise.

### GetLocationOk

`func (o *SitePasswordRotationInput) GetLocationOk() (*string, bool)`

GetLocationOk returns a tuple with the Location field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetLocation

`func (o *SitePasswordRotationInput) SetLocation(v string)`

SetLocation sets Location field to given value.


### GetRoles

`func (o *SitePasswordRotationInput) GetRoles() []string`

GetRoles returns the Roles field if non-nil, zero value otherwise.

### GetRolesOk

`func (o *SitePasswordRotationInput) GetRolesOk() (*[]string, bool)`

GetRolesOk returns a tuple with the Roles field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetRoles

`func (o *SitePasswordRotationInput) SetRoles(v []string)`

SetRoles sets Roles field to given value.

### HasRoles

`func (o *SitePasswordRotationInput) HasRoles() bool`

HasRoles returns a boolean if a field has been set.

### GetSelectedSecret

`func (o *SitePasswordRotationInput) GetSelectedSecret() string`

GetSelectedSecret returns the SelectedSecret field if non-nil, zero value otherwise.

### GetSelectedSecretOk

`func (o *SitePasswordRotationInput) GetSelectedSecretOk() (*string, bool)`

GetSelectedSecretOk returns a tuple with the SelectedSecret field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetSelectedSecret

`func (o *SitePasswordRotationInput) SetSelectedSecret(v string)`

SetSelectedSecret sets SelectedSecret field to given value.


### GetStatus

`func (o *SitePasswordRotationInput) GetStatus() []string`

GetStatus returns the Status field if non-nil, zero value otherwise.

### GetStatusOk

`func (o *SitePasswordRotationInput) GetStatusOk() (*[]string, bool)`

GetStatusOk returns a tuple with the Status field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetStatus

`func (o *SitePasswordRotationInput) SetStatus(v []string)`

SetStatus sets Status field to given value.

### HasStatus

`func (o *SitePasswordRotationInput) HasStatus() bool`

HasStatus returns a boolean if a field has been set.

### GetTenant

`func (o *SitePasswordRotationInput) GetTenant() string`

GetTenant returns the Tenant field if non-nil, zero value otherwise.

### GetTenantOk

`func (o *SitePasswordRotationInput) GetTenantOk() (*string, bool)`

GetTenantOk returns a tuple with the Tenant field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetTenant

`func (o *SitePasswordRotationInput) SetTenant(v string)`

SetTenant sets Tenant field to given value.

### HasTenant

`func (o *SitePasswordRotationInput) HasTenant() bool`

HasTenant returns a boolean if a field has been set.


[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


