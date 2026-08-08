import logging
import logging.config

CUSTOM_LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "default": {
            "()": "uvicorn.logging.DefaultFormatter",
            "fmt": "%(asctime)s %(levelprefix)s %(message)s",
            "datefmt": "%d/%b/%Y %X %z",
            "use_colors": True,
        },
        "access": {
            "()": "uvicorn.logging.AccessFormatter",
            "fmt": '%(asctime)s -- %(levelprefix)s %(client_addr)s - "%(request_line)s" %(status_code)s',
            "datefmt": "%d/%b/%Y %X %z",
            "use_colors": True,
        },
    },
    "handlers": {
        "default": {
            "formatter": "default",
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stderr",
        },
        "access": {
            "formatter": "access",
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stdout",
        },
    },
    "loggers": {
        "": {"handlers": ["default"], "level": "INFO"},
        "uvicorn": {"handlers": ["default"], "level": "INFO", "propagate": False},
        "uvicorn.error": {"level": "INFO"},
        "uvicorn.access": {"handlers": ["access"], "level": "INFO", "propagate": False},
        # Third-party noisy loggers set to ERROR level to silence INFO/WARN logs
        "aiokafka": {"level": "ERROR"},
        "aiokafka.conn": {"level": "ERROR"},
        "aiokafka.consumer.group_coordinator": {"level": "ERROR"},
        "motor": {"level": "ERROR"},
        "pymongo": {"level": "ERROR"},
        "sqlalchemy.engine": {"level": "ERROR"},
    },
}


def setup_logging():
    logging.config.dictConfig(CUSTOM_LOGGING_CONFIG)
