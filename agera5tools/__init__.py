# -*- coding: utf-8 -*-
# Copyright (c) May 2021, Wageningen Environmental Research
# Allard de Wit (allard.dewit@wur.nl)

# This will be set to True only for commandline mode. Not when importing
# agera5tools in python.
import os, sys
os.environ["CMD_MODE"] = "0"
from pathlib import Path
import logging
import logging.config

import yaml
from dotmap import DotMap
import click

from . import util

__version__ = "1.0.2"

def setup_logging(config):
    """sets up the logging system for both logging to file and to console.

    file logging is based on a rotating file handler to avoid log files becoming very large.

    :param config: a configuration object.
    """

    LOG_FILE_NAME = config.logging.log_path / config.logging.log_fname
    LOG_LEVEL_FILE = config.logging.log_level_file
    LOG_LEVEL_CONSOLE = config.logging.log_level_console
    LOG_CONFIG = \
        {
            'version': 1,
            'disable_existing_loggers': True,
            'formatters': {
                'standard': {
                    'format': '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
                },
                'brief': {
                    'format': '[%(levelname)s] - %(message)s'
                },
            },
            'handlers': {
                'console': {
                    'level': LOG_LEVEL_CONSOLE,
                    'class': 'logging.StreamHandler',
                    'formatter': 'brief'
                },
                'file': {
                    'level': LOG_LEVEL_FILE,
                    'class': 'logging.handlers.RotatingFileHandler',
                    'formatter': 'standard',
                    'filename': LOG_FILE_NAME,
                    'maxBytes': 1024 ** 2,
                    'backupCount': 7,
                    'mode': 'a',
                    'encoding': 'utf8'
                },
            },
            'root': {
                'handlers': ['console', 'file'],
                'propagate': True,
                'level': 'NOTSET'
            }
        }

    logging.config.dictConfig(LOG_CONFIG)

def read_config():
    """Reads the YAML file with configuration for AgERA5tools

    The config file is basically read as a dict. For convenience this converted into a DotMap object
    for easy access of config elements with dot access.

    :return:a DotMap object with the configuration
    """

    default_config = True
    if "AGERA5TOOLS_CONFIG" in os.environ:
        agera5t_config = Path(os.environ["AGERA5TOOLS_CONFIG"]).absolute()
        default_config = False
    else:
        agera5t_config = Path(__file__).parent / "agera5tools.yaml"
        msg = "No config found: Using default AGERA5TOOLS configuration!"
        click.echo(msg)
    print(f"using config from {agera5t_config}")

    try:
        with open(agera5t_config) as fp:
            r = yaml.safe_load(fp)
    except Exception as e:
        msg = f"Failed to read AGERA5Tools configuration from {agera5t_config}"
        click.echo(msg)
        sys.exit()

    c =  DotMap(r, _dynamic=False)
    # Update config values into proper objects
    c.region.boundingbox = util.BoundingBox(**c.region.boundingbox)
    c.data_storage.netcdf_path = Path(c.data_storage.netcdf_path)
    c.data_storage.tmp_path = Path(c.data_storage.tmp_path)
    c.data_storage.csv_path = Path(c.data_storage.csv_path)
    c.logging.log_path = Path(c.logging.log_path)
    c.data_storage.tmp_path.mkdir(exist_ok=True)
    c.data_storage.csv_path.mkdir(exist_ok=True)
    c.logging.log_path.mkdir(exist_ok=True)

    return c


config = read_config()
setup_logging(config)


from .dump_grid import dump_grid
from .dump_clip import dump, clip
from .extract_point import extract_point
from . import build
from . import init
from . import check
from . import mirror




