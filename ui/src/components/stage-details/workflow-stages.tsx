"use client";
/*
 * SPDX-FileCopyrightText: Copyright (c) 2024-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
 * SPDX-License-Identifier: Apache-2.0
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 * http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

import { useEffect, useState, useMemo } from "react";
import { StagesList } from "@/components/stage-details";
import { Badge } from "@/components/ui/badge";
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion";
import { Table, TableBody, TableCell, TableRow } from "@/components/ui/table";
import {
  Card,
  CardContent,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  ResizableHandle,
  ResizablePanel,
  ResizablePanelGroup,
} from "@/components/ui/resizable";
import WorkflowSummary from "@/components/stage-details/workflow-summary";
import WorkflowInputDisplay from "@/components/stage-details/workflow-input-display";
import { WorkflowClientComponentProps } from "@/types/workflow-page.types";
import { StateHistory, WorkflowStage } from "@/types/data-table.types";
import { Button } from "@/components/ui/button";
import { LoadingSpinner } from "@/components/ui/loading-spinner";
import { useToast } from "@/components/ui/use-toast";
import {
  cn,
  handleBadgeClassName,
  sanitizeUrl,
  getInitialStage,
} from "@/lib/utils";
import { ErrorTracebackViewer } from "@/components/error-traceback";
import Markdown, { defaultUrlTransform } from "react-markdown";
import remarkGfm from "remark-gfm";
import { Layers } from "lucide-react";
import "@/styles/markdown.css";

function getWorkflowStatusBadgeState(
  status: string
): StateHistory["state"] {
  switch (status) {
    case "RUNNING":
      return "IN_PROGRESS";
    case "COMPLETED":
      return "COMPLETE";
    case "TERMINATED":
      return "UNREACHABLE";
    case "FAILED":
      return "FAILED";
    default:
      return status as StateHistory["state"];
  }
}

const getApiConfig = async () => {
  const configResponse = await fetch('/api/config');
  return (await configResponse.json()).workflowApiUrl;
};

const sendWorkflowSignal = async (
  workflowId: string,
  stageName: string,
  signal: string
) => {
  const apiURL = await getApiConfig();
  const response = await fetch(
    sanitizeUrl(`${apiURL}/v1/workflow/${workflowId}/${signal}/${stageName}`),
    {
      credentials: "include",
      redirect: "error",
      mode: "cors",
      method: "post",
    }
  );

  if (!response.ok) {
    throw new Error(
      `API returned ${response.status}: ${await response.text()}`
    );
  }

  return response;
};

const terminateWorkflow = async (workflowId: string) => {
  const apiURL = await getApiConfig();
  const response = await fetch(
    sanitizeUrl(`${apiURL}/v1/workflow/${workflowId}/terminate`),
    {
      credentials: "include",
      redirect: "error",
      mode: "cors",
      method: "post",
    }
  );

  if (!response.ok) {
    throw new Error(
      `API returned ${response.status}: ${await response.text()}`
    );
  }

  return response;
};

function customUrlTransform(url: string) {
  // Allow CSV and Excel data URLs
  if (
    url.startsWith("data:text/csv") ||
    url.startsWith(
      "data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
  ) {
    return url;
  }
  return sanitizeUrl(defaultUrlTransform(url));
}

const StageOutput = ({ stage }: { stage: WorkflowStage }) => {
  if (stage.state === "FAILED") {
    return (
      <ErrorTracebackViewer error={{ traceback: stage.traceback || "" }} />
    );
  }

  const stageOutput = stage?.output as { display?: string } | null | undefined;
  const output = stageOutput?.display;
  if (!output) {
    return <div>No output to display</div>;
  }

  return (
    <Markdown
      className="stageMarkdown"
      remarkPlugins={[remarkGfm]}
      urlTransform={customUrlTransform}
    >
      {output}
    </Markdown>
  );
};

export const WorkflowClientComponent: React.FC<
  WorkflowClientComponentProps
> = ({ workflow, mutate }) => {
  const visibleStages = useMemo(
    () => workflow.stages.filter((stage) => stage.state !== "UNREACHABLE"),
    [workflow.stages]
  );

  const [stage, setStage] = useState<WorkflowStage | null>(
    getInitialStage(visibleStages)
  );
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [isTerminating, setIsTerminating] = useState<boolean>(false);
  const [terminateOutcome, setTerminateOutcome] = useState<
    "success" | "failed" | null
  >(null);
  const [isReviewed, setIsReviewed] = useState<boolean>(false);
  const { toast } = useToast();

  const canShowTerminate = true;
  const isTerminateEnabled =
    workflow.status === "RUNNING" && !isTerminating;

  const workflowStatusBadgeState = getWorkflowStatusBadgeState(
    workflow.status
  );

  useEffect(() => {
    if (!stage || !visibleStages.find((s) => s.name === stage.name)) {
      setStage(getInitialStage(visibleStages));
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps -- re-sync only when the workflow changes, not on every stage update
  }, [workflow.id]);

  useEffect(() => {
    setTerminateOutcome(null);
  }, [workflow.id]);

  async function handleRetry() {
    try {
      setIsLoading(true);
      await sendWorkflowSignal(workflow.id, stage!.name, "retry");
      toast({
        title: "Retry: Success",
        description: "Retrying Stage",
      });
      setIsLoading(false);
    } catch (error) {
      console.error(error);
      toast({
        variant: "destructive",
        title: "Retry: Failed",
        description: "Failed to retry stage.",
      });
      setIsLoading(false);
    }
  }

  async function handleApprove() {
    try {
      setIsLoading(true);
      await sendWorkflowSignal(workflow.id, stage!.name, "approve");
      toast({
        title: "Approval: Success",
        description: "Approving Stage",
      });
      setIsReviewed(true);
      setIsLoading(false);
    } catch (error) {
      console.error(error);
      toast({
        variant: "destructive",
        title: "Approval: Failed",
        description: "Failed to approve stage.",
      });
    }
  }

  async function handleReject() {
    try {
      setIsLoading(true);
      await sendWorkflowSignal(workflow.id, stage!.name, "reject");
      toast({
        title: "Rejection: Success",
        description: "Rejecting Stage.",
      });
      setIsReviewed(true);
      setIsLoading(false);
    } catch (error) {
      console.error(error);
      toast({
        variant: "destructive",
        title: "Rejection: Failed",
        description: "Failed to reject stage.",
      });
    }
  }

  async function handleTerminate() {
    try {
      setIsTerminating(true);
      setTerminateOutcome(null);
      await terminateWorkflow(workflow.id);
      setTerminateOutcome("success");
      toast({
        title: "Terminate: Success",
        description: "Workflow termination requested.",
      });
      await mutate?.();
    } catch (error) {
      console.error(error);
      setTerminateOutcome("failed");
      toast({
        variant: "destructive",
        title: "Terminate: Failed",
        description: "Failed to terminate workflow.",
      });
    } finally {
      setIsTerminating(false);
    }
  }

  const handleStageFooterButtons = (
    state: StateHistory["state"]
  ): React.ReactNode => {
    if (state == "PENDING_APPROVAL") {
      return (
        <div className="space-x-4">
          <Button
            className="w-32"
            variant="approval"
            disabled={isLoading || isReviewed}
            onClick={handleApprove}
          >
            {isLoading ? <LoadingSpinner /> : "Approve"}
          </Button>
          <Button
            className="w-32"
            variant="destructive"
            disabled={isLoading || isReviewed}
            onClick={handleReject}
          >
            {isLoading ? <LoadingSpinner /> : "Reject"}
          </Button>
        </div>
      );
    } else if (state == "FAILED") {
      return (
        <Button disabled={!stage!.retryable || isLoading} onClick={handleRetry}>
          {isLoading ? <LoadingSpinner /> : "Retry"}
        </Button>
      );
    }
    return null;
  };

  return (
    <div className="h-screen">
      <ResizablePanelGroup className="h-full" direction="horizontal">
        <ResizablePanel defaultSize={25} className="flex flex-col">
          <div className="flex flex-col items-center my-3 flex-shrink-0">
            <h1 className="text-center font-semibold text-2xl">
              Workflow Details
            </h1>
            {workflow.workflow_type && (
              <h2 className="text-center text-lg text-muted-foreground">
                {workflow.workflow_type}
              </h2>
            )}
            <Badge
              className={cn(
                "mt-3",
                handleBadgeClassName(workflowStatusBadgeState)
              )}
            >
              {workflow.status}
            </Badge>
            {canShowTerminate && (
              <div className="mt-3 flex flex-col items-center gap-1">
                <Button
                  variant="destructive"
                  size="sm"
                  disabled={!isTerminateEnabled}
                  onClick={handleTerminate}
                >
                  {isTerminating ? <LoadingSpinner /> : "Terminate"}
                </Button>
                {terminateOutcome === "success" && (
                  <span className="text-sm text-red-600">
                    Workflow was successfully terminated.
                  </span>
                )}
                {terminateOutcome === "failed" && (
                  <span className="text-sm text-red-600">
                    Terminate failed. Check logs for details.
                  </span>
                )}
              </div>
            )}
          </div>
          <WorkflowSummary workflow={workflow} />
          <div className="flex flex-col items-center overflow-hidden flex-1 mt-4">
            <span className="font-bold text-lg mb-2 flex-shrink-0">Stages</span>
            <div className="w-full overflow-y-auto">
              <StagesList stages={visibleStages} handleClick={setStage} />
            </div>
          </div>
        </ResizablePanel>
        <ResizableHandle />
        <ResizablePanel>
          <div className="flex w-full h-full items-center justify-center p-6">
            {stage ? (
              <Card
                className="w-full h-full justify-center overflow-auto"
                key={stage.name}
              >
                <CardHeader>
                  <CardTitle>{stage.name}</CardTitle>
                  <div className="flex space-x-2">
                    <Badge
                      className={handleBadgeClassName(
                        stage.state as StateHistory["state"]
                      )}
                    >
                      {stage.state}
                    </Badge>
                    {stage.requires_approval &&
                      stage.state == "PENDING_APPROVAL" && (
                        <Badge>Requires Approval</Badge>
                      )}
                  </div>
                </CardHeader>
                <CardContent>
                  <>
                    <span className="font-bold">Description:</span>
                    <span className="ml-2">{stage.description}</span>
                  </>
                  <Accordion type="multiple" defaultValue={["item-2"]}>
                    <AccordionItem value="item-1">
                      <AccordionTrigger>State History</AccordionTrigger>
                      <AccordionContent>
                        <Table>
                          <TableBody>
                            {stage.state_history.map((state, index) => (
                              <TableRow key={index}>
                                <TableCell>
                                  <Badge
                                    className={handleBadgeClassName(
                                      state.state
                                    )}
                                  >
                                    {state.state}
                                  </Badge>
                                </TableCell>
                                <TableCell>{state.time}</TableCell>
                              </TableRow>
                            ))}
                          </TableBody>
                        </Table>
                      </AccordionContent>
                    </AccordionItem>
                    <AccordionItem value="item-2">
                      <AccordionTrigger>Output</AccordionTrigger>
                      <AccordionContent>
                        <StageOutput stage={stage} />
                      </AccordionContent>
                    </AccordionItem>
                    <AccordionItem value="item-3">
                      <AccordionTrigger>Input Parameters</AccordionTrigger>
                      <AccordionContent>
                        <WorkflowInputDisplay workflow={workflow} />
                      </AccordionContent>
                    </AccordionItem>
                  </Accordion>
                </CardContent>
                <CardFooter>
                  {handleStageFooterButtons(
                    stage.state as StateHistory["state"]
                  )}
                </CardFooter>
              </Card>
            ) : (
              <Card className="w-full h-fit">
                <CardContent className="flex flex-col items-center justify-center py-16 px-6 space-y-4">
                  <div className="rounded-full bg-muted p-4">
                    <Layers className="h-8 w-8 text-muted-foreground" />
                  </div>
                  <div className="text-center space-y-2">
                    <h3 className="text-lg font-semibold text-foreground">
                      No Stages Available
                    </h3>
                    <p className="text-sm text-muted-foreground max-w-sm">
                      All workflow stages are currently unreachable.
                    </p>
                  </div>
                </CardContent>
              </Card>
            )}
          </div>
        </ResizablePanel>
      </ResizablePanelGroup>
    </div>
  );
};
