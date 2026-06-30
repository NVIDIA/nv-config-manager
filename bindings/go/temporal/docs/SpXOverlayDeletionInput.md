# SpXOverlayDeletionInput

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**NamespaceTag** | Pointer to **string** |  | [optional] [default to "spectrumx"]
**OverlayId** | **string** | Identifier of the SpX overlay to delete. | 
**Site** | **string** |  | 

## Methods

### NewSpXOverlayDeletionInput

`func NewSpXOverlayDeletionInput(overlayId string, site string, ) *SpXOverlayDeletionInput`

NewSpXOverlayDeletionInput instantiates a new SpXOverlayDeletionInput object
This constructor will assign default values to properties that have it defined,
and makes sure properties required by API are set, but the set of arguments
will change when the set of required properties is changed

### NewSpXOverlayDeletionInputWithDefaults

`func NewSpXOverlayDeletionInputWithDefaults() *SpXOverlayDeletionInput`

NewSpXOverlayDeletionInputWithDefaults instantiates a new SpXOverlayDeletionInput object
This constructor will only assign default values to properties that have it defined,
but it doesn't guarantee that properties required by API are set

### GetNamespaceTag

`func (o *SpXOverlayDeletionInput) GetNamespaceTag() string`

GetNamespaceTag returns the NamespaceTag field if non-nil, zero value otherwise.

### GetNamespaceTagOk

`func (o *SpXOverlayDeletionInput) GetNamespaceTagOk() (*string, bool)`

GetNamespaceTagOk returns a tuple with the NamespaceTag field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetNamespaceTag

`func (o *SpXOverlayDeletionInput) SetNamespaceTag(v string)`

SetNamespaceTag sets NamespaceTag field to given value.

### HasNamespaceTag

`func (o *SpXOverlayDeletionInput) HasNamespaceTag() bool`

HasNamespaceTag returns a boolean if a field has been set.

### GetOverlayId

`func (o *SpXOverlayDeletionInput) GetOverlayId() string`

GetOverlayId returns the OverlayId field if non-nil, zero value otherwise.

### GetOverlayIdOk

`func (o *SpXOverlayDeletionInput) GetOverlayIdOk() (*string, bool)`

GetOverlayIdOk returns a tuple with the OverlayId field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetOverlayId

`func (o *SpXOverlayDeletionInput) SetOverlayId(v string)`

SetOverlayId sets OverlayId field to given value.


### GetSite

`func (o *SpXOverlayDeletionInput) GetSite() string`

GetSite returns the Site field if non-nil, zero value otherwise.

### GetSiteOk

`func (o *SpXOverlayDeletionInput) GetSiteOk() (*string, bool)`

GetSiteOk returns a tuple with the Site field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetSite

`func (o *SpXOverlayDeletionInput) SetSite(v string)`

SetSite sets Site field to given value.



[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


