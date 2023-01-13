# Global daily weather data from AgERA5

<img src="https://dl.dropbox.com/s/d3mcuzf7os0be3x/agera5.png" width="400">

## Introduction
[AgERA5](https://doi.org/10.24381/cds.6c68c9bb) provides a global archive of daily meteorological 
variables over the period 1979 up till current. It contains 22 weather variables at a resolution of 
0.1 degree between -66.5 to 66.5 latitude. AgERA5 is derived from the ERA5 reanalysis but its contents
are specifically tailored for agricultural applications.

AgERA5 is freely available from the Copernicus Climate Data Store and can be downloaded as NetCDF files. However, working with
NetCDF files is cumbersome for many people outside the word of meteorology. The `agera5tools` package tries
to simplify the use of AgERA5 by allowing the user to set up a local mirror of AgERA5. Moreover, this mirror
can be adapted by reducing the size of the region of interest, by limiting the number of variables that
are mirrored and by limiting the temporal range (e.g. number of years).
Using this approach small, local mirrors can be created which is much more efficient compared
to having to download and process the entire AgERA5 archive. Finally, agera5tools
can be used to serve time-series of AgERA5 data on a local HTTP API which simplifies the use of data in various
application.

The default configuration file provided with the agera5tools package, sets up a mirror for Bangladesh starting
in the year 2022 and can do daily updates of the database. 

## The HTTP API

If you are looking at this page, it means that you have been able to successfully run `agera5tools serve`.
Therefore you are probably interested in understanding the HTTP API. 
Current there is only one call implemented by this API: 

 - `/api/v1/get_agera5`  

A description of the purpose and parameters of each API is provided below.  

## get_agera5

The compulsary API input parameters are:

 - latitude: the latitude of the site in decimal degrees 
 - longitude: the longitude of the site in decimal degrees 

Optionally, one can use: 

 - startdate: the first date of the time-series to retrieve (yyyy-mm-dd)
 - enddate: the last date of the time-series to retrieve (yyyy-mm-dd)

The API call returns a JSON response, that can be best viewed with the Firefox browser.

example: [Here](/api/v1/get_agera5?latitude=24.65&longitude=90.95&startdate=2022-06-01&enddate=2022-08-31)