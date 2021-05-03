# -*- coding: utf-8 -*-
# Copyright (c) May 2021, Wageningen Environmental Research
# Allard de Wit (allard.dewit@wur.nl)
from pathlib import Path
import sys, os
import datetime as dt
import sqlite3

import xarray as xr
import click

CMD_MODE = True if os.environ["CMD_MODE"] == "1" else False

variable_names = ['Temperature_Air_2m_Mean_24h',
                  'Temperature_Air_2m_Mean_Day_Time',
                  'Temperature_Air_2m_Mean_Night_Time',
                  'Dew_Point_Temperature_2m_Mean',
                  'Temperature_Air_2m_Max_24h',
                  'Temperature_Air_2m_Min_24h',
                  'Temperature_Air_2m_Max_Day_Time',
                  'Temperature_Air_2m_Min_Night_Time',
                  'Cloud_Cover_Mean',
                  'Snow_Thickness_LWE_Mean',
                  'Snow_Thickness_Mean',
                  'Vapour_Pressure_Mean',
                  'Precipitation_Flux',
                  'Solar_Radiation_Flux',
                  'Wind_Speed_10m_Mean',
                  'Relative_Humidity_2m_06h',
                  'Relative_Humidity_2m_09h',
                  'Relative_Humidity_2m_12h',
                  'Relative_Humidity_2m_15h',
                  'Relative_Humidity_2m_18h',
                  'Precipitation_Rain_Duration_Fraction',
                  'Precipitation_Solid_Duration_Fraction']


def create_target_fname(meteo_variable_full_name, day, agera5_dir, stat="final", v="1.0"):
    """Creates the AgERA5 variable filename for given variable and day

    :param meteo_variable_full_name: the full name of the meteo variable
    :param day: the date of the file
    :param agera5_dir: the path to the AgERA5 dataset
    :return: the full path to the target filename
    """
    name_with_dashes = meteo_variable_full_name.replace("_", "-")
    sday = day.strftime("%Y%m%d")
    nc_fname = f"{name_with_dashes}_C3S-glob-agric_AgERA5_{sday}_{stat}-v{v}.nc"
    nc_fname = Path(agera5_dir) / str(day.year) / name_with_dashes / nc_fname
    return nc_fname


def create_agera5_fnames(agera5_dir, day):
    """returns the list of 22 AgERA5 variable filenames.
    """
    fnames = []
    for varname in variable_names:
        fname = create_target_fname(varname, day, agera5_dir)
        if not fname.exists():
            msg = f"Cannot find file: {fname}"
            if CMD_MODE:
                print(msg)
                sys.exit()
            else:
                raise RuntimeError(msg)
        fnames.append(fname)

    return fnames


class BoundingBox:
    """Defines and checks a lat/lon boundingbox
    """

    def __init__(self, lon_min=-180, lon_max=180, lat_min=-90, lat_max=90):
        try:
            assert -180 <= lon_min <= 180, "Long_min not in -180:180 longitude range."
            assert -180 <= lon_max <= 180, "Long_max not in -180:180 longitude range."
            assert -90 <= lat_min <= 90, "Lat_min not in -90:90 latitude range."
            assert -90 <= lat_max <= 90, "Lat_max not in -90:90 latitude range."
            assert lon_max > lon_min, "Long_min smaller than Long_max."
            assert lat_max > lat_min, "Lat_min smaller than Lat_max."
            assert (lon_max - lon_min) > 0.5, "Long_min and Long_max too close, should be > 0.5 dd"
            assert (lon_max - lon_min) > 0.5, "Long_min and Long_max too close, should be > 0.5 dd"
        except AssertionError as e:
            if CMD_MODE:
                print(e)
                sys.exit()
            else:
                raise

        self.lon_min = lon_min
        self.lon_max = lon_max
        self.lat_min = lat_min
        self.lat_max = lat_max


class Point:
    """Defines a point with a given longitude/latitude

    :param lon: Longitude of point
    :param lat: Latitude of point
    """

    def __init__(self, lon, lat):
        if not -180 <= lon <= 180:
            click.echo("Longitude not within -180:180")
            sys.exit()
        if not -90 <= lat <= 90:
            click.echo("Latitude not within -90:90")
            sys.exit()
        self.latitude = lat
        self.longitude = lon


def convert_to_celsius(df):
    """Converts temperature columns from degrees K to C

    :param df: the AgERA5 dataframe
    :return: a DataFrame with con
    """
    for colname in df.columns:
        if colname.startswith("Temp") or colname.startswith("Dew"):
            df[colname] -= 273.15
    return df


def check_date_range(start_date, end_date):
    """Converts date strings into dates and does some other checks"""
    try:
        start_date = dt.datetime.strptime(start_date, "%Y-%m-%d").date()
        end_date = dt.datetime.strptime(end_date, "%Y-%m-%d").date()
        assert end_date >= start_date, "Error: end date before start date!"
        assert start_date >= dt.date(1979,1,1), "Error: start date before 1979-01-01!"
    except(ValueError, AssertionError) as e:
        if CMD_MODE:
            print(e)
            sys.exit()
        else:
            raise

    return start_date, end_date


def check_date(day):
    """Converts date strings into dates and does some other checks"""
    try:
        d = dt.datetime.strptime(day, "%Y-%m-%d").date()
        assert d >= dt.date(1979,1,1), "Error: day before 1979-01-01!"
    except(ValueError, AssertionError) as e:
        if CMD_MODE:
            print(e)
            sys.exit()
        else:
            raise

    return d


def write_dataframe(df, fname_output=None):
    """Writes a dataframe to an output.

    Support types for fname_output are:
     - None: sends to stdout
     - <file>.csv: exports to CSV
     - <file>.json: exports to JSON
     - <file>.db3: export to SQLite

    :param df: the input dataframe
    :param fname_output: the output filename or None
    """
    if fname_output is None:
        df.to_csv(sys.stdout, index=False, float_format="%7.3f")
    elif fname_output.suffix == ".csv":
        df.to_csv(fname_output, index=False, float_format="%7.3f")
    elif fname_output.suffix == ".json":
        df.to_json(fname_output, index=False, orient="records")
    elif fname_output.suffix == ".db3":
        with sqlite3.connect(fname_output) as dbconn:
            df.to_sql("agera5", dbconn, index=False, if_exists="append")
    else:
        click.echo("Unrecognized output type, CSV (.csv), JSON (.json) and SQLite (.db3) are supported...")


def add_grid(ds):
    """Adds the AgERA5 grid definition to the dataset.
    """
    agera5_grid = Path(__file__).parent / "grid_elevation_landfraction.nc"
    ds_grid = xr.open_dataset(agera5_grid)

    ds["grid_agera5"] = ds_grid.idgrid_era5

    return ds


