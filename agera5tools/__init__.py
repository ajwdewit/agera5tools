# -*- coding: utf-8 -*-
# Copyright (c) May 2021, Wageningen Environmental Research
# Allard de Wit (allard.dewit@wur.nl)

import os, sys
from pathlib import Path
import logging
import logging.config

__version__ = "2.1.0"

# This will be set to 1 only for commandline mode. Not when importing
# agera5tools in python.
os.environ["CMD_MODE"] = "0"


def setup_logging(config, has_filesystem):
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

    LOG_CONFIG_RTD = \
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
            },
            'root': {
                'handlers': ['console'],
                'propagate': True,
                'level': 'NOTSET'
            }
        }

    if has_filesystem:
        logging.config.dictConfig(LOG_CONFIG)
    else:
        logging.config.dictConfig(LOG_CONFIG_RTD)


def read_config(mk_paths=True):
    """Reads the YAML file with configuration for AgERA5tools

    if mk_paths is True, it will create the output directories.

    The config file is basically read as a dict. For convenience this converted into a DotMap object
    for easy access of config elements with dot access.

    :return:a DotMap object with the configuration
    """
    from .util import BoundingBox
    import yaml
    from dotmap import DotMap
    import click

    has_config = False
    if "AGERA5TOOLS_CONFIG" in os.environ:
        agera5t_config = Path(os.environ["AGERA5TOOLS_CONFIG"]).absolute()
        click.echo(f"using config from {agera5t_config}")
        has_config = True
    else:
        agera5t_config = Path(__file__).parent / "agera5tools.yaml"
        msg = "No config found, use `agera5tools init` to generate one!"
        click.echo(msg)

    c = None
    if has_config:
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
        if mk_paths:
            c.data_storage.netcdf_path.mkdir(exist_ok=True, parents=True)
            c.data_storage.tmp_path.mkdir(exist_ok=True, parents=True)
            c.data_storage.csv_path.mkdir(exist_ok=True, parents=True)
            c.logging.log_path.mkdir(exist_ok=True, parents=True)

    return c


if "READTHEDOCS" not in os.environ:  # Avoid imports for building documentation on RTD
    has_filesystem = True
    config = read_config(mk_paths=has_filesystem)
    setup_logging(config, has_filesystem)

    from . import util
    from .dump_grid import dump_grid
    from .dump_clip import dump, clip
    from .extract_point import extract_point
    from . import build
    from . import init
    from . import check
    from . import mirror
