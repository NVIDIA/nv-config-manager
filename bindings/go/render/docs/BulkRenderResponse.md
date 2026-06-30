# BulkRenderResponse

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**FailedDevices** | Pointer to [**[]FailedDevice**](FailedDevice.md) |  | [optional] 
**MaxConcurrency** | Pointer to **NullableInt32** |  | [optional] 
**Message** | **string** |  | 
**QueuedCount** | **int32** |  | 
**TotalDevices** | Pointer to **int32** | Total number of devices targeted | [optional] [default to 0]

## Methods

### NewBulkRenderResponse

`func NewBulkRenderResponse(message string, queuedCount int32, ) *BulkRenderResponse`

NewBulkRenderResponse instantiates a new BulkRenderResponse object
This constructor will assign default values to properties that have it defined,
and makes sure properties required by API are set, but the set of arguments
will change when the set of required properties is changed

### NewBulkRenderResponseWithDefaults

`func NewBulkRenderResponseWithDefaults() *BulkRenderResponse`

NewBulkRenderResponseWithDefaults instantiates a new BulkRenderResponse object
This constructor will only assign default values to properties that have it defined,
but it doesn't guarantee that properties required by API are set

### GetFailedDevices

`func (o *BulkRenderResponse) GetFailedDevices() []FailedDevice`

GetFailedDevices returns the FailedDevices field if non-nil, zero value otherwise.

### GetFailedDevicesOk

`func (o *BulkRenderResponse) GetFailedDevicesOk() (*[]FailedDevice, bool)`

GetFailedDevicesOk returns a tuple with the FailedDevices field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetFailedDevices

`func (o *BulkRenderResponse) SetFailedDevices(v []FailedDevice)`

SetFailedDevices sets FailedDevices field to given value.

### HasFailedDevices

`func (o *BulkRenderResponse) HasFailedDevices() bool`

HasFailedDevices returns a boolean if a field has been set.

### SetFailedDevicesNil

`func (o *BulkRenderResponse) SetFailedDevicesNil(b bool)`

 SetFailedDevicesNil sets the value for FailedDevices to be an explicit nil

### UnsetFailedDevices
`func (o *BulkRenderResponse) UnsetFailedDevices()`

UnsetFailedDevices ensures that no value is present for FailedDevices, not even an explicit nil
### GetMaxConcurrency

`func (o *BulkRenderResponse) GetMaxConcurrency() int32`

GetMaxConcurrency returns the MaxConcurrency field if non-nil, zero value otherwise.

### GetMaxConcurrencyOk

`func (o *BulkRenderResponse) GetMaxConcurrencyOk() (*int32, bool)`

GetMaxConcurrencyOk returns a tuple with the MaxConcurrency field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetMaxConcurrency

`func (o *BulkRenderResponse) SetMaxConcurrency(v int32)`

SetMaxConcurrency sets MaxConcurrency field to given value.

### HasMaxConcurrency

`func (o *BulkRenderResponse) HasMaxConcurrency() bool`

HasMaxConcurrency returns a boolean if a field has been set.

### SetMaxConcurrencyNil

`func (o *BulkRenderResponse) SetMaxConcurrencyNil(b bool)`

 SetMaxConcurrencyNil sets the value for MaxConcurrency to be an explicit nil

### UnsetMaxConcurrency
`func (o *BulkRenderResponse) UnsetMaxConcurrency()`

UnsetMaxConcurrency ensures that no value is present for MaxConcurrency, not even an explicit nil
### GetMessage

`func (o *BulkRenderResponse) GetMessage() string`

GetMessage returns the Message field if non-nil, zero value otherwise.

### GetMessageOk

`func (o *BulkRenderResponse) GetMessageOk() (*string, bool)`

GetMessageOk returns a tuple with the Message field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetMessage

`func (o *BulkRenderResponse) SetMessage(v string)`

SetMessage sets Message field to given value.


### GetQueuedCount

`func (o *BulkRenderResponse) GetQueuedCount() int32`

GetQueuedCount returns the QueuedCount field if non-nil, zero value otherwise.

### GetQueuedCountOk

`func (o *BulkRenderResponse) GetQueuedCountOk() (*int32, bool)`

GetQueuedCountOk returns a tuple with the QueuedCount field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetQueuedCount

`func (o *BulkRenderResponse) SetQueuedCount(v int32)`

SetQueuedCount sets QueuedCount field to given value.


### GetTotalDevices

`func (o *BulkRenderResponse) GetTotalDevices() int32`

GetTotalDevices returns the TotalDevices field if non-nil, zero value otherwise.

### GetTotalDevicesOk

`func (o *BulkRenderResponse) GetTotalDevicesOk() (*int32, bool)`

GetTotalDevicesOk returns a tuple with the TotalDevices field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetTotalDevices

`func (o *BulkRenderResponse) SetTotalDevices(v int32)`

SetTotalDevices sets TotalDevices field to given value.

### HasTotalDevices

`func (o *BulkRenderResponse) HasTotalDevices() bool`

HasTotalDevices returns a boolean if a field has been set.


[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


