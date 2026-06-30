# DiagnosticsWorkflowInput

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**Commands** | **[]string** |  | 
**DeviceIds** | **[]string** |  | 
**IncludeTechSupport** | Pointer to **bool** |  | [optional] [default to false]
**IssueKey** | Pointer to **string** |  | [optional] [default to ""]
**TicketingPlatform** | Pointer to **string** |  | [optional] [default to ""]
**User** | Pointer to **string** |  | [optional] [default to ""]

## Methods

### NewDiagnosticsWorkflowInput

`func NewDiagnosticsWorkflowInput(commands []string, deviceIds []string, ) *DiagnosticsWorkflowInput`

NewDiagnosticsWorkflowInput instantiates a new DiagnosticsWorkflowInput object
This constructor will assign default values to properties that have it defined,
and makes sure properties required by API are set, but the set of arguments
will change when the set of required properties is changed

### NewDiagnosticsWorkflowInputWithDefaults

`func NewDiagnosticsWorkflowInputWithDefaults() *DiagnosticsWorkflowInput`

NewDiagnosticsWorkflowInputWithDefaults instantiates a new DiagnosticsWorkflowInput object
This constructor will only assign default values to properties that have it defined,
but it doesn't guarantee that properties required by API are set

### GetCommands

`func (o *DiagnosticsWorkflowInput) GetCommands() []string`

GetCommands returns the Commands field if non-nil, zero value otherwise.

### GetCommandsOk

`func (o *DiagnosticsWorkflowInput) GetCommandsOk() (*[]string, bool)`

GetCommandsOk returns a tuple with the Commands field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetCommands

`func (o *DiagnosticsWorkflowInput) SetCommands(v []string)`

SetCommands sets Commands field to given value.


### GetDeviceIds

`func (o *DiagnosticsWorkflowInput) GetDeviceIds() []string`

GetDeviceIds returns the DeviceIds field if non-nil, zero value otherwise.

### GetDeviceIdsOk

`func (o *DiagnosticsWorkflowInput) GetDeviceIdsOk() (*[]string, bool)`

GetDeviceIdsOk returns a tuple with the DeviceIds field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetDeviceIds

`func (o *DiagnosticsWorkflowInput) SetDeviceIds(v []string)`

SetDeviceIds sets DeviceIds field to given value.


### GetIncludeTechSupport

`func (o *DiagnosticsWorkflowInput) GetIncludeTechSupport() bool`

GetIncludeTechSupport returns the IncludeTechSupport field if non-nil, zero value otherwise.

### GetIncludeTechSupportOk

`func (o *DiagnosticsWorkflowInput) GetIncludeTechSupportOk() (*bool, bool)`

GetIncludeTechSupportOk returns a tuple with the IncludeTechSupport field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetIncludeTechSupport

`func (o *DiagnosticsWorkflowInput) SetIncludeTechSupport(v bool)`

SetIncludeTechSupport sets IncludeTechSupport field to given value.

### HasIncludeTechSupport

`func (o *DiagnosticsWorkflowInput) HasIncludeTechSupport() bool`

HasIncludeTechSupport returns a boolean if a field has been set.

### GetIssueKey

`func (o *DiagnosticsWorkflowInput) GetIssueKey() string`

GetIssueKey returns the IssueKey field if non-nil, zero value otherwise.

### GetIssueKeyOk

`func (o *DiagnosticsWorkflowInput) GetIssueKeyOk() (*string, bool)`

GetIssueKeyOk returns a tuple with the IssueKey field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetIssueKey

`func (o *DiagnosticsWorkflowInput) SetIssueKey(v string)`

SetIssueKey sets IssueKey field to given value.

### HasIssueKey

`func (o *DiagnosticsWorkflowInput) HasIssueKey() bool`

HasIssueKey returns a boolean if a field has been set.

### GetTicketingPlatform

`func (o *DiagnosticsWorkflowInput) GetTicketingPlatform() string`

GetTicketingPlatform returns the TicketingPlatform field if non-nil, zero value otherwise.

### GetTicketingPlatformOk

`func (o *DiagnosticsWorkflowInput) GetTicketingPlatformOk() (*string, bool)`

GetTicketingPlatformOk returns a tuple with the TicketingPlatform field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetTicketingPlatform

`func (o *DiagnosticsWorkflowInput) SetTicketingPlatform(v string)`

SetTicketingPlatform sets TicketingPlatform field to given value.

### HasTicketingPlatform

`func (o *DiagnosticsWorkflowInput) HasTicketingPlatform() bool`

HasTicketingPlatform returns a boolean if a field has been set.

### GetUser

`func (o *DiagnosticsWorkflowInput) GetUser() string`

GetUser returns the User field if non-nil, zero value otherwise.

### GetUserOk

`func (o *DiagnosticsWorkflowInput) GetUserOk() (*string, bool)`

GetUserOk returns a tuple with the User field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetUser

`func (o *DiagnosticsWorkflowInput) SetUser(v string)`

SetUser sets User field to given value.

### HasUser

`func (o *DiagnosticsWorkflowInput) HasUser() bool`

HasUser returns a boolean if a field has been set.


[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


