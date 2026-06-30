# DiffGroup

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**Devices** | [**[]DeviceDiffData**](DeviceDiffData.md) |  | 
**DiffContent** | **string** |  | 
**DiffHash** | **string** |  | 

## Methods

### NewDiffGroup

`func NewDiffGroup(devices []DeviceDiffData, diffContent string, diffHash string, ) *DiffGroup`

NewDiffGroup instantiates a new DiffGroup object
This constructor will assign default values to properties that have it defined,
and makes sure properties required by API are set, but the set of arguments
will change when the set of required properties is changed

### NewDiffGroupWithDefaults

`func NewDiffGroupWithDefaults() *DiffGroup`

NewDiffGroupWithDefaults instantiates a new DiffGroup object
This constructor will only assign default values to properties that have it defined,
but it doesn't guarantee that properties required by API are set

### GetDevices

`func (o *DiffGroup) GetDevices() []DeviceDiffData`

GetDevices returns the Devices field if non-nil, zero value otherwise.

### GetDevicesOk

`func (o *DiffGroup) GetDevicesOk() (*[]DeviceDiffData, bool)`

GetDevicesOk returns a tuple with the Devices field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetDevices

`func (o *DiffGroup) SetDevices(v []DeviceDiffData)`

SetDevices sets Devices field to given value.


### GetDiffContent

`func (o *DiffGroup) GetDiffContent() string`

GetDiffContent returns the DiffContent field if non-nil, zero value otherwise.

### GetDiffContentOk

`func (o *DiffGroup) GetDiffContentOk() (*string, bool)`

GetDiffContentOk returns a tuple with the DiffContent field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetDiffContent

`func (o *DiffGroup) SetDiffContent(v string)`

SetDiffContent sets DiffContent field to given value.


### GetDiffHash

`func (o *DiffGroup) GetDiffHash() string`

GetDiffHash returns the DiffHash field if non-nil, zero value otherwise.

### GetDiffHashOk

`func (o *DiffGroup) GetDiffHashOk() (*string, bool)`

GetDiffHashOk returns a tuple with the DiffHash field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetDiffHash

`func (o *DiffGroup) SetDiffHash(v string)`

SetDiffHash sets DiffHash field to given value.



[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


