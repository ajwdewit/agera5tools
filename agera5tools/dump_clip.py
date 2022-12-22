# -*- coding: utf-8 -*-
# Copyright (c) December 2022, Wageningen Environmental Research
# Allard de Wit (allard.dewit@wur.nl)
import os, sys

import xarray as xr
import click

from .util import create_agera5_fnames, add_grid
from .build import modify_dataframe
from . import config

CMD_MODE = True if os.environ["CMD_MODE"] == "1" else False

selected_variables = [varname for varname, selected in config.variables.items() if selected]

def dump(day, bbox, add_gridid=False):
    """Converts the data for all AgERA5 variables for given day to a pandas dataframe.

    :param day: the date to process
    :param bbox: BoundingBox object indicating the lat/lon bounding box to select.
    :param add_gridid: Boolean indicating if a grid ID must be returned instead of lat/lon coordinates.
    :return: a dataframe with all selected AgERA5 variables.
    """
    in_bbox = config.region.boundingbox.region_in_bbox(bbox)
    if not in_bbox:
        msg = "Region for clipping not in the bounding box of this AgERA5tools configuration!"
        if CMD_MODE:
            click.echo(msg)
            sys.exit()
        else:
            raise RuntimeError(msg)

    fnames = create_agera5_fnames(config.data_storage.netcdf_path, selected_variables, day)
    ds = xr.open_mfdataset(fnames)
    ds = ds.sel(lon=slice(bbox.lon_min, bbox.lon_max), lat=slice(bbox.lat_max, bbox.lat_min))

    if add_gridid:
        ds = add_grid(ds)
    df = ds.to_dataframe()
    df = modify_dataframe(df)

    return df


def clip(day, bbox, add_gridid=False):
    """Extracts a portion of agERA5 for the given bounding box and returns a Xarray dataset.

    :param day: the date for which to clip
    :param bbox: a BoundingBox object
    :param add_idgrid: Add a grid ID (True) or not (False - default)
    :return: an xarray dataset containing all select AgERA5 variables for the given bounding box and day
    """
    in_bbox = config.region.boundingbox.region_in_bbox(bbox)
    if not in_bbox:
        msg = "Region for clipping not in the bounding box of this AgERA5tools configuration!"
        if CMD_MODE:
            click.echo(msg)
            sys.exit()
        else:
            raise RuntimeError(msg)

    fnames = create_agera5_fnames(config.data_storage.netcdf_path, selected_variables, day)
    ds = xr.open_mfdataset(fnames)
    if add_gridid:
        ds = add_grid(ds)
    ds_clip = ds.sel(lon=slice(bbox.lon_min, bbox.lon_max), lat=slice(bbox.lat_max, bbox.lat_min))

    return ds_clip
