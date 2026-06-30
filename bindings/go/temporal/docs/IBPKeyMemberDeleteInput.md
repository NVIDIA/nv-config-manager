# IBPKeyMemberDeleteInput

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**Guids** | Pointer to **[]string** |  | [optional] [default to {}]
**Host** | **string** |  | 
**Interfaces** | Pointer to [**[]InterfaceRef**](InterfaceRef.md) |  | [optional] [default to {}]
**Pkey** | **string** |  | 

## Methods

### NewIBPKeyMemberDeleteInput

`func NewIBPKeyMemberDeleteInput(host string, pkey string, ) *IBPKeyMemberDeleteInput`

NewIBPKeyMemberDeleteInput instantiates a new IBPKeyMemberDeleteInput object
This constructor will assign default values to properties that have it defined,
and makes sure properties required by API are set, but the set of arguments
will change when the set of required properties is changed

### NewIBPKeyMemberDeleteInputWithDefaults

`func NewIBPKeyMemberDeleteInputWithDefaults() *IBPKeyMemberDeleteInput`

NewIBPKeyMemberDeleteInputWithDefaults instantiates a new IBPKeyMemberDeleteInput object
This constructor will only assign default values to properties that have it defined,
but it doesn't guarantee that properties required by API are set

### GetGuids

`func (o *IBPKeyMemberDeleteInput) GetGuids() []string`

GetGuids returns the Guids field if non-nil, zero value otherwise.

### GetGuidsOk

`func (o *IBPKeyMemberDeleteInput) GetGuidsOk() (*[]string, bool)`

GetGuidsOk returns a tuple with the Guids field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetGuids

`func (o *IBPKeyMemberDeleteInput) SetGuids(v []string)`

SetGuids sets Guids field to given value.

### HasGuids

`func (o *IBPKeyMemberDeleteInput) HasGuids() bool`

HasGuids returns a boolean if a field has been set.

### GetHost

`func (o *IBPKeyMemberDeleteInput) GetHost() string`

GetHost returns the Host field if non-nil, zero value otherwise.

### GetHostOk

`func (o *IBPKeyMemberDeleteInput) GetHostOk() (*string, bool)`

GetHostOk returns a tuple with the Host field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetHost

`func (o *IBPKeyMemberDeleteInput) SetHost(v string)`

SetHost sets Host field to given value.


### GetInterfaces

`func (o *IBPKeyMemberDeleteInput) GetInterfaces() []InterfaceRef`

GetInterfaces returns the Interfaces field if non-nil, zero value otherwise.

### GetInterfacesOk

`func (o *IBPKeyMemberDeleteInput) GetInterfacesOk() (*[]InterfaceRef, bool)`

GetInterfacesOk returns a tuple with the Interfaces field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetInterfaces

`func (o *IBPKeyMemberDeleteInput) SetInterfaces(v []InterfaceRef)`

SetInterfaces sets Interfaces field to given value.

### HasInterfaces

`func (o *IBPKeyMemberDeleteInput) HasInterfaces() bool`

HasInterfaces returns a boolean if a field has been set.

### GetPkey

`func (o *IBPKeyMemberDeleteInput) GetPkey() string`

GetPkey returns the Pkey field if non-nil, zero value otherwise.

### GetPkeyOk

`func (o *IBPKeyMemberDeleteInput) GetPkeyOk() (*string, bool)`

GetPkeyOk returns a tuple with the Pkey field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetPkey

`func (o *IBPKeyMemberDeleteInput) SetPkey(v string)`

SetPkey sets Pkey field to given value.



[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


