# DiffResponse

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**Device** | Pointer to [**NullableDeviceMetadata**](DeviceMetadata.md) |  | [optional] 
**DeviceUuid** | **string** | Device UUID | 
**Diff** | **string** | Unified diff output | 
**DiffStats** | **map[string]int32** | Statistics about the diff | 
**Filename** | **string** | File name | 
**FromVersion** | **int32** | Source version | 
**NewContent** | **string** | Content of target version | 
**OldContent** | **string** | Content of source version | 
**ToVersion** | **int32** | Target version | 

## Methods

### NewDiffResponse

`func NewDiffResponse(deviceUuid string, diff string, diffStats map[string]int32, filename string, fromVersion int32, newContent string, oldContent string, toVersion int32, ) *DiffResponse`

NewDiffResponse instantiates a new DiffResponse object
This constructor will assign default values to properties that have it defined,
and makes sure properties required by API are set, but the set of arguments
will change when the set of required properties is changed

### NewDiffResponseWithDefaults

`func NewDiffResponseWithDefaults() *DiffResponse`

NewDiffResponseWithDefaults instantiates a new DiffResponse object
This constructor will only assign default values to properties that have it defined,
but it doesn't guarantee that properties required by API are set

### GetDevice

`func (o *DiffResponse) GetDevice() DeviceMetadata`

GetDevice returns the Device field if non-nil, zero value otherwise.

### GetDeviceOk

`func (o *DiffResponse) GetDeviceOk() (*DeviceMetadata, bool)`

GetDeviceOk returns a tuple with the Device field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetDevice

`func (o *DiffResponse) SetDevice(v DeviceMetadata)`

SetDevice sets Device field to given value.

### HasDevice

`func (o *DiffResponse) HasDevice() bool`

HasDevice returns a boolean if a field has been set.

### SetDeviceNil

`func (o *DiffResponse) SetDeviceNil(b bool)`

 SetDeviceNil sets the value for Device to be an explicit nil

### UnsetDevice
`func (o *DiffResponse) UnsetDevice()`

UnsetDevice ensures that no value is present for Device, not even an explicit nil
### GetDeviceUuid

`func (o *DiffResponse) GetDeviceUuid() string`

GetDeviceUuid returns the DeviceUuid field if non-nil, zero value otherwise.

### GetDeviceUuidOk

`func (o *DiffResponse) GetDeviceUuidOk() (*string, bool)`

GetDeviceUuidOk returns a tuple with the DeviceUuid field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetDeviceUuid

`func (o *DiffResponse) SetDeviceUuid(v string)`

SetDeviceUuid sets DeviceUuid field to given value.


### GetDiff

`func (o *DiffResponse) GetDiff() string`

GetDiff returns the Diff field if non-nil, zero value otherwise.

### GetDiffOk

`func (o *DiffResponse) GetDiffOk() (*string, bool)`

GetDiffOk returns a tuple with the Diff field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetDiff

`func (o *DiffResponse) SetDiff(v string)`

SetDiff sets Diff field to given value.


### GetDiffStats

`func (o *DiffResponse) GetDiffStats() map[string]int32`

GetDiffStats returns the DiffStats field if non-nil, zero value otherwise.

### GetDiffStatsOk

`func (o *DiffResponse) GetDiffStatsOk() (*map[string]int32, bool)`

GetDiffStatsOk returns a tuple with the DiffStats field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetDiffStats

`func (o *DiffResponse) SetDiffStats(v map[string]int32)`

SetDiffStats sets DiffStats field to given value.


### GetFilename

`func (o *DiffResponse) GetFilename() string`

GetFilename returns the Filename field if non-nil, zero value otherwise.

### GetFilenameOk

`func (o *DiffResponse) GetFilenameOk() (*string, bool)`

GetFilenameOk returns a tuple with the Filename field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetFilename

`func (o *DiffResponse) SetFilename(v string)`

SetFilename sets Filename field to given value.


### GetFromVersion

`func (o *DiffResponse) GetFromVersion() int32`

GetFromVersion returns the FromVersion field if non-nil, zero value otherwise.

### GetFromVersionOk

`func (o *DiffResponse) GetFromVersionOk() (*int32, bool)`

GetFromVersionOk returns a tuple with the FromVersion field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetFromVersion

`func (o *DiffResponse) SetFromVersion(v int32)`

SetFromVersion sets FromVersion field to given value.


### GetNewContent

`func (o *DiffResponse) GetNewContent() string`

GetNewContent returns the NewContent field if non-nil, zero value otherwise.

### GetNewContentOk

`func (o *DiffResponse) GetNewContentOk() (*string, bool)`

GetNewContentOk returns a tuple with the NewContent field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetNewContent

`func (o *DiffResponse) SetNewContent(v string)`

SetNewContent sets NewContent field to given value.


### GetOldContent

`func (o *DiffResponse) GetOldContent() string`

GetOldContent returns the OldContent field if non-nil, zero value otherwise.

### GetOldContentOk

`func (o *DiffResponse) GetOldContentOk() (*string, bool)`

GetOldContentOk returns a tuple with the OldContent field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetOldContent

`func (o *DiffResponse) SetOldContent(v string)`

SetOldContent sets OldContent field to given value.


### GetToVersion

`func (o *DiffResponse) GetToVersion() int32`

GetToVersion returns the ToVersion field if non-nil, zero value otherwise.

### GetToVersionOk

`func (o *DiffResponse) GetToVersionOk() (*int32, bool)`

GetToVersionOk returns a tuple with the ToVersion field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetToVersion

`func (o *DiffResponse) SetToVersion(v int32)`

SetToVersion sets ToVersion field to given value.



[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


