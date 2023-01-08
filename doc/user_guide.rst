Introduction
============

Since 2021 the `AgERA5`_ dataset is available on the Copernicus Climate Data Store (CDS). AgERA5 provides
daily values of 22 commonly used meteorological variables globally at a 0.1x0.1 degree resolution.
AgERA5 is derived
from the ERA5 reanalysis dataset developed by ECMWF, but is specifically designed for agrometeorological
applications. For example, ERA5 consists of hourly data which is often not convenient for agrometeorological
purposes where daily data is often required. So the AgERA5 product already does the aggregation from
hourly to daily values taking into account that the definition of day-time and night-time is time-zone
dependent. Moreover, many agro-relevant variables have been derived such as daily min/max temperature,
total daily solar radiation, daily precipitation sums, etc. Finally, similar to ERA5, AgERA5 is updated
daily with a delay on realtime of 8 days.

Nevertheless, setting up AgERA5 in a way that is convenient for end users still requires a considerable effort.
For example, the dataset is provided by the CDS as netCDF files but a way to easily access the data is
not available. In this respect, the end-user experience of the `NASA POWER`_ dataset is much better as it provides
a user interface and a convenient web API to query data. The AgERA5tools package has been developed
to alleviate the problem with accessing AgERA5 data. It makes setting up a local mirror of AgERA5 much easier,
time series of meteorological data can be extracted easily and it provides a web API that can be used by
other applications to easily access AgERA5 data.


.. _`AgERA5`: https://cds.climate.copernicus.eu/cdsapp#!/dataset/sis-agrometeorological-indicators
.. _`NASA POWER`: https://power.larc.nasa.gov/

Setting up AgERA5tools
======================

Creating a python environment
-----------------------------

A python environment has to be created that has all the requirements for AgERA5tools. AgERA5tools was developed using
python 3.8.10 but this is not critical. Older or more recent version of python will most likely work as well.
Third party packages required for installing are:

- Pandas >= 1.5
- SQLAlchemy >= 1.4
- PyYAML >= 6.0
- xarray >= 2022.12.0
- click >= 8.1
- flask >= 2.2
- cdsapi >= 0.5.1
- dotmap >= 1.3
- netCDF4 >= 1.6
- requests >= 2.28

Although exact version numbers are provided, this is probably not critical.

Creating a conda environment can be done (installing the Anaconda python environment is not covered here) from the
command prompt with the `conda` command::

    $ conda create --name py38_a5t python=3.8 pandas sqlalchemy pyyaml xarray click flask netCDF4 requests

The environment can be actived with::

    $ conda activate py38_a5t

Finally, a few additional packages need to be installed with pip::

    $ pip install cdsapi dotmap


Installing AgERA5tools
----------------------

AgERA5tools can now be installed with::

   $ pip install agera5tools

The `agera5tools` package can now be imported from python::

    $ python
    Python 3.8.10 (default, Nov 14 2022, 12:59:47)
    [GCC 9.4.0] on linux
    Type "help", "copyright", "credits" or "license" for more information.
    >>> import agera5tools
    No config found: Using default AGERA5TOOLS configuration!
    using config from /home/allard/Projects/crucial/agera5tools/agera5tools/agera5tools.yaml
    >>>

Moreover, there should be an `agera5tools` command in your current environment::

    $ agera5tools
    No config found: Using default AGERA5TOOLS configuration!
    using config from /home/allard/Projects/crucial/agera5tools/venv/lib/python3.8/site-packages/agera5tools/agera5tools.yaml
    Usage: agera5tools [OPTIONS] COMMAND [ARGS]...

    Options:
      --help  Show this message and exit.

    Commands:
      build          Builds the AgERA5 database by bulk download from CDS
      check          Checks the completeness of NetCDF files from which the...
      clip           Extracts a portion of agERA5 for the given bounding box...
      dump           Dump AgERA5 data for a given day to CSV, JSON or SQLite
      dump_grid      Dump the agERA5 grid to a CSV, JSON or SQLite DB.
      extract_point  Extracts AgERA5 data for given location and date range.
      init           Initializes AgERA5tools
      mirror         Incrementally updates the AgERA5 database by daily...
      serve          Starts the http server to serve AgERA5 data through HTTP


Since we have not set up `agera5tools`, the package is complaining that a configuration file cannot be found. We will
now initialize agera5tools and create a configuration

Setting up agera5tools
----------------------

The first step is to run the `init` command. This command