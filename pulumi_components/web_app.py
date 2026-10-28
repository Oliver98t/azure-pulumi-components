import pulumi
from pulumi_azure_native import (
    applicationinsights,
    monitor,
    operationalinsights,
    resources,
    web,
)


class WebAppComponent(pulumi.ComponentResource):
    def __init__(
        self,
        name: str,
        location: str,
        subnet_id: pulumi.Input[str],
        allowed_origins: pulumi.Input[str] | None = None,
        opts: pulumi.ResourceOptions | None = None,
    ):
        super().__init__("WebApp", name, None, opts)

        child_opts = pulumi.ResourceOptions(parent=self)
        
        self.outputs = {}
        self.resource_group = resources.ResourceGroup(
            "resource-group",
            resource_group_name=f"{name}-rg",
            location=location,
            tags={
                "environment": pulumi.get_stack(),
                "project": pulumi.get_project(),
                "managed-by": "pulumi",
            },
            opts=child_opts,
        )
        self.outputs['resource_group_name'] = self.resource_group.name

        self.log_analytics_workspace = operationalinsights.Workspace(
            f"{name}-logs",
            resource_group_name=self.resource_group.name,
            location=self.resource_group.location,
            sku=operationalinsights.WorkspaceSkuArgs(name="PerGB2018"),
            retention_in_days=30,
            opts=child_opts,
        )

        self.application_insights = applicationinsights.Component(
            f"{name}-insights",
            resource_group_name=self.resource_group.name,
            location=self.resource_group.location,
            application_type="web",
            kind="web",
            workspace_resource_id=self.log_analytics_workspace.id,
            opts=child_opts,
        )
        self.outputs['application_insights'] = self.application_insights.name

        self.service_plan = web.AppServicePlan(
            "service-plan",
            name=f"{name}-plan",
            resource_group_name=self.resource_group.name,
            location=self.resource_group.location,
            kind="linux",
            reserved=True,
            sku=web.SkuDescriptionArgs(name="B1", tier="Basic"),
            opts=child_opts,
        )
        self.outputs['service_plan_name'] = self.service_plan.name

        self.web_app = web.WebApp(
            "web-app",
            name=f"{name}-web",
            resource_group_name=self.resource_group.name,
            location=self.resource_group.location,
            kind="app,linux",
            server_farm_id=self.service_plan.id,
            virtual_network_subnet_id=subnet_id,
            https_only=True,
            site_config=web.SiteConfigArgs(
                always_on=True,
                app_command_line="python server.py",
                app_settings=[
                    web.NameValuePairArgs(
                        name="CORS_ORIGINS",
                        value=allowed_origins,
                    ),
                    web.NameValuePairArgs(
                        name="APPLICATIONINSIGHTS_CONNECTION_STRING",
                        value=self.application_insights.connection_string,
                    ),
                    web.NameValuePairArgs(
                        name="SCM_DO_BUILD_DURING_DEPLOYMENT",
                        value="1",
                    ),
                ],
                linux_fx_version="Python|3.12",
            ),
            opts=child_opts,
        )
        self.diagnostic_setting = monitor.DiagnosticSetting(
            f"{name}-console-logs",
            resource_uri=self.web_app.id,
            workspace_id=self.log_analytics_workspace.id,
            log_analytics_destination_type="Dedicated",
            logs=[
                monitor.DiagnosticsLogSettingsArgs(
                    category="AppServiceConsoleLogs",
                    enabled=True,
                ),
            ],
            opts=child_opts,
        )
        self.outputs['web_app_name'] = self.web_app.name
        self.outputs['web_app_url'] = pulumi.Output.concat(
                                            "https://",
                                            self.web_app.default_host_name,
                                        )
        self.register_outputs(self.outputs)