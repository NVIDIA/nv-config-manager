# WorkflowSummaryResponse

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**CloseTime** | **NullableTime** |  | 
**FailedStage** | **bool** |  | 
**Href** | **string** | Calculate URL to Temporal UI Workflow View. | [readonly] 
**Id** | **string** |  | 
**PendingApproval** | **bool** |  | 
**SearchAttributes** | [**map[string]SearchAttributesValue**](SearchAttributesValue.md) |  | 
**StartTime** | **time.Time** |  | 
**StartedBy** | **string** |  | 
**Status** | **string** |  | 
**WorkflowInput** | **interface{}** |  | 
**WorkflowType** | **string** |  | 

## Methods

### NewWorkflowSummaryResponse

`func NewWorkflowSummaryResponse(closeTime NullableTime, failedStage bool, href string, id string, pendingApproval bool, searchAttributes map[string]SearchAttributesValue, startTime time.Time, startedBy string, status string, workflowInput interface{}, workflowType string, ) *WorkflowSummaryResponse`

NewWorkflowSummaryResponse instantiates a new WorkflowSummaryResponse object
This constructor will assign default values to properties that have it defined,
and makes sure properties required by API are set, but the set of arguments
will change when the set of required properties is changed

### NewWorkflowSummaryResponseWithDefaults

`func NewWorkflowSummaryResponseWithDefaults() *WorkflowSummaryResponse`

NewWorkflowSummaryResponseWithDefaults instantiates a new WorkflowSummaryResponse object
This constructor will only assign default values to properties that have it defined,
but it doesn't guarantee that properties required by API are set

### GetCloseTime

`func (o *WorkflowSummaryResponse) GetCloseTime() time.Time`

GetCloseTime returns the CloseTime field if non-nil, zero value otherwise.

### GetCloseTimeOk

`func (o *WorkflowSummaryResponse) GetCloseTimeOk() (*time.Time, bool)`

GetCloseTimeOk returns a tuple with the CloseTime field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetCloseTime

`func (o *WorkflowSummaryResponse) SetCloseTime(v time.Time)`

SetCloseTime sets CloseTime field to given value.


### SetCloseTimeNil

`func (o *WorkflowSummaryResponse) SetCloseTimeNil(b bool)`

 SetCloseTimeNil sets the value for CloseTime to be an explicit nil

### UnsetCloseTime
`func (o *WorkflowSummaryResponse) UnsetCloseTime()`

UnsetCloseTime ensures that no value is present for CloseTime, not even an explicit nil
### GetFailedStage

`func (o *WorkflowSummaryResponse) GetFailedStage() bool`

GetFailedStage returns the FailedStage field if non-nil, zero value otherwise.

### GetFailedStageOk

`func (o *WorkflowSummaryResponse) GetFailedStageOk() (*bool, bool)`

GetFailedStageOk returns a tuple with the FailedStage field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetFailedStage

`func (o *WorkflowSummaryResponse) SetFailedStage(v bool)`

SetFailedStage sets FailedStage field to given value.


### GetHref

`func (o *WorkflowSummaryResponse) GetHref() string`

GetHref returns the Href field if non-nil, zero value otherwise.

### GetHrefOk

`func (o *WorkflowSummaryResponse) GetHrefOk() (*string, bool)`

GetHrefOk returns a tuple with the Href field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetHref

`func (o *WorkflowSummaryResponse) SetHref(v string)`

SetHref sets Href field to given value.


### GetId

`func (o *WorkflowSummaryResponse) GetId() string`

GetId returns the Id field if non-nil, zero value otherwise.

### GetIdOk

`func (o *WorkflowSummaryResponse) GetIdOk() (*string, bool)`

GetIdOk returns a tuple with the Id field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetId

`func (o *WorkflowSummaryResponse) SetId(v string)`

SetId sets Id field to given value.


### GetPendingApproval

`func (o *WorkflowSummaryResponse) GetPendingApproval() bool`

GetPendingApproval returns the PendingApproval field if non-nil, zero value otherwise.

### GetPendingApprovalOk

`func (o *WorkflowSummaryResponse) GetPendingApprovalOk() (*bool, bool)`

GetPendingApprovalOk returns a tuple with the PendingApproval field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetPendingApproval

`func (o *WorkflowSummaryResponse) SetPendingApproval(v bool)`

SetPendingApproval sets PendingApproval field to given value.


### GetSearchAttributes

`func (o *WorkflowSummaryResponse) GetSearchAttributes() map[string]SearchAttributesValue`

GetSearchAttributes returns the SearchAttributes field if non-nil, zero value otherwise.

### GetSearchAttributesOk

`func (o *WorkflowSummaryResponse) GetSearchAttributesOk() (*map[string]SearchAttributesValue, bool)`

GetSearchAttributesOk returns a tuple with the SearchAttributes field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetSearchAttributes

`func (o *WorkflowSummaryResponse) SetSearchAttributes(v map[string]SearchAttributesValue)`

SetSearchAttributes sets SearchAttributes field to given value.


### GetStartTime

`func (o *WorkflowSummaryResponse) GetStartTime() time.Time`

GetStartTime returns the StartTime field if non-nil, zero value otherwise.

### GetStartTimeOk

`func (o *WorkflowSummaryResponse) GetStartTimeOk() (*time.Time, bool)`

GetStartTimeOk returns a tuple with the StartTime field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetStartTime

`func (o *WorkflowSummaryResponse) SetStartTime(v time.Time)`

SetStartTime sets StartTime field to given value.


### GetStartedBy

`func (o *WorkflowSummaryResponse) GetStartedBy() string`

GetStartedBy returns the StartedBy field if non-nil, zero value otherwise.

### GetStartedByOk

`func (o *WorkflowSummaryResponse) GetStartedByOk() (*string, bool)`

GetStartedByOk returns a tuple with the StartedBy field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetStartedBy

`func (o *WorkflowSummaryResponse) SetStartedBy(v string)`

SetStartedBy sets StartedBy field to given value.


### GetStatus

`func (o *WorkflowSummaryResponse) GetStatus() string`

GetStatus returns the Status field if non-nil, zero value otherwise.

### GetStatusOk

`func (o *WorkflowSummaryResponse) GetStatusOk() (*string, bool)`

GetStatusOk returns a tuple with the Status field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetStatus

`func (o *WorkflowSummaryResponse) SetStatus(v string)`

SetStatus sets Status field to given value.


### GetWorkflowInput

`func (o *WorkflowSummaryResponse) GetWorkflowInput() interface{}`

GetWorkflowInput returns the WorkflowInput field if non-nil, zero value otherwise.

### GetWorkflowInputOk

`func (o *WorkflowSummaryResponse) GetWorkflowInputOk() (*interface{}, bool)`

GetWorkflowInputOk returns a tuple with the WorkflowInput field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetWorkflowInput

`func (o *WorkflowSummaryResponse) SetWorkflowInput(v interface{})`

SetWorkflowInput sets WorkflowInput field to given value.


### SetWorkflowInputNil

`func (o *WorkflowSummaryResponse) SetWorkflowInputNil(b bool)`

 SetWorkflowInputNil sets the value for WorkflowInput to be an explicit nil

### UnsetWorkflowInput
`func (o *WorkflowSummaryResponse) UnsetWorkflowInput()`

UnsetWorkflowInput ensures that no value is present for WorkflowInput, not even an explicit nil
### GetWorkflowType

`func (o *WorkflowSummaryResponse) GetWorkflowType() string`

GetWorkflowType returns the WorkflowType field if non-nil, zero value otherwise.

### GetWorkflowTypeOk

`func (o *WorkflowSummaryResponse) GetWorkflowTypeOk() (*string, bool)`

GetWorkflowTypeOk returns a tuple with the WorkflowType field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetWorkflowType

`func (o *WorkflowSummaryResponse) SetWorkflowType(v string)`

SetWorkflowType sets WorkflowType field to given value.



[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


