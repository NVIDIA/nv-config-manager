# ObjectInfo

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**Etag** | Pointer to **NullableString** |  | [optional] 
**Key** | **string** | Object key/path | 
**LastModified** | [**LastModified**](LastModified.md) |  | 
**Metadata** | Pointer to **map[string]string** |  | [optional] 
**Size** | **int32** | Object size in bytes | 
**Tags** | Pointer to **map[string]string** |  | [optional] 

## Methods

### NewObjectInfo

`func NewObjectInfo(key string, lastModified LastModified, size int32, ) *ObjectInfo`

NewObjectInfo instantiates a new ObjectInfo object
This constructor will assign default values to properties that have it defined,
and makes sure properties required by API are set, but the set of arguments
will change when the set of required properties is changed

### NewObjectInfoWithDefaults

`func NewObjectInfoWithDefaults() *ObjectInfo`

NewObjectInfoWithDefaults instantiates a new ObjectInfo object
This constructor will only assign default values to properties that have it defined,
but it doesn't guarantee that properties required by API are set

### GetEtag

`func (o *ObjectInfo) GetEtag() string`

GetEtag returns the Etag field if non-nil, zero value otherwise.

### GetEtagOk

`func (o *ObjectInfo) GetEtagOk() (*string, bool)`

GetEtagOk returns a tuple with the Etag field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetEtag

`func (o *ObjectInfo) SetEtag(v string)`

SetEtag sets Etag field to given value.

### HasEtag

`func (o *ObjectInfo) HasEtag() bool`

HasEtag returns a boolean if a field has been set.

### SetEtagNil

`func (o *ObjectInfo) SetEtagNil(b bool)`

 SetEtagNil sets the value for Etag to be an explicit nil

### UnsetEtag
`func (o *ObjectInfo) UnsetEtag()`

UnsetEtag ensures that no value is present for Etag, not even an explicit nil
### GetKey

`func (o *ObjectInfo) GetKey() string`

GetKey returns the Key field if non-nil, zero value otherwise.

### GetKeyOk

`func (o *ObjectInfo) GetKeyOk() (*string, bool)`

GetKeyOk returns a tuple with the Key field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetKey

`func (o *ObjectInfo) SetKey(v string)`

SetKey sets Key field to given value.


### GetLastModified

`func (o *ObjectInfo) GetLastModified() LastModified`

GetLastModified returns the LastModified field if non-nil, zero value otherwise.

### GetLastModifiedOk

`func (o *ObjectInfo) GetLastModifiedOk() (*LastModified, bool)`

GetLastModifiedOk returns a tuple with the LastModified field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetLastModified

`func (o *ObjectInfo) SetLastModified(v LastModified)`

SetLastModified sets LastModified field to given value.


### GetMetadata

`func (o *ObjectInfo) GetMetadata() map[string]string`

GetMetadata returns the Metadata field if non-nil, zero value otherwise.

### GetMetadataOk

`func (o *ObjectInfo) GetMetadataOk() (*map[string]string, bool)`

GetMetadataOk returns a tuple with the Metadata field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetMetadata

`func (o *ObjectInfo) SetMetadata(v map[string]string)`

SetMetadata sets Metadata field to given value.

### HasMetadata

`func (o *ObjectInfo) HasMetadata() bool`

HasMetadata returns a boolean if a field has been set.

### SetMetadataNil

`func (o *ObjectInfo) SetMetadataNil(b bool)`

 SetMetadataNil sets the value for Metadata to be an explicit nil

### UnsetMetadata
`func (o *ObjectInfo) UnsetMetadata()`

UnsetMetadata ensures that no value is present for Metadata, not even an explicit nil
### GetSize

`func (o *ObjectInfo) GetSize() int32`

GetSize returns the Size field if non-nil, zero value otherwise.

### GetSizeOk

`func (o *ObjectInfo) GetSizeOk() (*int32, bool)`

GetSizeOk returns a tuple with the Size field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetSize

`func (o *ObjectInfo) SetSize(v int32)`

SetSize sets Size field to given value.


### GetTags

`func (o *ObjectInfo) GetTags() map[string]string`

GetTags returns the Tags field if non-nil, zero value otherwise.

### GetTagsOk

`func (o *ObjectInfo) GetTagsOk() (*map[string]string, bool)`

GetTagsOk returns a tuple with the Tags field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetTags

`func (o *ObjectInfo) SetTags(v map[string]string)`

SetTags sets Tags field to given value.

### HasTags

`func (o *ObjectInfo) HasTags() bool`

HasTags returns a boolean if a field has been set.

### SetTagsNil

`func (o *ObjectInfo) SetTagsNil(b bool)`

 SetTagsNil sets the value for Tags to be an explicit nil

### UnsetTags
`func (o *ObjectInfo) UnsetTags()`

UnsetTags ensures that no value is present for Tags, not even an explicit nil

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


