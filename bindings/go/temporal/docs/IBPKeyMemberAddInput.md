# IBPKeyMemberAddInput

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**GuidMemberships** | Pointer to **[]string** |  | [optional] [default to {}]
**Guids** | Pointer to **[]string** |  | [optional] [default to {}]
**Host** | **string** |  | 
**Interfaces** | Pointer to [**[]InterfaceRef**](InterfaceRef.md) |  | [optional] [default to {}]
**IpOverIb** | Pointer to **bool** |  | [optional] [default to true]
**MembershipType** | Pointer to **string** |  | [optional] [default to "full"]
**Pkey** | **string** |  | 

## Methods

### NewIBPKeyMemberAddInput

`func NewIBPKeyMemberAddInput(host string, pkey string, ) *IBPKeyMemberAddInput`

NewIBPKeyMemberAddInput instantiates a new IBPKeyMemberAddInput object
This constructor will assign default values to properties that have it defined,
and makes sure properties required by API are set, but the set of arguments
will change when the set of required properties is changed

### NewIBPKeyMemberAddInputWithDefaults

`func NewIBPKeyMemberAddInputWithDefaults() *IBPKeyMemberAddInput`

NewIBPKeyMemberAddInputWithDefaults instantiates a new IBPKeyMemberAddInput object
This constructor will only assign default values to properties that have it defined,
but it doesn't guarantee that properties required by API are set

### GetGuidMemberships

`func (o *IBPKeyMemberAddInput) GetGuidMemberships() []string`

GetGuidMemberships returns the GuidMemberships field if non-nil, zero value otherwise.

### GetGuidMembershipsOk

`func (o *IBPKeyMemberAddInput) GetGuidMembershipsOk() (*[]string, bool)`

GetGuidMembershipsOk returns a tuple with the GuidMemberships field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetGuidMemberships

`func (o *IBPKeyMemberAddInput) SetGuidMemberships(v []string)`

SetGuidMemberships sets GuidMemberships field to given value.

### HasGuidMemberships

`func (o *IBPKeyMemberAddInput) HasGuidMemberships() bool`

HasGuidMemberships returns a boolean if a field has been set.

### GetGuids

`func (o *IBPKeyMemberAddInput) GetGuids() []string`

GetGuids returns the Guids field if non-nil, zero value otherwise.

### GetGuidsOk

`func (o *IBPKeyMemberAddInput) GetGuidsOk() (*[]string, bool)`

GetGuidsOk returns a tuple with the Guids field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetGuids

`func (o *IBPKeyMemberAddInput) SetGuids(v []string)`

SetGuids sets Guids field to given value.

### HasGuids

`func (o *IBPKeyMemberAddInput) HasGuids() bool`

HasGuids returns a boolean if a field has been set.

### GetHost

`func (o *IBPKeyMemberAddInput) GetHost() string`

GetHost returns the Host field if non-nil, zero value otherwise.

### GetHostOk

`func (o *IBPKeyMemberAddInput) GetHostOk() (*string, bool)`

GetHostOk returns a tuple with the Host field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetHost

`func (o *IBPKeyMemberAddInput) SetHost(v string)`

SetHost sets Host field to given value.


### GetInterfaces

`func (o *IBPKeyMemberAddInput) GetInterfaces() []InterfaceRef`

GetInterfaces returns the Interfaces field if non-nil, zero value otherwise.

### GetInterfacesOk

`func (o *IBPKeyMemberAddInput) GetInterfacesOk() (*[]InterfaceRef, bool)`

GetInterfacesOk returns a tuple with the Interfaces field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetInterfaces

`func (o *IBPKeyMemberAddInput) SetInterfaces(v []InterfaceRef)`

SetInterfaces sets Interfaces field to given value.

### HasInterfaces

`func (o *IBPKeyMemberAddInput) HasInterfaces() bool`

HasInterfaces returns a boolean if a field has been set.

### GetIpOverIb

`func (o *IBPKeyMemberAddInput) GetIpOverIb() bool`

GetIpOverIb returns the IpOverIb field if non-nil, zero value otherwise.

### GetIpOverIbOk

`func (o *IBPKeyMemberAddInput) GetIpOverIbOk() (*bool, bool)`

GetIpOverIbOk returns a tuple with the IpOverIb field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetIpOverIb

`func (o *IBPKeyMemberAddInput) SetIpOverIb(v bool)`

SetIpOverIb sets IpOverIb field to given value.

### HasIpOverIb

`func (o *IBPKeyMemberAddInput) HasIpOverIb() bool`

HasIpOverIb returns a boolean if a field has been set.

### GetMembershipType

`func (o *IBPKeyMemberAddInput) GetMembershipType() string`

GetMembershipType returns the MembershipType field if non-nil, zero value otherwise.

### GetMembershipTypeOk

`func (o *IBPKeyMemberAddInput) GetMembershipTypeOk() (*string, bool)`

GetMembershipTypeOk returns a tuple with the MembershipType field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetMembershipType

`func (o *IBPKeyMemberAddInput) SetMembershipType(v string)`

SetMembershipType sets MembershipType field to given value.

### HasMembershipType

`func (o *IBPKeyMemberAddInput) HasMembershipType() bool`

HasMembershipType returns a boolean if a field has been set.

### GetPkey

`func (o *IBPKeyMemberAddInput) GetPkey() string`

GetPkey returns the Pkey field if non-nil, zero value otherwise.

### GetPkeyOk

`func (o *IBPKeyMemberAddInput) GetPkeyOk() (*string, bool)`

GetPkeyOk returns a tuple with the Pkey field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetPkey

`func (o *IBPKeyMemberAddInput) SetPkey(v string)`

SetPkey sets Pkey field to given value.



[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


