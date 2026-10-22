# Azure Pulumi Components

Reusable Python Pulumi components for deploying Azure Function Apps, Web Apps,
and Static Web Apps.
The Function App example
provisions a resource group, storage account, Linux Consumption plan, Function App,
Log Analytics workspace, and Application Insights. The sample function exposes
`/api/hello` and requires a function key.

## Prerequisites

- Python 3.12 or newer for the Pulumi project; the deployed Function App uses 3.12.
- [uv](https://docs.astral.sh/uv/getting-started/installation/).
- [Pulumi CLI](https://www.pulumi.com/docs/install/).
- [Azure CLI](https://learn.microsoft.com/cli/azure/install-azure-cli) and an Azure subscription.
- [Azure Functions Core Tools v4](https://learn.microsoft.com/azure/azure-functions/functions-run-local)
  to publish the function code.
- Node.js 20.19+ on the 20.x line, or 22.12+ with npm, to build the Vite frontend.

Run the setup and test commands below from the repository root.

## Repository Layout

| Path | Purpose |
| --- | --- |
| [pulumi_components/function_app.py](pulumi_components/function_app.py) | Reusable `FunctionAppComponent` |
| [pulumi_components/web_app.py](pulumi_components/web_app.py) | Reusable `WebAppComponent` with VNet integration |
| [pulumi_components/static_web_app.py](pulumi_components/static_web_app.py) | Reusable public `StaticWebAppComponent` |
| [infrastructure/__main__.py](infrastructure/__main__.py) | Example Pulumi program and stack outputs |
| [source/function-app](source/function-app) | Azure Functions application and runtime requirements |
| [source/web-app](source/web-app) | FastAPI application and runtime requirements |
| [source/frontend](source/frontend) | React and Vite frontend for Static Web Apps |
| [deploy_web_app.sh](deploy_web_app.sh) | Code-only ZIP deployment for the Web App |
| [deploy_static_web_app.sh](deploy_static_web_app.sh) | Build and publish the React frontend to Static Web Apps |
| [tests/test_function_app.py](tests/test_function_app.py) | Component tests using Pulumi mocks |
| [tests/test_web_app.py](tests/test_web_app.py) | Web App configuration and VNet integration tests |
| [tests/test_static_web_app.py](tests/test_static_web_app.py) | Static Web App hosting, outputs, and resource parenting tests |
| [deploy_func.sh](deploy_func.sh) | Infrastructure deployment and function publishing |

## Using uv

[pyproject.toml](pyproject.toml) defines the project dependencies and dependency
groups. [uv.lock](uv.lock) records the resolved versions. `uv sync` creates or
updates the root `.venv` and installs the local component package.

### Dependency Groups

| Selection | Dependencies | Command |
| --- | --- | --- |
| Base project | `pulumi`, `pulumi-azure-native`, and the local package | `uv sync --locked` |
| Base project plus tests | Base dependencies and `pytest` from the `test` group | `uv sync --locked --group test` |
| All groups | Base dependencies and every declared group (currently only `test`) | `uv sync --locked --all-groups` |

Only `test` is currently declared as a dependency group. There is no `dev` group;
the `test` group is not included by default. `--group test` adds it alongside the
base dependencies.

For an explicitly base-only environment, use:

```bash
uv sync --locked --no-default-groups
```

`--only-group test` installs just the group's dependencies, omitting the project
and its base dependencies. Do not use it for these tests: they also need Pulumi
and the local component package. Syncing without `--group test` removes test-only
packages from the environment.

`--locked` fails if the lockfile needs updating instead of silently changing it.
After intentionally changing dependencies, use `uv sync` without `--locked` to
update the lockfile, then commit both dependency files.

### Running Tests

```bash
uv run --locked --group test python -m pytest
```

`uv run` synchronizes the requested dependencies before running the command; no
manual virtual environment activation is needed. Include `--group test` even
after a test-group sync so the command keeps those dependencies available.
The tests use Pulumi mocks and do not deploy resources or require Azure credentials.

### Adding Dependencies

```bash
uv add <package>
uv add --group test <test-package>
```

The first command adds a base project dependency. The second adds a dependency to
the `test` group. Both update the project metadata and lockfile. Additional groups
can be created with `uv add --group <group-name> <package>` and selected with
`uv sync --group <group-name>`.

The Function App's [requirements.txt](source/function-app/requirements.txt) is
separate from the root project's dependency groups. Azure installs those runtime
dependencies during the remote build; adding a root dependency with `uv add`
does not add it to the deployed function.

## Deploying to Azure

### Public Static Web App

`StaticWebAppComponent` creates a resource group and a public Azure Static Web App
on the Free plan. Azure provides the default `azurestaticapps.net` hostname and
managed HTTPS. No VNet, subnet, private endpoint, App Service plan, or custom DNS
is required.

```python
import pulumi

from pulumi_components.static_web_app import StaticWebAppComponent

frontend = StaticWebAppComponent(
    name="my-frontend",
    location="westus2",
)

for key, value in frontend.outputs.items():
    pulumi.export(key, value)
```

Outputs are `resource_group_name`, `static_web_app_name`, and
`static_web_app_url`. Choose an Azure region supported by Static Web Apps, such as
`westus2`; its available resource regions differ from App Service.

The [example Pulumi program](infrastructure/__main__.py) includes this component
alongside the existing Function App and Web App, exporting its outputs with the
`static-web-app-` prefix. Run `pulumi preview` and then `pulumi up` from
`infrastructure` to provision the configured resources. The existing Web App
example still requires its network stack and integration subnet.

This component provisions hosting only: it does not deploy frontend files,
configure repository integration, create custom domains, or modify backend CORS.
Publish your compiled frontend separately using
[the Static Web Apps CLI](https://learn.microsoft.com/azure/static-web-apps/static-web-apps-cli-deploy)
or a deployment workflow. Keep deployment tokens in your CI secret store, not
source control or public stack outputs.

For a browser-rendered frontend calling the FastAPI App Service directly, configure
the API URL in your frontend and allow the frontend's exact HTTPS origin in the
API's CORS policy. The API must be reachable from users' browsers. Static Web Apps
does not provide a private network path to the API, and CORS is not authentication.
Frontend configuration is visible to users; never include backend secrets in it.

### React and Vite Frontend Example

The sample in [source/frontend](source/frontend) uses React and Vite, with a simple
interactive counter managed by React state. It runs independently of the FastAPI
backend. The UI is defined in [App.jsx](source/frontend/src/App.jsx).

From the repository root:

```bash
cd source/frontend
npm ci
npm run dev
```

Open the local URL printed by Vite. To build and preview the production files:

```bash
npm run build
npm run preview
```

The build produces `source/frontend/dist`, which can be published to the Static
Web App. For a deployment workflow, use `source/frontend` as the app location,
`npm run build` as the build command, and `dist` as the output location relative
to the app. The Vite development and preview servers are for local use, not
production hosting. Dependencies and generated build files are ignored by Git;
the npm lockfile is committed for reproducible installs.

### Deploying the Frontend

After provisioning the infrastructure, sign in with `az login`, select the target
Azure subscription with `az account set --subscription <subscription-id>`, and
select the matching Pulumi stack in `infrastructure`. Your Azure identity needs
permission to retrieve the Static Web App's deployment token.

From the repository root:

```bash
bash deploy_static_web_app.sh
```

The script reads `static-web-app-static_web_app_name` and
`static-web-app-resource_group_name` from the selected stack, installs the locked
npm dependencies, builds the frontend, and publishes `dist` to the **production**
environment using the pinned Static Web Apps CLI. It updates frontend content
only; it does not run `pulumi up` or deploy the FastAPI backend.

The deployment token is fetched using Azure CLI and passed to the deployment
process through `SWA_CLI_DEPLOYMENT_TOKEN`, not command-line arguments or a file.
Shell tracing is disabled to avoid logging it. Do not enable verbose/debug
logging when handling deployment credentials.

The CLI may download its deployment client on first use, so internet access is
required. Build, authentication, and CLI failures stop the script. After a
successful deployment, open the URL from
`pulumi stack output static-web-app-static_web_app_url` in `infrastructure`
to verify the live site.

Run the deployment script's mocked success and failure tests without Azure access:

```bash
bash tests/test_deploy_static_web_app.sh
```

### Web App with VNet Integration

`WebAppComponent` creates a resource group, Linux Basic B1 App Service plan,
Python 3.12 Web App, Log Analytics workspace, and Application Insights. It accepts
an existing subnet ID as either a string or a Pulumi `Output[str]`; it does not
create or modify the VNet or subnet.

```python
import pulumi

from pulumi_components.web_app import WebAppComponent

config = pulumi.Config()
web_app = WebAppComponent(
    name="my-web-app",
    location="uksouth",
    subnet_id=config.require("webAppSubnetId"),
)

pulumi.export("web_app_name", web_app.web_app.name)
pulumi.export("web_app_url", web_app.web_app_url)
```

Set `webAppSubnetId` to the full Azure resource ID of the integration subnet.
When creating the subnet in the same Pulumi program, pass `subnet.id` instead to
preserve the resource dependency.

The subnet must be in the same region as the Web App, delegated to
`Microsoft.Web/serverFarms`, and sized at least `/28` (`/26` is recommended for
scaling). Ensure the deployment identity has permission to join the subnet.
The B1 plan supports regional VNet integration and incurs charges.

VNet integration provides outbound access to the VNet; it does not make the
Web App's inbound endpoint private or route all internet-bound traffic through
the VNet. HTTPS is required, Always On is enabled, and remote build is configured
for code deployments. Application code must be published separately; the component
does not deploy code. The existing Function App example remains unchanged.

The Web App diagnostic setting exports `AppServiceConsoleLogs` to the component's
Log Analytics workspace using resource-specific tables (`Dedicated`). This is
separate from the application's OpenTelemetry export to Application Insights.
Apply it with `pulumi up` from `infrastructure`; no application redeployment is
required for this diagnostic setting. Only new console logs are exported, and
ingestion can take several minutes. Log Analytics ingestion charges may apply.
Generate requests to the app, then query the component's workspace:

```kusto
AppServiceConsoleLogs
| where TimeGenerated > ago(1h)
| project TimeGenerated, Level, ResultDescription
| order by TimeGenerated desc
```

### FastAPI Web App Example

The sample in [source/web-app](source/web-app) uses FastAPI and Uvicorn.
`GET /check` returns `{"message": "Hello from Azure Web App!"}` as JSON;
`/docs` provides interactive API documentation.

The sample uses application-managed `azure-monitor-opentelemetry` to collect
FastAPI request traces, supported outbound dependencies, metrics, and logs from
the `web_app` logger. The component supplies
`APPLICATIONINSIGHTS_CONNECTION_STRING` and does not enable the App Service
Application Insights agent, avoiding conflicts with agent-bundled Python libraries.
Use `logging.getLogger("web_app")` (or a child such as `web_app.orders`) for
application logs sent to Application Insights. Console output remains available;
arbitrary stdout and other loggers are not exported by the SDK, but console
output is exported separately through the App Service diagnostic setting.
Without a connection string, local runs emit a warning and use console logging
only. Invalid configured connection strings are not silently ignored.
The `server.py` entry point configures both Python and Uvicorn logging: messages
below ERROR (including startup, access logs, and warnings) go to stdout; ERROR
and CRITICAL go to stderr. Azure SDK logging is limited to warnings and errors.
This prevents informational server logs being classified as errors because of
their output stream. Application Insights retains structured Python severity.
Azure platform messages outside this Python process have their own logging.

Run it locally from the repository root:

```bash
cd source/web-app
uv run --no-project --with-requirements requirements.txt \
  python server.py
```

The Web App component sets the Azure startup command to:

```text
python server.py
```

When updating to this entry point, deploy the application code (including
`server.py`) with `bash deploy_web_app.sh`, then apply the startup command
change with `pulumi up` from `infrastructure`. Existing ingested records are
not reclassified.

Apply this configuration with `pulumi up` from `infrastructure`, then publish
the application code separately:

```bash
bash deploy_web_app.sh
```

When migrating from the injected agent, apply `pulumi up` first to remove
`ApplicationInsightsAgent_EXTENSION_VERSION`, then run the deployment script
to install and publish the application-managed SDK. Infrastructure deployment
alone does not install the new application dependencies. After deployment,
request `/check` and check Application Insights transaction search and the `traces`
table for `Serving the greeting`; telemetry ingestion can take several minutes.

The script requires Bash, `zip`, Pulumi CLI, and Azure CLI. Sign in to Azure,
select the correct subscription, and select the intended Pulumi stack first.
It reads that stack's Web App name and resource group, packages the contents of
`source/web-app` at the ZIP root, and uses
`az webapp deploy --type zip --async true --track-status false`.
It excludes local virtual environments, caches, Git metadata, `node_modules`,
and `.env*` files, and removes its temporary ZIP on exit. Keep other secrets
outside the application directory.

Startup tracking is explicitly disabled so the CLI does not continue polling
Linux site readiness after asynchronous submission.
The script exits after submission rather than waiting for the remote build and
startup, reducing exposure to gateway timeouts during long-running deployments.
Successful submission does not prove the deployment succeeded. It prints commands
to check the latest deployment status and logs; status `3` means failed and `4`
means successful. Confirm the deployment ID is the one you submitted (the latest
record can change if another deployment starts), then verify the application URL
responds successfully. If submission returns a gateway error, inspect deployment
status before retrying because Azure may still have accepted the deployment.

The script works from any working directory and does not create or configure
infrastructure. The enabled remote build installs the application requirements;
these are separate from the root Pulumi dependencies.

### Function App Example

Authenticate, install the base dependencies, and select the example stack:

```bash
az login
az account set --subscription <subscription-id>
pulumi login
uv sync --locked
cd infrastructure
pulumi stack select dev --create
pulumi config set azure-native:location CentralUS
pulumi preview
pulumi up
pulumi stack output
cd ..
```

[infrastructure/Pulumi.yaml](infrastructure/Pulumi.yaml) configures Pulumi's Python
runtime to use `uv`. The `dev` stack is configured for `CentralUS`; the program
falls back to `WestUS2` when no location is set. Deployment creates billable Azure
resources.

Once the stack is selected, deploy the infrastructure and publish the function
code from the repository root:

```bash
bash deploy_func.sh
```

The script runs `pulumi up -y` (automatically approving changes), reads the
`function_app_name` stack output, and publishes the code using
`func azure functionapp publish` with a Python remote build. Infrastructure
deployment alone does not publish the function code.

To remove the Azure resources when finished:

```bash
cd infrastructure
pulumi destroy
```