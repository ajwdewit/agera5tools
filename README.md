# AgERA5tools
Tools for mirroring, manipulating (exporting, extracting) and 
serving [AgERA5](https://doi.org/10.24381/cds.6c68c9bb) data.

The agera5tools consist of a set of commandline scripts as well as the `agera5tools` python package
which can be used to 
- set up a mirror for AgERA5 that can automatically build a 
  local copy and keep it up to date with the latest AgERA5 data.
- Allow operations on the downloaded NetCDF files directly such as dumping, point extraction and clipping
- Serve AgERA5 data on web API through the HTTP protocol. By providing the latitude and longitude in the
  URL, agera5tools can retrieve the corresponding data and return it as JSON.


## Commandline tools

The agera5 commandline tools currently have 8 options. The first four are for setting up and managing
the local AgERA5 database:
- *init* to generate a configuration file and initialize the set up.
- *build* to download the relevant AgERA5 data from Copernicus Climate Data Store (CDS) and build the local database.
- *mirror* to update the current database with new days from the CDS.
- *serve* to serve AgERA5 data through a web API and return as JSON encoded data.

The other four tools operate directly on the NetCDF files downloaded from the CDS.
- *extract_point*: this can be used to extract a time-series of variables for a given location
- *dump* which can be used to dump one day of AgERA5 data to CSV, JSON or SQLite 
- *clip* which can be used to extract a subset of AgERA5 data which will be written to a new NetCDF file.
- *dump_grid* which dumps the AgERA5 grid definition to CSV, JSON or SQLite.

### Init

```Shell
$ agera5tools init --help
using config from /data/agera5/agera5tools.yaml
Usage: agera5tools init [OPTIONS]

  Initializes AgERA5tools

  This implies the following:
   - Creating a template configuration file in the current directory
   - Creating a $HOME/.cdsapirc file for access to the CDS
   - Creating the database tables
   - Filling the grid table with the reference grid.

Options:
  --help  Show this message and exit.
```

### Build

```Shell
$ agera5tools build --help
using config from /data/agera5/agera5tools.yaml
Usage: agera5tools build [OPTIONS]

  Builds the AgERA5 database by bulk download from CDS

Options:
  -d, --to_database  Load AgERA5 data into the database
  -c, --to_csv       Write AgERA5 data to compressed CSV files.
  --help             Show this message and exit.
```

### Mirror

```Shell
$ agera5tools mirror --help
using config from /data/agera5/agera5tools.yaml
Usage: agera5tools mirror [OPTIONS]

  Incrementally updates the AgERA5 database by daily downloads from the CDS.

Options:
  -c, --to_csv  Write AgERA5 data to compressed CSV files.
  --help        Show this message and exit.
```

### Serve

```Shell
$ agera5tools serve --help
using config from /data/agera5/agera5tools.yaml
Usage: agera5tools serve [OPTIONS]

  Starts the http server to serve AgERA5 data through HTTP

Options:
  -p, --port INTEGER  Port to number to start listening, default=8080.
  --help              Show this message and exit.
```

### Extract point

```Shell
$ agera5tools extract_point --help
Usage: agera5tools extract_point [OPTIONS] AGERA5_PATH LONGITUDE LATITUDE
                                 STARTDATE ENDDATE
  Extracts AgERA5 data for given location and date range.

  AGERA5_PATH: path to the AgERA5 dataset
  LONGITUDE: the longitude for which to extract [dd, -180:180]
  LATITUDE: the latitude for which to extract [dd, -90:90]
  STARTDATE: the start date (yyyy-mm-dd, >=1979-01-01)
  ENDDATE: the last date (yyyy-mm-dd, <= 1 week ago)

Options:
  -o, --output PATH  output file to write to: .csv, .json and .db3 (SQLite)
                     are supported.Giving no output will write to stdout in
                     CSV format

  --tocelsius        Convert temperature values from degrees Kelvin to Celsius
  --help             Show this message and exit.
```

### Dump

```Shell
$ agera5tools dump --help
Usage: agera5tools dump [OPTIONS] AGERA5_PATH DAY

  Dump AgERA5 data for a given day to CSV, JSON or SQLite

  AGERA5_PATH: Path to the AgERA5 dataset
  DAY: specifies the day to be dumped (yyyy-mm-dd)

Options:
  -o, --output PATH  output file to write to: .csv, .json and .db3 (SQLite)
                     are supported. Giving no output will write to stdout in
                     CSV format

  --tocelsius        Convert temperature values from degrees Kelvin to Celsius
  --add_gridid       Adds a grid ID instead of latitude/longitude columns.
  --bbox FLOAT...    Bounding box: <lon_min> <lon_max> <lat_min< <lat max>
  --help             Show this message and exit.
```

### Clip

```Shell
$ agera5tools clip --help
Usage: agera5tools clip [OPTIONS] AGERA5_PATH DAY

  Extracts a portion of agERA5 for the given bounding box and saves to
  NetCDF.

  AGERA5_PATH: Path to the AgERA5 dataset
  DAY: specifies the day to be dumped (yyyy-mm-dd)

Options:
  --base_fname TEXT      Base file name to use, otherwise will use
                         'agera5_clipped'

  -o, --output_dir PATH  Directory to write output to. If not provided, will
                         use current directory.

  --box FLOAT...         Bounding box: <lon_min> <lon_max> <lat_min< <lat max>
  --help                 Show this message and exit.
```

### dump_grid

```Shell
Usage: agera5tools dump_grid [OPTIONS]

  Dump the agERA5 grid to a CSV, JSON or SQLite DB.

Options:
  -o, --output PATH  output file to write to: .csv, .json and .db3 (SQLite)
                     are supported.Giving no output will write to stdout in
                     CSV format

  --help             Show this message and exit.

```

## Python package

The shell commands described above can also be used from python directly by importing the agera5tools package. 
Their working is nearly identical as the shell commands. The major difference is that the python functions 
return either datasets (clip) or dataframes (extract_point, dump, dump_grid). An example for the `clip` function:

```python
In [1]: import datetime as dt
   ...: import agera5tools
   ...: from agera5tools.util import BoundingBox
   ...: day = dt.date(2018,1,1)
   ...: bbox = BoundingBox(lon_min=87, lon_max=90, lat_min=24, lat_max=27)
   ...: ds = agera5tools.clip(day, bbox)
   ...: 

In [2]: ds
Out[2]: 
<xarray.Dataset>
Dimensions:                            (time: 1, lon: 30, lat: 30)
Coordinates:
  * time                               (time) datetime64[ns] 2018-01-01
  * lon                                (lon) float64 87.1 87.2 ... 89.9 90.0
  * lat                                (lat) float64 26.9 26.8 ... 24.1 24.0
Data variables:
    Precipitation_Flux                 (time, lat, lon) float32 dask.array<chunksize=(1, 30, 30), meta=np.ndarray>
    Solar_Radiation_Flux               (time, lat, lon) float32 dask.array<chunksize=(1, 30, 30), meta=np.ndarray>
    Temperature_Air_2m_Max_Day_Time    (time, lat, lon) float32 dask.array<chunksize=(1, 30, 30), meta=np.ndarray>
    Temperature_Air_2m_Mean_24h        (time, lat, lon) float32 dask.array<chunksize=(1, 30, 30), meta=np.ndarray>
    Temperature_Air_2m_Min_Night_Time  (time, lat, lon) float32 dask.array<chunksize=(1, 30, 30), meta=np.ndarray>
    Vapour_Pressure_Mean               (time, lat, lon) float32 dask.array<chunksize=(1, 30, 30), meta=np.ndarray>
    Wind_Speed_10m_Mean                (time, lat, lon) float32 dask.array<chunksize=(1, 30, 30), meta=np.ndarray>
Attributes:
    CDI:          Climate Data Interface version 1.9.2 (http://mpimet.mpg.de/...
    history:      Fri Mar 12 15:04:43 2021: cdo splitday /archive/ESG/wit015/...
    Conventions:  CF-1.7
    CDO:          Climate Data Operators version 1.9.2 (http://mpimet.mpg.de/...
```

It works in a very similar way for the `extract_point` function:

```python
In[6]: from agera5tools.util import Point

In[7]: pnt = Point(latitude=26, longitude=89)
In[8]: df = agera5tools.extract_point(pnt, startday=dt.date(2018, 1, 1), endday=dt.date(2018, 1, 31)),
In [7]: df.head(5)
Out[7]: 
          day  precipitation_flux  solar_radiation_flux  ...  temperature_air_2m_min_night_time  vapour_pressure_mean  wind_speed_10m_mean
0  2018-01-01                0.31              13282992  ...                          12.156799             11.809731             1.317589
1  2018-01-02                1.91              13646220  ...                          12.342041             11.711860             1.416075
2  2018-01-03                0.14              14817991  ...                          11.064514             11.198871             1.524268
3  2018-01-04                0.03              14131904  ...                          10.861877             11.413278             1.566405
4  2018-01-05                0.07              14315206  ...                          12.292969             10.984181             1.597181

[5 rows x 8 columns]
```

Note that extracting point data for a long timeseries can be time-consuming because all netCDF files have to be opened, decompressed and the point extracted. 

## Installing agera5tools

### Requirements
The agera5tools package requires python >=3.8 and has a number of dependencies:
- pandas == 1.4.1
- PyYAML >= 6.0
- Pandas >= 1.5
- SQLAlchemy >= 1.4
- PyYAML >= 6.0
- xarray >= 2022.12.0
- dask >= 2022.7.0
- click >= 8.1
- flask >= 2.2
- cdsapi >= 0.5.1
- dotmap >= 1.3
- netCDF4 >= 1.6
- requests >= 2.28
- wsgiserver >= 1.3
 
Lower versions of dependencies may work, but have not been tested.
 
### Installing

Installing `agera5tools` can be done through the github repository to get the latest version:

```shell script
pip install https://github.com/ajwdewit/agera5tools/archive/refs/heads/main.zip
``` 

or directory from PyPI:

```shell script
pip install agera5tools
``` 
