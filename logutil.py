"""
Utility class to set up logging
"""

from typing import Final, Dict, Any
import os
import sys
import logging, logging.config
from pathlib import Path
from datetime import datetime


DEBUG: Final[bool] = bool(os.getenv('DEBUG', ''))

def setup_logger() -> None:
    if getattr(sys, 'frozen', False):
        app_dir = os.path.dirname(sys.executable)
    elif __file__:
        app_dir = os.path.dirname(__file__)

    log_dir = Path(app_dir) / 'logs'
    now = datetime.now()
    log_config: Dict[str, Any] = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "simple": {
                "format": "%(levelname)-8s : %(message)s",
            },
            "verbose": {
                "format": "[%(asctime)s]%(levelname)s|%(module)s|line#%(lineno)d| : %(message)s",
                "datefmt": "%Y-%m-%dT%H:%M:%S",
            }
        },
        "handlers": {
            "stdout": {
                "class": "logging.StreamHandler",
                "level": "INFO",
                "formatter": "simple",
                "stream": "ext://sys.stdout",
            },
            "file": {
                "class": "logging.FileHandler",
                "level": "WARNING",
                "formatter": "verbose",
                "filename": str(log_dir / f"error_{now.strftime('%Y-%m-%d')}.log"),
                "encoding": "utf8",
                "delay": True,
            }
        },
        "loggers": {
            "root": {
                "level": "DEBUG",
                "handlers": [
                    "stdout",
                    "file",
                ]
            }
        }
    }

    if not log_dir.is_dir():
        log_dir.mkdir()

    logging.config.dictConfig(log_config)
    stdouthandler = logging.getHandlerByName('stdout')
    if stdouthandler and DEBUG:
        stdouthandler.setLevel(logging.DEBUG)


def shutdown_logger(logger: logging.Logger) -> None:
    for handler in logger.handlers:
        handler.close()
        logger.removeHandler(handler)
    logging.shutdown()
