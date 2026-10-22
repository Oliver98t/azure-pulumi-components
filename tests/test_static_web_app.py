import pulumi
import pytest

from pulumi_components.static_web_app import StaticWebAppComponent


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
        if args.typ == "azure-native:web:StaticSite":
            outputs["defaultHostname"] = "sample.azurestaticapps.net"
        return f"{args.name}_id", outputs

    def call(self, args: pulumi.runtime.MockCallArgs):
        return {}


@pytest.fixture(autouse=True)
def configure_pulumi_mocks():
    mocks = Mocks()
    pulumi.runtime.set_mocks(mocks, project="test-project", stack="test")
    return mocks


@pulumi.runtime.test
def test_static_web_app_component_exports_names_and_https_url():
    component = StaticWebAppComponent("sample", "westus2")

    def assert_outputs(values):
        resource_group_name, app_name, app_url = values
        assert resource_group_name == "sample-rg"
        assert app_name == "sample-static"
        assert app_url == "https://sample.azurestaticapps.net"

    return pulumi.Output.all(
        component.outputs["resource_group_name"],
        component.outputs["static_web_app_name"],
        component.outputs["static_web_app_url"],
    ).apply(assert_outputs)


@pulumi.runtime.test
def test_static_web_app_component_creates_public_free_hosting(
    configure_pulumi_mocks: Mocks,
):
    component = StaticWebAppComponent("sample", "westus2")

    def assert_outputs(values):
        location, sku, public_network_access, app_tags, rg_tags = values
        app_inputs = next(
            resource.inputs
            for resource in configure_pulumi_mocks.resources
            if resource.typ == "azure-native:web:StaticSite"
        )
        assert app_inputs["resourceGroupName"] == "sample-rg"
        assert location == "westus2"
        assert sku == {"name": "Free", "tier": "Free"}
        assert public_network_access == "Enabled"
        assert app_tags == rg_tags == {
            "environment": "test",
            "project": "test-project",
            "managed-by": "pulumi",
        }
        resource_types = {
            resource.typ
            for resource in configure_pulumi_mocks.resources
            if resource.typ != "StaticWebApp"
        }
        assert resource_types == {
            "azure-native:resources:ResourceGroup",
            "azure-native:web:StaticSite",
        }

    return pulumi.Output.all(
        component.static_web_app.location,
        component.static_web_app.sku,
        component.static_web_app.public_network_access,
        component.static_web_app.tags,
        component.resource_group.tags,
    ).apply(assert_outputs)


@pulumi.runtime.test
def test_static_web_app_component_parents_resources():
    component = StaticWebAppComponent("sample", "westus2")

    def assert_parents(values):
        resource_group_urn, app_urn = values
        assert "::StaticWebApp$azure-native:resources:ResourceGroup::sample-rg" in (
            resource_group_urn
        )
        assert "::StaticWebApp$azure-native:web:StaticSite::sample-static" in app_urn

    return pulumi.Output.all(
        component.resource_group.urn,
        component.static_web_app.urn,
    ).apply(assert_parents)
