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
- dask >= 2022.7.7
- click >= 8.1
- flask >= 2.2
- cdsapi >= 0.5.1
- dotmap >= 1.3
- netCDF4 >= 1.6
- requests >= 2.28
- wsgiserver >= 1.3

Although exact version numbers are provided, this is usually not critical.

Creating a conda environment can be done (installing the Anaconda python environment is not covered here) from the
command prompt with the `conda` command::

    $ conda create --name py38_a5t python=3.8 pandas sqlalchemy pyyaml xarray dask click flask netCDF4 requests

The environment can be activated with::

    $ conda activate py38_a5t

Finally, a few additional packages need to be installed with pip::

    $ pip install cdsapi dotmap wsgiserver


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
now initialize agera5tools and create a configuration.

Initializing agera5tools - part I
---------------------------------

First of all, a location needs to be created where agera5tools can store the configuration file, data, logs and
temporary storage. In this setup we assume that this will be under `/data/agera5/`. An SQLite database will then
be created under `/data/agera5/agera5.db`, log files will reside under `/data/agera5/logs/`, NetCDF files
downloaded from the Climate Data Store will go under `/data/agera5/ncfiles` while CSV exports and temporary
files go under `/data/agera5/csv` and `/data/agera5/tmp`.

The first step is to run the `init` command. This command creates a default configuration file in the current
directory. Press enter to abort the init process in order to first modify the configuration file::

    $ agera5tools init
    No config found: Using default AGERA5TOOLS configuration!
    using config from /home/wit015/bin/miniconda3/envs/py38_a5t/lib/python3.8/site-packages/agera5tools/agera5tools.yaml
    Successfully created agera5tools config file at: /home/wit015/Sources/python/agera5tools/tmp/agera5tools.yaml

    If this is the first time you run `init` you probably want to inspect/update your configuration
    file first. [y/N]:
    Aborted!

Now we need to inspect the `agera5tools.yaml` file with a text editor. We will go through the section of the
configuration file below.

Adapting the configuration file
-------------------------------

For this guide we will mostly use the default settings which are already defined in the `agera5tools.yaml` file.
It will set up agera5tools for a region including Bangladesh for a single year (2022). This will lead
to a relatively small database file of 1.3 Gb. Be aware that choosing a large region, will very quickly lead to
a large database and in such cases other database solutions should be chosen.

Logging
.......

Only the path to the logging directory needs to be set.

.. code:: yaml

    logging:
      # Details for the log. Log levels follow conventions of the python logging framework.
      log_path: /data/agera5/logs
      log_fname: agera5tools.log
      log_level_console: WARNING
      log_level_file: INFO

Region definition
.................

The region of interest is defined by the min/max longitude and latitude in decimal degrees. Moreover a name for
the region should be provided.

.. code:: yaml

    region:
      # This defines the characteristics of the region that you want to set up.
      name: "Bangladesh"
      boundingbox:
        lon_min: 87
        lat_min: 20.5
        lon_max: 93
        lat_max: 27

Temporal range
..............

The emporal range defines the time range for which the database should be retrieved from the CDS.
Most important here is the start_year which should be >= 1979. For a database which will be
updated daily (e.g. a mirror), the end_year should be in the future but for a database with a
fixed time period another end_year can be chosen. For the current example, we only select data
from 1 January 2022 onward by setting `start_year: 2022` and `end_year: 2099`.

.. code:: yaml

    temporal_range:
      # Temporal range defines the time range for which the database should be retrieved from the CDS.
      # Most important here is the start_year which should be >= 1979. For a database which will be
      # updated daily (e.g. a mirror), the end_year should be in the future but for a database with a
      # fixed time period another end_year can be chosen.
      start_year: 2022
      end_year: 2099

Miscellaneous
.............

The most important setting here is the `reference_point`. This point is defined by its latitude/longitude
and is used by agera5tools to query the database for the dates where AgERA5 data is available dates.
Based on the difference between
the available dates in the database and the current date, agera5tools decides which days should be mirrored
and retrieved from the CDS. Note that the `reference_point` should lie *within the bounding box of the area
of interest* and should be *located on land*.

Some other settings have to do with the search radius (can be left as is) and whether values in Kelvin
should be converted to Celsius.

.. code:: yaml

    misc:
      # Miscellaneous settings:
      #  - The reference point defines a point within the boundingbox that will be used by the mirror
      #    procedure to check the available dates in the database. This point should be on land!
      #  - grid_search_radius is the radius within which the nearest grid ID will be searched,
      #    leave as is.
      #  - kelvin_to_celsius indicates if temperature conversion should be done.
      reference_point:
        lon: 90.00
        lat: 23.97
      grid_search_radius: 0.2
      kelvin_to_celsius: yes

Credentials for the Climate Data Store
......................................

The API credentials for the Climate Data Store can be obtained by registering on the `CDS`_
and retrieving the UID and API key from your login details page on the CDS. Note that the
UID and API Key are *different from the username/password* that you used to register on the CDS.
Moreover, if you are already using the python `cdsapi` package to retrieve data from the CDS,
you probably already have a `.cdsapirc` file in your home folder and you can skip this step.

.. _`CDS`: https://cds.climate.copernicus.eu

.. code:: yaml

    cdsapi:
      # Details for the Copernicus Climate Data Store. Information here will be written into the
      # $HOME/.cdsapirc file, which is used by the python API client for the CDS.
      url: https://cds.climate.copernicus.eu/api/v2
      key: <Your API key here>
      uid: <Your UID here>
      verify: 1

Database settings
.................

The database settings define the data source name to the database and the table name used to
store the AgERA5 data. Note that the DSN should follow the SQLAlchemy database URL naming
convention. The example below uses a local SQLite database which is a serverless database
without security risks.

.. warning::
    The data source name to the database stores the database username/password in plain text.
    This is a potential security risk and for servers that are exposed on the web other
    solutions are required. This could be done by putting agera5tools in a Docker container
    and using `Sealed Secrets`_

.. _`Sealed Secrets`: https://registry.hub.docker.com/r/bitnami/sealed-secrets-controller#!

.. code:: yaml

    database:
      # Details for the database that will be used to store the AgERA5 data.
      # The data source name (dsn) points to the database and should have the form of an
      # SQLAlchemy database URL: https://docs.sqlalchemy.org/en/20/core/engines.html
      # Note that the URL may contain the database password in plain text which is a security
      # risk.
      dsn: sqlite:////data/agera5/agera5.db
      agera5_table_name: weather_grid_agera5
      grid_table_name: grid_agera5

Data storage locations
......................

Agera5tools requires several locations on the filesystem for storing netCDF files, log files and
optionally compressed CSV exports that can be used to manually load data into the database.
Keeping the NetCDF files that are downloaded from the CDS is optional, but makes rebuilding the
database faster as no downloads to have be carried out.

.. code:: yaml

    data_storage:
      # Storage path for NetCDF files, CSV files and temporary storage.
      netcdf_path: /data/agera5/ncfiles/
      keep_netcdf: yes
      tmp_path: /data/agera5/tmp
      csv_path: /data/agera5/csv

AgERA5 variable selection
.........................

The YAML configuration below can be used to select which AgERA5 variables must be downloaded
and made available through the web API. By default 7 variables are selected which are used
to run common crop simulation models like WOFOST, LINGRA, DSSAT, etc.

.. code:: yaml

    variables:
      # Select which variables should be downloaded from the CDS
      Temperature_Air_2m_Mean_24h: yes
      Temperature_Air_2m_Mean_Day_Time: no
      Temperature_Air_2m_Mean_Night_Time: no

      ...

      Relative_Humidity_2m_18h: no
      Precipitation_Rain_Duration_Fraction: no
      Precipitation_Solid_Duration_Fraction: no


Initializing agera5tools - Part II
----------------------------------

After modifying the agera5tools configuration file, we need to instruct agera5tools to use our new
configuration file. This is done by setting an environment variable which points to the location of
the configuration file. In a Linux bash shell this is done as:

.. code:: bash

    $ export AGERA5TOOLS_CONFIG=/data/agera5/agera5tools.yaml
    $ agera5tools
    using config from /data/agera5/agera5tools.yaml
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

When running the `agera5tools` command, it now stops complaining about a missing configuration file
and it points to the correct file location. Note that on Windows OS, setting an environment variable
should be done as:

.. code:: dos

    $ export AGERA5TOOLS_CONFIG c:\data\agera5\agera5tools.yaml

Now we can finalize the init proces by rerunning the `init` command:

.. code:: bash

    $ agera5tools init
    using config from /data/agera5/agera5tools.yaml
    Successfully created agera5tools config file at: /home/wit015/Sources/python/agera5tools/agera5tools.yaml

    If this is the first time you run `init` you probably want to abort now and inspect/update your
    configuration file first. [y/N]: y
    The .cdsapirc file already exists at /home/wit015/.cdsapirc
    Succesfully created tables on DSN=Engine(sqlite:////data/agera5/agera5.db)
    AgERA5tools successfully initialized!.

As you see, agera5tools has checked if a .cdsapirc file exists. In this case it did find one, otherwise it would
have created one. Next, it has created an SQLite database that will be used for storing the AgERA5 data. Note that
for small setups an SQLite database is fine. However, for covering large areas a more capable database server will
be required such as MySQL or PostgreSQL.

Building the database
---------------------

The next step in the agera5tools setup is to build the database. This means that agera5tools will download the
netCDF files from the `CDS`_ for the period, region and variables that you specified in the configuration file.
The data will be exported and loaded into the database specified in the configuration file. The `build` command
was designed for bulk downloading and processing which is done once. Next, the `mirror` command can be used for
incremental updates of the database.

When looking at the `build` command in more detail, it provides to additional options which are `--to_database`
and `--to_csv`:

.. code:: bash

    $ agera5tools build --help
    using config from /data/agera5/agera5tools.yaml
    Usage: agera5tools build [OPTIONS]

      Builds the AgERA5 database by bulk download from CDS

    Options:
      -d, --to_database  Load AgERA5 data into the database
      -c, --to_csv       Write AgERA5 data to compressed CSV files.
      --help             Show this message and exit.

Without those options, the build command only downloads NetCDF files but does not load anything in the database
or export to CSV. It will therefore issue a warning that no output will be written.

The background of implementing these options is that the database loading of agera5tools relies on the `to_sql()`
functionality of `pandas` which is a relatively slow method. For small setups this is fine and you can directly
load by specifying `--to_database`. However, for setups over large regions, this can be very slow and instead
you want to export to CSV files. Next you can load the database by using dedicated loading tools such as
`pgloader`_ for postgress, `sqlloader`_ for ORACLE and MySQL `LOAD DATA` statements which take the CSV files as
input.

For the current example, we will run `build` and directly write data into the SQLite database:

.. code:: bash

    $ agera5tools build --to_database
    using config from /data/agera5/agera5tools.yaml
    Export to database: True
    Export to CSV: False

Note that the downloading and building of the database will not produce any output on the console. Instead
output is reported in the log file and one should monitor the log file in order to know the progress.
An example of the output produced in the log file is here::

    2023-01-10 15:14:24,105 [INFO] agera5tools.build: Starting AgERA5 download for 2021-11
    2023-01-10 15:14:24,119 [INFO] agera5tools.build: Skipping download, NetCDF files already exist.
    2023-01-10 15:14:24,119 [INFO] agera5tools.build: Starting AgERA5 download for 2021-12
    2023-01-10 15:14:24,143 [INFO] agera5tools.build: Skipping download, NetCDF files already exist.
    2023-01-10 15:14:31,620 [INFO] agera5tools.build: Written AgERA5 data for 2020-01 to database.
    2023-01-10 15:14:40,532 [INFO] agera5tools.build: Written AgERA5 data for 2020-02 to database.
    2023-01-10 15:14:50,363 [INFO] agera5tools.build: Written AgERA5 data for 2020-03 to database.
    2023-01-10 15:15:01,190 [INFO] agera5tools.build: Written AgERA5 data for 2020-04 to database.
    2023-01-10 15:15:11,829 [INFO] agera5tools.build: Written AgERA5 data for 2020-05 to database.
    2023-01-10 15:15:22,660 [INFO] agera5tools.build: Written AgERA5 data for 2020-06 to database.

Finally, the `build` command will complete:

.. code:: bash

    $ agera5tools build --to_database
    using config from /data/agera5/agera5tools.yaml
    Export to database: True
    Export to CSV: False
    Done building database, use the `mirror` command to keep the DB up to date


.. _`pgloader`: https://pgloader.io/
.. _`sqlloader`: https://docs.oracle.com/en/database/oracle/oracle-database/12.2/sutil/oracle-sql-loader-commands.html


Keeping AgERA5 up to date: mirroring
------------------------------------

The AgERA5 dataset receives daily updates and thus a new set of NetCDF files is available on the CDS around 17:00 UTC.
To keep your local copy of AgERA5 in sync with the AgERA5 data on the CDS, agera5tools provides a `mirror` command. This
`mirror` command will query the local AgERA5 database for the available days and compares it to the days that should be
available. The latter is computed as the 1 :sup:`st` of January of the start year in the configuration, up till 8
days before today.

The `mirror` command provides only a single option `--to_csv` which allows to write the data to a compressed CSV file.
The `mirror` command will always update the database because mirror assumes that the amount of data to load is limited
(only a few days) for which performance is sufficient.

.. code:: bash

    $ agera5tools mirror --help
    using config from /data/agera5/agera5tools.yaml
    Usage: agera5tools mirror [OPTIONS]

      Incrementally updates the AgERA5 database by daily downloads from the CDS

    Options:
      -c, --to_csv  Write AgERA5 data to compressed CSV files.
      --help        Show this message and exit.

When running the `mirror` command on a database with a few days missing, it will update the database and report
on the number of days missing. Detailed information can be found in the log files.

.. code:: bash

    $ agera5tools mirror
    using config from /data/agera5/agera5tools.yaml
    Updated the AgERA5 database with the following days: 2023-01-04, 2023-01-05



Other agera5tools commands
==========================

The agera5tools package provides several other commands that can be useful when working with AgERA5. These
commands operate on the NetCDF files directly and are therefore only useful when the NetCDF files are kept.


Check
-----

The `check` command can be used to check if the collection of NetCDF files obtained from the CDS is
complete. For example, running `agera5tools check` on a database that was not updated for a
day will provide the list of missing netCDF files:

.. code:: bash

    $ agera5tools check
    using config from /data/agera5/agera5tools.yaml
    Found 7 missing NetCDF files under /data/agera5/ncfiles:
     - /data/agera5/ncfiles/2022/Temperature-Air-2m-Mean-24h/Temperature-Air-2m-Mean-24h_C3S-glob-agric_AgERA5_20221231_final-v1.0.nc
     - /data/agera5/ncfiles/2022/Temperature-Air-2m-Max-Day-Time/Temperature-Air-2m-Max-Day-Time_C3S-glob-agric_AgERA5_20221231_final-v1.0.nc
     - /data/agera5/ncfiles/2022/Temperature-Air-2m-Min-Night-Time/Temperature-Air-2m-Min-Night-Time_C3S-glob-agric_AgERA5_20221231_final-v1.0.nc
     - /data/agera5/ncfiles/2022/Vapour-Pressure-Mean/Vapour-Pressure-Mean_C3S-glob-agric_AgERA5_20221231_final-v1.0.nc
     - /data/agera5/ncfiles/2022/Precipitation-Flux/Precipitation-Flux_C3S-glob-agric_AgERA5_20221231_final-v1.0.nc
     - /data/agera5/ncfiles/2022/Solar-Radiation-Flux/Solar-Radiation-Flux_C3S-glob-agric_AgERA5_20221231_final-v1.0.nc
     - /data/agera5/ncfiles/2022/Wind-Speed-10m-Mean/Wind-Speed-10m-Mean_C3S-glob-agric_AgERA5_20221231_final-v1.0.nc


Clip
----

The `clip` command can be used to clip a rectangular area out of the region for which agera5tools is
set up, for a given day. Note that the bounding box of the region for clipping should lie within the
bounding box of the agera5tools setup. The command creates a new NetCDF file which contains all the
AgERA5 variables in one file:

.. code:: bash

    $ agera5tools clip -o /tmp/a5t/ --bbox 88 90 25 27 2022-07-03
    using config from /data/agera5/agera5tools.yaml
    Written results to: /tmp/a5t/agera5_clipped_2022-07-03.nc

    $ ncdump -h /tmp/a5t/agera5_clipped_2022-07-03.nc
    netcdf agera5_clipped_2022-07-03 {
    dimensions:
        time = 1 ;
        lon = 20 ;
        lat = 20 ;
    variables:
        int64 time(time) ;
            time:standard_name = "time" ;
            time:long_name = "time" ;
            time:axis = "T" ;
            time:units = "days since 1900-01-01" ;
            time:calendar = "proleptic_gregorian" ;
        double lon(lon) ;
            lon:_FillValue = NaN ;
            lon:standard_name = "longitude" ;
            lon:long_name = "longitude" ;
            lon:units = "degrees_east" ;
            lon:axis = "X" ;
        double lat(lat) ;
            lat:_FillValue = NaN ;
            lat:standard_name = "latitude" ;
            lat:long_name = "latitude" ;
            lat:units = "degrees_north" ;
            lat:axis = "Y" ;
        float Precipitation_Flux(time, lat, lon) ;
            Precipitation_Flux:_FillValue = -9999.f ;
            Precipitation_Flux:units = "mm d-1" ;
            Precipitation_Flux:long_name = "Total precipitation (00-00LT)" ;
            Precipitation_Flux:temporal_aggregation = "Sum 00-00LT" ;
            Precipitation_Flux:missing_value = -9999.f ;
        float Solar_Radiation_Flux(time, lat, lon) ;
            Solar_Radiation_Flux:_FillValue = -9999.f ;
            Solar_Radiation_Flux:units = "J m-2 d-1" ;
            Solar_Radiation_Flux:long_name = "Surface solar radiation downwards (00-00LT)" ;
            Solar_Radiation_Flux:temporal_aggregation = "Sum 00-00LT" ;
            Solar_Radiation_Flux:missing_value = -9999.f ;
        float Temperature_Air_2m_Max_Day_Time(time, lat, lon) ;
            Temperature_Air_2m_Max_Day_Time:_FillValue = -9999.f ;
            Temperature_Air_2m_Max_Day_Time:units = "K" ;
            Temperature_Air_2m_Max_Day_Time:long_name = "Maximum temperature at 2 meter (06-18LT)" ;
            Temperature_Air_2m_Max_Day_Time:temporal_aggregation = "Max 06-18LT" ;
            Temperature_Air_2m_Max_Day_Time:missing_value = -9999.f ;
        float Temperature_Air_2m_Mean_24h(time, lat, lon) ;
            Temperature_Air_2m_Mean_24h:_FillValue = -9999.f ;
            Temperature_Air_2m_Mean_24h:units = "K" ;
            Temperature_Air_2m_Mean_24h:long_name = "2 meter air temperature (00-00LT)" ;
            Temperature_Air_2m_Mean_24h:temporal_aggregation = "Mean 00-00LT" ;
            Temperature_Air_2m_Mean_24h:missing_value = -9999.f ;
        float Temperature_Air_2m_Min_Night_Time(time, lat, lon) ;
            Temperature_Air_2m_Min_Night_Time:_FillValue = -9999.f ;
            Temperature_Air_2m_Min_Night_Time:units = "K" ;
            Temperature_Air_2m_Min_Night_Time:long_name = "Minimum temperature at 2 meter (18-06LT)" ;
            Temperature_Air_2m_Min_Night_Time:temporal_aggregation = "Min 18-06LT" ;
            Temperature_Air_2m_Min_Night_Time:missing_value = -9999.f ;
        float Vapour_Pressure_Mean(time, lat, lon) ;
            Vapour_Pressure_Mean:_FillValue = -9999.f ;
            Vapour_Pressure_Mean:units = "hPa" ;
            Vapour_Pressure_Mean:long_name = "Vapour pressure (00-00LT)" ;
            Vapour_Pressure_Mean:temporal_aggregation = "Mean 00-00LT" ;
            Vapour_Pressure_Mean:missing_value = -9999.f ;
        float Wind_Speed_10m_Mean(time, lat, lon) ;
            Wind_Speed_10m_Mean:_FillValue = -9999.f ;
            Wind_Speed_10m_Mean:units = "m s-1" ;
            Wind_Speed_10m_Mean:long_name = "10 metre wind component (00-00LT)" ;
            Wind_Speed_10m_Mean:temporal_aggregation = "Mean 00-00LT" ;
            Wind_Speed_10m_Mean:missing_value = -9999.f ;

    // global attributes:
            :Conventions = "CF-1.7" ;
    }



Dump
----

The `dump` command can be used to take the contents of the NetCDF files of AgERA5 for a given day,
and dump the results to a tabular format which can be either CSV, JSON or an SQLite database
depending on the suffix of the output filename (.csv, .json or .db3). If no output filename is
provided, the dump command will send its output to standard output in CSV format.

The example below shows how to dump to JSON for a small region within Bangladesh:

.. code:: bash

    $ agera5tools dump -o /tmp/a5t/agera_2022-07-03.json --bbox 88 90 25 27 2022-07-03
    using config from /data/agera5/agera5tools.yaml
    Written JSON output to: /tmp/a5t/agera_2022-07-03.json

    $ cat /tmp/a5t/agera_2022-07-03.json | jq
    [
      {
        "day": 1656806400000,
        "lon": 88.15,
        "lat": 26.95,
        "precipitation_flux": 3.5599999428,
        "solar_radiation_flux": 16385375,
        "temperature_air_2m_max_day_time": 24.7488708496,
        "temperature_air_2m_mean_24h": 21.5311584473,
        "temperature_air_2m_min_night_time": 18.8098754883,
        "vapour_pressure_mean": 22.9674816132,
        "wind_speed_10m_mean": 1.1026197672
      },
    ...
      {
        "day": 1656806400000,
        "lon": 90.05,
        "lat": 25.05,
        "precipitation_flux": 4.4800000191,
        "solar_radiation_flux": 18370952,
        "temperature_air_2m_max_day_time": 32.2112121582,
        "temperature_air_2m_mean_24h": 28.7552490234,
        "temperature_air_2m_min_night_time": 26.2648620605,
        "vapour_pressure_mean": 32.9158477783,
        "wind_speed_10m_mean": 2.8463871479
      }
    ]

Extract_point
-------------

The `extract_point` command can be used to extract the time-series of AgERA5 data for a given location
specified by its latitude and longitude, moreover the time-series can be limited by a start date and an
end date. The output will be written in a tabular format which can be either CSV, JSON or an SQLite database
depending on the suffix of the output filename (.csv, .json or .db3). If no output filename is
provided, the `extract_point` command will send its output to standard output in CSV format.

.. code:: bash

    $ agera5tools extract_point 90 24 2022-06-01 2022-06-05
    using config from /data/agera5/agera5tools.yaml
    day,precipitation_flux,solar_radiation_flux,temperature_air_2m_max_day_time,temperature_air_2m_mean_24h,temperature_air_2m_min_night_time,vapour_pressure_mean,wind_speed_10m_mean
    2022-06-01,   6.03,19547780,  31.98,  28.38,  25.76,  32.43,   2.59
    2022-06-02,  44.67,9140519,  30.06,  28.03,  25.56,  32.08,   2.04
    2022-06-03,   2.93,12673785,  31.15,  28.59,  26.02,  32.72,   3.41
    2022-06-04,   2.16,16276887,  32.50,  28.10,  26.70,  32.77,   3.69
    2022-06-05,   3.09,18650926,  32.79,  29.38,  26.75,  34.05,   3.82


Dump_grid
---------

The `dump_grid` command can be used to dump the grid definition of AgERA5 to a tabular format.
It has little use outside the initial set up of the AgERA5 database, but is added for convenience.
For set ups for large regions it is often more convenient to dump the grid to CSV and load it
with a dedicated tool. Similar to `dump`  `extract_point`, the `dump_grid` command can write to
CSV, JSON or SQLite and will write to stdout if no output is given:

.. code:: bash

    $ agera5tools dump_grid | head
    using config from /data/agera5/agera5tools.yaml
    ll_latitude,ll_longitude,idgrid_era5,elevation,land_fraction,latitude,longitude
      83.90, -40.30,6258197,  -4.62,   0.00,  83.95, -40.25
      83.90, -40.20,6258198,  -4.62,   0.00,  83.95, -40.15
      83.90, -40.10,6258199,  -4.62,   0.00,  83.95, -40.05
      83.90, -40.00,6258200,   7.40,   0.00,  83.95, -39.95
      83.90, -39.90,6258201,   7.40,   0.00,  83.95, -39.85
      83.90, -39.80,6258202,   7.40,   0.00,  83.95, -39.75
      83.90, -39.70,6258203,  19.50,   0.00,  83.95, -39.65
      83.90, -39.60,6258204,  19.50,   0.00,  83.95, -39.55



Serving AgERA5 data through an HTTP API
=======================================

Creating a local mirror of the AgERA5 database only starts to be useful when the data is easily
accessible for applications. For this purpose, agera5tools can serve the AgERA5 data in the
database through a web API using the HTTP protocol. Time-series of AgERA5 data can be requested
through a parameterized URL which provides the location for which the data is requested as well
as an optional start and end date. Through this approach AgERA5 data can be made available for
application running locally or through a webserver on the local network.

For serving data on a local network agera5tools provides the `serve` command which has a single
option `--port=<number>`. By default the port number is 8080, but the port number can be changed
to solve conflicts with existing web applications or by allowing multiple agera5tools instances
to run simultaneously:

.. code:: bash

    $ agera5tools serve
    using config from /data/agera5/agera5tools.yaml
    Started serving AgERA5 data on http://localhost:8080

When a web browser is pointed to `http://localhost:8080`, the browser will show a short help text
as show in the image below.

.. image:: ./_static/agera5tools_serve.png
   :width: 400


Moreover, the help page contains an example URL at the bottom below
that can be used to query data from the database and demonstrate the response, as shown below.

.. image:: ./_static/agera5tools_response.png
   :width: 400



finally, take note of the warning below on using `agera5tools serve`.


.. warning::
    The `serve` capabilities of agera5tools are based on the `Flask web framework`_ combined with a
    `WSGI server`_. This combination is an effective and lightweight approach to serving data on a
    local machine or a local network. This approach is not guaranteed to be safe and robust enough
    to serve AgERA5 on a web address that is exposed to the outside world. For such a task you
    will probably need a set up that combines a secure high performance web server (such as NGINX)
    that works with a WSGI server on the background (the one that can serve Flask applications).
    Ideally this could be done using docker for which a nice tutorial and base docker images are
    available `here`_.

.. _`Flask web framework`: https://flask.palletsprojects.com/en/2.2.x/
.. _`WSGI server`: https://pypi.org/project/WSGIserver/
.. _`here`: https://github.com/tiangolo/uwsgi-nginx-flask-docker
