# WorkflowDetailResponse

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**CloseTime** | **NullableTime** |  | 
**FailedStage** | **bool** |  | 
**Href** | **string** | Calculate URL to Temporal UI Workflow View. | [readonly] 
**Id** | **string** |  | 
**PendingApproval** | **bool** |  | 
**Result** | **interface{}** |  | 
**SearchAttributes** | [**map[string]SearchAttributesValue**](SearchAttributesValue.md) |  | 
**Stages** | [**[]Stage**](Stage.md) |  | 
**StartTime** | **time.Time** |  | 
**StartedBy** | **string** |  | 
**Status** | **string** |  | 
**WorkflowInput** | **interface{}** |  | 
**WorkflowType** | **string** |  | 

## Methods

### NewWorkflowDetailResponse

`func NewWorkflowDetailResponse(closeTime NullableTime, failedStage bool, href string, id string, pendingApproval bool, result interface{}, searchAttributes map[string]SearchAttributesValue, stages []Stage, startTime time.Time, startedBy string, status string, workflowInput interface{}, workflowType string, ) *WorkflowDetailResponse`

NewWorkflowDetailResponse instantiates a new WorkflowDetailResponse object
This constructor will assign default values to properties that have it defined,
and makes sure properties required by API are set, but the set of arguments
will change when the set of required properties is changed

### NewWorkflowDetailResponseWithDefaults

`func NewWorkflowDetailResponseWithDefaults() *WorkflowDetailResponse`

NewWorkflowDetailResponseWithDefaults instantiates a new WorkflowDetailResponse object
This constructor will only assign default values to properties that have it defined,
but it doesn't guarantee that properties required by API are set

### GetCloseTime

`func (o *WorkflowDetailResponse) GetCloseTime() time.Time`

GetCloseTime returns the CloseTime field if non-nil, zero value otherwise.

### GetCloseTimeOk

`func (o *WorkflowDetailResponse) GetCloseTimeOk() (*time.Time, bool)`

GetCloseTimeOk returns a tuple with the CloseTime field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetCloseTime

`func (o *WorkflowDetailResponse) SetCloseTime(v time.Time)`

SetCloseTime sets CloseTime field to given value.


### SetCloseTimeNil

`func (o *WorkflowDetailResponse) SetCloseTimeNil(b bool)`

 SetCloseTimeNil sets the value for CloseTime to be an explicit nil

### UnsetCloseTime
`func (o *WorkflowDetailResponse) UnsetCloseTime()`

UnsetCloseTime ensures that no value is present for CloseTime, not even an explicit nil
### GetFailedStage

`func (o *WorkflowDetailResponse) GetFailedStage() bool`

GetFailedStage returns the FailedStage field if non-nil, zero value otherwise.

### GetFailedStageOk

`func (o *WorkflowDetailResponse) GetFailedStageOk() (*bool, bool)`

GetFailedStageOk returns a tuple with the FailedStage field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetFailedStage

`func (o *WorkflowDetailResponse) SetFailedStage(v bool)`

SetFailedStage sets FailedStage field to given value.


### GetHref

`func (o *WorkflowDetailResponse) GetHref() string`

GetHref returns the Href field if non-nil, zero value otherwise.

### GetHrefOk

`func (o *WorkflowDetailResponse) GetHrefOk() (*string, bool)`

GetHrefOk returns a tuple with the Href field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetHref

`func (o *WorkflowDetailResponse) SetHref(v string)`

SetHref sets Href field to given value.


### GetId

`func (o *WorkflowDetailResponse) GetId() string`

GetId returns the Id field if non-nil, zero value otherwise.

### GetIdOk

`func (o *WorkflowDetailResponse) GetIdOk() (*string, bool)`

GetIdOk returns a tuple with the Id field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetId

`func (o *WorkflowDetailResponse) SetId(v string)`

SetId sets Id field to given value.


### GetPendingApproval

`func (o *WorkflowDetailResponse) GetPendingApproval() bool`

GetPendingApproval returns the PendingApproval field if non-nil, zero value otherwise.

### GetPendingApprovalOk

`func (o *WorkflowDetailResponse) GetPendingApprovalOk() (*bool, bool)`

GetPendingApprovalOk returns a tuple with the PendingApproval field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetPendingApproval

`func (o *WorkflowDetailResponse) SetPendingApproval(v bool)`

SetPendingApproval sets PendingApproval field to given value.


### GetResult

`func (o *WorkflowDetailResponse) GetResult() interface{}`

GetResult returns the Result field if non-nil, zero value otherwise.

### GetResultOk

`func (o *WorkflowDetailResponse) GetResultOk() (*interface{}, bool)`

GetResultOk returns a tuple with the Result field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetResult

`func (o *WorkflowDetailResponse) SetResult(v interface{})`

SetResult sets Result field to given value.


### SetResultNil

`func (o *WorkflowDetailResponse) SetResultNil(b bool)`

 SetResultNil sets the value for Result to be an explicit nil

### UnsetResult
`func (o *WorkflowDetailResponse) UnsetResult()`

UnsetResult ensures that no value is present for Result, not even an explicit nil
### GetSearchAttributes

`func (o *WorkflowDetailResponse) GetSearchAttributes() map[string]SearchAttributesValue`

GetSearchAttributes returns the SearchAttributes field if non-nil, zero value otherwise.

### GetSearchAttributesOk

`func (o *WorkflowDetailResponse) GetSearchAttributesOk() (*map[string]SearchAttributesValue, bool)`

GetSearchAttributesOk returns a tuple with the SearchAttributes field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetSearchAttributes

`func (o *WorkflowDetailResponse) SetSearchAttributes(v map[string]SearchAttributesValue)`

SetSearchAttributes sets SearchAttributes field to given value.


### GetStages

`func (o *WorkflowDetailResponse) GetStages() []Stage`

GetStages returns the Stages field if non-nil, zero value otherwise.

### GetStagesOk

`func (o *WorkflowDetailResponse) GetStagesOk() (*[]Stage, bool)`

GetStagesOk returns a tuple with the Stages field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetStages

`func (o *WorkflowDetailResponse) SetStages(v []Stage)`

SetStages sets Stages field to given value.


### GetStartTime

`func (o *WorkflowDetailResponse) GetStartTime() time.Time`

GetStartTime returns the StartTime field if non-nil, zero value otherwise.

### GetStartTimeOk

`func (o *WorkflowDetailResponse) GetStartTimeOk() (*time.Time, bool)`

GetStartTimeOk returns a tuple with the StartTime field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetStartTime

`func (o *WorkflowDetailResponse) SetStartTime(v time.Time)`

SetStartTime sets StartTime field to given value.


### GetStartedBy

`func (o *WorkflowDetailResponse) GetStartedBy() string`

GetStartedBy returns the StartedBy field if non-nil, zero value otherwise.

### GetStartedByOk

`func (o *WorkflowDetailResponse) GetStartedByOk() (*string, bool)`

GetStartedByOk returns a tuple with the StartedBy field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetStartedBy

`func (o *WorkflowDetailResponse) SetStartedBy(v string)`

SetStartedBy sets StartedBy field to given value.


### GetStatus

`func (o *WorkflowDetailResponse) GetStatus() string`

GetStatus returns the Status field if non-nil, zero value otherwise.

### GetStatusOk

`func (o *WorkflowDetailResponse) GetStatusOk() (*string, bool)`

GetStatusOk returns a tuple with the Status field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetStatus

`func (o *WorkflowDetailResponse) SetStatus(v string)`

SetStatus sets Status field to given value.


### GetWorkflowInput

`func (o *WorkflowDetailResponse) GetWorkflowInput() interface{}`

GetWorkflowInput returns the WorkflowInput field if non-nil, zero value otherwise.

### GetWorkflowInputOk

`func (o *WorkflowDetailResponse) GetWorkflowInputOk() (*interface{}, bool)`

GetWorkflowInputOk returns a tuple with the WorkflowInput field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetWorkflowInput

`func (o *WorkflowDetailResponse) SetWorkflowInput(v interface{})`

SetWorkflowInput sets WorkflowInput field to given value.


### SetWorkflowInputNil

`func (o *WorkflowDetailResponse) SetWorkflowInputNil(b bool)`

 SetWorkflowInputNil sets the value for WorkflowInput to be an explicit nil

### UnsetWorkflowInput
`func (o *WorkflowDetailResponse) UnsetWorkflowInput()`

UnsetWorkflowInput ensures that no value is present for WorkflowInput, not even an explicit nil
### GetWorkflowType

`func (o *WorkflowDetailResponse) GetWorkflowType() string`

GetWorkflowType returns the WorkflowType field if non-nil, zero value otherwise.

### GetWorkflowTypeOk

`func (o *WorkflowDetailResponse) GetWorkflowTypeOk() (*string, bool)`

GetWorkflowTypeOk returns a tuple with the WorkflowType field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetWorkflowType

`func (o *WorkflowDetailResponse) SetWorkflowType(v string)`

SetWorkflowType sets WorkflowType field to given value.



[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


