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

@click.group()
def cli():
    pass


@click.command("extract_point")
@click.argument("agera5_path",type=click.Path(exists=True))
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


cli.add_command(cmd_extract_point)
cli.add_command(cmd_dump)
cli.add_command(cmd_clip)
cli.add_command(cmd_dump_grid)


if __name__ == "__main__":
    cli()