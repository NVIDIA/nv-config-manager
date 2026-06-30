# BackupInput

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**DeviceId** | **string** |  | 
**IntendedConfigCommitId** | **NullableString** |  | 
**Trigger** | [**TriggerEnum**](TriggerEnum.md) |  | 
**User** | **NullableString** |  | 
**UserDomain** | **NullableString** |  | 
**WorkflowId** | **NullableString** |  | 

## Methods

### NewBackupInput

`func NewBackupInput(deviceId string, intendedConfigCommitId NullableString, trigger TriggerEnum, user NullableString, userDomain NullableString, workflowId NullableString, ) *BackupInput`

NewBackupInput instantiates a new BackupInput object
This constructor will assign default values to properties that have it defined,
and makes sure properties required by API are set, but the set of arguments
will change when the set of required properties is changed

### NewBackupInputWithDefaults

`func NewBackupInputWithDefaults() *BackupInput`

NewBackupInputWithDefaults instantiates a new BackupInput object
This constructor will only assign default values to properties that have it defined,
but it doesn't guarantee that properties required by API are set

### GetDeviceId

`func (o *BackupInput) GetDeviceId() string`

GetDeviceId returns the DeviceId field if non-nil, zero value otherwise.

### GetDeviceIdOk

`func (o *BackupInput) GetDeviceIdOk() (*string, bool)`

GetDeviceIdOk returns a tuple with the DeviceId field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetDeviceId

`func (o *BackupInput) SetDeviceId(v string)`

SetDeviceId sets DeviceId field to given value.


### GetIntendedConfigCommitId

`func (o *BackupInput) GetIntendedConfigCommitId() string`

GetIntendedConfigCommitId returns the IntendedConfigCommitId field if non-nil, zero value otherwise.

### GetIntendedConfigCommitIdOk

`func (o *BackupInput) GetIntendedConfigCommitIdOk() (*string, bool)`

GetIntendedConfigCommitIdOk returns a tuple with the IntendedConfigCommitId field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetIntendedConfigCommitId

`func (o *BackupInput) SetIntendedConfigCommitId(v string)`

SetIntendedConfigCommitId sets IntendedConfigCommitId field to given value.


### SetIntendedConfigCommitIdNil

`func (o *BackupInput) SetIntendedConfigCommitIdNil(b bool)`

 SetIntendedConfigCommitIdNil sets the value for IntendedConfigCommitId to be an explicit nil

### UnsetIntendedConfigCommitId
`func (o *BackupInput) UnsetIntendedConfigCommitId()`

UnsetIntendedConfigCommitId ensures that no value is present for IntendedConfigCommitId, not even an explicit nil
### GetTrigger

`func (o *BackupInput) GetTrigger() TriggerEnum`

GetTrigger returns the Trigger field if non-nil, zero value otherwise.

### GetTriggerOk

`func (o *BackupInput) GetTriggerOk() (*TriggerEnum, bool)`

GetTriggerOk returns a tuple with the Trigger field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetTrigger

`func (o *BackupInput) SetTrigger(v TriggerEnum)`

SetTrigger sets Trigger field to given value.


### GetUser

`func (o *BackupInput) GetUser() string`

GetUser returns the User field if non-nil, zero value otherwise.

### GetUserOk

`func (o *BackupInput) GetUserOk() (*string, bool)`

GetUserOk returns a tuple with the User field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetUser

`func (o *BackupInput) SetUser(v string)`

SetUser sets User field to given value.


### SetUserNil

`func (o *BackupInput) SetUserNil(b bool)`

 SetUserNil sets the value for User to be an explicit nil

### UnsetUser
`func (o *BackupInput) UnsetUser()`

UnsetUser ensures that no value is present for User, not even an explicit nil
### GetUserDomain

`func (o *BackupInput) GetUserDomain() string`

GetUserDomain returns the UserDomain field if non-nil, zero value otherwise.

### GetUserDomainOk

`func (o *BackupInput) GetUserDomainOk() (*string, bool)`

GetUserDomainOk returns a tuple with the UserDomain field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetUserDomain

`func (o *BackupInput) SetUserDomain(v string)`

SetUserDomain sets UserDomain field to given value.


### SetUserDomainNil

`func (o *BackupInput) SetUserDomainNil(b bool)`

 SetUserDomainNil sets the value for UserDomain to be an explicit nil

### UnsetUserDomain
`func (o *BackupInput) UnsetUserDomain()`

UnsetUserDomain ensures that no value is present for UserDomain, not even an explicit nil
### GetWorkflowId

`func (o *BackupInput) GetWorkflowId() string`

GetWorkflowId returns the WorkflowId field if non-nil, zero value otherwise.

### GetWorkflowIdOk

`func (o *BackupInput) GetWorkflowIdOk() (*string, bool)`

GetWorkflowIdOk returns a tuple with the WorkflowId field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetWorkflowId

`func (o *BackupInput) SetWorkflowId(v string)`

SetWorkflowId sets WorkflowId field to given value.


### SetWorkflowIdNil

`func (o *BackupInput) SetWorkflowIdNil(b bool)`

 SetWorkflowIdNil sets the value for WorkflowId to be an explicit nil

### UnsetWorkflowId
`func (o *BackupInput) UnsetWorkflowId()`

UnsetWorkflowId ensures that no value is present for WorkflowId, not even an explicit nil

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


