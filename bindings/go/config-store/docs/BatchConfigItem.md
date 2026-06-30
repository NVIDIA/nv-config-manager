# BatchConfigItem

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**Author** | **string** | Author email | 
**CommitMessage** | **string** | Commit message | 
**Content** | **string** | Configuration file content | 
**CreatedAt** | Pointer to **NullableTime** |  | [optional] 
**FileType** | Pointer to [**FileType**](FileType.md) | Config file type (intended or backup) | [optional] [default to INTENDED]
**Filename** | **string** | File name | 

## Methods

### NewBatchConfigItem

`func NewBatchConfigItem(author string, commitMessage string, content string, filename string, ) *BatchConfigItem`

NewBatchConfigItem instantiates a new BatchConfigItem object
This constructor will assign default values to properties that have it defined,
and makes sure properties required by API are set, but the set of arguments
will change when the set of required properties is changed

### NewBatchConfigItemWithDefaults

`func NewBatchConfigItemWithDefaults() *BatchConfigItem`

NewBatchConfigItemWithDefaults instantiates a new BatchConfigItem object
This constructor will only assign default values to properties that have it defined,
but it doesn't guarantee that properties required by API are set

### GetAuthor

`func (o *BatchConfigItem) GetAuthor() string`

GetAuthor returns the Author field if non-nil, zero value otherwise.

### GetAuthorOk

`func (o *BatchConfigItem) GetAuthorOk() (*string, bool)`

GetAuthorOk returns a tuple with the Author field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetAuthor

`func (o *BatchConfigItem) SetAuthor(v string)`

SetAuthor sets Author field to given value.


### GetCommitMessage

`func (o *BatchConfigItem) GetCommitMessage() string`

GetCommitMessage returns the CommitMessage field if non-nil, zero value otherwise.

### GetCommitMessageOk

`func (o *BatchConfigItem) GetCommitMessageOk() (*string, bool)`

GetCommitMessageOk returns a tuple with the CommitMessage field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetCommitMessage

`func (o *BatchConfigItem) SetCommitMessage(v string)`

SetCommitMessage sets CommitMessage field to given value.


### GetContent

`func (o *BatchConfigItem) GetContent() string`

GetContent returns the Content field if non-nil, zero value otherwise.

### GetContentOk

`func (o *BatchConfigItem) GetContentOk() (*string, bool)`

GetContentOk returns a tuple with the Content field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetContent

`func (o *BatchConfigItem) SetContent(v string)`

SetContent sets Content field to given value.


### GetCreatedAt

`func (o *BatchConfigItem) GetCreatedAt() time.Time`

GetCreatedAt returns the CreatedAt field if non-nil, zero value otherwise.

### GetCreatedAtOk

`func (o *BatchConfigItem) GetCreatedAtOk() (*time.Time, bool)`

GetCreatedAtOk returns a tuple with the CreatedAt field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetCreatedAt

`func (o *BatchConfigItem) SetCreatedAt(v time.Time)`

SetCreatedAt sets CreatedAt field to given value.

### HasCreatedAt

`func (o *BatchConfigItem) HasCreatedAt() bool`

HasCreatedAt returns a boolean if a field has been set.

### SetCreatedAtNil

`func (o *BatchConfigItem) SetCreatedAtNil(b bool)`

 SetCreatedAtNil sets the value for CreatedAt to be an explicit nil

### UnsetCreatedAt
`func (o *BatchConfigItem) UnsetCreatedAt()`

UnsetCreatedAt ensures that no value is present for CreatedAt, not even an explicit nil
### GetFileType

`func (o *BatchConfigItem) GetFileType() FileType`

GetFileType returns the FileType field if non-nil, zero value otherwise.

### GetFileTypeOk

`func (o *BatchConfigItem) GetFileTypeOk() (*FileType, bool)`

GetFileTypeOk returns a tuple with the FileType field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetFileType

`func (o *BatchConfigItem) SetFileType(v FileType)`

SetFileType sets FileType field to given value.

### HasFileType

`func (o *BatchConfigItem) HasFileType() bool`

HasFileType returns a boolean if a field has been set.

### GetFilename

`func (o *BatchConfigItem) GetFilename() string`

GetFilename returns the Filename field if non-nil, zero value otherwise.

### GetFilenameOk

`func (o *BatchConfigItem) GetFilenameOk() (*string, bool)`

GetFilenameOk returns a tuple with the Filename field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetFilename

`func (o *BatchConfigItem) SetFilename(v string)`

SetFilename sets Filename field to given value.



[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


