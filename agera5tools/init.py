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
import platform
import time
from pathlib import Path
import logging
from types import SimpleNamespace

import click
import sqlalchemy as sa

from . import config
from .dump_grid import dump_grid
from .util import chunker, get_user_home


def make_paths():
    config.data_storage.netcdf_path.mkdir(exist_ok=True, parents=True)
    config.data_storage.tmp_path.mkdir(exist_ok=True, parents=True)
    config.data_storage.csv_path.mkdir(exist_ok=True, parents=True)
    config.logging.log_path.mkdir(exist_ok=True, parents=True)


def read_CDS_config(path):
    config = {}
    with open(path) as f:
        for line in f.readlines():
            if ":" in line:
                k, v = line.strip().split(":", 1)
                if k in ("url", "key", "verify"):
                    config[k] = v.strip()
    return SimpleNamespace(**config)


def check_CDS_credentials(config, CDS_config):
    """Checks if the UID/key in the current .cdsapirc file (CDS_config) matches with the ones
    provided in the YAML file (config).
    """
    uid1, key1 = CDS_config.key.replace(" ", "").split(":")
    uid2, key2 = str(config.cdsapi.uid), str(config.cdsapi.key)

    return True if (uid1, key1) == (uid2, key2) else False



def set_CDSAPI_credentials():
    """Sets the credentials for the Copernicus Climate Data Store.
    """
    home = Path.home()
    cdsapirc = home / ".cdsapirc"
    credentials = (f"url: {config.cdsapi.url}\n"
                   f"key: {config.cdsapi.uid}:{config.cdsapi.key}\n"
                   "verify: 1\n")

    click.echo(f"Checking credentials for the Copernicus Climate Data Store.")
    if not cdsapirc.exists():
        with open(cdsapirc, "w") as fp:
            fp.write(credentials)
        click.echo(f"Successfully created .cdsapirc file at {cdsapirc}")
    else:
        click.echo(f"The .cdsapirc file already exists at {cdsapirc}")
        CDS_config = read_CDS_config(cdsapirc)
        matches = check_CDS_credentials(config, CDS_config)
        if matches:
            click.echo("OK: Credentials in .cdsapirc file match with the ones in agera5tools.yaml.")
        else:
            msg = "WARNING: Credentials in .cdsapirc file do NOT match with ones in agera5tools.yaml."
            click.echo(msg)
            r = click.confirm(f"Generate a new .cdsapirc file?")
            if r:
                with open(cdsapirc, "w") as fp:
                    fp.write(credentials)
                click.echo(f"Successfully created .cdsapirc file at {cdsapirc}")
            else:
                click.echo("Leaving current .cdsapirc file as is.")


def create_AgERA5_config():
    """Create a config file for AgERA5tools in the current folder.
    """

    agera5_conf = Path.cwd() / "agera5tools.yaml"
    if agera5_conf.exists():
        r = click.confirm(f"the file '{agera5_conf}' already exists, overwrite?")
        if r is False:
            return False

    # Write a new config file, but first replace the /USERHOME/ with the users
    # actual home directory
    home = get_user_home() + "/"
    template_agera5t_config = Path(__file__).parent / "agera5tools.yaml"
    agera5t_config = open(template_agera5t_config).read()
    agera5t_config = agera5t_config.replace("/USERHOME/", home)
    with open(agera5_conf, "w") as fp:
        fp.write(agera5t_config)

    msg = f"Successfully created agera5tools config file at: \n   {agera5_conf}"
    click.echo(msg)

    return True


def fill_grid_table():
    """Fill the grid table in the agera5 database.
    """
    logger = logging.getLogger(__name__)

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
    meta = sa.MetaData(engine)
    tbl = sa.Table(config.database.grid_table_name, meta, autoload=True)
    recs = df.to_dict(orient="records")
    nrecs_written = 0
    t1 = time.time()
    try:
        with engine.begin() as DBconn:
            ins = tbl.insert()
            for chunk in chunker(recs, config.database.chunk_size):
                DBconn.execute(ins, chunk)
                nrecs_written += len(chunk)
                msg = f"Written {nrecs_written} from total {len(recs)} records to database."
                logger.info(msg)
        msg = f"Written grid definition to database in {time.time() - t1} seconds."
        logger.info(msg)
    except sa.exc.IntegrityError as e:
        msg = f"Grid definition already exists in grid table! No records written."
        click.echo(msg)
        logger.info(msg)


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

    if "AGERA5TOOLS_CONFIG" not in os.environ:
        first_time = create_AgERA5_config()
        if first_time:
            msg = ("\nYou just created a new configuration file time. Now carry out the following steps:\n"
                   "1) inspect/update your configuration file first and update the paths for data storage. "
                   "Currently all paths point to your home folder, which may not be suitable.\n"
                   "2) Set the AGERA5TOOLS_CONFIG environment variable to the location of the "
                   "configuration file.\n"
                   "3) Next rerun `init` to finalize the initialization\n")
        else:
            msg = ("\nExisting configuration file was found. Now carry out the following steps:\n"
                   "1) inspect/update your configuration file first and update the paths for data storage. "
                   "Currently all paths point to your home folder, which may not be suitable.\n"
                   "2) Set the AGERA5TOOLS_CONFIG environment variable to the location of the "
                   "configuration file\n"
                   "3) Next rerun `init` to finalize the initialization\n")
        click.echo(msg)
        return False

    set_CDSAPI_credentials()
    make_paths()
    build_database()
    fill_grid_table()

    return True

if __name__ == "__main__":
    init()