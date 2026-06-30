# ConfigVersionResponse

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**Author** | **string** | Author email | 
**CommitMessage** | **string** | Commit message | 
**ContentHash** | **string** | SHA256 hash of content | 
**CreatedAt** | **time.Time** | Timestamp when version was created | 
**FileType** | [**FileType**](FileType.md) | Config file type (intended or backup) | 
**Version** | **int32** | Version number | 

## Methods

### NewConfigVersionResponse

`func NewConfigVersionResponse(author string, commitMessage string, contentHash string, createdAt time.Time, fileType FileType, version int32, ) *ConfigVersionResponse`

NewConfigVersionResponse instantiates a new ConfigVersionResponse object
This constructor will assign default values to properties that have it defined,
and makes sure properties required by API are set, but the set of arguments
will change when the set of required properties is changed

### NewConfigVersionResponseWithDefaults

`func NewConfigVersionResponseWithDefaults() *ConfigVersionResponse`

NewConfigVersionResponseWithDefaults instantiates a new ConfigVersionResponse object
This constructor will only assign default values to properties that have it defined,
but it doesn't guarantee that properties required by API are set

### GetAuthor

`func (o *ConfigVersionResponse) GetAuthor() string`

GetAuthor returns the Author field if non-nil, zero value otherwise.

### GetAuthorOk

`func (o *ConfigVersionResponse) GetAuthorOk() (*string, bool)`

GetAuthorOk returns a tuple with the Author field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetAuthor

`func (o *ConfigVersionResponse) SetAuthor(v string)`

SetAuthor sets Author field to given value.


### GetCommitMessage

`func (o *ConfigVersionResponse) GetCommitMessage() string`

GetCommitMessage returns the CommitMessage field if non-nil, zero value otherwise.

### GetCommitMessageOk

`func (o *ConfigVersionResponse) GetCommitMessageOk() (*string, bool)`

GetCommitMessageOk returns a tuple with the CommitMessage field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetCommitMessage

`func (o *ConfigVersionResponse) SetCommitMessage(v string)`

SetCommitMessage sets CommitMessage field to given value.


### GetContentHash

`func (o *ConfigVersionResponse) GetContentHash() string`

GetContentHash returns the ContentHash field if non-nil, zero value otherwise.

### GetContentHashOk

`func (o *ConfigVersionResponse) GetContentHashOk() (*string, bool)`

GetContentHashOk returns a tuple with the ContentHash field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetContentHash

`func (o *ConfigVersionResponse) SetContentHash(v string)`

SetContentHash sets ContentHash field to given value.


### GetCreatedAt

`func (o *ConfigVersionResponse) GetCreatedAt() time.Time`

GetCreatedAt returns the CreatedAt field if non-nil, zero value otherwise.

### GetCreatedAtOk

`func (o *ConfigVersionResponse) GetCreatedAtOk() (*time.Time, bool)`

GetCreatedAtOk returns a tuple with the CreatedAt field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetCreatedAt

`func (o *ConfigVersionResponse) SetCreatedAt(v time.Time)`

SetCreatedAt sets CreatedAt field to given value.


### GetFileType

`func (o *ConfigVersionResponse) GetFileType() FileType`

GetFileType returns the FileType field if non-nil, zero value otherwise.

### GetFileTypeOk

`func (o *ConfigVersionResponse) GetFileTypeOk() (*FileType, bool)`

GetFileTypeOk returns a tuple with the FileType field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetFileType

`func (o *ConfigVersionResponse) SetFileType(v FileType)`

SetFileType sets FileType field to given value.


### GetVersion

`func (o *ConfigVersionResponse) GetVersion() int32`

GetVersion returns the Version field if non-nil, zero value otherwise.

### GetVersionOk

`func (o *ConfigVersionResponse) GetVersionOk() (*int32, bool)`

GetVersionOk returns a tuple with the Version field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetVersion

`func (o *ConfigVersionResponse) SetVersion(v int32)`

SetVersion sets Version field to given value.



[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


