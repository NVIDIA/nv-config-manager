# ConfigCreateRequest

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**Author** | **string** | Author email | 
**CommitMessage** | **string** | Commit message describing the change | 
**Content** | **string** | Configuration file content | 
**CreatedAt** | Pointer to **NullableTime** |  | [optional] 
**FileType** | Pointer to [**FileType**](FileType.md) | Config file type (intended or backup) | [optional] [default to INTENDED]

## Methods

### NewConfigCreateRequest

`func NewConfigCreateRequest(author string, commitMessage string, content string, ) *ConfigCreateRequest`

NewConfigCreateRequest instantiates a new ConfigCreateRequest object
This constructor will assign default values to properties that have it defined,
and makes sure properties required by API are set, but the set of arguments
will change when the set of required properties is changed

### NewConfigCreateRequestWithDefaults

`func NewConfigCreateRequestWithDefaults() *ConfigCreateRequest`

NewConfigCreateRequestWithDefaults instantiates a new ConfigCreateRequest object
This constructor will only assign default values to properties that have it defined,
but it doesn't guarantee that properties required by API are set

### GetAuthor

`func (o *ConfigCreateRequest) GetAuthor() string`

GetAuthor returns the Author field if non-nil, zero value otherwise.

### GetAuthorOk

`func (o *ConfigCreateRequest) GetAuthorOk() (*string, bool)`

GetAuthorOk returns a tuple with the Author field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetAuthor

`func (o *ConfigCreateRequest) SetAuthor(v string)`

SetAuthor sets Author field to given value.


### GetCommitMessage

`func (o *ConfigCreateRequest) GetCommitMessage() string`

GetCommitMessage returns the CommitMessage field if non-nil, zero value otherwise.

### GetCommitMessageOk

`func (o *ConfigCreateRequest) GetCommitMessageOk() (*string, bool)`

GetCommitMessageOk returns a tuple with the CommitMessage field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetCommitMessage

`func (o *ConfigCreateRequest) SetCommitMessage(v string)`

SetCommitMessage sets CommitMessage field to given value.


### GetContent

`func (o *ConfigCreateRequest) GetContent() string`

GetContent returns the Content field if non-nil, zero value otherwise.

### GetContentOk

`func (o *ConfigCreateRequest) GetContentOk() (*string, bool)`

GetContentOk returns a tuple with the Content field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetContent

`func (o *ConfigCreateRequest) SetContent(v string)`

SetContent sets Content field to given value.


### GetCreatedAt

`func (o *ConfigCreateRequest) GetCreatedAt() time.Time`

GetCreatedAt returns the CreatedAt field if non-nil, zero value otherwise.

### GetCreatedAtOk

`func (o *ConfigCreateRequest) GetCreatedAtOk() (*time.Time, bool)`

GetCreatedAtOk returns a tuple with the CreatedAt field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetCreatedAt

`func (o *ConfigCreateRequest) SetCreatedAt(v time.Time)`

SetCreatedAt sets CreatedAt field to given value.

### HasCreatedAt

`func (o *ConfigCreateRequest) HasCreatedAt() bool`

HasCreatedAt returns a boolean if a field has been set.

### SetCreatedAtNil

`func (o *ConfigCreateRequest) SetCreatedAtNil(b bool)`

 SetCreatedAtNil sets the value for CreatedAt to be an explicit nil

### UnsetCreatedAt
`func (o *ConfigCreateRequest) UnsetCreatedAt()`

UnsetCreatedAt ensures that no value is present for CreatedAt, not even an explicit nil
### GetFileType

`func (o *ConfigCreateRequest) GetFileType() FileType`

GetFileType returns the FileType field if non-nil, zero value otherwise.

### GetFileTypeOk

`func (o *ConfigCreateRequest) GetFileTypeOk() (*FileType, bool)`

GetFileTypeOk returns a tuple with the FileType field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetFileType

`func (o *ConfigCreateRequest) SetFileType(v FileType)`

SetFileType sets FileType field to given value.

### HasFileType

`func (o *ConfigCreateRequest) HasFileType() bool`

HasFileType returns a boolean if a field has been set.


[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


