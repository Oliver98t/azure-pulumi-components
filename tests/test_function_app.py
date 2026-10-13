import pulumi
import pytest

from pulumi_components.function_app import FunctionAppComponent


class Mocks(pulumi.runtime.Mocks):
    def new_resource(self, args: pulumi.runtime.MockResourceArgs):
        outputs = dict(args.inputs)
        outputs.setdefault(
            "name",
            args.inputs.get("name") or args.inputs.get("accountName") or args.name,
        )
        outputs.setdefault("defaultHostName", f"{args.name}.azurewebsites.net")
        outputs.setdefault("connectionString", "InstrumentationKey=test-key")
        return f"{args.name}_id", outputs

    def call(self, args: pulumi.runtime.MockCallArgs):
        return {"keys": [{"value": "test-storage-key"}]}


@pytest.fixture(autouse=True)
def configure_pulumi_mocks():
    pulumi.runtime.set_mocks(Mocks(), project="test-project", stack="test")


@pulumi.runtime.test
def test_function_app_component_creates_expected_resources():
    component = FunctionAppComponent("sample", "uksouth")

    def assert_outputs(values: list[str]):
        storage_account_name, service_plan_name, function_app_name = values
        assert storage_account_name.startswith("sample")
        assert service_plan_name == "sample-plan"
        assert function_app_name == "sample-func"

    return pulumi.Output.all(
        component.storage_account.name,
        component.service_plan.name,
        component.function_app.name,
    ).apply(assert_outputs)