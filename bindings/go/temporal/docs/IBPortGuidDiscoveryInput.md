# IBPortGuidDiscoveryInput

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**DryRun** | Pointer to **bool** |  | [optional] [default to true]
**SwitchDeviceIds** | **[]string** |  | 
**UfmDeviceId** | **string** |  | 

## Methods

### NewIBPortGuidDiscoveryInput

`func NewIBPortGuidDiscoveryInput(switchDeviceIds []string, ufmDeviceId string, ) *IBPortGuidDiscoveryInput`

NewIBPortGuidDiscoveryInput instantiates a new IBPortGuidDiscoveryInput object
This constructor will assign default values to properties that have it defined,
and makes sure properties required by API are set, but the set of arguments
will change when the set of required properties is changed

### NewIBPortGuidDiscoveryInputWithDefaults

`func NewIBPortGuidDiscoveryInputWithDefaults() *IBPortGuidDiscoveryInput`

NewIBPortGuidDiscoveryInputWithDefaults instantiates a new IBPortGuidDiscoveryInput object
This constructor will only assign default values to properties that have it defined,
but it doesn't guarantee that properties required by API are set

### GetDryRun

`func (o *IBPortGuidDiscoveryInput) GetDryRun() bool`

GetDryRun returns the DryRun field if non-nil, zero value otherwise.

### GetDryRunOk

`func (o *IBPortGuidDiscoveryInput) GetDryRunOk() (*bool, bool)`

GetDryRunOk returns a tuple with the DryRun field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetDryRun

`func (o *IBPortGuidDiscoveryInput) SetDryRun(v bool)`

SetDryRun sets DryRun field to given value.

### HasDryRun

`func (o *IBPortGuidDiscoveryInput) HasDryRun() bool`

HasDryRun returns a boolean if a field has been set.

### GetSwitchDeviceIds

`func (o *IBPortGuidDiscoveryInput) GetSwitchDeviceIds() []string`

GetSwitchDeviceIds returns the SwitchDeviceIds field if non-nil, zero value otherwise.

### GetSwitchDeviceIdsOk

`func (o *IBPortGuidDiscoveryInput) GetSwitchDeviceIdsOk() (*[]string, bool)`

GetSwitchDeviceIdsOk returns a tuple with the SwitchDeviceIds field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetSwitchDeviceIds

`func (o *IBPortGuidDiscoveryInput) SetSwitchDeviceIds(v []string)`

SetSwitchDeviceIds sets SwitchDeviceIds field to given value.


### GetUfmDeviceId

`func (o *IBPortGuidDiscoveryInput) GetUfmDeviceId() string`

GetUfmDeviceId returns the UfmDeviceId field if non-nil, zero value otherwise.

### GetUfmDeviceIdOk

`func (o *IBPortGuidDiscoveryInput) GetUfmDeviceIdOk() (*string, bool)`

GetUfmDeviceIdOk returns a tuple with the UfmDeviceId field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetUfmDeviceId

`func (o *IBPortGuidDiscoveryInput) SetUfmDeviceId(v string)`

SetUfmDeviceId sets UfmDeviceId field to given value.



[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


