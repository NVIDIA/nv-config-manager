# RenderResponse

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**UpdatedFiles** | Pointer to [**[]FileCommit**](FileCommit.md) | Files that changed during the render | [optional] 

## Methods

### NewRenderResponse

`func NewRenderResponse() *RenderResponse`

NewRenderResponse instantiates a new RenderResponse object
This constructor will assign default values to properties that have it defined,
and makes sure properties required by API are set, but the set of arguments
will change when the set of required properties is changed

### NewRenderResponseWithDefaults

`func NewRenderResponseWithDefaults() *RenderResponse`

NewRenderResponseWithDefaults instantiates a new RenderResponse object
This constructor will only assign default values to properties that have it defined,
but it doesn't guarantee that properties required by API are set

### GetUpdatedFiles

`func (o *RenderResponse) GetUpdatedFiles() []FileCommit`

GetUpdatedFiles returns the UpdatedFiles field if non-nil, zero value otherwise.

### GetUpdatedFilesOk

`func (o *RenderResponse) GetUpdatedFilesOk() (*[]FileCommit, bool)`

GetUpdatedFilesOk returns a tuple with the UpdatedFiles field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetUpdatedFiles

`func (o *RenderResponse) SetUpdatedFiles(v []FileCommit)`

SetUpdatedFiles sets UpdatedFiles field to given value.

### HasUpdatedFiles

`func (o *RenderResponse) HasUpdatedFiles() bool`

HasUpdatedFiles returns a boolean if a field has been set.


[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


