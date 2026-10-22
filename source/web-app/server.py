import logging

import uvicorn


class BelowErrorFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        return record.levelno < logging.ERROR


LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "filters": {"below_error": {"()": BelowErrorFilter}},
    "formatters": {
        "default": {"format": "%(levelname)s:%(name)s:%(message)s"},
    },
    "handlers": {
        "stdout": {
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stdout",
            "formatter": "default",
            "filters": ["below_error"],
        },
        "stderr": {
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stderr",
            "formatter": "default",
            "level": "ERROR",
        },
    },
    "root": {"handlers": ["stdout", "stderr"], "level": "INFO"},
    "loggers": {
        "azure": {"handlers": [], "level": "WARNING", "propagate": True},
        "uvicorn": {"handlers": [], "level": "INFO", "propagate": True},
        "uvicorn.error": {"handlers": [], "level": "INFO", "propagate": True},
        "uvicorn.access": {"handlers": [], "level": "INFO", "propagate": True},
    },
}


if __name__ == "__main__":
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=8000,
        log_config=LOGGING_CONFIG,
    )
