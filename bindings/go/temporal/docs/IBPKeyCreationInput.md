# IBPKeyCreationInput

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**Host** | **string** |  | 
**IpOverIb** | Pointer to **bool** |  | [optional] [default to true]
**Pkey** | Pointer to **NullableString** |  | [optional] 
**PkeyMax** | Pointer to **int32** |  | [optional] [default to 32766]
**PkeyMin** | Pointer to **int32** |  | [optional] [default to 1]
**Site** | Pointer to **NullableString** |  | [optional] 

## Methods

### NewIBPKeyCreationInput

`func NewIBPKeyCreationInput(host string, ) *IBPKeyCreationInput`

NewIBPKeyCreationInput instantiates a new IBPKeyCreationInput object
This constructor will assign default values to properties that have it defined,
and makes sure properties required by API are set, but the set of arguments
will change when the set of required properties is changed

### NewIBPKeyCreationInputWithDefaults

`func NewIBPKeyCreationInputWithDefaults() *IBPKeyCreationInput`

NewIBPKeyCreationInputWithDefaults instantiates a new IBPKeyCreationInput object
This constructor will only assign default values to properties that have it defined,
but it doesn't guarantee that properties required by API are set

### GetHost

`func (o *IBPKeyCreationInput) GetHost() string`

GetHost returns the Host field if non-nil, zero value otherwise.

### GetHostOk

`func (o *IBPKeyCreationInput) GetHostOk() (*string, bool)`

GetHostOk returns a tuple with the Host field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetHost

`func (o *IBPKeyCreationInput) SetHost(v string)`

SetHost sets Host field to given value.


### GetIpOverIb

`func (o *IBPKeyCreationInput) GetIpOverIb() bool`

GetIpOverIb returns the IpOverIb field if non-nil, zero value otherwise.

### GetIpOverIbOk

`func (o *IBPKeyCreationInput) GetIpOverIbOk() (*bool, bool)`

GetIpOverIbOk returns a tuple with the IpOverIb field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetIpOverIb

`func (o *IBPKeyCreationInput) SetIpOverIb(v bool)`

SetIpOverIb sets IpOverIb field to given value.

### HasIpOverIb

`func (o *IBPKeyCreationInput) HasIpOverIb() bool`

HasIpOverIb returns a boolean if a field has been set.

### GetPkey

`func (o *IBPKeyCreationInput) GetPkey() string`

GetPkey returns the Pkey field if non-nil, zero value otherwise.

### GetPkeyOk

`func (o *IBPKeyCreationInput) GetPkeyOk() (*string, bool)`

GetPkeyOk returns a tuple with the Pkey field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetPkey

`func (o *IBPKeyCreationInput) SetPkey(v string)`

SetPkey sets Pkey field to given value.

### HasPkey

`func (o *IBPKeyCreationInput) HasPkey() bool`

HasPkey returns a boolean if a field has been set.

### SetPkeyNil

`func (o *IBPKeyCreationInput) SetPkeyNil(b bool)`

 SetPkeyNil sets the value for Pkey to be an explicit nil

### UnsetPkey
`func (o *IBPKeyCreationInput) UnsetPkey()`

UnsetPkey ensures that no value is present for Pkey, not even an explicit nil
### GetPkeyMax

`func (o *IBPKeyCreationInput) GetPkeyMax() int32`

GetPkeyMax returns the PkeyMax field if non-nil, zero value otherwise.

### GetPkeyMaxOk

`func (o *IBPKeyCreationInput) GetPkeyMaxOk() (*int32, bool)`

GetPkeyMaxOk returns a tuple with the PkeyMax field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetPkeyMax

`func (o *IBPKeyCreationInput) SetPkeyMax(v int32)`

SetPkeyMax sets PkeyMax field to given value.

### HasPkeyMax

`func (o *IBPKeyCreationInput) HasPkeyMax() bool`

HasPkeyMax returns a boolean if a field has been set.

### GetPkeyMin

`func (o *IBPKeyCreationInput) GetPkeyMin() int32`

GetPkeyMin returns the PkeyMin field if non-nil, zero value otherwise.

### GetPkeyMinOk

`func (o *IBPKeyCreationInput) GetPkeyMinOk() (*int32, bool)`

GetPkeyMinOk returns a tuple with the PkeyMin field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetPkeyMin

`func (o *IBPKeyCreationInput) SetPkeyMin(v int32)`

SetPkeyMin sets PkeyMin field to given value.

### HasPkeyMin

`func (o *IBPKeyCreationInput) HasPkeyMin() bool`

HasPkeyMin returns a boolean if a field has been set.

### GetSite

`func (o *IBPKeyCreationInput) GetSite() string`

GetSite returns the Site field if non-nil, zero value otherwise.

### GetSiteOk

`func (o *IBPKeyCreationInput) GetSiteOk() (*string, bool)`

GetSiteOk returns a tuple with the Site field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetSite

`func (o *IBPKeyCreationInput) SetSite(v string)`

SetSite sets Site field to given value.

### HasSite

`func (o *IBPKeyCreationInput) HasSite() bool`

HasSite returns a boolean if a field has been set.

### SetSiteNil

`func (o *IBPKeyCreationInput) SetSiteNil(b bool)`

 SetSiteNil sets the value for Site to be an explicit nil

### UnsetSite
`func (o *IBPKeyCreationInput) UnsetSite()`

UnsetSite ensures that no value is present for Site, not even an explicit nil

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


