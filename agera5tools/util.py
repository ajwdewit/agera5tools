# -*- coding: utf-8 -*-
# Copyright (c) May 2021, Wageningen Environmental Research
# Allard de Wit (allard.dewit@wur.nl)
import logging
from pathlib import Path
import sys, os
import datetime as dt
import sqlite3
import calendar
from math import log10

import pandas as pd
from numpy import arccos, cos, radians, sin

import yaml
import xarray as xr
import click

CMD_MODE = True if os.environ["CMD_MODE"] == "1" else False

variable_names = {'Temperature_Air_2m_Mean_24h': dict(variable="2m_temperature", statistic ="24_hour_mean"),
                  'Temperature_Air_2m_Mean_Day_Time': dict(variable="2m_temperature", statistic ="day_time_mean"),
                  'Temperature_Air_2m_Mean_Night_Time': dict(variable="2m_temperature", statistic ="night_time_mean"),
                  'Dew_Point_Temperature_2m_Mean': dict(variable="2m_dewpoint_temperature", statistic ="24_hour_mean"),
                  'Temperature_Air_2m_Max_24h': dict(variable="2m_temperature", statistic ="24_hour_maximum"),
                  'Temperature_Air_2m_Min_24h': dict(variable="2m_temperature", statistic ="24_hour_minimum"),
                  'Temperature_Air_2m_Max_Day_Time': dict(variable="2m_temperature", statistic ="day_time_maximum"),
                  'Temperature_Air_2m_Min_Night_Time': dict(variable="2m_temperature", statistic ="night_time_minimum"),
                  'Cloud_Cover_Mean': dict(variable="cloud_cover", statistic ="24_hour_mean"),
                  'Snow_Thickness_LWE_Mean': dict(variable="snow_thickness_lwe", statistic ="24_hour_mean"),
                  'Snow_Thickness_Mean': dict(variable="snow_thickness", statistic ="24_hour_mean"),
                  'Vapour_Pressure_Mean': dict(variable="vapour_pressure", statistic ="24_hour_mean"),
                  'Precipitation_Flux': dict(variable="precipitation_flux"),
                  'Solar_Radiation_Flux': dict(variable="solar_radiation_flux"),
                  'Wind_Speed_10m_Mean': dict(variable="10m_wind_speed", statistic="24_hour_mean"),
                  'Relative_Humidity_2m_06h': dict(variable="2m_relative_humidity", time="06_00"),
                  'Relative_Humidity_2m_09h': dict(variable="2m_relative_humidity", time="09_00"),
                  'Relative_Humidity_2m_12h': dict(variable="2m_relative_humidity", time="12_00"),
                  'Relative_Humidity_2m_15h': dict(variable="2m_relative_humidity", time="15_00"),
                  'Relative_Humidity_2m_18h': dict(variable="2m_relative_humidity", time="18_00"),
                  'Precipitation_Rain_Duration_Fraction': dict(variable="solid_precipitation_duration_fraction"),
                  'Precipitation_Solid_Duration_Fraction': dict(variable="liquid_precipitation_duration_fraction")
                  }


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


def create_agera5_fnames(agera5_dir, var_names, day):
    """returns the list of 22 AgERA5 variable filenames.
    """
    fnames = []
    for var_name in var_names:
        fname = create_target_fname(var_name, day, agera5_dir)
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

    def get_cds_bbox(self):
        return [self.lat_max, self.lon_min, self.lat_min, self.lon_max]

    def point_in_bbox(self, pnt):
        r = (self.lon_min <= pnt.longitude <= self.lon_max) & \
            (self.lat_min <= pnt.latitude <= self.lat_max)
        return r

    def region_in_bbox(self, bbox):
        r = (self.lon_min <= bbox.lon_min <= self.lon_max) & \
            (self.lon_min <= bbox.lon_max <= self.lon_max) & \
            (self.lat_min <= bbox.lat_min <= self.lat_max) & \
            (self.lat_min <= bbox.lat_max <= self.lat_max)
        return r



class Point:
    """Defines a point with a given longitude/latitude

    :param longitude: Longitude of point
    :param latitude: Latitude of point
    """

    def __init__(self, longitude, latitude):
        try:
            assert -180 <= longitude <= 180, "Longitude not within -180:180"
            assert -90 <= latitude <= 90, "Latitude not within -90:90"
            self.latitude = latitude
            self.longitude = longitude
        except AssertionError as e:
            if CMD_MODE:
                print(e)
                sys.exit()
            else:
                raise

    def __str__(self):
        return f"longitude {self.longitude:6.2f} and/or latitude {self.latitude:5.2f}"


def convert_to_celsius(df):
    """Converts temperature columns from degrees K to C

    :param df: the AgERA5 dataframe
    :return: a DataFrame with con
    """
    for colname in df.columns:
        colname = colname.lower()
        if colname.startswith("temp") or colname.startswith("dew"):
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
        df.to_csv(sys.stdout, index=False, float_format="%7.2f")
    elif fname_output.suffix == ".csv":
        df.to_csv(fname_output, index=False, float_format="%7.2f")
        click.echo(f"Written CSV output to: {fname_output}")
    elif fname_output.suffix == ".json":
        df.to_json(fname_output, orient="records")
        click.echo(f"Written JSON output to: {fname_output}")
    elif fname_output.suffix == ".db3":
        with sqlite3.connect(fname_output) as dbconn:
            df.to_sql("agera5", dbconn, index=False, if_exists="append")
        click.echo(f"Written SQlite output to: {fname_output}")
    else:
        click.echo("Unrecognized output type, CSV (.csv), JSON (.json) and SQLite (.db3) are supported...")


def add_grid(ds):
    """Adds the AgERA5 grid definition to the dataset.
    """
    agera5_grid = Path(__file__).parent / "grid_elevation_landfraction.nc"
    ds_grid = xr.open_dataset(agera5_grid)

    ds["idgrid"] = ds_grid.idgrid_era5

    return ds


def days_in_month(year, month):

    if month in (1, 3, 5, 7, 8, 10, 12):
        return 31
    if month == 2:
        if calendar.isleap(year):
            return 29
        else:
            return 28
    return 30


def get_grid(engine, lon, lat, search_radius):
    sql = f""" 
    SELECT idgrid, longitude, latitude
    FROM grid_agera5
    WHERE latitude < {lat + search_radius} AND latitude > {lat - search_radius} AND 
        longitude < {lon + search_radius} AND longitude > {lon - search_radius} 
    """
    df = pd.read_sql_query(sql, engine)
    if len(df) > 0:
        tiny = 0.001
        df["dist"] = (6371 * arccos(cos(radians(lat + tiny)) * cos(radians(df.latitude.values)) *
                             cos(radians(df.longitude.values) - radians(lon + tiny)) +
                             sin(radians(lat + tiny)) * sin(radians(df.latitude.values))))
        return int(df.idgrid[df.dist.argmin()])
    else:
        return None


def last_day_in_month(year, month):
    """Returns the last day in the month
    :return: a date object containing the last day in the month
    """
    if month == 12:
        return dt.date(year, 12, 31)
    else:
        return dt.date(year, month+1, 1) - dt.timedelta(days=1)


def wind10to2(wind10):
    """Converts windspeed at 10m to windspeed at 2m using log. wind profile
    """
    wind2 = wind10 * (log10(2./0.033) / log10(10/0.033))
    return wind2


def json_date_serial(obj):
    """Serializer for date/datetime objects.
    """
    if isinstance(obj, (dt.date, dt.datetime)):
        return obj.isoformat()
    raise TypeError("Object '%s' not JSON serializable." % type(obj))



class BoundedFloat:
    """This represents a float value that lies between a min and max value.

    If now a ValueError is raised
    """

    def __init__(self, minvalue, maxvalue, msg):
        self.minlat = minvalue
        self.maxlat = maxvalue
        self.msg = msg

    def __call__(self, x):
        x = float(x)
        if not (self.minlat < x < self.maxlat):
            raise ValueError(self.msg)
        return x


def day_fmt(days):
    """Properly formats a list or set of days:
    yyyy-mm-dd, yyyy-mm-dd, ...

    """
    s = ""
    for d in days:
        s += f"{d.strftime('%Y-%m-%d')}, "
    if s:
        s = s[:-2]
    else:
        s = "N/A"

    return s


def chunker(seq, size):
    """Returns a generator that divides seq in chunks of given size.

    The last chunk can have less than size entities.

    :param seq: The sequence to be chunked
    :param size: The chunk size, should be > 0
    :return: a generator that chunks the sequence
    """
    return (seq[pos:pos + size] for pos in range(0, len(seq), size))
