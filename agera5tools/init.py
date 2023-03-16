# -*- coding: utf-8 -*-
# Copyright (c) December 2022, Wageningen Environmental Research
# Allard de Wit (allard.dewit@wur.nl)
"""Initializes AgERA5tools and sets up various properties:
- Access to the ECMWF CDS through cdsapi
- Location for AgERA5 NetCD files
- Location for AgERA5 relational database
- The selection of meteo variables to download
- The geographic window to download
- The start year to begin downloading AgERA5
"""
import sys, os
from pathlib import Path
import shutil

import click
import sqlalchemy as sa

from . import config
from .dump_grid import dump_grid


def set_CDSAPI_credentials():
    """Sets the credentials for the Copernicus Climate Data Store.
    """
    home = Path.home()
    cdsapirc = home / ".cdsapirc"
    if not cdsapirc.exists():
        credentials = (f"url: {config.cdsapi.url}\n"
                       f"key: {config.cdsapi.uid}:{config.cdsapi.key}\n"
                       "verify: 1\n")
        with open(cdsapirc, "w") as fp:
            fp.write(credentials)
        click.echo(f"Succesfully created .cdsapirc file at {cdsapirc}")
    else:
        click.echo(f"The .cdsapirc file already exists at {cdsapirc}")


def create_AgERA5_config():
    """Create a config file for AgERA5tools in the current folder.
    """
    if "AGERA5TOOLS_CONFIG" in os.environ:
        # Config already defined, we do not need a new one
        return

    template_agera5t_config = Path(__file__).parent / "agera5tools.yaml"
    agera5_conf = Path.cwd() / "agera5tools.yaml"
    if agera5_conf.exists():
        r = click.confirm(f"the file '{agera5_conf}' already exists, overwrite?")
        if r is False:
            return

    shutil.copy(template_agera5t_config, agera5_conf)
    click.echo(f"Successfully created agera5tools config file at: {agera5_conf}")


def fill_grid_table():
    """Fill the grid table in the agera5 database.
    """
    df = dump_grid()
    # Subset grid to only contain relevant region
    ix = ((df.latitude >= config.region.boundingbox.lat_min) &
          (df.latitude <= config.region.boundingbox.lat_max) &
          (df.longitude >= config.region.boundingbox.lon_min) &
          (df.longitude <= config.region.boundingbox.lon_max))
    df = df[ix]
    df = (df.drop(columns=["ll_latitude", "ll_longitude", "land_fraction"])
            .rename(columns={"idgrid_era5": "idgrid"}))

    engine = sa.create_engine(config.database.dsn)
    with engine.begin() as DBconn:
        df.to_sql("grid_agera5", DBconn, if_exists="append", index=False, method="multi")


def build_database():
    engine = sa.create_engine(config.database.dsn)
    meta = sa.MetaData(engine)

    # Build table with weather data
    tbl1 = sa.Table(config.database.agera5_table_name, meta,
                   sa.Column("idgrid", sa.Integer, primary_key=True),
                   sa.Column("day", sa.Date, primary_key=True))
    for variable, selected in config.variables.items():
        if selected:
            tbl1.append_column(sa.Column(variable.lower(), sa.Float))

    # Build table with grid definition
    tbl2 = sa.Table(config.database.grid_table_name, meta,
                   sa.Column("idgrid", sa.Integer, primary_key=True),
                   sa.Column("longitude", sa.Float),
                   sa.Column("latitude", sa.Float),
                   sa.Column("elevation", sa.Float,),
                   )
    try:
        tbl2.create()
        tbl1.create()
        click.echo(f"Succesfully created tables on DSN={engine}")
    except sa.exc.OperationalError as e:
        click.echo("Failed creating tables, do they already exist?")
        r = click.confirm(f"Continue with initializing?")
        if not r:
            sys.exit()

def init():
    create_AgERA5_config()
    click.confirm(("\nIf this is the first time you run `init` you probably want to abort now and "
                   "inspect/update your configuration file first. Continue?"), abort=True)
    set_CDSAPI_credentials()
    build_database()
    fill_grid_table()

if __name__ == "__main__":
    init()