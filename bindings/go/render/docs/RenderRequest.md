# RenderRequest

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**CommitMessage** | Pointer to **NullableString** |  | [optional] 

## Methods

### NewRenderRequest

`func NewRenderRequest() *RenderRequest`

NewRenderRequest instantiates a new RenderRequest object
This constructor will assign default values to properties that have it defined,
and makes sure properties required by API are set, but the set of arguments
will change when the set of required properties is changed

### NewRenderRequestWithDefaults

`func NewRenderRequestWithDefaults() *RenderRequest`

NewRenderRequestWithDefaults instantiates a new RenderRequest object
This constructor will only assign default values to properties that have it defined,
but it doesn't guarantee that properties required by API are set

### GetCommitMessage

`func (o *RenderRequest) GetCommitMessage() string`

GetCommitMessage returns the CommitMessage field if non-nil, zero value otherwise.

### GetCommitMessageOk

`func (o *RenderRequest) GetCommitMessageOk() (*string, bool)`

GetCommitMessageOk returns a tuple with the CommitMessage field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetCommitMessage

`func (o *RenderRequest) SetCommitMessage(v string)`

SetCommitMessage sets CommitMessage field to given value.

### HasCommitMessage

`func (o *RenderRequest) HasCommitMessage() bool`

HasCommitMessage returns a boolean if a field has been set.

### SetCommitMessageNil

`func (o *RenderRequest) SetCommitMessageNil(b bool)`

 SetCommitMessageNil sets the value for CommitMessage to be an explicit nil

### UnsetCommitMessage
`func (o *RenderRequest) UnsetCommitMessage()`

UnsetCommitMessage ensures that no value is present for CommitMessage, not even an explicit nil

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


