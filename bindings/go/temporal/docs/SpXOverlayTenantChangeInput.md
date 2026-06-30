# SpXOverlayTenantChangeInput

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**DeviceId** | **string** |  | 
**NamespaceTag** | Pointer to **string** |  | [optional] [default to "spectrumx"]
**OverlayId** | **string** | Identifier of the SpX overlay to assign and deploy tenant configuration for. | 
**PortNames** | **[]string** |  | 
**Site** | **string** |  | 

## Methods

### NewSpXOverlayTenantChangeInput

`func NewSpXOverlayTenantChangeInput(deviceId string, overlayId string, portNames []string, site string, ) *SpXOverlayTenantChangeInput`

NewSpXOverlayTenantChangeInput instantiates a new SpXOverlayTenantChangeInput object
This constructor will assign default values to properties that have it defined,
and makes sure properties required by API are set, but the set of arguments
will change when the set of required properties is changed

### NewSpXOverlayTenantChangeInputWithDefaults

`func NewSpXOverlayTenantChangeInputWithDefaults() *SpXOverlayTenantChangeInput`

NewSpXOverlayTenantChangeInputWithDefaults instantiates a new SpXOverlayTenantChangeInput object
This constructor will only assign default values to properties that have it defined,
but it doesn't guarantee that properties required by API are set

### GetDeviceId

`func (o *SpXOverlayTenantChangeInput) GetDeviceId() string`

GetDeviceId returns the DeviceId field if non-nil, zero value otherwise.

### GetDeviceIdOk

`func (o *SpXOverlayTenantChangeInput) GetDeviceIdOk() (*string, bool)`

GetDeviceIdOk returns a tuple with the DeviceId field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetDeviceId

`func (o *SpXOverlayTenantChangeInput) SetDeviceId(v string)`

SetDeviceId sets DeviceId field to given value.


### GetNamespaceTag

`func (o *SpXOverlayTenantChangeInput) GetNamespaceTag() string`

GetNamespaceTag returns the NamespaceTag field if non-nil, zero value otherwise.

### GetNamespaceTagOk

`func (o *SpXOverlayTenantChangeInput) GetNamespaceTagOk() (*string, bool)`

GetNamespaceTagOk returns a tuple with the NamespaceTag field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetNamespaceTag

`func (o *SpXOverlayTenantChangeInput) SetNamespaceTag(v string)`

SetNamespaceTag sets NamespaceTag field to given value.

### HasNamespaceTag

`func (o *SpXOverlayTenantChangeInput) HasNamespaceTag() bool`

HasNamespaceTag returns a boolean if a field has been set.

### GetOverlayId

`func (o *SpXOverlayTenantChangeInput) GetOverlayId() string`

GetOverlayId returns the OverlayId field if non-nil, zero value otherwise.

### GetOverlayIdOk

`func (o *SpXOverlayTenantChangeInput) GetOverlayIdOk() (*string, bool)`

GetOverlayIdOk returns a tuple with the OverlayId field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetOverlayId

`func (o *SpXOverlayTenantChangeInput) SetOverlayId(v string)`

SetOverlayId sets OverlayId field to given value.


### GetPortNames

`func (o *SpXOverlayTenantChangeInput) GetPortNames() []string`

GetPortNames returns the PortNames field if non-nil, zero value otherwise.

### GetPortNamesOk

`func (o *SpXOverlayTenantChangeInput) GetPortNamesOk() (*[]string, bool)`

GetPortNamesOk returns a tuple with the PortNames field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetPortNames

`func (o *SpXOverlayTenantChangeInput) SetPortNames(v []string)`

SetPortNames sets PortNames field to given value.


### GetSite

`func (o *SpXOverlayTenantChangeInput) GetSite() string`

GetSite returns the Site field if non-nil, zero value otherwise.

### GetSiteOk

`func (o *SpXOverlayTenantChangeInput) GetSiteOk() (*string, bool)`

GetSiteOk returns a tuple with the Site field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetSite

`func (o *SpXOverlayTenantChangeInput) SetSite(v string)`

SetSite sets Site field to given value.



[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


