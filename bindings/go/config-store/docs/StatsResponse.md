# StatsResponse

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**StorageBytes** | **int32** | Total storage used in bytes (compressed) | 
**StorageMb** | **float32** | Total storage used in MB (compressed) | 
**TotalConfigVersions** | **int32** | Total number of config file versions | 
**UniqueDevices** | **int32** | Number of unique devices with configs | 
**UniqueFiles** | **int32** | Number of unique config files (device + filename) | 

## Methods

### NewStatsResponse

`func NewStatsResponse(storageBytes int32, storageMb float32, totalConfigVersions int32, uniqueDevices int32, uniqueFiles int32, ) *StatsResponse`

NewStatsResponse instantiates a new StatsResponse object
This constructor will assign default values to properties that have it defined,
and makes sure properties required by API are set, but the set of arguments
will change when the set of required properties is changed

### NewStatsResponseWithDefaults

`func NewStatsResponseWithDefaults() *StatsResponse`

NewStatsResponseWithDefaults instantiates a new StatsResponse object
This constructor will only assign default values to properties that have it defined,
but it doesn't guarantee that properties required by API are set

### GetStorageBytes

`func (o *StatsResponse) GetStorageBytes() int32`

GetStorageBytes returns the StorageBytes field if non-nil, zero value otherwise.

### GetStorageBytesOk

`func (o *StatsResponse) GetStorageBytesOk() (*int32, bool)`

GetStorageBytesOk returns a tuple with the StorageBytes field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetStorageBytes

`func (o *StatsResponse) SetStorageBytes(v int32)`

SetStorageBytes sets StorageBytes field to given value.


### GetStorageMb

`func (o *StatsResponse) GetStorageMb() float32`

GetStorageMb returns the StorageMb field if non-nil, zero value otherwise.

### GetStorageMbOk

`func (o *StatsResponse) GetStorageMbOk() (*float32, bool)`

GetStorageMbOk returns a tuple with the StorageMb field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetStorageMb

`func (o *StatsResponse) SetStorageMb(v float32)`

SetStorageMb sets StorageMb field to given value.


### GetTotalConfigVersions

`func (o *StatsResponse) GetTotalConfigVersions() int32`

GetTotalConfigVersions returns the TotalConfigVersions field if non-nil, zero value otherwise.

### GetTotalConfigVersionsOk

`func (o *StatsResponse) GetTotalConfigVersionsOk() (*int32, bool)`

GetTotalConfigVersionsOk returns a tuple with the TotalConfigVersions field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetTotalConfigVersions

`func (o *StatsResponse) SetTotalConfigVersions(v int32)`

SetTotalConfigVersions sets TotalConfigVersions field to given value.


### GetUniqueDevices

`func (o *StatsResponse) GetUniqueDevices() int32`

GetUniqueDevices returns the UniqueDevices field if non-nil, zero value otherwise.

### GetUniqueDevicesOk

`func (o *StatsResponse) GetUniqueDevicesOk() (*int32, bool)`

GetUniqueDevicesOk returns a tuple with the UniqueDevices field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetUniqueDevices

`func (o *StatsResponse) SetUniqueDevices(v int32)`

SetUniqueDevices sets UniqueDevices field to given value.


### GetUniqueFiles

`func (o *StatsResponse) GetUniqueFiles() int32`

GetUniqueFiles returns the UniqueFiles field if non-nil, zero value otherwise.

### GetUniqueFilesOk

`func (o *StatsResponse) GetUniqueFilesOk() (*int32, bool)`

GetUniqueFilesOk returns a tuple with the UniqueFiles field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetUniqueFiles

`func (o *StatsResponse) SetUniqueFiles(v int32)`

SetUniqueFiles sets UniqueFiles field to given value.



[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


