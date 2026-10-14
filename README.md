# Azure Pulumi Components

Reusable Python Pulumi components for deploying an Azure Function App. The example
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

Run the setup and test commands below from the repository root.

## Repository Layout

| Path | Purpose |
| --- | --- |
| [pulumi_components/function_app.py](pulumi_components/function_app.py) | Reusable `FunctionAppComponent` |
| [infrastructure/__main__.py](infrastructure/__main__.py) | Example Pulumi program and stack outputs |
| [source/function-app](source/function-app) | Azure Functions application and runtime requirements |
| [tests/test_function_app.py](tests/test_function_app.py) | Component tests using Pulumi mocks |
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