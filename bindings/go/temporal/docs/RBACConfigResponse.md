# RBACConfigResponse

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**Error** | Pointer to **NullableString** |  | [optional] 
**FileExists** | **bool** |  | 
**Status** | **string** |  | 
**Workflows** | Pointer to [**map[string]WorkflowRoles**](WorkflowRoles.md) |  | [optional] 
**WorkflowsCount** | Pointer to **NullableInt32** |  | [optional] 

## Methods

### NewRBACConfigResponse

`func NewRBACConfigResponse(fileExists bool, status string, ) *RBACConfigResponse`

NewRBACConfigResponse instantiates a new RBACConfigResponse object
This constructor will assign default values to properties that have it defined,
and makes sure properties required by API are set, but the set of arguments
will change when the set of required properties is changed

### NewRBACConfigResponseWithDefaults

`func NewRBACConfigResponseWithDefaults() *RBACConfigResponse`

NewRBACConfigResponseWithDefaults instantiates a new RBACConfigResponse object
This constructor will only assign default values to properties that have it defined,
but it doesn't guarantee that properties required by API are set

### GetError

`func (o *RBACConfigResponse) GetError() string`

GetError returns the Error field if non-nil, zero value otherwise.

### GetErrorOk

`func (o *RBACConfigResponse) GetErrorOk() (*string, bool)`

GetErrorOk returns a tuple with the Error field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetError

`func (o *RBACConfigResponse) SetError(v string)`

SetError sets Error field to given value.

### HasError

`func (o *RBACConfigResponse) HasError() bool`

HasError returns a boolean if a field has been set.

### SetErrorNil

`func (o *RBACConfigResponse) SetErrorNil(b bool)`

 SetErrorNil sets the value for Error to be an explicit nil

### UnsetError
`func (o *RBACConfigResponse) UnsetError()`

UnsetError ensures that no value is present for Error, not even an explicit nil
### GetFileExists

`func (o *RBACConfigResponse) GetFileExists() bool`

GetFileExists returns the FileExists field if non-nil, zero value otherwise.

### GetFileExistsOk

`func (o *RBACConfigResponse) GetFileExistsOk() (*bool, bool)`

GetFileExistsOk returns a tuple with the FileExists field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetFileExists

`func (o *RBACConfigResponse) SetFileExists(v bool)`

SetFileExists sets FileExists field to given value.


### GetStatus

`func (o *RBACConfigResponse) GetStatus() string`

GetStatus returns the Status field if non-nil, zero value otherwise.

### GetStatusOk

`func (o *RBACConfigResponse) GetStatusOk() (*string, bool)`

GetStatusOk returns a tuple with the Status field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetStatus

`func (o *RBACConfigResponse) SetStatus(v string)`

SetStatus sets Status field to given value.


### GetWorkflows

`func (o *RBACConfigResponse) GetWorkflows() map[string]WorkflowRoles`

GetWorkflows returns the Workflows field if non-nil, zero value otherwise.

### GetWorkflowsOk

`func (o *RBACConfigResponse) GetWorkflowsOk() (*map[string]WorkflowRoles, bool)`

GetWorkflowsOk returns a tuple with the Workflows field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetWorkflows

`func (o *RBACConfigResponse) SetWorkflows(v map[string]WorkflowRoles)`

SetWorkflows sets Workflows field to given value.

### HasWorkflows

`func (o *RBACConfigResponse) HasWorkflows() bool`

HasWorkflows returns a boolean if a field has been set.

### SetWorkflowsNil

`func (o *RBACConfigResponse) SetWorkflowsNil(b bool)`

 SetWorkflowsNil sets the value for Workflows to be an explicit nil

### UnsetWorkflows
`func (o *RBACConfigResponse) UnsetWorkflows()`

UnsetWorkflows ensures that no value is present for Workflows, not even an explicit nil
### GetWorkflowsCount

`func (o *RBACConfigResponse) GetWorkflowsCount() int32`

GetWorkflowsCount returns the WorkflowsCount field if non-nil, zero value otherwise.

### GetWorkflowsCountOk

`func (o *RBACConfigResponse) GetWorkflowsCountOk() (*int32, bool)`

GetWorkflowsCountOk returns a tuple with the WorkflowsCount field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetWorkflowsCount

`func (o *RBACConfigResponse) SetWorkflowsCount(v int32)`

SetWorkflowsCount sets WorkflowsCount field to given value.

### HasWorkflowsCount

`func (o *RBACConfigResponse) HasWorkflowsCount() bool`

HasWorkflowsCount returns a boolean if a field has been set.

### SetWorkflowsCountNil

`func (o *RBACConfigResponse) SetWorkflowsCountNil(b bool)`

 SetWorkflowsCountNil sets the value for WorkflowsCount to be an explicit nil

### UnsetWorkflowsCount
`func (o *RBACConfigResponse) UnsetWorkflowsCount()`

UnsetWorkflowsCount ensures that no value is present for WorkflowsCount, not even an explicit nil

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


