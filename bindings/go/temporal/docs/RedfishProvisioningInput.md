# RedfishProvisioningInput

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**BmcSwitchRoles** | **[]string** |  | 
**DpuManufacturers** | Pointer to **[]string** |  | [optional] [default to {"Mellanox Technologies", "MLNX"}]
**HttpTimeoutS** | Pointer to **int32** |  | [optional] [default to 5]
**IpRangeEnd** | **string** |  | 
**IpRangeStart** | **string** |  | 
**Port** | Pointer to **int32** |  | [optional] [default to 443]
**Site** | **string** |  | 

## Methods

### NewRedfishProvisioningInput

`func NewRedfishProvisioningInput(bmcSwitchRoles []string, ipRangeEnd string, ipRangeStart string, site string, ) *RedfishProvisioningInput`

NewRedfishProvisioningInput instantiates a new RedfishProvisioningInput object
This constructor will assign default values to properties that have it defined,
and makes sure properties required by API are set, but the set of arguments
will change when the set of required properties is changed

### NewRedfishProvisioningInputWithDefaults

`func NewRedfishProvisioningInputWithDefaults() *RedfishProvisioningInput`

NewRedfishProvisioningInputWithDefaults instantiates a new RedfishProvisioningInput object
This constructor will only assign default values to properties that have it defined,
but it doesn't guarantee that properties required by API are set

### GetBmcSwitchRoles

`func (o *RedfishProvisioningInput) GetBmcSwitchRoles() []string`

GetBmcSwitchRoles returns the BmcSwitchRoles field if non-nil, zero value otherwise.

### GetBmcSwitchRolesOk

`func (o *RedfishProvisioningInput) GetBmcSwitchRolesOk() (*[]string, bool)`

GetBmcSwitchRolesOk returns a tuple with the BmcSwitchRoles field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetBmcSwitchRoles

`func (o *RedfishProvisioningInput) SetBmcSwitchRoles(v []string)`

SetBmcSwitchRoles sets BmcSwitchRoles field to given value.


### GetDpuManufacturers

`func (o *RedfishProvisioningInput) GetDpuManufacturers() []string`

GetDpuManufacturers returns the DpuManufacturers field if non-nil, zero value otherwise.

### GetDpuManufacturersOk

`func (o *RedfishProvisioningInput) GetDpuManufacturersOk() (*[]string, bool)`

GetDpuManufacturersOk returns a tuple with the DpuManufacturers field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetDpuManufacturers

`func (o *RedfishProvisioningInput) SetDpuManufacturers(v []string)`

SetDpuManufacturers sets DpuManufacturers field to given value.

### HasDpuManufacturers

`func (o *RedfishProvisioningInput) HasDpuManufacturers() bool`

HasDpuManufacturers returns a boolean if a field has been set.

### GetHttpTimeoutS

`func (o *RedfishProvisioningInput) GetHttpTimeoutS() int32`

GetHttpTimeoutS returns the HttpTimeoutS field if non-nil, zero value otherwise.

### GetHttpTimeoutSOk

`func (o *RedfishProvisioningInput) GetHttpTimeoutSOk() (*int32, bool)`

GetHttpTimeoutSOk returns a tuple with the HttpTimeoutS field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetHttpTimeoutS

`func (o *RedfishProvisioningInput) SetHttpTimeoutS(v int32)`

SetHttpTimeoutS sets HttpTimeoutS field to given value.

### HasHttpTimeoutS

`func (o *RedfishProvisioningInput) HasHttpTimeoutS() bool`

HasHttpTimeoutS returns a boolean if a field has been set.

### GetIpRangeEnd

`func (o *RedfishProvisioningInput) GetIpRangeEnd() string`

GetIpRangeEnd returns the IpRangeEnd field if non-nil, zero value otherwise.

### GetIpRangeEndOk

`func (o *RedfishProvisioningInput) GetIpRangeEndOk() (*string, bool)`

GetIpRangeEndOk returns a tuple with the IpRangeEnd field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetIpRangeEnd

`func (o *RedfishProvisioningInput) SetIpRangeEnd(v string)`

SetIpRangeEnd sets IpRangeEnd field to given value.


### GetIpRangeStart

`func (o *RedfishProvisioningInput) GetIpRangeStart() string`

GetIpRangeStart returns the IpRangeStart field if non-nil, zero value otherwise.

### GetIpRangeStartOk

`func (o *RedfishProvisioningInput) GetIpRangeStartOk() (*string, bool)`

GetIpRangeStartOk returns a tuple with the IpRangeStart field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetIpRangeStart

`func (o *RedfishProvisioningInput) SetIpRangeStart(v string)`

SetIpRangeStart sets IpRangeStart field to given value.


### GetPort

`func (o *RedfishProvisioningInput) GetPort() int32`

GetPort returns the Port field if non-nil, zero value otherwise.

### GetPortOk

`func (o *RedfishProvisioningInput) GetPortOk() (*int32, bool)`

GetPortOk returns a tuple with the Port field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetPort

`func (o *RedfishProvisioningInput) SetPort(v int32)`

SetPort sets Port field to given value.

### HasPort

`func (o *RedfishProvisioningInput) HasPort() bool`

HasPort returns a boolean if a field has been set.

### GetSite

`func (o *RedfishProvisioningInput) GetSite() string`

GetSite returns the Site field if non-nil, zero value otherwise.

### GetSiteOk

`func (o *RedfishProvisioningInput) GetSiteOk() (*string, bool)`

GetSiteOk returns a tuple with the Site field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetSite

`func (o *RedfishProvisioningInput) SetSite(v string)`

SetSite sets Site field to given value.



[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


