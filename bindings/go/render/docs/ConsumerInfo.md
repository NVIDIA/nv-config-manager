# ConsumerInfo

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**Name** | **string** |  | 
**NumAckPending** | **int32** |  | 
**NumDelivered** | **int32** |  | 
**NumPending** | **int32** |  | 
**Stream** | **string** |  | 
**Subject** | **string** |  | 

## Methods

### NewConsumerInfo

`func NewConsumerInfo(name string, numAckPending int32, numDelivered int32, numPending int32, stream string, subject string, ) *ConsumerInfo`

NewConsumerInfo instantiates a new ConsumerInfo object
This constructor will assign default values to properties that have it defined,
and makes sure properties required by API are set, but the set of arguments
will change when the set of required properties is changed

### NewConsumerInfoWithDefaults

`func NewConsumerInfoWithDefaults() *ConsumerInfo`

NewConsumerInfoWithDefaults instantiates a new ConsumerInfo object
This constructor will only assign default values to properties that have it defined,
but it doesn't guarantee that properties required by API are set

### GetName

`func (o *ConsumerInfo) GetName() string`

GetName returns the Name field if non-nil, zero value otherwise.

### GetNameOk

`func (o *ConsumerInfo) GetNameOk() (*string, bool)`

GetNameOk returns a tuple with the Name field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetName

`func (o *ConsumerInfo) SetName(v string)`

SetName sets Name field to given value.


### GetNumAckPending

`func (o *ConsumerInfo) GetNumAckPending() int32`

GetNumAckPending returns the NumAckPending field if non-nil, zero value otherwise.

### GetNumAckPendingOk

`func (o *ConsumerInfo) GetNumAckPendingOk() (*int32, bool)`

GetNumAckPendingOk returns a tuple with the NumAckPending field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetNumAckPending

`func (o *ConsumerInfo) SetNumAckPending(v int32)`

SetNumAckPending sets NumAckPending field to given value.


### GetNumDelivered

`func (o *ConsumerInfo) GetNumDelivered() int32`

GetNumDelivered returns the NumDelivered field if non-nil, zero value otherwise.

### GetNumDeliveredOk

`func (o *ConsumerInfo) GetNumDeliveredOk() (*int32, bool)`

GetNumDeliveredOk returns a tuple with the NumDelivered field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetNumDelivered

`func (o *ConsumerInfo) SetNumDelivered(v int32)`

SetNumDelivered sets NumDelivered field to given value.


### GetNumPending

`func (o *ConsumerInfo) GetNumPending() int32`

GetNumPending returns the NumPending field if non-nil, zero value otherwise.

### GetNumPendingOk

`func (o *ConsumerInfo) GetNumPendingOk() (*int32, bool)`

GetNumPendingOk returns a tuple with the NumPending field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetNumPending

`func (o *ConsumerInfo) SetNumPending(v int32)`

SetNumPending sets NumPending field to given value.


### GetStream

`func (o *ConsumerInfo) GetStream() string`

GetStream returns the Stream field if non-nil, zero value otherwise.

### GetStreamOk

`func (o *ConsumerInfo) GetStreamOk() (*string, bool)`

GetStreamOk returns a tuple with the Stream field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetStream

`func (o *ConsumerInfo) SetStream(v string)`

SetStream sets Stream field to given value.


### GetSubject

`func (o *ConsumerInfo) GetSubject() string`

GetSubject returns the Subject field if non-nil, zero value otherwise.

### GetSubjectOk

`func (o *ConsumerInfo) GetSubjectOk() (*string, bool)`

GetSubjectOk returns a tuple with the Subject field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetSubject

`func (o *ConsumerInfo) SetSubject(v string)`

SetSubject sets Subject field to given value.



[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


