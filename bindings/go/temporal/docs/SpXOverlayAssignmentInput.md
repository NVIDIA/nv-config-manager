# SpXOverlayAssignmentInput

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**Device** | [**Device1**](Device1.md) |  | 
**NamespaceTag** | Pointer to **string** |  | [optional] [default to "spectrumx"]
**OverlayId** | **string** | Identifier of the SpX overlay whose VRF will be assigned to the device and ports. | 
**PortNames** | **[]string** |  | 
**Site** | **string** |  | 

## Methods

### NewSpXOverlayAssignmentInput

`func NewSpXOverlayAssignmentInput(device Device1, overlayId string, portNames []string, site string, ) *SpXOverlayAssignmentInput`

NewSpXOverlayAssignmentInput instantiates a new SpXOverlayAssignmentInput object
This constructor will assign default values to properties that have it defined,
and makes sure properties required by API are set, but the set of arguments
will change when the set of required properties is changed

### NewSpXOverlayAssignmentInputWithDefaults

`func NewSpXOverlayAssignmentInputWithDefaults() *SpXOverlayAssignmentInput`

NewSpXOverlayAssignmentInputWithDefaults instantiates a new SpXOverlayAssignmentInput object
This constructor will only assign default values to properties that have it defined,
but it doesn't guarantee that properties required by API are set

### GetDevice

`func (o *SpXOverlayAssignmentInput) GetDevice() Device1`

GetDevice returns the Device field if non-nil, zero value otherwise.

### GetDeviceOk

`func (o *SpXOverlayAssignmentInput) GetDeviceOk() (*Device1, bool)`

GetDeviceOk returns a tuple with the Device field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetDevice

`func (o *SpXOverlayAssignmentInput) SetDevice(v Device1)`

SetDevice sets Device field to given value.


### GetNamespaceTag

`func (o *SpXOverlayAssignmentInput) GetNamespaceTag() string`

GetNamespaceTag returns the NamespaceTag field if non-nil, zero value otherwise.

### GetNamespaceTagOk

`func (o *SpXOverlayAssignmentInput) GetNamespaceTagOk() (*string, bool)`

GetNamespaceTagOk returns a tuple with the NamespaceTag field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetNamespaceTag

`func (o *SpXOverlayAssignmentInput) SetNamespaceTag(v string)`

SetNamespaceTag sets NamespaceTag field to given value.

### HasNamespaceTag

`func (o *SpXOverlayAssignmentInput) HasNamespaceTag() bool`

HasNamespaceTag returns a boolean if a field has been set.

### GetOverlayId

`func (o *SpXOverlayAssignmentInput) GetOverlayId() string`

GetOverlayId returns the OverlayId field if non-nil, zero value otherwise.

### GetOverlayIdOk

`func (o *SpXOverlayAssignmentInput) GetOverlayIdOk() (*string, bool)`

GetOverlayIdOk returns a tuple with the OverlayId field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetOverlayId

`func (o *SpXOverlayAssignmentInput) SetOverlayId(v string)`

SetOverlayId sets OverlayId field to given value.


### GetPortNames

`func (o *SpXOverlayAssignmentInput) GetPortNames() []string`

GetPortNames returns the PortNames field if non-nil, zero value otherwise.

### GetPortNamesOk

`func (o *SpXOverlayAssignmentInput) GetPortNamesOk() (*[]string, bool)`

GetPortNamesOk returns a tuple with the PortNames field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetPortNames

`func (o *SpXOverlayAssignmentInput) SetPortNames(v []string)`

SetPortNames sets PortNames field to given value.


### GetSite

`func (o *SpXOverlayAssignmentInput) GetSite() string`

GetSite returns the Site field if non-nil, zero value otherwise.

### GetSiteOk

`func (o *SpXOverlayAssignmentInput) GetSiteOk() (*string, bool)`

GetSiteOk returns a tuple with the Site field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetSite

`func (o *SpXOverlayAssignmentInput) SetSite(v string)`

SetSite sets Site field to given value.



[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


