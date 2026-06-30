# MultiDeployInput

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**CommitConfirm** | Pointer to **bool** |  | [optional] [default to true]
**Location** | Pointer to **NullableString** |  | [optional] 
**MaxBatchSize** | Pointer to **int32** |  | [optional] [default to 10]
**Role** | **string** |  | 
**Status** | Pointer to **[]string** |  | [optional] 
**Tenant** | Pointer to **NullableString** |  | [optional] 

## Methods

### NewMultiDeployInput

`func NewMultiDeployInput(role string, ) *MultiDeployInput`

NewMultiDeployInput instantiates a new MultiDeployInput object
This constructor will assign default values to properties that have it defined,
and makes sure properties required by API are set, but the set of arguments
will change when the set of required properties is changed

### NewMultiDeployInputWithDefaults

`func NewMultiDeployInputWithDefaults() *MultiDeployInput`

NewMultiDeployInputWithDefaults instantiates a new MultiDeployInput object
This constructor will only assign default values to properties that have it defined,
but it doesn't guarantee that properties required by API are set

### GetCommitConfirm

`func (o *MultiDeployInput) GetCommitConfirm() bool`

GetCommitConfirm returns the CommitConfirm field if non-nil, zero value otherwise.

### GetCommitConfirmOk

`func (o *MultiDeployInput) GetCommitConfirmOk() (*bool, bool)`

GetCommitConfirmOk returns a tuple with the CommitConfirm field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetCommitConfirm

`func (o *MultiDeployInput) SetCommitConfirm(v bool)`

SetCommitConfirm sets CommitConfirm field to given value.

### HasCommitConfirm

`func (o *MultiDeployInput) HasCommitConfirm() bool`

HasCommitConfirm returns a boolean if a field has been set.

### GetLocation

`func (o *MultiDeployInput) GetLocation() string`

GetLocation returns the Location field if non-nil, zero value otherwise.

### GetLocationOk

`func (o *MultiDeployInput) GetLocationOk() (*string, bool)`

GetLocationOk returns a tuple with the Location field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetLocation

`func (o *MultiDeployInput) SetLocation(v string)`

SetLocation sets Location field to given value.

### HasLocation

`func (o *MultiDeployInput) HasLocation() bool`

HasLocation returns a boolean if a field has been set.

### SetLocationNil

`func (o *MultiDeployInput) SetLocationNil(b bool)`

 SetLocationNil sets the value for Location to be an explicit nil

### UnsetLocation
`func (o *MultiDeployInput) UnsetLocation()`

UnsetLocation ensures that no value is present for Location, not even an explicit nil
### GetMaxBatchSize

`func (o *MultiDeployInput) GetMaxBatchSize() int32`

GetMaxBatchSize returns the MaxBatchSize field if non-nil, zero value otherwise.

### GetMaxBatchSizeOk

`func (o *MultiDeployInput) GetMaxBatchSizeOk() (*int32, bool)`

GetMaxBatchSizeOk returns a tuple with the MaxBatchSize field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetMaxBatchSize

`func (o *MultiDeployInput) SetMaxBatchSize(v int32)`

SetMaxBatchSize sets MaxBatchSize field to given value.

### HasMaxBatchSize

`func (o *MultiDeployInput) HasMaxBatchSize() bool`

HasMaxBatchSize returns a boolean if a field has been set.

### GetRole

`func (o *MultiDeployInput) GetRole() string`

GetRole returns the Role field if non-nil, zero value otherwise.

### GetRoleOk

`func (o *MultiDeployInput) GetRoleOk() (*string, bool)`

GetRoleOk returns a tuple with the Role field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetRole

`func (o *MultiDeployInput) SetRole(v string)`

SetRole sets Role field to given value.


### GetStatus

`func (o *MultiDeployInput) GetStatus() []string`

GetStatus returns the Status field if non-nil, zero value otherwise.

### GetStatusOk

`func (o *MultiDeployInput) GetStatusOk() (*[]string, bool)`

GetStatusOk returns a tuple with the Status field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetStatus

`func (o *MultiDeployInput) SetStatus(v []string)`

SetStatus sets Status field to given value.

### HasStatus

`func (o *MultiDeployInput) HasStatus() bool`

HasStatus returns a boolean if a field has been set.

### SetStatusNil

`func (o *MultiDeployInput) SetStatusNil(b bool)`

 SetStatusNil sets the value for Status to be an explicit nil

### UnsetStatus
`func (o *MultiDeployInput) UnsetStatus()`

UnsetStatus ensures that no value is present for Status, not even an explicit nil
### GetTenant

`func (o *MultiDeployInput) GetTenant() string`

GetTenant returns the Tenant field if non-nil, zero value otherwise.

### GetTenantOk

`func (o *MultiDeployInput) GetTenantOk() (*string, bool)`

GetTenantOk returns a tuple with the Tenant field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetTenant

`func (o *MultiDeployInput) SetTenant(v string)`

SetTenant sets Tenant field to given value.

### HasTenant

`func (o *MultiDeployInput) HasTenant() bool`

HasTenant returns a boolean if a field has been set.

### SetTenantNil

`func (o *MultiDeployInput) SetTenantNil(b bool)`

 SetTenantNil sets the value for Tenant to be an explicit nil

### UnsetTenant
`func (o *MultiDeployInput) UnsetTenant()`

UnsetTenant ensures that no value is present for Tenant, not even an explicit nil

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


