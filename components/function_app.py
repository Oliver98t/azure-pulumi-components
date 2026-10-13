import hashlib
import pulumi
from pulumi_azure_native import (
	applicationinsights,
	operationalinsights,
	resources,
	storage,
	web,
)

class FunctionAppComponent(pulumi.ComponentResource):
    def __init__(
            self, 
            name: str, 
            location: str, 
            opts: pulumi.ResourceOptions | None = None
    ):
        super().__init__(
            "FunctionApp", 
            name, 
            None, 
            opts
        )

        self.resource_group = resources.ResourceGroup(
            "resource-group",
            resource_group_name=f"{name}-rg",
            location=location,
            tags={
                "environment": pulumi.get_stack(),
                "project": pulumi.get_project(),
                "managed-by": "pulumi",
            },
        )

        self.log_analytics_workspace = operationalinsights.Workspace(
            f"{name}-logs",
            resource_group_name=self.resource_group.name,
            location=self.resource_group.location,
            sku=operationalinsights.WorkspaceSkuArgs(name="PerGB2018"),
            retention_in_days=30,
        )

        self.application_insights = applicationinsights.Component(
            f"{name}-insights",
            resource_group_name=self.resource_group.name,
            location=self.resource_group.location,
            application_type="web",
            kind="web",
            workspace_resource_id=self.log_analytics_workspace.id,
        )

        # Storage names are globally unique, lowercase, and limited to 24 characters.
        storage_name_prefix = name.replace("-", "")
        storage_name_hash = hashlib.sha256(name.encode()).hexdigest()[:8]
        storage_account_name = f"{storage_name_prefix[:15]}{storage_name_hash}"
        self.storage_account = storage.StorageAccount(
            "storage-account",
            account_name=storage_account_name,
            resource_group_name=self.resource_group.name,
            location=self.resource_group.location,
            kind="StorageV2",
            sku=storage.SkuArgs(name="Standard_LRS"),
        )
        storage_keys = storage.list_storage_account_keys_output(
            resource_group_name=self.resource_group.name,
            account_name=self.storage_account.name,
        )
        storage_connection_string = pulumi.Output.all(
            self.storage_account.name,
            storage_keys.keys,
        ).apply(
            lambda values: (
                "DefaultEndpointsProtocol=https;"
                f"AccountName={values[0]};"
                f"AccountKey={next(key["value"] for key in values[1] if key.get("value"))};"
                "EndpointSuffix=core.windows.net"
            )
        )

        self.service_plan = web.AppServicePlan(
            "service-plan",
            name=f"{name}-plan",
            resource_group_name=self.resource_group.name,
            location=self.resource_group.location,
            kind="functionapp,linux",
            reserved=True,
            sku=web.SkuDescriptionArgs(
                name="Y1",
                tier="Dynamic",
            ),
        )

        self.function_app = web.WebApp(
            "function-app",
            name=f"{name}-func",
            resource_group_name=self.resource_group.name,
            location=self.resource_group.location,
            kind="functionapp,linux",
            server_farm_id=self.service_plan.id,
            https_only=True,
            site_config=web.SiteConfigArgs(
                app_settings=[
                    web.NameValuePairArgs(
                        name="AzureWebJobsStorage",
                        value=storage_connection_string,
                    ),
                    web.NameValuePairArgs(
                        name="APPLICATIONINSIGHTS_CONNECTION_STRING",
                        value=self.application_insights.connection_string,
                    ),
                    web.NameValuePairArgs(
                        name="ApplicationInsightsAgent_EXTENSION_VERSION",
                        value="~3",
                    ),
                    web.NameValuePairArgs(name="FUNCTIONS_EXTENSION_VERSION", value="~4"),
                    web.NameValuePairArgs(name="FUNCTIONS_WORKER_RUNTIME", value="python"),
                    web.NameValuePairArgs(name="WEBSITE_RUN_FROM_PACKAGE", value="1"),
                    web.NameValuePairArgs(name="SCM_DO_BUILD_DURING_DEPLOYMENT", value="1"),
                ],
                linux_fx_version="Python|3.12",
            ),
        )
        self.register_outputs({
            "resource_group_name": self.resource_group.name,
            "storage_account_name": self.storage_account.name,
            "application_insights_name": self.application_insights.name,
            "service_plan_name": self.service_plan.name,
            "function_app_name": self.function_app.name,
            "function_app_url": pulumi.Output.concat(
                "https://",
                self.function_app.default_host_name,
            ),
        })