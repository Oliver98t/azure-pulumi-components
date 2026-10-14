import logging

import azure.functions as func

logger = logging.getLogger(__name__)

app = func.FunctionApp(http_auth_level=func.AuthLevel.FUNCTION)


@app.route(route="hello")
def hello(req: func.HttpRequest) -> func.HttpResponse:
    logger.info("Handling hello request: method=%s route=%s", req.method, req.route_params)
    response = func.HttpResponse("Hello from Azure Functions!")
    logger.info("Hello request completed: status_code=%s", response.status_code)
    return response
