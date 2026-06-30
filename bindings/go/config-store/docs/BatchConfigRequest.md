# BatchConfigRequest

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**Files** | [**[]BatchConfigItem**](BatchConfigItem.md) | List of files to create/update | 

## Methods

### NewBatchConfigRequest

`func NewBatchConfigRequest(files []BatchConfigItem, ) *BatchConfigRequest`

NewBatchConfigRequest instantiates a new BatchConfigRequest object
This constructor will assign default values to properties that have it defined,
and makes sure properties required by API are set, but the set of arguments
will change when the set of required properties is changed

### NewBatchConfigRequestWithDefaults

`func NewBatchConfigRequestWithDefaults() *BatchConfigRequest`

NewBatchConfigRequestWithDefaults instantiates a new BatchConfigRequest object
This constructor will only assign default values to properties that have it defined,
but it doesn't guarantee that properties required by API are set

### GetFiles

`func (o *BatchConfigRequest) GetFiles() []BatchConfigItem`

GetFiles returns the Files field if non-nil, zero value otherwise.

### GetFilesOk

`func (o *BatchConfigRequest) GetFilesOk() (*[]BatchConfigItem, bool)`

GetFilesOk returns a tuple with the Files field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetFiles

`func (o *BatchConfigRequest) SetFiles(v []BatchConfigItem)`

SetFiles sets Files field to given value.



[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


