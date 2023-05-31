# -*- coding: utf-8 -*-
"""
Created on Tue May 30 10:50:51 2023

@author: Erty
"""

import os
import sys
import logging
from pathlib import Path
from datetime import datetime


def get_logger(log_name: str):
    if getattr(sys, 'frozen', False):
        app_dir = os.path.dirname(sys.executable)
    elif __file__:
        app_dir = os.path.dirname(__file__)

    logdir = Path(app_dir) / 'logs'
    if not logdir.is_dir():
        logdir.mkdir()

    logger = logging.getLogger(log_name)
    logger.setLevel(logging.DEBUG)

    now = datetime.now()
    filelog = logging.FileHandler(
        logdir / f"error_{now.strftime('%Y-%m-%d')}.log", delay=True)
    filelog.setLevel(logging.WARNING)
    filelog.setFormatter(
        logging.Formatter('%(asctime)s | %(levelname)-8s : %(message)s')
    )

    conlog = logging.StreamHandler()
    conlog.setLevel(logging.INFO)
    conlog.setFormatter(
        logging.Formatter('%(levelname)-8s : %(message)s')
    )

    logger.addHandler(filelog)
    logger.addHandler(conlog)

    return logger


def shutdown_logger(logger: logging.Logger) -> None:
    for handler in logger.handlers[:]:
        handler.close()
        logger.removeHandler(handler)
    logging.shutdown()
