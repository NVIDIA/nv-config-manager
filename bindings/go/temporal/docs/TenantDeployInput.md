# TenantDeployInput

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**IntendedConfigCommitId** | **string** | Optional config-store commit ID for the intended startup configuration from the same render snapshot as tenant_config_commit_id. Must be supplied with tenant_config_commit_id; omit both to deploy the latest tenant and intended configurations. | 
**TenantConfigCommitId** | **string** | Optional config-store commit ID for the tenant configuration. Must be supplied with intended_config_commit_id; omit both to deploy the latest tenant and intended configurations. | 

## Methods

### NewTenantDeployInput

`func NewTenantDeployInput(intendedConfigCommitId string, tenantConfigCommitId string, ) *TenantDeployInput`

NewTenantDeployInput instantiates a new TenantDeployInput object
This constructor will assign default values to properties that have it defined,
and makes sure properties required by API are set, but the set of arguments
will change when the set of required properties is changed

### NewTenantDeployInputWithDefaults

`func NewTenantDeployInputWithDefaults() *TenantDeployInput`

NewTenantDeployInputWithDefaults instantiates a new TenantDeployInput object
This constructor will only assign default values to properties that have it defined,
but it doesn't guarantee that properties required by API are set

### GetIntendedConfigCommitId

`func (o *TenantDeployInput) GetIntendedConfigCommitId() string`

GetIntendedConfigCommitId returns the IntendedConfigCommitId field if non-nil, zero value otherwise.

### GetIntendedConfigCommitIdOk

`func (o *TenantDeployInput) GetIntendedConfigCommitIdOk() (*string, bool)`

GetIntendedConfigCommitIdOk returns a tuple with the IntendedConfigCommitId field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetIntendedConfigCommitId

`func (o *TenantDeployInput) SetIntendedConfigCommitId(v string)`

SetIntendedConfigCommitId sets IntendedConfigCommitId field to given value.


### GetTenantConfigCommitId

`func (o *TenantDeployInput) GetTenantConfigCommitId() string`

GetTenantConfigCommitId returns the TenantConfigCommitId field if non-nil, zero value otherwise.

### GetTenantConfigCommitIdOk

`func (o *TenantDeployInput) GetTenantConfigCommitIdOk() (*string, bool)`

GetTenantConfigCommitIdOk returns a tuple with the TenantConfigCommitId field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetTenantConfigCommitId

`func (o *TenantDeployInput) SetTenantConfigCommitId(v string)`

SetTenantConfigCommitId sets TenantConfigCommitId field to given value.



[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


