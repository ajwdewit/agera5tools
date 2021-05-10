# AgERA5tools
Tools for manipulating (exporting, extracting) AgERA5 data.

The agera5tools consist of a set of commandline scripts as well as the `agera5tools` python package
which can be used to access AgERA5 data directly from python scripts.

## Commandline tools

The agera5 commandline tools currently have 4 options:
- *extract_point*: this can be used to extract a time-series of variables for a given location
- *dump* which can be used to dump one day of AgERA5 data to CSV, JSON or SQLite 
- *clip* which can be used to extract a subset of AgERA5 data which will be written to a new NetCDF file.
- *dump_grid* which dumps the AgERA5 grid definition to CSV, JSON or SQLite.

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

The shell commands described above can also be used from python directly by importing the agera5tools package. Their working is nearly identical as the shell commands. The major difference is that the python functions return either datasets (clip) or dataframes (extract_point, dump, dump_grid). An example for the `clip` function:

```python
In [1]: import datetime as dt
   ...: import agera5tools
   ...: from agera5tools.util import BoundingBox
   ...: agera5_dir = "/data/wit015/crucial/data_CDS/6_data_ERA5_01grid_dailyAg_corr"
   ...: day  = dt.date(2018,1,1)
   ...: bbox = BoundingBox(lon_min=4, lon_max=6, lat_min=52, lat_max=54)
   ...: ds = agera5tools.clip(agera5_dir, day, bbox)
   ...: 

In [2]: ds
Out[2]: 
<xarray.Dataset>
Dimensions:                                (lat: 20, lon: 20, time: 1)
Coordinates:
  * time                                   (time) datetime64[ns] 2018-01-01
  * lon                                    (lon) float64 4.1 4.2 4.3 ... 5.9 6.0
  * lat                                    (lat) float64 53.9 53.8 ... 52.1 52.0
Data variables:
    Cloud_Cover_Mean                       (time, lat, lon) float32 dask.array<chunksize=(1, 20, 20), meta=np.ndarray>
    Dew_Point_Temperature_2m_Mean          (time, lat, lon) float32 dask.array<chunksize=(1, 20, 20), meta=np.ndarray>
    Precipitation_Flux                     (time, lat, lon) float32 dask.array<chunksize=(1, 20, 20), meta=np.ndarray>
    Precipitation_Rain_Duration_Fraction   (time, lat, lon) float32 dask.array<chunksize=(1, 20, 20), meta=np.ndarray>
    Precipitation_Solid_Duration_Fraction  (time, lat, lon) float32 dask.array<chunksize=(1, 20, 20), meta=np.ndarray>
    Relative_Humidity_2m_06h               (time, lat, lon) float32 dask.array<chunksize=(1, 20, 20), meta=np.ndarray>
    Relative_Humidity_2m_09h               (time, lat, lon) float32 dask.array<chunksize=(1, 20, 20), meta=np.ndarray>
    Relative_Humidity_2m_12h               (time, lat, lon) float32 dask.array<chunksize=(1, 20, 20), meta=np.ndarray>
    Relative_Humidity_2m_15h               (time, lat, lon) float32 dask.array<chunksize=(1, 20, 20), meta=np.ndarray>
    Relative_Humidity_2m_18h               (time, lat, lon) float32 dask.array<chunksize=(1, 20, 20), meta=np.ndarray>
    Snow_Thickness_LWE_Mean                (time, lat, lon) float32 dask.array<chunksize=(1, 20, 20), meta=np.ndarray>
    Snow_Thickness_Mean                    (time, lat, lon) float32 dask.array<chunksize=(1, 20, 20), meta=np.ndarray>
    Solar_Radiation_Flux                   (time, lat, lon) float32 dask.array<chunksize=(1, 20, 20), meta=np.ndarray>
    Temperature_Air_2m_Max_24h             (time, lat, lon) float32 dask.array<chunksize=(1, 20, 20), meta=np.ndarray>
    Temperature_Air_2m_Max_Day_Time        (time, lat, lon) float32 dask.array<chunksize=(1, 20, 20), meta=np.ndarray>
    Temperature_Air_2m_Mean_24h            (time, lat, lon) float32 dask.array<chunksize=(1, 20, 20), meta=np.ndarray>
    Temperature_Air_2m_Mean_Day_Time       (time, lat, lon) float32 dask.array<chunksize=(1, 20, 20), meta=np.ndarray>
    Temperature_Air_2m_Mean_Night_Time     (time, lat, lon) float32 dask.array<chunksize=(1, 20, 20), meta=np.ndarray>
    Temperature_Air_2m_Min_24h             (time, lat, lon) float32 dask.array<chunksize=(1, 20, 20), meta=np.ndarray>
    Temperature_Air_2m_Min_Night_Time      (time, lat, lon) float32 dask.array<chunksize=(1, 20, 20), meta=np.ndarray>
    Vapour_Pressure_Mean                   (time, lat, lon) float32 dask.array<chunksize=(1, 20, 20), meta=np.ndarray>
    Wind_Speed_10m_Mean                    (time, lat, lon) float32 dask.array<chunksize=(1, 20, 20), meta=np.ndarray>
Attributes:
    CDI:          Climate Data Interface version 1.9.2 (http://mpimet.mpg.de/...
    history:      Fri Mar 12 15:02:25 2021: cdo splitday /archive/ESG/wit015/...
    Conventions:  CF-1.7
    CDO:          Climate Data Operators version 1.9.2 (http://mpimet.mpg.de/...
```

It works in a very similar way for the `extract_point` function:
```python
In [6]: from agera5tools.util import Point
   ...: pnt = Point(lat=52, lon=5)
   ...: df = agera5tools.extract_point(agera5_dir, pnt, startday=dt.date(2018,1,1), endday=dt.date(2018,1,31), tocelsius=True)
   ...: 
         time  lon   lat  ...  Temperature_Air_2m_Min_Night_Time  Vapour_Pressure_Mean  Wind_Speed_10m_Mean
0  2018-01-01  5.0  52.0  ...                           6.088837              8.179029             5.252212
0  2018-01-02  5.0  52.0  ...                           4.557800              8.838871             6.389601
0  2018-01-03  5.0  52.0  ...                           6.112335              8.319856            10.432665
0  2018-01-04  5.0  52.0  ...                           5.801544              8.891143             6.885569
0  2018-01-05  5.0  52.0  ...                           5.203705              8.262363             4.899943

[5 rows x 25 columns]
```
In this case, the temperature related variables are now converted from Kelvin to Celsius as well. 

Note that extracting point data for a long timeseries can be time-consuming because all netCDF files have to be opened, decompressed and the point extracted. 

## Installing agera5tools

### Requirements
The agera5tools package requires python >=3.7 and has a number of dependencies:
 - xarray (>= 0.16)
 - click (>=7.0)
 - netcdf4 ()>=1.5)
 
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
