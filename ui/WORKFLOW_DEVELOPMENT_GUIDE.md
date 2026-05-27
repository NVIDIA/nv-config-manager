# Workflow Development Guide

This guide provides instructions for creating new workflow forms, implementing API mocks, and writing tests.

## Quick Decision Guide

- **Only need site + device fields?** → Use `DeviceWorkflowForm` (see [Using DeviceWorkflowForm](#using-deviceworkflowform))
- **Need custom fields?** → Create a custom form using `site-cable-validation` as reference (see [Creating Custom Forms](#creating-custom-forms))

## Table of Contents

- [Creating Workflow Forms](#creating-workflow-forms)
  - [Using DeviceWorkflowForm](#using-deviceworkflowform)
  - [Creating Custom Forms](#creating-custom-forms)
- [Setting Up API Mocks](#setting-up-api-mocks)
  - [Creating Handler Files](#creating-handler-files)
  - [Setting Up Playwright Mocks](#setting-up-playwright-mocks)
- [Writing Tests](#writing-tests)
  - [Testing DeviceWorkflowForm](#testing-deviceworkflowform)
  - [Testing Custom Forms](#testing-custom-forms)

## Creating Workflow Forms

### Using DeviceWorkflowForm

If your workflow only requires **site** and **device** fields, use the generic `DeviceWorkflowForm` component:

1. First, create the loading page:

```tsx
// src/app/workflows/myworkflow/form/loading.tsx
import * as React from "react";
import { WorkflowFormSkeleton } from "@/components/loading";

const MyWorkflowLoading: React.FC = () => {
  return <WorkflowFormSkeleton />;
};

export default MyWorkflowLoading;
```

2. Then create the main page:

```tsx
// src/app/workflows/myworkflow/form/page.tsx
"use client";

import * as React from "react";
import { useToast } from "@/components/ui/use-toast";
import { startWorkflow } from "@/lib/utils";
import {
  DeviceWorkflowForm,
  DeviceWorkflowFormSchema,
} from "@/components/forms/workflow";

const MyWorkflowForm = () => {
  const { toast } = useToast();

  const onSubmit = (data: DeviceWorkflowFormSchema) => {
    const endpoint = "/v1/workflow/ngc/my_workflow";
    const params = {
      device_id: data.device,
    };

    startWorkflow(endpoint, params).catch((error) => {
      toast({
        variant: "destructive",
        title: "Workflow Failed",
        description: `Failed to create workflow: ${error}`,
      });
    });
  };

  return <DeviceWorkflowForm title="My Workflow Form" onSubmit={onSubmit} />;
};

export default MyWorkflowForm;
```

### Creating Custom Forms

For workflows requiring additional fields beyond site and device, create a custom form. Use the **site-cable-validation** workflow as a reference example. You can find it at:

- Form: `src/app/workflows/sitecablevalidationworkflow/form/site-cable-validation-workflow-form.tsx`
- Tests: `tests/e2e/siteCableValidationForm.spec.ts`

Another good example is the **cumulus-hardware-validation** workflow at:

- Form: `src/app/workflows/cumulushardwarevalidationworkflow/form/cumulus-hardware-validation-form.tsx`
- Tests: `tests/e2e/cumulusHardwareValidationForm.spec.ts`

#### 1. Create the Loading Page

All workflow forms need a loading page. Create `loading.tsx` in your form directory:

```tsx
// src/app/workflows/myworkflow/form/loading.tsx
import * as React from "react";
import { WorkflowFormSkeleton } from "@/components/loading";

const MyWorkflowLoading: React.FC = () => {
  return <WorkflowFormSkeleton />;
};

export default MyWorkflowLoading;
```

#### 2. Define the Validation Schema

```tsx
// src/app/workflows/myworkflow/form/my-workflow-form.tsx
import { z } from "zod";

const formSchema = z.object({
  site: z.string().min(1, "Site is required"),
  roles: z.array(z.string()).min(1, "At least one role is required"),
  status: z.array(z.string()).min(1, "At least one status is required"),
  tenant: z.string().min(1, "Tenant is required"),
  device_type_ids: z.array(z.string()).optional(),
  raise_for_invalid: z.boolean().default(false),
});

type FormData = z.infer<typeof formSchema>;
```

#### 3. Create the Form Component

```tsx
"use client";

import * as React from "react";
import { useSearchParams } from "next/navigation";
import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Form } from "@/components/ui/form";
import { useToast } from "@/components/ui/use-toast";
import { WorkflowFormField } from "@/components/forms/formfield";
import { useEnvData } from "@/hooks";
import { startWorkflow } from "@/lib/utils";

export default function MyWorkflowForm() {
  const [isSubmitting, setIsSubmitting] = React.useState<boolean>(false);
  const { data: envData } = useEnvData({});
  const { toast } = useToast();
  const searchParams = useSearchParams();

  const form = useForm<FormData>({
    resolver: zodResolver(formSchema),
    defaultValues: {
      site: searchParams?.get("site") || "",
      roles: searchParams?.getAll("role") || [],
      status: searchParams?.getAll("status") || [],
      tenant: searchParams?.get("tenant") || "",
      device_type_ids: searchParams?.getAll("device_type_ids") || [],
      raise_for_invalid: searchParams?.get("raise_for_invalid") === "true",
    },
  });

  const onSubmit = async (data: FormData) => {
    setIsSubmitting(true);
    const endpoint = "/v1/workflow/ngc/my_custom_workflow";
    const params: MyWorkflowInput = {
      site: data.site,
      roles: data.roles,
      status: data.status,
      tenant: data.tenant,
      device_type_ids: data.device_type_ids,
      raise_for_invalid: data.raise_for_invalid,
    };

    try {
      await startWorkflow(endpoint, params);
    } catch (error) {
      toast({
        variant: "destructive",
        title: "Workflow Failed",
        description: `Failed to create workflow: ${error}`,
      });
      setIsSubmitting(false);
    }
  };

  const handleChange = () => {
    // Mark that user has made manual changes
    // This prevents URL params from overriding user input
  };

  return (
    <Card className="w-full max-w-4xl mx-auto">
      <CardHeader>
        <CardTitle>My Custom Workflow Form</CardTitle>
      </CardHeader>
      <CardContent>
        <Form {...form}>
          <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
            {/* Site Selection */}
            <WorkflowFormField
              type="select"
              control={form.control}
              name="site"
              label="Site"
              options={envData.siteData}
              isSubmitting={isSubmitting}
              handleChange={handleChange}
            />

            {/* Multi-select for Roles */}
            <WorkflowFormField
              type="select"
              control={form.control}
              name="roles"
              label="Roles"
              options={envData.rolesData}
              isSubmitting={isSubmitting}
              handleChange={handleChange}
              multiple={true}
            />

            {/* Multi-select for Status */}
            <WorkflowFormField
              type="select"
              control={form.control}
              name="status"
              label="Device Status"
              options={envData.statusData}
              isSubmitting={isSubmitting}
              handleChange={handleChange}
              multiple={true}
            />

            {/* Tenant Selection */}
            <WorkflowFormField
              type="select"
              control={form.control}
              name="tenant"
              label="Tenant"
              options={envData.tenantsData}
              isSubmitting={isSubmitting}
              handleChange={handleChange}
            />

            {/* Boolean field */}
            <WorkflowFormField
              type="checkbox"
              control={form.control}
              name="raise_for_invalid"
              label="Raise for Invalid"
              isSubmitting={isSubmitting}
              handleChange={handleChange}
            />

            <Button type="submit" disabled={isSubmitting}>
              {isSubmitting ? "Submitting..." : "Submit"}
            </Button>
          </form>
        </Form>
      </CardContent>
    </Card>
  );
}
```

## Setting Up API Mocks

### Creating Handler Files

1. Create a handler file in `src/mocks/handlers/`:

**Naming Convention**: Use camelCase with `Handlers` suffix (e.g., `myWorkflowHandlers.ts`)

```typescript
// src/mocks/handlers/myWorkflowHandlers.ts
import { http, HttpResponse } from "msw";
import { sanitizeUrl } from "@/lib/utils";
import { mockApiURL as apiURL } from "@/config/mockApiUrl";

export const myWorkflowHandlers = [
  http.post(
    sanitizeUrl(`${apiURL}/v1/workflow/ngc/my_workflow`),
    async ({ request }) => {
      const body = await request.json();

      // Add validation logic if needed
      if (body.site === "forbidden-site") {
        return HttpResponse.json(
          {
            error: "Forbidden: You do not have permission to run this workflow",
          },
          { status: 403 }
        );
      }

      // Return success response
      return HttpResponse.json(
        {
          id: `my-workflow-${Date.now()}`,
          href: `https://temporal.example.com/workflows/my-workflow-${Date.now()}`,
        },
        { status: 201 }
      );
    }
  ),
];
```

2. Import the handler in `src/mocks/handlers/index.ts`:

```typescript
// src/mocks/handlers/index.ts
import { myWorkflowHandlers } from "./myWorkflowHandlers";

export const handlers = [
  ...healthcheckHandlers,
  ...workflowHandlers,
  // ... other handlers
  ...myWorkflowHandlers, // Add your handler here
];
```

### Setting Up Playwright Mocks

Add the API mock in `tests/e2e/shared/apiMocks.ts`:

```typescript
// tests/e2e/shared/apiMocks.ts

// 1. Create the mock function
export async function mockMyWorkflowEndpoint(page: Page) {
  await page.route(`**/v1/workflow/ngc/my_workflow`, async (route) => {
    const request = route.request();
    const body = JSON.parse((await request.postData()) || "{}");

    // Add validation logic
    if (body.site === FORBIDDEN_SITE_ID) {
      await route.fulfill({
        status: 403,
        json: {
          error: "Forbidden: You do not have permission to run this workflow",
        },
      });
      return;
    }

    // Simulate processing delay
    await delay(2500);

    // Return success response
    await route.fulfill({
      status: 201,
      json: {
        id: body.site || "workflow-id",
        href: `https://url-to-temporal.com/namespaces/default/workflows/${
          body.site || "workflow-id"
        }`,
      },
    });
  });
}

// 2. Add to setupApiMocks function
export async function setupApiMocks(page: Page) {
  // ... existing mocks
  await mockMyWorkflowEndpoint(page);
}
```

## Writing Tests

### Testing DeviceWorkflowForm

For workflows using `DeviceWorkflowForm`, import and use the shared test utilities:

```typescript
// tests/e2e/myWorkflowForm.spec.ts
import { expect } from "@playwright/test";
import { test } from "./shared/utils";
import { runWorkflowFormTests } from "./shared/workflowFormTests";
import { DEVICES_LIST, SITES_LIST } from "@/mocks/data";

// Run standard tests for DeviceWorkflowForm
runWorkflowFormTests({
  formPath: "/workflows/myworkflow/form",
  formTitle: "My Workflow",
  defaultPlatform: "Arista EOS", // Optional: specify the platform for device filtering
});

// Add additional tests specific to your workflow
test.describe("My Workflow Form - Additional Tests", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/workflows/myworkflow/form");
  });

  test("custom validation test", async ({ page }) => {
    // Fill in site
    await page.getByRole("button", { name: "Site" }).click();
    await page.getByRole("dialog").getByText(SITES_LIST.pdx01).click();

    // Fill in device
    await page.getByRole("button", { name: "Device" }).click();
    await page
      .getByRole("dialog")
      .getByText(DEVICES_LIST.PDX01[0].name)
      .click();

    // Submit form
    await page.getByRole("button", { name: "Submit" }).click();

    // Verify navigation to workflow details
    await expect(
      page.getByRole("heading", { name: "Workflow Details" })
    ).toBeVisible({ timeout: 30000 });
  });

  test("handles specific error scenarios", async ({ page }) => {
    // Test your workflow-specific error cases
    // For example, testing with specific device types or configurations
  });
});
```

### Testing Custom Forms

For custom forms, write comprehensive tests covering all fields and scenarios:

```typescript
// tests/e2e/myCustomWorkflowForm.spec.ts
import { expect } from "@playwright/test";
import { test } from "./shared/utils";
import { SITES_LIST, ROLES_LIST, STATUS_LIST, TENANT_LIST } from "@/mocks/data";

test.describe("My Custom Workflow Form", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/workflows/mycustomworkflow/form");
  });

  test("submits form with all fields", async ({ page }) => {
    // Fill in site
    await page.getByRole("button", { name: "Site" }).click();
    await page.getByRole("dialog").getByText(SITES_LIST.pdx01).click();

    // Fill in roles (multi-select)
    await page.getByRole("button", { name: "Roles" }).click();
    await page.getByRole("dialog").getByText(ROLES_LIST.leaf).click();
    await page.getByRole("dialog").getByText(ROLES_LIST.spine).click();
    // Click outside to close dropdown
    await page
      .getByRole("heading", { name: "My Custom Workflow Form" })
      .click();

    // Fill in status (multi-select)
    await page.getByRole("button", { name: "Status" }).click();
    await page.getByRole("dialog").getByText(STATUS_LIST.active).click();
    await page
      .getByRole("heading", { name: "My Custom Workflow Form" })
      .click();

    // Fill in tenant
    await page.getByRole("button", { name: "Tenant" }).click();
    await page.getByRole("dialog").getByText(TENANT_LIST.ngc).click();

    // Toggle boolean field
    await page.getByRole("checkbox", { name: "Raise for Invalid" }).click();

    // Submit form
    await page.getByRole("button", { name: "Submit" }).click();

    // Verify navigation to workflow details
    await expect(
      page.getByRole("heading", { name: "Workflow Details" })
    ).toBeVisible({ timeout: 30000 });
  });

  test("validates required fields", async ({ page }) => {
    // Try to submit without filling required fields
    await page.getByRole("button", { name: "Submit" }).click();

    // Check for validation errors
    await expect(page.getByText("Site is required")).toBeVisible();
    await expect(page.getByText("At least one role is required")).toBeVisible();
  });

  test("loads from URL parameters", async ({ page }) => {
    // Navigate with URL parameters
    await page.goto(
      "/workflows/mycustomworkflow/form" +
        `?site=${SITES_LIST.pdx01}` +
        `&role=${ROLES_LIST.leaf}` +
        `&status=${STATUS_LIST.active}` +
        `&tenant=${TENANT_LIST.ngc}`
    );

    // Verify fields are pre-populated
    await expect(
      page.getByRole("button", { name: SITES_LIST.pdx01, exact: true })
    ).toBeVisible();
    await expect(
      page.getByRole("button", { name: ROLES_LIST.leaf, exact: true })
    ).toBeVisible();
  });

  test("handles API errors", async ({ page }) => {
    // Use forbidden site to trigger error
    await page.getByRole("button", { name: "Site" }).click();
    await page.getByRole("dialog").getByText("forbidden-site").click();

    // Fill other required fields...

    await page.getByRole("button", { name: "Submit" }).click();

    // Verify error message
    await expect(page.getByText("Workflow Failed")).toBeVisible({
      timeout: 30000,
    });
  });
});
```

## Best Practices

1. **Form Validation**: Always use Zod schemas for type-safe validation
2. **Error Handling**: Implement proper error states and user feedback
3. **Loading States**: Show loading indicators during API calls
4. **URL Parameters**: Support pre-filling forms via URL parameters
5. **Testing**: Write comprehensive tests covering happy paths and error scenarios
6. **Mock Data**: Use consistent mock data from `@/mocks/data`
7. **Accessibility**: Ensure all form elements have proper labels and ARIA attributes

## Directory Structure

```
src/
├── app/workflows/
│   └── myworkflow/
│       └── form/
│           ├── page.tsx
│           ├── loading.tsx
│           └── my-workflow-form.tsx (for custom forms)
├── config/
│   └── site.ts (register workflow here)
├── mocks/
│   └── handlers/
│       ├── index.ts
│       ├── workflowHandlers.ts (add to workflowTypes)
│       └── myWorkflowHandlers.ts
tests/
└── e2e/
    ├── shared/
    │   └── apiMocks.ts (add to mockWorkflowTypesEndpoint)
    └── myWorkflowForm.spec.ts
```

## Development Checklist

When creating a new workflow, ensure you:

### Form Creation

- [ ] Create the workflow form directory: `src/app/workflows/{workflowname}/form/`
- [ ] Create `page.tsx` (and custom form component if needed)
- [ ] Create `loading.tsx` with `WorkflowFormSkeleton` component
- [ ] Implement proper validation with Zod schema
- [ ] Support URL parameter pre-filling
- [ ] Handle loading and error states

### Workflow Registration

**Note**: These registrations are required for the workflow to appear in the application's navigation and workflow list page.

- [ ] Add workflow to `src/config/site.ts` in the `workflows` array:
  ```typescript
  {
    title: "My Workflow",
    slug: "myworkflow",
    enabled: true,
  }
  ```
- [ ] Add workflow type to `workflowTypes` array in `src/mocks/handlers/workflowHandlers.ts`:
  ```typescript
  export const workflowTypes = [
    // ... existing types
    "MyWorkflow", // Add your workflow type here
  ];
  ```
- [ ] Add workflow type to `mockWorkflowTypesEndpoint` in `tests/e2e/shared/apiMocks.ts`:
  ```typescript
  const workflowTypes = [
    // ... existing types
    "MyWorkflow", // Add your workflow type here
  ];
  ```

### API Mocking

- [ ] Create handler file: `src/mocks/handlers/{workflow}Handlers.ts`
- [ ] Import handler in `src/mocks/handlers/index.ts`
- [ ] Create Playwright mock in `tests/e2e/shared/apiMocks.ts`
- [ ] Add mock to `setupApiMocks` function

### Testing

- [ ] Create test file: `tests/e2e/{workflow}Form.spec.ts`
- [ ] For DeviceWorkflowForm: Use `runWorkflowFormTests` for basic tests
- [ ] Add workflow-specific test cases
- [ ] Test error scenarios and edge cases
- [ ] Test URL parameter loading

### Final Steps

- [ ] Verify form submits correctly
- [ ] Ensure navigation to workflow details page works
- [ ] Test with forbidden/error scenarios
- [ ] Run all tests: `npm run test:e2e`
