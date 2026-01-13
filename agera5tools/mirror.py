# -*- coding: utf-8 -*-
# Copyright (c) December 2022, Wageningen Environmental Research
# Allard de Wit (allard.dewit@wur.nl)
import logging
from uuid import uuid4
import datetime as dt
import concurrent.futures
import copy
import time

import cdsapi
from tqdm import tqdm
import pandas as pd
import sqlalchemy as sa
from requests.exceptions import SSLError, HTTPError

from .util import variable_names, get_grid, create_target_fname
from .build import unpack_cds_download, convert_ncfiles_to_dataframe, df_to_csv, df_to_database
from . import config


def find_days_in_database():
    """Finds the available days in the AgERA5 database by querying the time-series on the
    point defined by `config.misc.reference_point`

    :return: A set of date objects present in the database
    """
    engine = sa.create_engine(config.database.dsn)
    with engine.connect() as DBconn:
        idgrid = get_grid(DBconn, config.misc.reference_point.lon, config.misc.reference_point.lat,
                          config.database.grid_table_name, config.misc.grid_search_radius)
        sql = sa.text(f"select day from {config.database.agera5_table_name} where idgrid={idgrid}")
        df = pd.read_sql_query(sql, DBconn)
    engine.dispose()
    dates = {d.day for d in df.itertuples()}
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
    version = str(config.misc.agera5_version).replace(".", "_")

    logger = logging.getLogger(__name__)

    cds_query = {
            'format': 'zip',
            'variable': cds_variable_details.pop("variable"),
            'year': f'{day.year}',
            'month': f'{day.month:02}',
            'day': [f"{day.day:02}"],
            'area': config.region.boundingbox.get_cds_bbox(),
            'version': f'{version}',
    }
    cds_query.update(cds_variable_details)

    download_fname = config.data_storage.tmp_path / f"cds_download_{uuid4()}.zip"
    done = False
    for ntry in range(config.cdsapi.max_tries):
        try:
            c = cdsapi.Client(quiet=True)
            c.retrieve('sis-agrometeorological-indicators', cds_query, download_fname)
            msg = f"Downloaded data for {agera5_variable_name} for {day} to {download_fname}."
            logger.debug(msg)
            done = True
            break
        except (SSLError, HTTPError) as e:
            msg = f"Download failed for {agera5_variable_name} for {day} at try {ntry}. Retrying after 5 minutes."
            logger.warning(msg)
            time.sleep(300)
        except Exception as e:
            logger.exception(f"Failed downloading {agera5_variable_name} - {day}")
            break
    else:
        msg = f"Download failed for {agera5_variable_name} for {day} after {config.cdsapi.max_tries} retries."
        logger.error(msg)

    return dict(day=day, varname=agera5_variable_name, download_fname=download_fname, success=done)


def download_missing_days(days, selected_variables):
    """Download AgERA5 for given days and selected variables

    :param days: a list of days
    :param selected_variables: a list of selected AgERA5 variable names
    :return: a tuple with the available NetCDF filenames and the days that failed to download
    """

    logger = logging.getLogger(__name__)
    for day in tqdm(sorted(days), desc="Downloading data"):
        logger.info(f"Starting AgERA5 download for {day}")
        to_download = []
        for varname in selected_variables:
            nc_fname = create_target_fname(varname, day,
                                           agera5_dir=config.data_storage.netcdf_path,
                                           version=config.misc.agera5_version)
            if not nc_fname.exists():
                to_download.append((varname, day))

        if not to_download:
            # there is nothing to download for this day, all files exist
            # this is mainly to ensure that the tqdm progress bar gets updated.
            continue

        logger.info(f"Starting concurrent CDS download of {len(to_download)} AgERA5 variables.")
        with concurrent.futures.ThreadPoolExecutor(max_workers=config.cdsapi.concurrent_downloads) as executor:
            downloaded_sets = executor.map(download_one_day, to_download)

        downloaded_ncfiles = []
        for dset in downloaded_sets:
            if dset["success"] is False:
                continue
            ncfiles = unpack_cds_download(dset)
            downloaded_ncfiles.extend(ncfiles)

    # Finally collect all available ncfiles for all days
    available_ncfiles_for_day = {}
    for day in sorted(days):
        available_ncfiles = []
        for varname in selected_variables:
            nc_fname = create_target_fname(varname, day,
                                           agera5_dir=config.data_storage.netcdf_path,
                                           version=config.misc.agera5_version)
            if not nc_fname.exists():
                available_ncfiles = None
                break
            else:
                available_ncfiles.append(nc_fname)
        if available_ncfiles:
            available_ncfiles_for_day[day] = available_ncfiles

    days_failed = set(days) - set(available_ncfiles_for_day.keys())

    return available_ncfiles_for_day, days_failed


def mirror(to_csv=True, dry_run=False):
    """mirrors the AgERA5tools database.

    This procedure will mirror the AgERA5 data at the Copernicus Climate Datastore. It will
    incrementally update the local database by downloading files for each day. Note that this
    procedure should be run daily to update the local database with the remote AgERA5 data at
    the CDS.

    :param to_csv: Flag indicating if a compressed CSV file should be written.
    """
    logger = logging.getLogger(__name__)
    selected_variables = [varname for varname, selected in config.variables.items() if selected]
    days = find_days_to_update()
    if days:
        logger.info(f"Found following days for updating AgERA5: {days}")
    else:
        logger.info(f"Found no days for updating AgERA5")
        return days, set(), set()

    if dry_run:  # Do not actually start processing
        return days, set(), set()

    available_ncfiles_for_day, days_failed_to_download = download_missing_days(days, selected_variables)

    days_failed_to_insert = set()
    for day, ncfiles in tqdm(available_ncfiles_for_day.items(),  desc="Inserting data"):

        df = convert_ncfiles_to_dataframe(ncfiles)

        success = df_to_database(df, descriptor=day)
        if not success:
            days_failed_to_insert.add(day)

        if to_csv:
            csv_fname = config.data_storage.csv_path / f"weather_grid_agera5_{day}.csv.gz"
            df_to_csv(df, csv_fname)

        # Delete NetCDF files if required
        if config.data_storage.keep_netcdf is False:
            [f.unlink() for f in available_ncfiles_for_day]

    return days, days_failed_to_download, days_failed_to_insert


if __name__ == "__main__":
    mirror()
