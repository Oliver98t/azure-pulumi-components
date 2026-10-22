import pulumi

from pulumi_components.function_app import FunctionAppComponent
from pulumi_components.web_app import WebAppComponent

def export_component_outputs(prefix_name: str, outputs: dict):
	for output in outputs:
		pulumi.export(f"{prefix_name}-{output}", outputs[output])

base_name = f"{pulumi.get_project()}".lower()
location = pulumi.Config("azure-native").get("location") or "WestUS2"

# function app test
#####################################################################
function_app = FunctionAppComponent(
    name=f"{base_name}-function-app",
	location=location,
)
#####################################################################

# web app app test
#####################################################################
network_stack = pulumi.StackReference(
    f"{pulumi.get_organization()}/azure-pulumi-infrastructure/{pulumi.get_stack()}"
)

subnet_id = network_stack.require_output("subnet_id")

web_app = WebAppComponent(
    name=f"{base_name}-web-app",
    location=location,
    subnet_id=subnet_id
)
#####################################################################

export_component_outputs("function-app", function_app.ouptuts)
export_component_outputs("web-app", web_app.outputs)