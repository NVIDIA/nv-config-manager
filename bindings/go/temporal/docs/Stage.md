# Stage

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**ApprovalThreshold** | Pointer to **int32** |  | [optional] [default to 0]
**Approvers** | Pointer to [**[]Review**](Review.md) |  | [optional] [default to {}]
**ChildWorkflows** | Pointer to **[]string** |  | [optional] [default to {}]
**DependsOn** | **[]string** |  | 
**Description** | **string** |  | 
**ExecutionTime** | **NullableFloat32** |  | [readonly] 
**Input** | Pointer to **interface{}** |  | [optional] 
**Name** | **string** |  | 
**Output** | Pointer to **interface{}** |  | [optional] 
**Rejecters** | Pointer to [**[]Review**](Review.md) |  | [optional] [default to {}]
**RequiresApproval** | **bool** |  | 
**RetryCount** | Pointer to **int32** |  | [optional] [default to 0]
**Retryable** | **bool** |  | 
**State** | [**StateEnum**](StateEnum.md) |  | 
**StateHistory** | Pointer to [**[]HistoryEntry**](HistoryEntry.md) |  | [optional] [default to {}]
**Traceback** | **NullableString** |  | 

## Methods

### NewStage

`func NewStage(dependsOn []string, description string, executionTime NullableFloat32, name string, requiresApproval bool, retryable bool, state StateEnum, traceback NullableString, ) *Stage`

NewStage instantiates a new Stage object
This constructor will assign default values to properties that have it defined,
and makes sure properties required by API are set, but the set of arguments
will change when the set of required properties is changed

### NewStageWithDefaults

`func NewStageWithDefaults() *Stage`

NewStageWithDefaults instantiates a new Stage object
This constructor will only assign default values to properties that have it defined,
but it doesn't guarantee that properties required by API are set

### GetApprovalThreshold

`func (o *Stage) GetApprovalThreshold() int32`

GetApprovalThreshold returns the ApprovalThreshold field if non-nil, zero value otherwise.

### GetApprovalThresholdOk

`func (o *Stage) GetApprovalThresholdOk() (*int32, bool)`

GetApprovalThresholdOk returns a tuple with the ApprovalThreshold field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetApprovalThreshold

`func (o *Stage) SetApprovalThreshold(v int32)`

SetApprovalThreshold sets ApprovalThreshold field to given value.

### HasApprovalThreshold

`func (o *Stage) HasApprovalThreshold() bool`

HasApprovalThreshold returns a boolean if a field has been set.

### GetApprovers

`func (o *Stage) GetApprovers() []Review`

GetApprovers returns the Approvers field if non-nil, zero value otherwise.

### GetApproversOk

`func (o *Stage) GetApproversOk() (*[]Review, bool)`

GetApproversOk returns a tuple with the Approvers field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetApprovers

`func (o *Stage) SetApprovers(v []Review)`

SetApprovers sets Approvers field to given value.

### HasApprovers

`func (o *Stage) HasApprovers() bool`

HasApprovers returns a boolean if a field has been set.

### GetChildWorkflows

`func (o *Stage) GetChildWorkflows() []string`

GetChildWorkflows returns the ChildWorkflows field if non-nil, zero value otherwise.

### GetChildWorkflowsOk

`func (o *Stage) GetChildWorkflowsOk() (*[]string, bool)`

GetChildWorkflowsOk returns a tuple with the ChildWorkflows field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetChildWorkflows

`func (o *Stage) SetChildWorkflows(v []string)`

SetChildWorkflows sets ChildWorkflows field to given value.

### HasChildWorkflows

`func (o *Stage) HasChildWorkflows() bool`

HasChildWorkflows returns a boolean if a field has been set.

### GetDependsOn

`func (o *Stage) GetDependsOn() []string`

GetDependsOn returns the DependsOn field if non-nil, zero value otherwise.

### GetDependsOnOk

`func (o *Stage) GetDependsOnOk() (*[]string, bool)`

GetDependsOnOk returns a tuple with the DependsOn field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetDependsOn

`func (o *Stage) SetDependsOn(v []string)`

SetDependsOn sets DependsOn field to given value.


### GetDescription

`func (o *Stage) GetDescription() string`

GetDescription returns the Description field if non-nil, zero value otherwise.

### GetDescriptionOk

`func (o *Stage) GetDescriptionOk() (*string, bool)`

GetDescriptionOk returns a tuple with the Description field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetDescription

`func (o *Stage) SetDescription(v string)`

SetDescription sets Description field to given value.


### GetExecutionTime

`func (o *Stage) GetExecutionTime() float32`

GetExecutionTime returns the ExecutionTime field if non-nil, zero value otherwise.

### GetExecutionTimeOk

`func (o *Stage) GetExecutionTimeOk() (*float32, bool)`

GetExecutionTimeOk returns a tuple with the ExecutionTime field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetExecutionTime

`func (o *Stage) SetExecutionTime(v float32)`

SetExecutionTime sets ExecutionTime field to given value.


### SetExecutionTimeNil

`func (o *Stage) SetExecutionTimeNil(b bool)`

 SetExecutionTimeNil sets the value for ExecutionTime to be an explicit nil

### UnsetExecutionTime
`func (o *Stage) UnsetExecutionTime()`

UnsetExecutionTime ensures that no value is present for ExecutionTime, not even an explicit nil
### GetInput

`func (o *Stage) GetInput() interface{}`

GetInput returns the Input field if non-nil, zero value otherwise.

### GetInputOk

`func (o *Stage) GetInputOk() (*interface{}, bool)`

GetInputOk returns a tuple with the Input field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetInput

`func (o *Stage) SetInput(v interface{})`

SetInput sets Input field to given value.

### HasInput

`func (o *Stage) HasInput() bool`

HasInput returns a boolean if a field has been set.

### SetInputNil

`func (o *Stage) SetInputNil(b bool)`

 SetInputNil sets the value for Input to be an explicit nil

### UnsetInput
`func (o *Stage) UnsetInput()`

UnsetInput ensures that no value is present for Input, not even an explicit nil
### GetName

`func (o *Stage) GetName() string`

GetName returns the Name field if non-nil, zero value otherwise.

### GetNameOk

`func (o *Stage) GetNameOk() (*string, bool)`

GetNameOk returns a tuple with the Name field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetName

`func (o *Stage) SetName(v string)`

SetName sets Name field to given value.


### GetOutput

`func (o *Stage) GetOutput() interface{}`

GetOutput returns the Output field if non-nil, zero value otherwise.

### GetOutputOk

`func (o *Stage) GetOutputOk() (*interface{}, bool)`

GetOutputOk returns a tuple with the Output field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetOutput

`func (o *Stage) SetOutput(v interface{})`

SetOutput sets Output field to given value.

### HasOutput

`func (o *Stage) HasOutput() bool`

HasOutput returns a boolean if a field has been set.

### SetOutputNil

`func (o *Stage) SetOutputNil(b bool)`

 SetOutputNil sets the value for Output to be an explicit nil

### UnsetOutput
`func (o *Stage) UnsetOutput()`

UnsetOutput ensures that no value is present for Output, not even an explicit nil
### GetRejecters

`func (o *Stage) GetRejecters() []Review`

GetRejecters returns the Rejecters field if non-nil, zero value otherwise.

### GetRejectersOk

`func (o *Stage) GetRejectersOk() (*[]Review, bool)`

GetRejectersOk returns a tuple with the Rejecters field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetRejecters

`func (o *Stage) SetRejecters(v []Review)`

SetRejecters sets Rejecters field to given value.

### HasRejecters

`func (o *Stage) HasRejecters() bool`

HasRejecters returns a boolean if a field has been set.

### GetRequiresApproval

`func (o *Stage) GetRequiresApproval() bool`

GetRequiresApproval returns the RequiresApproval field if non-nil, zero value otherwise.

### GetRequiresApprovalOk

`func (o *Stage) GetRequiresApprovalOk() (*bool, bool)`

GetRequiresApprovalOk returns a tuple with the RequiresApproval field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetRequiresApproval

`func (o *Stage) SetRequiresApproval(v bool)`

SetRequiresApproval sets RequiresApproval field to given value.


### GetRetryCount

`func (o *Stage) GetRetryCount() int32`

GetRetryCount returns the RetryCount field if non-nil, zero value otherwise.

### GetRetryCountOk

`func (o *Stage) GetRetryCountOk() (*int32, bool)`

GetRetryCountOk returns a tuple with the RetryCount field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetRetryCount

`func (o *Stage) SetRetryCount(v int32)`

SetRetryCount sets RetryCount field to given value.

### HasRetryCount

`func (o *Stage) HasRetryCount() bool`

HasRetryCount returns a boolean if a field has been set.

### GetRetryable

`func (o *Stage) GetRetryable() bool`

GetRetryable returns the Retryable field if non-nil, zero value otherwise.

### GetRetryableOk

`func (o *Stage) GetRetryableOk() (*bool, bool)`

GetRetryableOk returns a tuple with the Retryable field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetRetryable

`func (o *Stage) SetRetryable(v bool)`

SetRetryable sets Retryable field to given value.


### GetState

`func (o *Stage) GetState() StateEnum`

GetState returns the State field if non-nil, zero value otherwise.

### GetStateOk

`func (o *Stage) GetStateOk() (*StateEnum, bool)`

GetStateOk returns a tuple with the State field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetState

`func (o *Stage) SetState(v StateEnum)`

SetState sets State field to given value.


### GetStateHistory

`func (o *Stage) GetStateHistory() []HistoryEntry`

GetStateHistory returns the StateHistory field if non-nil, zero value otherwise.

### GetStateHistoryOk

`func (o *Stage) GetStateHistoryOk() (*[]HistoryEntry, bool)`

GetStateHistoryOk returns a tuple with the StateHistory field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetStateHistory

`func (o *Stage) SetStateHistory(v []HistoryEntry)`

SetStateHistory sets StateHistory field to given value.

### HasStateHistory

`func (o *Stage) HasStateHistory() bool`

HasStateHistory returns a boolean if a field has been set.

### GetTraceback

`func (o *Stage) GetTraceback() string`

GetTraceback returns the Traceback field if non-nil, zero value otherwise.

### GetTracebackOk

`func (o *Stage) GetTracebackOk() (*string, bool)`

GetTracebackOk returns a tuple with the Traceback field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetTraceback

`func (o *Stage) SetTraceback(v string)`

SetTraceback sets Traceback field to given value.


### SetTracebackNil

`func (o *Stage) SetTracebackNil(b bool)`

 SetTracebackNil sets the value for Traceback to be an explicit nil

### UnsetTraceback
`func (o *Stage) UnsetTraceback()`

UnsetTraceback ensures that no value is present for Traceback, not even an explicit nil

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


