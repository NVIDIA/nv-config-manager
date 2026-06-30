# SpXOverlayCreationInput

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**NamespaceTag** | Pointer to **string** |  | [optional] [default to "spectrumx"]
**OverlayId** | **string** | Unique identifier for the SpX overlay. Used as an idempotency key — re-running with the same ID returns existing VRFs without creating new ones. | 
**RdMax** | Pointer to **int32** | Upper bound of the route-distinguisher allocation range (0–65535). Must be greater than rd_min. | [optional] [default to 65000]
**RdMin** | Pointer to **int32** | Lower bound of the route-distinguisher allocation range (0–65535). The first available RD in [rd_min, rd_max] is allocated. | [optional] [default to 60000]
**Site** | **string** |  | 
**Tenant** | **string** |  | 

## Methods

### NewSpXOverlayCreationInput

`func NewSpXOverlayCreationInput(overlayId string, site string, tenant string, ) *SpXOverlayCreationInput`

NewSpXOverlayCreationInput instantiates a new SpXOverlayCreationInput object
This constructor will assign default values to properties that have it defined,
and makes sure properties required by API are set, but the set of arguments
will change when the set of required properties is changed

### NewSpXOverlayCreationInputWithDefaults

`func NewSpXOverlayCreationInputWithDefaults() *SpXOverlayCreationInput`

NewSpXOverlayCreationInputWithDefaults instantiates a new SpXOverlayCreationInput object
This constructor will only assign default values to properties that have it defined,
but it doesn't guarantee that properties required by API are set

### GetNamespaceTag

`func (o *SpXOverlayCreationInput) GetNamespaceTag() string`

GetNamespaceTag returns the NamespaceTag field if non-nil, zero value otherwise.

### GetNamespaceTagOk

`func (o *SpXOverlayCreationInput) GetNamespaceTagOk() (*string, bool)`

GetNamespaceTagOk returns a tuple with the NamespaceTag field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetNamespaceTag

`func (o *SpXOverlayCreationInput) SetNamespaceTag(v string)`

SetNamespaceTag sets NamespaceTag field to given value.

### HasNamespaceTag

`func (o *SpXOverlayCreationInput) HasNamespaceTag() bool`

HasNamespaceTag returns a boolean if a field has been set.

### GetOverlayId

`func (o *SpXOverlayCreationInput) GetOverlayId() string`

GetOverlayId returns the OverlayId field if non-nil, zero value otherwise.

### GetOverlayIdOk

`func (o *SpXOverlayCreationInput) GetOverlayIdOk() (*string, bool)`

GetOverlayIdOk returns a tuple with the OverlayId field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetOverlayId

`func (o *SpXOverlayCreationInput) SetOverlayId(v string)`

SetOverlayId sets OverlayId field to given value.


### GetRdMax

`func (o *SpXOverlayCreationInput) GetRdMax() int32`

GetRdMax returns the RdMax field if non-nil, zero value otherwise.

### GetRdMaxOk

`func (o *SpXOverlayCreationInput) GetRdMaxOk() (*int32, bool)`

GetRdMaxOk returns a tuple with the RdMax field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetRdMax

`func (o *SpXOverlayCreationInput) SetRdMax(v int32)`

SetRdMax sets RdMax field to given value.

### HasRdMax

`func (o *SpXOverlayCreationInput) HasRdMax() bool`

HasRdMax returns a boolean if a field has been set.

### GetRdMin

`func (o *SpXOverlayCreationInput) GetRdMin() int32`

GetRdMin returns the RdMin field if non-nil, zero value otherwise.

### GetRdMinOk

`func (o *SpXOverlayCreationInput) GetRdMinOk() (*int32, bool)`

GetRdMinOk returns a tuple with the RdMin field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetRdMin

`func (o *SpXOverlayCreationInput) SetRdMin(v int32)`

SetRdMin sets RdMin field to given value.

### HasRdMin

`func (o *SpXOverlayCreationInput) HasRdMin() bool`

HasRdMin returns a boolean if a field has been set.

### GetSite

`func (o *SpXOverlayCreationInput) GetSite() string`

GetSite returns the Site field if non-nil, zero value otherwise.

### GetSiteOk

`func (o *SpXOverlayCreationInput) GetSiteOk() (*string, bool)`

GetSiteOk returns a tuple with the Site field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetSite

`func (o *SpXOverlayCreationInput) SetSite(v string)`

SetSite sets Site field to given value.


### GetTenant

`func (o *SpXOverlayCreationInput) GetTenant() string`

GetTenant returns the Tenant field if non-nil, zero value otherwise.

### GetTenantOk

`func (o *SpXOverlayCreationInput) GetTenantOk() (*string, bool)`

GetTenantOk returns a tuple with the Tenant field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetTenant

`func (o *SpXOverlayCreationInput) SetTenant(v string)`

SetTenant sets Tenant field to given value.



[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


