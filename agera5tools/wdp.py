# -*- coding: utf-8 -*-
# Copyright (c) 2023 Wageningen Environmental Research, Wageningen-UR
# Allard de Wit (allard.dewit@wur.nl), February 2023
"""A weather data provider for reading data from the HTTP API provided by agera5tools.
"""
from datetime import date
import requests
import yaml

from pcse.base import WeatherDataContainer, WeatherDataProvider
from pcse.util import reference_ET
from pcse.exceptions import PCSEError

mm_to_cm = lambda x: x/10.


class AgERA5WeatherDataProvider(WeatherDataProvider):
    """WeatherDataProvider that can be used to combine the weather data served
    by `agera5tools serve` with crop models provided by PCSE
    (see also https://pcse.readthedocs.io).



    """
    variable_renaming = [("temperature_air_2m_max_day_time", "TMAX", None),
                         ("temperature_air_2m_min_night_time", "TMIN", None),
                         ("temperature_air_2m_mean_24h",  "TEMP", None),
                         ("vapour_pressure_mean", "VAP", None),
                         ("wind_speed_10m_mean", "WIND", None),
                         ("precipitation_flux", "RAIN",mm_to_cm),
                         ("solar_radiation_flux", "IRRAD",None),
                         ("day", "DAY", None)]
    angstA = 0.25
    angstB = 0.45
    ETmodel = "PM"

    def __init__(self, hostname="localhost", port=8080, **inputs):
        WeatherDataProvider.__init__(self)
        url = f'http://{hostname}:{port}/api/v1/get_agera5'
        r = requests.get(url, params=inputs)
        r_data = yaml.safe_load(r.text.replace('"', ''))
        if r_data["success"] is False:
            msg = f"Failed retrieving AgERA5 data: {r_data['message']}"
            raise RuntimeError(msg)

        self.elevation = r_data["data"]["location_info"]["grid_agera5_elevation"]
        self.longitude = inputs["longitude"]
        self.latitude = inputs["latitude"]
        region_name = r_data["data"]["location_info"]["region_name"]
        self.description = [f"Weather data from AgERA5 for {region_name}"]
        for daily_weather in r_data["data"]["weather_variables"]:
            self._make_WeatherDataContainer(daily_weather)

    def _make_WeatherDataContainer(self, daily_weather):

        thisdate = daily_weather["day"]
        t = {"LAT": self.latitude, "LON": self.longitude, "ELEV": self.elevation}
        for old_name, new_name, conversion in self.variable_renaming:
            if conversion is not None:
                t[new_name] = conversion(daily_weather[old_name])
            else:
                t[new_name] = daily_weather[old_name]

        # Reference evapotranspiration in mm/day
        try:
            E0, ES0, ET0 = reference_ET(t["DAY"] , t["LAT"], t["ELEV"], t["TMIN"], t["TMAX"], t["IRRAD"],
                                        t["VAP"], t["WIND"], self.angstA, self.angstB, self.ETmodel)
        except ValueError as e:
            msg = (("Failed to calculate reference ET values on %s. " % thisdate) +
                   ("With input values:\n %s.\n" % str(t)) +
                   ("Due to error: %s" % e))
            raise PCSEError(msg)

        # update record with ET values value convert to cm/day
        t.update({"E0": E0 / 10., "ES0": ES0 / 10., "ET0": ET0 / 10.})

        # Build weather data container from dict 't'
        wdc = WeatherDataContainer(**t)

        # add wdc to dictionary for thisdate
        self._store_WeatherDataContainer(wdc, thisdate)



def main():

    print("Checking AgERA5WeatherDataProvider on default agera5tools setup:")
    wdp = AgERA5WeatherDataProvider(latitude=25.49, longitude=89.45,
                                    startdate=date(2022,1,1), enddate=date(2022,12,31))
    if wdp.missing == 0 and wdp.first_date == date(2022,1,1) and wdp.last_date == date(2022,12,31):
        print(" - Correct HTTP call returning data")
    else:
        print(" - Request has data, but has missing days and/or incorrect start/end")

    try:
        wdp = AgERA5WeatherDataProvider(latitude=50, longitude=89.45,
                                        startdate=date(2022,1,1), enddate=date(2022,12,31))
    except RuntimeError:
        print(" - Out of bounding box error is correct")

    try:
        wdp = AgERA5WeatherDataProvider(latitude=25.49, longitude=89.45,
                                        startdate=date(2015,1,1), enddate=date(2015,12,31))
    except RuntimeError:
        print(" - Out of date range error is correct")



if __name__ == "__main__":
    main()