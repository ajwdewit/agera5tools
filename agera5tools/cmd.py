# -*- coding: utf-8 -*-
# Copyright (c) May 2021, Wageningen Environmental Research
# Allard de Wit (allard.dewit@wur.nl)
import os, sys
from pathlib import Path
import click

# flags commandline mode
os.environ["CMD_MODE"] = "1"

from .util import BoundingBox, check_date, check_date_range, write_dataframe, Point
from .extract_point import extract_point
from .dump_clip import dump, clip
from .dump_grid import dump_grid
from .init import init
from .build import build
from .mirror import mirror
from .check import check
from . import config

selected_variables = [varname for varname, selected in config.variables.items() if selected]

@click.group()
def cli():
    pass


@click.command("extract_point")
@click.argument("longitude",type=click.FLOAT)
@click.argument("latitude",type=click.FLOAT)
@click.argument("startdate")
@click.argument("enddate")
@click.option("-o", "--output", type=click.Path(),
              help=("output file to write to: .csv, .json and .db3 (SQLite) are supported."
                    "Giving no output will write to stdout in CSV format"))
@click.option("--tocelsius", help="Convert temperature values from degrees Kelvin to Celsius",
              is_flag=True)
def cmd_extract_point(agera5_path, longitude, latitude, startdate, enddate, output=None, tocelsius=False):
    """Extracts AgERA5 data for given location and date range.

    \b
    AGERA5_PATH: path to the AgERA5 dataset
    LONGITUDE: the longitude for which to extract [dd, -180:180]
    LATITUDE: the latitude for which to extract [dd, -90:90]
    STARTDATE: the start date (yyyy-mm-dd, >=1979-01-01)
    ENDDATE: the last date (yyyy-mm-dd, <= 1 week ago)
    """
    point = Point(longitude, latitude)
    startdate, enddate = check_date_range(startdate, enddate)
    df = extract_point(agera5_path, point, startdate, enddate, tocelsius)
    if output is not None:
        output = Path(output)
    write_dataframe(df, output)


@click.command("dump")
@click.argument("agera5_path",type=click.Path(exists=True))
@click.argument("day")
@click.option("-o", "--output", type=click.Path(),
              help=("output file to write to: .csv, .json and .db3 (SQLite) are supported. "
                    "Giving no output will write to stdout in CSV format"))
@click.option("--tocelsius", help="Convert temperature values from degrees Kelvin to Celsius",
              is_flag=True)
@click.option("--add_gridid", help="Adds a grid ID instead of latitude/longitude columns.",
              is_flag=True)
@click.option('--bbox', nargs=4, type=float,
              help=("Bounding box: <lon_min> <lon_max> <lat_min< <lat max>"))
def cmd_dump(agera5_path, day, output=None, bbox=None, tocelsius=False, add_gridid=False):
    """Dump AgERA5 data for a given day to CSV, JSON or SQLite

    \b
    AGERA5_PATH: Path to the AgERA5 dataset
    DAY: specifies the day to be dumped (yyyy-mm-dd)
    """
    day = check_date(day)
    output = Path(output) if output is not None else None
    bbox = BoundingBox() if bbox is None else BoundingBox(*bbox)
    df = dump(agera5_path, day, bbox, tocelsius, add_gridid)
    if output is not None:
        output = Path(output)
    write_dataframe(df, output)


@click.command("clip")
@click.argument("agera5_path", type=click.Path(exists=True))
@click.argument("day")
@click.option("--base_fname", help="Base file name to use, otherwise will use 'agera5_clipped'",
              default="agera5_clipped")
@click.option("-o", "--output_dir", type=click.Path(exists=True),
              help=("Directory to write output to. If not provided, will use current directory."))
@click.option('--bbox', nargs=4, type=float,
              help=("Bounding box: <lon_min> <lon_max> <lat_min< <lat max>"))
def cmd_clip(agera5_path, day, output_dir=None, bbox=None, base_fname="agera5_clipped"):
    """Extracts a portion of agERA5 for the given bounding box and saves all
    22 variables to a single NetCDF.

    \b
    AGERA5_PATH: Path to the AgERA5 dataset
    DAY: specifies the day to be clipped (yyyy-mm-dd)
    """
    day = check_date(day)
    output_dir = Path.cwd() if output_dir is None else Path(output_dir)
    bbox = BoundingBox() if bbox is None else BoundingBox(*bbox)
    ds_clip = clip(agera5_path, day, bbox)
    fname_output = output_dir / f"{base_fname}_{day}.nc"
    ds_clip.to_netcdf(fname_output)


@click.command("dump_grid")
@click.option("-o", "--output", type=click.Path(),
              help=("output file to write to: .csv, .json and .db3 (SQLite) are supported."
                    "Giving no output will write to stdout in CSV format"))
def cmd_dump_grid(output=None):
    """Dump the agERA5 grid to a CSV, JSON or SQLite DB.
    """
    df = dump_grid()
    if output is not None:
        output = Path(output)
    write_dataframe(df, output)


@click.command("init")
def cmd_init():
    """Initializes AgERA5tools
    """
    try:
        init()
        print(f"AgERA5tools successfully initialized!.")
    except RuntimeError as e:
        print(f"AgERA5tools failed to initialize: {e}")
    except KeyboardInterrupt:
        print("Exiting...")


@click.command("build")
@click.option("-d", "--to_database", is_flag=True, flag_value=True,
              help="Load AgERA5 data into the database")
@click.option("-c", "--to_csv", is_flag=True, flag_value=True,
              help="Write AgERA5 data to compressed CSV files.")
def cmd_build(to_database, to_csv):
    """Builds the AgERA5 database by bulk download from CDS
    """
    print(f"db: {to_database}")
    print(f"csv: {to_csv}")
    if to_csv is False and to_database is False:
        msg = ("Warning: Only NetCDF files will be updated, no tabular output will be written, "
               "use either --to_database or --to_csv")
        click.echo(msg)

    build(to_database, to_csv)
    msg = "Done building database, use the `mirror` command to keep the DB up to date"
    click.echo(msg)


@click.command("mirror")
@click.option("-c", "--to_csv", is_flag=True,
              help="Write AgERA5 data to compressed CSV files.")
def cmd_mirror(to_database=False, to_csv=False):
    """Incrementally updates the AgERA5 database by daily downloads from the CDS
    """
    days = mirror(to_database, to_csv)
    if not days:
        click.echo("Found no days to update the AgERA5 database for")
    else:
        click.echo(f"Updated the AgERA5 database with the following days: {days}")


@click.command("check")
def cmd_check():
    """Checks the completeness of NetCDF files from which the database is built
    """
    missing = check()
    if not missing:
        click.echo(f"Found no missing NetCDF files under {config.data_storage.netcdf_path}")
    else:
        click.echo(f"Found {len(missing)} missing NetCDF files under {config.data_storage.netcdf_path}:")
        for f in missing:
            click.echo(f" - {f}")


cli.add_command(cmd_extract_point)
cli.add_command(cmd_dump)
cli.add_command(cmd_clip)
cli.add_command(cmd_dump_grid)
cli.add_command(cmd_init)
cli.add_command(cmd_build)
cli.add_command(cmd_mirror)
cli.add_command(cmd_check)

if __name__ == "__main__":
    cli()