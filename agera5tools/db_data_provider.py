# -*- coding: utf-8 -*-
# Copyright (c) December 2022, Wageningen Environmental Research
# Allard de Wit (allard.dewit@wur.nl)
import datetime as dt

from sqlalchemy import MetaData, Table, select, and_
import sqlalchemy as sa
from dotmap import DotMap
import pandas as pd

from . import config
from .util import Point, check_date, get_grid


def fetch_grid_agera5_properties(engine, idgrid):
    """Retrieves latitude, longitude, elevation from "grid" table and
    assigns them to self.latitude, self.longitude, self.elevation."""
    metadata = sa.MetaData(engine)
    tg = Table(config.database.grid_table_name, metadata, autoload=True)
    sc = select([tg.c.latitude, tg.c.longitude, tg.c.elevation],
                tg.c.idgrid == idgrid).execute()
    row = sc.fetchone()
    sc.close()
    if row is None:
        msg = "No land grid at this location or outside region definition!"
        raise RuntimeError(msg)

    latitude = float(row.latitude)
    longitude = float(row.longitude)
    elevation = float(row.elevation)

    return DotMap(latitude=latitude, longitude=longitude, elevation=elevation)


def fetch_agera5_weather_from_db(engine, idgrid, startdate, enddate):
    """Retrieves the meteo data from table "grid_weather".
    """
    metadata = sa.MetaData(engine)
    gw = Table(config.database.agera5_table_name, metadata, autoload=True)
    sel = select([gw], and_(gw.c.idgrid == idgrid,
                            gw.c.day >= startdate,
                            gw.c.day <= enddate))
    df = pd.read_sql(sel, engine)
    df.index = pd.to_datetime(df.day)

    return df


def get_agera5(latitude, longitude, startdate=None, enddate=None):
    # Check the start and end dates and assign when ok
    try:
        startdate = check_date(startdate)
    except ValueError:
        startdate = dt.date(config.temporal_range.start_year, 1, 1)
    try:
        enddate = check_date(enddate)
    except ValueError:
        enddate = dt.date(config.temporal_range.end_year, 12, 31)

    pnt = Point(longitude, latitude)
    if not config.region.boundingbox.point_in_bbox(pnt):
        msg = f'{pnt} not in boundingbox of region!'
        raise RuntimeError(msg)

    engine = sa.create_engine(config.database.dsn)
    print(f"Requesting data for lat {latitude:7.2f}, lon {longitude:7.2f}")
    idgrid_agera5 = get_grid(engine, pnt.longitude, pnt.latitude, config.misc.grid_search_radius)
    grid_agera5_properties = fetch_grid_agera5_properties(engine, idgrid_agera5)
    df_AgERA5 = fetch_agera5_weather_from_db(engine, idgrid_agera5, startdate, enddate)

    if len(df_AgERA5) == 0:
        raise RuntimeError("No AgERA5 data found for this location and/or date range")

    return_value = {
        "location_info": {
            "input_latitude": latitude,
            "input_longitude": longitude,
            "grid_agera5_latitude": grid_agera5_properties.latitude,
            "grid_agera5_longitude": grid_agera5_properties.longitude,
            "grid_agera5_elevation": grid_agera5_properties.elevation,
            "region_name": config.region.name,
        },
        "weather_variables": df_AgERA5.to_dict(orient="records"),
        "info": "data retrieval successful"
    }
    return return_value
