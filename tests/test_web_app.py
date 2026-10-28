import pulumi
import pytest

from pulumi_components.web_app import WebAppComponent


SUBNET_ID = (
    "/subscriptions/test-subscription/resourceGroups/network-rg"
    "/providers/Microsoft.Network/virtualNetworks/test-vnet/subnets/web"
)


class Mocks(pulumi.runtime.Mocks):
    def __init__(self):
        self.resources: list[pulumi.runtime.MockResourceArgs] = []

    def new_resource(self, args: pulumi.runtime.MockResourceArgs):
        self.resources.append(args)
        outputs = dict(args.inputs)
        outputs.setdefault(
            "name",
            args.inputs.get("resourceGroupName") or args.name,
        )
        outputs.setdefault("defaultHostName", f"{outputs['name']}.azurewebsites.net")
        outputs.setdefault("connectionString", "InstrumentationKey=test-key")
        return f"{args.name}_id", outputs

    def call(self, args: pulumi.runtime.MockCallArgs):
        return {}


@pytest.fixture(autouse=True)
def configure_pulumi_mocks():
    mocks = Mocks()
    pulumi.runtime.set_mocks(mocks, project="test-project", stack="test")
    return mocks


@pulumi.runtime.test
def test_web_app_component_creates_expected_resources():
    component = WebAppComponent("sample", "uksouth", SUBNET_ID)

    def assert_outputs(values):
        resource_group_name, plan_name, app_name, app_url, location, tags = values
        assert resource_group_name == "sample-rg"
        assert plan_name == "sample-plan"
        assert app_name == "sample-web"
        assert app_url == "https://sample-web.azurewebsites.net"
        assert location == "uksouth"
        assert tags == {
            "environment": "test",
            "project": "test-project",
            "managed-by": "pulumi",
        }

    return pulumi.Output.all(
        component.resource_group.name,
        component.service_plan.name,
        component.web_app.name,
        component.outputs["web_app_url"],
        component.web_app.location,
        component.resource_group.tags,
    ).apply(assert_outputs)


@pulumi.runtime.test
def test_web_app_component_configures_linux_plan_and_vnet_integration(
    configure_pulumi_mocks: Mocks,
):
    component = WebAppComponent(
        "sample",
        "uksouth",
        pulumi.Output.from_input(SUBNET_ID),
        allowed_origins=pulumi.Output.from_input(
            "https://frontend.azurestaticapps.net"
        ),
    )

    def assert_outputs(values):
        subnet_id, plan_id, reserved, sku, kind, https_only, site_config = values
        assert subnet_id == SUBNET_ID
        assert plan_id == "service-plan_id"
        assert reserved is True
        assert sku["name"] == "B1"
        assert sku["tier"] == "Basic"
        assert kind == "app,linux"
        assert https_only is True
        assert site_config["always_on"] is True
        assert site_config["linux_fx_version"] == "Python|3.12"
        assert site_config["app_command_line"] == (
            "python server.py"
        )
        app_inputs = next(
            resource.inputs
            for resource in configure_pulumi_mocks.resources
            if resource.typ == "azure-native:web:WebApp"
        )
        settings = {
            setting["name"]: setting["value"]
            for setting in app_inputs["siteConfig"]["appSettings"]
        }
        assert settings == {
            "CORS_ORIGINS": "https://frontend.azurestaticapps.net",
            "APPLICATIONINSIGHTS_CONNECTION_STRING": "InstrumentationKey=test-key",
            "SCM_DO_BUILD_DURING_DEPLOYMENT": "1",
        }

    return pulumi.Output.all(
        component.web_app.virtual_network_subnet_id,
        component.web_app.server_farm_id,
        component.service_plan.reserved,
        component.service_plan.sku,
        component.web_app.kind,
        component.web_app.https_only,
        component.web_app.site_config,
    ).apply(assert_outputs)


@pulumi.runtime.test
def test_web_app_component_exports_console_logs_to_workspace(
    configure_pulumi_mocks: Mocks,
):
    component = WebAppComponent("sample", "uksouth", SUBNET_ID)

    def assert_outputs(values):
        _, workspace_id, destination_type, logs = values
        diagnostic_inputs = next(
            resource.inputs
            for resource in configure_pulumi_mocks.resources
            if resource.typ == "azure-native:monitor:DiagnosticSetting"
        )
        assert diagnostic_inputs["resourceUri"] == "web-app_id"
        assert workspace_id == "sample-logs_id"
        assert destination_type == "Dedicated"
        assert len(logs) == 1
        assert logs[0]["category"] == "AppServiceConsoleLogs"
        assert logs[0]["enabled"] is True

    return pulumi.Output.all(
        component.diagnostic_setting.id,
        component.diagnostic_setting.workspace_id,
        component.diagnostic_setting.log_analytics_destination_type,
        component.diagnostic_setting.logs,
    ).apply(assert_outputs)


@pulumi.runtime.test
def test_web_app_component_connects_application_insights_to_workspace():
    component = WebAppComponent("sample", "uksouth", SUBNET_ID)

    def assert_outputs(values):
        workspace_id, retention, sku, application_type = values
        assert workspace_id == "sample-logs_id"
        assert retention == 30
        assert sku["name"] == "PerGB2018"
        assert application_type == "web"

    return pulumi.Output.all(
        component.application_insights.workspace_resource_id,
        component.log_analytics_workspace.retention_in_days,
        component.log_analytics_workspace.sku,
        component.application_insights.application_type,
    ).apply(assert_outputs)
