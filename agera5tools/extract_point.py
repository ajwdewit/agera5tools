# -*- coding: utf-8 -*-
# Copyright (c) May 2021, Wageningen Environmental Research
# Allard de Wit (allard.dewit@wur.nl)
import sys, os
import xarray as xr
import pandas as pd

CMD_MODE = True if os.environ["CMD_MODE"] == "1" else False
from .util import create_agera5_fnames, convert_to_celsius


def extract_point(agera5_dir, point, startday, endday, tocelsius=False):

    df_final = pd.DataFrame()
    for day in pd.date_range(startday, endday):
        fnames = create_agera5_fnames(agera5_dir, day)
        ds = xr.open_mfdataset(fnames)
        pnt = ds.sel(lon=point.longitude, lat=point.latitude, method="nearest")
        df = pnt.to_dataframe()
        df.reset_index(inplace=True)
        ix = df.Wind_Speed_10m_Mean.notnull()
        if not any(ix):
            print(f"No data for given lon/lat ({point.longitude:7.2f}/{point.latitude:7.2f}),"
                  f" probably over water...")
            if CMD_MODE:
                sys.exit()
            else:
                return None
        df_final = df_final.append(df[ix])

    # convert to simple date
    df_final['time'] = pd.to_datetime(df_final.time).dt.date
    df_final["Solar_Radiation_Flux"] = df_final.Solar_Radiation_Flux.astype(int)

    if tocelsius:
        df_final = convert_to_celsius(df_final)

    return df_final
