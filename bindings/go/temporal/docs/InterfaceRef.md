# InterfaceRef

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**Device** | **string** |  | 
**Interface** | **string** |  | 
**Membership** | Pointer to **NullableString** |  | [optional] 

## Methods

### NewInterfaceRef

`func NewInterfaceRef(device string, interface_ string, ) *InterfaceRef`

NewInterfaceRef instantiates a new InterfaceRef object
This constructor will assign default values to properties that have it defined,
and makes sure properties required by API are set, but the set of arguments
will change when the set of required properties is changed

### NewInterfaceRefWithDefaults

`func NewInterfaceRefWithDefaults() *InterfaceRef`

NewInterfaceRefWithDefaults instantiates a new InterfaceRef object
This constructor will only assign default values to properties that have it defined,
but it doesn't guarantee that properties required by API are set

### GetDevice

`func (o *InterfaceRef) GetDevice() string`

GetDevice returns the Device field if non-nil, zero value otherwise.

### GetDeviceOk

`func (o *InterfaceRef) GetDeviceOk() (*string, bool)`

GetDeviceOk returns a tuple with the Device field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetDevice

`func (o *InterfaceRef) SetDevice(v string)`

SetDevice sets Device field to given value.


### GetInterface

`func (o *InterfaceRef) GetInterface() string`

GetInterface returns the Interface field if non-nil, zero value otherwise.

### GetInterfaceOk

`func (o *InterfaceRef) GetInterfaceOk() (*string, bool)`

GetInterfaceOk returns a tuple with the Interface field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetInterface

`func (o *InterfaceRef) SetInterface(v string)`

SetInterface sets Interface field to given value.


### GetMembership

`func (o *InterfaceRef) GetMembership() string`

GetMembership returns the Membership field if non-nil, zero value otherwise.

### GetMembershipOk

`func (o *InterfaceRef) GetMembershipOk() (*string, bool)`

GetMembershipOk returns a tuple with the Membership field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetMembership

`func (o *InterfaceRef) SetMembership(v string)`

SetMembership sets Membership field to given value.

### HasMembership

`func (o *InterfaceRef) HasMembership() bool`

HasMembership returns a boolean if a field has been set.

### SetMembershipNil

`func (o *InterfaceRef) SetMembershipNil(b bool)`

 SetMembershipNil sets the value for Membership to be an explicit nil

### UnsetMembership
`func (o *InterfaceRef) UnsetMembership()`

UnsetMembership ensures that no value is present for Membership, not even an explicit nil

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


