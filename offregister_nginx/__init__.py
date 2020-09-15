import yaml
import logging

from os import path
from logging.config import dictConfig as _dictConfig

__author__ = "Samuel Marks"
__version__ = "0.0.3"


def _get_logger():
    with open(path.join(path.dirname(__file__), "_data", "logging.yml"), "rt") as f:
        data = yaml.load(f)
    _dictConfig(data)
    return logging.getLogger()


logger = _get_logger()
