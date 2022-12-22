# -*- coding: utf-8 -*-
# Copyright (c) December 2022, Wageningen Environmental Research
# Allard de Wit (allard.dewit@wur.nl)

import datetime as dt
from itertools import product

from . import config
from .util import create_target_fname


def determine_day_range():
    """Determines the days that should be available given the configuration and the current date

    :return: a list of date objects
    """
    latest_agera5_day = dt.date.today() - dt.timedelta(days=8)
    latest_config_day = dt.date(config.temporal_range.end_year, 12, 31)
    max_day = min(latest_agera5_day, latest_config_day)
    start_day = dt.date(config.temporal_range.start_year, 1, 1)
    ndays = (max_day - start_day).days
    days_required = [start_day + dt.timedelta(days=i) for i in range(ndays+1)]

    return days_required


def check():
    """This checks the existence of the NetCDF files in the archive and does some basic checking on the
    files itself.

    :return: the list of missing files
    """
    days = determine_day_range()
    selected_variables = [varname for varname, selected in config.variables.items() if selected]
    missing_nc_fnames = []
    for varname, day in product(selected_variables, days):
        f = create_target_fname(varname, day, config.data_storage.netcdf_path)
        if not f.exists():
            missing_nc_fnames.append(f)

    return missing_nc_fnames


if __name__ == "__main__":
    check()