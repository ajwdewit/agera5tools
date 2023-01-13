# -*- coding: utf-8 -*-
# Copyright (c) December 2022, Wageningen Environmental Research
# Allard de Wit (allard.dewit@wur.nl)
from pathlib import Path

import xarray as xr


def dump_grid():
    """Exports the AgERA5 grid that is embedded in the agera5tools packages

    :return: a dataframe with the grid definition
    """
    agera5_grid = Path(__file__).parent / "grid_elevation_landfraction.nc"
    ds = xr.open_dataset(agera5_grid)
    df = ds.to_dataframe()
    # remove line with missing grid values
    df = df[df.idgrid_era5 != -999]
    df.reset_index(inplace=True)
    # compute grid centre instead of lower left
    df["latitude"] = df.lat + 0.05
    df["longitude"] = df.lon + 0.05
    df = df.rename(columns={"lon": "ll_longitude", "lat": "ll_latitude"})
    # Only keep grids with land areas
    ix = df.land_fraction > 0
    df = df[ix]

    return df
