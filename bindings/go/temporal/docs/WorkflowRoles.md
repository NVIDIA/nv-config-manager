# WorkflowRoles

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**ExecuteRoles** | **[]string** |  | 
**ReadRoles** | **[]string** |  | 

## Methods

### NewWorkflowRoles

`func NewWorkflowRoles(executeRoles []string, readRoles []string, ) *WorkflowRoles`

NewWorkflowRoles instantiates a new WorkflowRoles object
This constructor will assign default values to properties that have it defined,
and makes sure properties required by API are set, but the set of arguments
will change when the set of required properties is changed

### NewWorkflowRolesWithDefaults

`func NewWorkflowRolesWithDefaults() *WorkflowRoles`

NewWorkflowRolesWithDefaults instantiates a new WorkflowRoles object
This constructor will only assign default values to properties that have it defined,
but it doesn't guarantee that properties required by API are set

### GetExecuteRoles

`func (o *WorkflowRoles) GetExecuteRoles() []string`

GetExecuteRoles returns the ExecuteRoles field if non-nil, zero value otherwise.

### GetExecuteRolesOk

`func (o *WorkflowRoles) GetExecuteRolesOk() (*[]string, bool)`

GetExecuteRolesOk returns a tuple with the ExecuteRoles field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetExecuteRoles

`func (o *WorkflowRoles) SetExecuteRoles(v []string)`

SetExecuteRoles sets ExecuteRoles field to given value.


### GetReadRoles

`func (o *WorkflowRoles) GetReadRoles() []string`

GetReadRoles returns the ReadRoles field if non-nil, zero value otherwise.

### GetReadRolesOk

`func (o *WorkflowRoles) GetReadRolesOk() (*[]string, bool)`

GetReadRolesOk returns a tuple with the ReadRoles field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetReadRoles

`func (o *WorkflowRoles) SetReadRoles(v []string)`

SetReadRoles sets ReadRoles field to given value.



[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


