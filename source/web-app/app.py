import logging
import os
import sys

from azure.monitor.opentelemetry import configure_azure_monitor
from fastapi import FastAPI
from fastapi.responses import PlainTextResponse

logging.basicConfig(level=logging.INFO, stream=sys.stdout)
logging.getLogger("azure").setLevel(logging.WARNING)
logger = logging.getLogger("web_app")
logger.setLevel(logging.INFO)

if os.environ.get("APPLICATIONINSIGHTS_CONNECTION_STRING"):
    configure_azure_monitor(logger_name=logger.name)
else:
    logger.warning(
        "APPLICATIONINSIGHTS_CONNECTION_STRING is not set; "
        "Azure Monitor telemetry is disabled. Logging to the console only."
    )

app = FastAPI()


@app.get("/check", response_class=PlainTextResponse)
def hello() -> str:
    logger.info("Serving the greeting")
    return "Hello from Azure Web App!"