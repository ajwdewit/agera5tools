# -*- coding: utf-8 -*-
# Copyright (c) May 2021, Wageningen Environmental Research
# Allard de Wit (allard.dewit@wur.nl)
import os, sys
import xarray as xr
import pandas as pd
from .util import create_agera5_fnames, convert_to_celsius, add_grid

CMD_MODE = True if os.environ["CMD_MODE"] == "1" else False


def dump(agera5_dir, day, bbox, tocelsius=False, add_gridid=False):
    """Converts the data for all AgERA5 variables for given day to a pandas dataframe.

    :param agera5_dir: the location of the AgERA5 dataset
    :param day: the date to process
    :param bbox: BoundingBox object indicating the lat/lon bounding box to select.
    :param tocelsius: Boolean indicating if a conversion of K to C is needed.
    :param add_gridid: Boolean indicating if a grid ID must be returned instead of lat/lon coordinates.
    :return: a dataframe with all 22 variables.
    """
    fnames = create_agera5_fnames(agera5_dir, day)
    ds = xr.open_mfdataset(fnames)
    ds = ds.sel(lon=slice(bbox.lon_min, bbox.lon_max), lat=slice(bbox.lat_max, bbox.lat_min))
    if add_gridid:
        ds = add_grid(ds)

    df = ds.to_dataframe()
    df.reset_index(inplace=True)
    ix = df.Wind_Speed_10m_Mean.notnull()
    df = df[ix]

    df['time'] = pd.to_datetime(df.time).dt.date
    df["Solar_Radiation_Flux"] = df.Solar_Radiation_Flux.astype(int)
    if tocelsius:
        df = convert_to_celsius(df)
    if add_gridid:
        df = df.drop(columns=["lat", "lon"])
        ix = df.grid_agera5 == -999
        if any(ix):
            df = df[~ix]

    return df


def clip(agera5_dir, day, bbox, add_gridid=False):
    """Extracts a portion of agERA5 for the given bounding box and returns a Xarray dataset.

    :param agera5_dir: the path to AgERA5
    :param day: the date for which to clip
    :param bbox: a BoundingBox object
    :param add_idgrid: Add a grid ID (True) or not (False - default)
    :return: an xarray dataset containing all 22 variables for the given bounding box and day
    """
    fnames = create_agera5_fnames(agera5_dir, day)
    ds = xr.open_mfdataset(fnames)
    if add_gridid:
        ds = add_grid(ds)
    ds_clip = ds.sel(lon=slice(bbox.lon_min, bbox.lon_max), lat=slice(bbox.lat_max, bbox.lat_min))

    return ds_clip
