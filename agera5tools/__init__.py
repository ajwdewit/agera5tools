# -*- coding: utf-8 -*-
# Copyright (c) May 2021, Wageningen Environmental Research
# Allard de Wit (allard.dewit@wur.nl)

# This will be set to True only for commandline mode. Not when importing
# agera5tools in python.
import os
os.environ["CMD_MODE"] = "0"

from .dump_grid import dump_grid
from .dump_clip import dump, clip
from .extract_point import extract_point


__version__ = "1.0.2"
