# -*- coding: utf-8 -*-
# Copyright (c) May 2021, Wageningen Environmental Research
# Allard de Wit (allard.dewit@wur.nl)
import sys, os
import xarray as xr
import pandas as pd

CMD_MODE = True if os.environ["CMD_MODE"] == "1" else False
from .util import create_target_fname, convert_to_celsius
from . import config
selected_variables = [varname for varname, selected in config.variables.items() if selected]


def extract_point(point, startday, endday):
    """Extracts data for given point and variable names over the give date range

    :param point: the point for which to extract data
    :param startday: the start date
    :param endday: the end date
    :return: a dataframe with AgERA5 meteo variables
    """

    df_final = pd.DataFrame()
    for day in pd.date_range(startday, endday):
        fnames = [create_target_fname(v, day, config.data_storage.netcdf_path) for v in selected_variables]
        ds = xr.open_mfdataset(fnames)
        pnt_data = ds.sel(lon=point.longitude, lat=point.latitude, method="nearest")
        df = pnt_data.to_dataframe()
        ix = ~df.isna().any(axis=1)
        if not any(ix):
            print(f"No data for given lon/lat ({point.longitude:7.2f}/{point.latitude:7.2f}),"
                  f" probably over water...")
            if CMD_MODE:
                sys.exit()
            else:
                return None
        df_final = pd.concat([df_final, df[ix]])

    rename_cols = {c:c.lower() for c in df_final.columns}
    rename_cols.update({"time": "day"})
    df_final = (df_final.reset_index()
                        .drop(columns=["lat", "lon"])
                        .rename(columns=rename_cols)
                )
    # convert to simple date
    df_final['day'] = df_final.day.dt.date
    if "solar_radiation_flux" in df_final.columns:
        df_final["solar_radiation_flux"] = df_final.solar_radiation_flux.astype(int)

    if config.misc.kelvin_to_celsius:
        df_final = convert_to_celsius(df_final)

    return df_final
