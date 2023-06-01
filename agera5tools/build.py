# -*- coding: utf-8 -*-
# Copyright (c) December 2022, Wageningen Environmental Research
# Allard de Wit (allard.dewit@wur.nl)
import logging
import shutil
import time
from uuid import uuid4
import datetime as dt
from zipfile import ZipFile
import concurrent.futures
import copy
from itertools import product

import cdsapi
import xarray as xr
import sqlalchemy as sa

from .util import days_in_month, variable_names, create_target_fname, last_day_in_month, \
    add_grid, convert_to_celsius, chunker
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
    zip_fname = download_details["download_fname"]
    if zip_fname is None:
        return []

    with ZipFile(zip_fname) as myzip:
        for zipfname in myzip.infolist():
            myzip.extract(zipfname, config.data_storage.tmp_path)
            tmp_fname = config.data_storage.tmp_path / zipfname.filename
            day = parse_date_from_zipfname(zipfname)
            nc_fname = create_target_fname(download_details["varname"], day, config.data_storage.netcdf_path)
            move_agera5_file(tmp_fname, nc_fname)
            nc_fnames_from_zip.append(nc_fname)

    # Delete tmp download zip file
    zip_fname.unlink()

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


def modify_dataframe(df):
    """Modifies the dataframe to have it properly formatted. Such as:
     - Renaming columns and forcing them into lower case
     - Make the 'day' column a proper date object
     - reset the index and remove lat/lon columns
     - removing rows with N/A values
     - removing rows with idgrid == -999
     - convert Kelvin to Celsius if configured so.

    :param df: a dataframe with AgERA5 data
    :return: a modified dataframe
    """
    # Rename columns
    rename_cols = {c:c.lower() for c in df.columns}
    rename_cols.update({"time": "day"})
    df = (df.reset_index()
            .rename(columns=rename_cols)
          )
    # Drop lat/lon columns if an idgrid column is present
    # otherwise, add 0.05 to move coordinates to grid centre
    if "idgrid" in df.columns:
        df = df.drop(columns=["lat", "lon"])
    else:
        df["lat"] += 0.05
        df["lon"] += 0.05

    # Convert day to a proper date object
    df["day"] = df["day"].dt.date

    # Remove any rows with N/A values
    ix = df.isna().any(axis=1)
    df = df[~ix]

    # Remove rows with idgrid == -999
    # this represents grids at the lowest row
    ix = df.idgrid == -999
    df = df[~ix]

    # Convert Kelvin to Celsius if configured
    if config.misc.kelvin_to_celsius:
        df = convert_to_celsius(df)

    # Solar radiation flux can be integer for more compact output
    if "solar_radiation_flux" in df.columns:
        df["solar_radiation_flux"] = df.solar_radiation_flux.astype(int)

    return df


def convert_ncfiles_to_dataframe(nc_files):
    """reads the NetCDF files as multifile dataset, add a grid ID layer and convert it to dataframe

    :param nc_files: a list of NetCDF file to treat as one meta file
    :return: a dataframe representation of the NetCDF files
    """
    ds = xr.open_mfdataset(nc_files)
    ds = add_grid(ds)
    df = ds.to_dataframe()
    df = modify_dataframe(df)
    return df


def df_to_database(df, descriptor):
    """Insert dataframe rows into the database.

    :param df: a dataframe with AgERA5 data
    :param descriptor: a descriptor for this set of data, usually year-month ("2000-01") or a date ("2000-01-01")
    """
    logger = logging.getLogger(__name__)
    engine = sa.create_engine(config.database.dsn)
    meta = sa.MetaData(engine)
    tbl = sa.Table(config.database.agera5_table_name, meta, autoload=True)
    try:
        recs = df.to_dict(orient="records")
        nrecs_written = 0
        t1 = time.time()
        with engine.begin() as DBconn:
            ins = tbl.insert()
            for chunk in chunker(recs, config.database.chunk_size):
                DBconn.execute(ins, chunk)
                nrecs_written += len(chunk)
                msg = f"Written {nrecs_written} from total {len(recs)} records to database."
                logger.info(msg)
        msg = f"Written AgERA5 data for {descriptor} to database in {time.time() - t1} seconds."
        logger.info(msg)
    except sa.exc.IntegrityError as e:
        logger.error(f"Failed inserting AgERA5 data for {descriptor}: duplicate rows!")


def df_to_csv(df, descriptor):
    """Write dataframe to a compressed CSV file

    :param df:  a dataframe with AgERA5 data
    :param descriptor: a descriptor for this set of data, usually year-month ("2000-01") or a date ("2000-01-01")
    :return: the name of the CSV file where data is written.
    """
    logger = logging.getLogger(__name__)
    csv_fname = config.data_storage.csv_path / f"weather_grid_agera5_{descriptor}.csv.gz"
    try:
        df.to_csv(csv_fname, header=True, index=False, date_format="%Y-%m-%d",
                      compression={'method': 'gzip', 'compresslevel': 5})
        logger.info(f"Written output for {descriptor} to CSV: {csv_fname}")
    except Exception as e:
        logger.exception(f"Failed writing CSV file with AgERA5 data for {descriptor}).")

    return csv_fname


def nc_files_available(varname, year, month):
    """This checks the available NetCDF file on the disk cache. If all files are already available, return True
    else False.

    :param varname: the AgERA5 variable name
    :param year: the year
    :param month: the month
    :return: True|False
    """
    ndays = days_in_month(year, month)
    days = [dt.date(year, month, d+1) for d in range(ndays)]
    nc_fnames = [create_target_fname(varname, day, config.data_storage.netcdf_path) for day in days]
    files_exist = [f.exists() for f in nc_fnames]
    return all(files_exist)


def get_nc_filenames(varnames, year, month, check=True):
    """Constructs the complete set of AgERA5 NetCDF filenames for given variables names, month and year.

    :param varnames: The list of AgERA5 variables names
    :param year: the year
    :param month: the month
    :param check: check if all files actually exist
    :return: A list of full paths to the NetCDF files
    """
    logger = logging.getLogger(__name__)
    ndays = days_in_month(year, month)
    days = [dt.date(year, month, d+1) for d in range(ndays)]
    nc_fnames = []
    for varname, day in product(varnames, days):
        fname = create_target_fname(varname, day, config.data_storage.netcdf_path)
        nc_fnames.append(fname)

    if check:
        missing = [f for f in nc_fnames if not f.exists()]
        if missing:
            for f in missing:
                logger.error(f"AgERA5 file is missing: {f}")
            msg =f"Cannot continue, {len(missing)} AgERA5 files are missing, see log for details"
            logger.error(msg)
            raise RuntimeError(msg)

    return nc_fnames

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
    selected_variables = [varname for varname, selected in config.variables.items() if selected]

    for year, month in build_month_years:
        logger.info(f"Starting AgERA5 download for {year}-{month:02}")
        potential_downloads = [(v, year, month) for v in selected_variables]
        actual_downloads = [inp for inp in potential_downloads if not nc_files_available(*inp)]
        if actual_downloads:
            logger.info(f"Starting concurrent CDS download of {len(actual_downloads)} AgERA5 variables.")
            with concurrent.futures.ThreadPoolExecutor(max_workers=len(actual_downloads)) as executor:
                downloaded_sets = executor.map(download_one_month, actual_downloads)

            downloaded_ncfiles = []
            for dset in downloaded_sets:
                ncfiles = unpack_cds_download(dset)
                downloaded_ncfiles.extend(ncfiles)
        else:
            logger.info(f"Skipping download, NetCDF files already exist.")

    for year, month in build_month_years:
        nc_files = get_nc_filenames(selected_variables, year, month)
        df = convert_ncfiles_to_dataframe(nc_files)
        if to_database:
            df_to_database(df, descriptor=f"{year}-{month:02}")
        if to_csv:
            df_to_csv(df, descriptor=f"{year}-{month:02}")

        # Delete NetCDF files if required
        if config.data_storage.keep_netcdf is False:
            [f.unlink() for f in nc_files]



if __name__ == "__main__":
    build()