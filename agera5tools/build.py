# -*- coding: utf-8 -*-
# Copyright (c) December 2022, Wageningen Environmental Research
# Allard de Wit (allard.dewit@wur.nl)

# This will be set to True only for commandline mode. Not when importing
# agera5tools in python.
import logging
import shutil
from uuid import uuid4
import datetime as dt
from zipfile import ZipFile
import concurrent.futures
import copy
import time
from pathlib import Path

import cdsapi
import sqlalchemy as sa
import xarray as xr

from .util import days_in_month, variable_names, create_target_fname, last_day_in_month, add_grid
from . import config


def parse_date_from_zipfname(zipfname):
    """Parse the date from the filename and returns a date object.
    """
    d = zipfname.filename.split("_")[3]
    d = dt.datetime.strptime(d, "%Y%m%d")
    return d.date()


def move_agera5_file(source_fname, target_fname):
    """Moves the file from source to target but includes building of directory structure if required

    :param source_fname: The (full) path to the source file
    :param target_fname: The (full) path to the target file
    """
    target_fname.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(source_fname, target_fname)


def unpack_cds_download(download_details):
    """Unpacks a downloaded file on the cds and moves the files to the right location

    :param download_details: the details for this download
    :return: a list of paths to downloaded files
    """
    nc_fnames_from_zip = []
    with ZipFile(download_details["download_fname"]) as myzip:
        for zipfname in myzip.infolist():
            myzip.extract(zipfname, config.data_storage.tmp_path)
            tmp_fname = config.data_storage.tmp_path / zipfname.filename
            day = parse_date_from_zipfname(zipfname)
            nc_fname = create_target_fname(download_details["varname"], day, config.data_storage.netcdf_path)
            move_agera5_file(tmp_fname, nc_fname)
            nc_fnames_from_zip.append(nc_fname)

    return nc_fnames_from_zip


def download_one_month(input):
    """Download one month of CDS data for given variable name, year and month

    :param input: a tuple of three elements consisting of
       - agera5_variable_name: the full name of the AgERA5 variable, as in YAML configuration
       - year: the year for the download
       - month: the month for the download
    :return: a dict with input variables and the path to the downloaded filename
    """
    agera5_variable_name, year, month = input
    ndays_in_month = days_in_month(year, month)
    cds_variable_details = copy.deepcopy(variable_names[agera5_variable_name])

    cds_query = {
            'format': 'zip',
            'variable': cds_variable_details.pop("variable"),
            'year': f'{year}',
            'month': f'{month:02}',
            'day': [f"{s+1:02}" for s in range(ndays_in_month)],
            'area': config.region.boundingbox.get_cds_bbox(),
        }
    cds_query.update(cds_variable_details)

    download_fname = config.data_storage.tmp_path / f"cds_download_{uuid4()}.zip"
    c = cdsapi.Client(quiet=True)
    c.retrieve('sis-agrometeorological-indicators', cds_query, download_fname)

    msg = f"Downloaded data for {agera5_variable_name} for {year}-{month:02} to {download_fname}."
    logger = logging.getLogger(__name__)
    logger.debug(msg)

    return dict(year=year, month=month, varname=agera5_variable_name, download_fname=download_fname)


def determine_build_range():
    """Determines the range of years/months to build the initial AgERA5 database based on the configuration

    :return: a list of [(year, month), ...]
    """
    latest_agera5_day = dt.date.today() - dt.timedelta(days=8)
    latest_config_day = dt.date(config.temporal_range.end_year, 12, 31)
    max_day = min(latest_agera5_day, latest_config_day)
    build_month_years = []
    for yr in range(config.temporal_range.start_year, 9999):
        for month in range(1, 13):
            last_day = last_day_in_month(yr, month)
            if last_day > max_day:
                break
            build_month_years.append((yr, month))

    return build_month_years


def convert_ncfiles_to_dataframe(nc_files):
    """reads the NetCDF files as multifile dataset and convert to dataframe

    This also includes adding the AgERA5 grid, renaming all columns to lower case,
    removing rows witn N/A values and dropping the lat/lon columns.

    :param nc_files:
    :return: a dataframe representation of the NetCDF files
    """
    ds = xr.open_mfdataset(nc_files)
    ds = add_grid(ds)
    df = ds.to_dataframe()

    rename_cols = {c:c.lower() for c in df.columns}
    rename_cols.update({"time": "day"})
    df = (df.reset_index()
            .drop(columns=["lat", "lon"])
            .rename(columns=rename_cols)
          )
    ix = df.isna().any(axis=1)
    df = df[~ix]
    return df


def df_to_database(df, year, month):
    """Insert dataframe rows into the database.

    :param df: a dataframe with AgERA5 data
    """
    engine = sa.create_engine(config.database.dsn)
    # t1 = time.time()
    try:
        with engine.begin() as DBconn:
            df.to_sql(config.database.agera5_table_name, DBconn, if_exists="append", index=False)
        # print(f"Inserting data took {time.time() - t1:5.1} seconds")
    except sa.exc.IntegrityError as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Failed inserting AgERA5 data for {year}-{month:02}: duplicate rows!")


def df_to_csv(df, year, month):
    """Write dataframe to a compressed CSV file

    :param df:  a dataframe with AgERA5 data
    :return: the name of the CSV file where data is written.
    """
    csv_fname = config.data_storage.csv_path / f"weather_grid_agera5_{year}_{month:02}.csv.gz"
    try:
        df.to_csv(csv_fname, header=True, index=False, date_format="%Y-%m-%d",
                      compression={'method': 'gzip', 'compresslevel': 5})
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.exception(f"Failed writing CSV file with AgERA5 data for {year}-{month:02}.")


def build(to_database=True, to_csv=False):
    """Builds the AgERA5tools database.

    This step is useful to initially populate the database with data because the build step downloads the data
    in monthly chunks with is much more efficient. When the build step is finished, the `mirror` command can be
    used to incrementally update the AgERA5 database.

    :param to_database: Flag indicating if results should be written to the database immediately
    :param to_csv: Flag indicating if a compressed CSV file should be written.
    """
    logger = logging.getLogger(__name__)
    build_month_years = determine_build_range()
    for year, month in build_month_years:
        logger.info(f"Starting AgERA5 download for {year}-{month:02}")
        to_download = []
        for varname, selected in config.variables.items():
            if selected:
                to_download.append((varname, year, month))
        logger.info(f"Starting concurrent CDS download of {len(to_download)} AgERA5 variables.")
        with concurrent.futures.ThreadPoolExecutor(max_workers=len(to_download)) as executor:
            downloaded_sets = executor.map(download_one_month, to_download)

        downloaded_ncfiles = []
        for dset in downloaded_sets:
            ncfiles = unpack_cds_download(dset)
            downloaded_ncfiles.extend(ncfiles)

        df = convert_ncfiles_to_dataframe(downloaded_ncfiles)
        if to_database:
            df_to_database(df, year, month)
        if to_csv:
            df_to_csv(df, year, month)

if __name__ == "__main__":
    build()