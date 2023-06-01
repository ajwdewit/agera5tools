# -*- coding: utf-8 -*-
# Copyright (c) December 2022, Wageningen Environmental Research
# Allard de Wit (allard.dewit@wur.nl)
import logging
from uuid import uuid4
import datetime as dt
import concurrent.futures
import copy

import cdsapi
import sqlalchemy as sa

from .util import variable_names, get_grid
from .build import unpack_cds_download, convert_ncfiles_to_dataframe, df_to_csv, df_to_database
from . import config

selected_variables = [varname for varname, selected in config.variables.items() if selected]


def find_days_in_database():
    """Finds the available days in the AgERA5 database by querying the time-series on the
    point defined by `config.misc.reference_point`

    :return: A set of date objects present in the database
    """
    engine = sa.create_engine(config.database.dsn)
    meta = sa.MetaData(engine)
    idgrid = get_grid(engine, config.misc.reference_point.lon, config.misc.reference_point.lat,
                      config.misc.grid_search_radius)
    tbl = sa.Table(config.database.agera5_table_name, meta, autoload=True)
    s = sa.select([tbl.c.day]).where(tbl.c.idgrid==idgrid)
    rows = s.execute().fetchall()
    dates = {d for d, in rows}
    return dates


def find_days_potential():
    """Determine dates which should potentially be available based on latest AgERA5 day
    and the configuration settings

    :return: a set of date objects that should potentially be available.
    """
    latest_agera5_day = dt.date.today() - dt.timedelta(days=8)
    latest_config_day = dt.date(config.temporal_range.end_year, 12, 31)
    max_day = min(latest_agera5_day, latest_config_day)
    earliest_config_day = dt.date(config.temporal_range.start_year, 1, 1)
    ndays = (max_day - earliest_config_day).days + 1
    return {earliest_config_day + dt.timedelta(days=i) for i in range(ndays)}


def find_days_to_update():
    """This function finds the days missing in the database and returns them.

    :return: a set of date objects of days missing in the database
    """
    days_in_db = find_days_in_database()
    days_potential = find_days_potential()
    return days_potential.difference(days_in_db)


def download_one_day(input):
    """Download one month of CDS data for given variable name, year and month

    :param input: a tuple of three elements consisting of
       - agera5_variable_name: the full name of the AgERA5 variable, as in YAML configuration
       - date: the day for the download
    :return: a dict with input variables and the path to the downloaded filename
    """
    agera5_variable_name, day = input
    cds_variable_details = copy.deepcopy(variable_names[agera5_variable_name])

    cds_query = {
            'format': 'zip',
            'variable': cds_variable_details.pop("variable"),
            'year': f'{day.year}',
            'month': f'{day.month:02}',
            'day': [f"{day.day:02}"],
            'area': config.region.boundingbox.get_cds_bbox(),
        }
    cds_query.update(cds_variable_details)

    download_fname = config.data_storage.tmp_path / f"cds_download_{uuid4()}.zip"
    c = cdsapi.Client(quiet=True)
    logger = logging.getLogger(__name__)
    try:
        c.retrieve('sis-agrometeorological-indicators', cds_query, download_fname)
        msg = f"Downloaded data for {agera5_variable_name} for {day} to {download_fname}."
        logger.debug(msg)
    except Exception as e:
        logger.exception(f"Failed downloading {agera5_variable_name} - {day}")
        download_fname = None

    return dict(day=day, varname=agera5_variable_name, download_fname=download_fname)


def mirror(to_csv=True):
    """mirrors the AgERA5tools database.

    This procedure will mirror the AgERA5 data at the Copernicus Climate Datastore. It will
    incrementally update the local database by downloading files for each day. Note that this
    procedure should be run daily to update the local database with the remote AgERA5 data at
    the CDS.

    :param to_csv: Flag indicating if a compressed CSV file should be written.
    """
    logger = logging.getLogger(__name__)
    days = find_days_to_update()
    if days:
        logger.info(f"Found following days for updating AgERA5: {days}")
    else:
        logger.info(f"Found no days for updating AgERA5")
    days_failed = set()
    for day in sorted(days):
        logger.info(f"Starting AgERA5 download for {day}")
        to_download = []
        for varname in selected_variables:
            to_download.append((varname, day))

        logger.info(f"Starting concurrent CDS download of {len(to_download)} AgERA5 variables.")
        with concurrent.futures.ThreadPoolExecutor(max_workers=len(to_download)) as executor:
            downloaded_sets = executor.map(download_one_day, to_download)

        downloaded_ncfiles = []
        for dset in downloaded_sets:
            ncfiles = unpack_cds_download(dset)
            downloaded_ncfiles.extend(ncfiles)

        if len(downloaded_ncfiles) != len(selected_variables):
            days_failed.add(day)
            continue

        df = convert_ncfiles_to_dataframe(downloaded_ncfiles)
        df_to_database(df, descriptor=day)
        if to_csv:
            df_to_csv(df, descriptor=day)

        # Delete NetCDF files if required
        if config.data_storage.keep_netcdf is False:
            [f.unlink() for f in downloaded_ncfiles]

    return days, days_failed

if __name__ == "__main__":
    mirror()