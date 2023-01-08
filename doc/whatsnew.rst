What's new
==========

Version 2.0
-----------

Version 2.0 of AgERA5tools is completely restructured and can be used to set up
a local mirror of AgERA5. The software will automatically download the requested AgERA5
data from the `Copernicus Climate Data Store`_, store it in a relational database
and make it available through a http API. A call to this API can be used to
retrieve a time-series of AgERA5 data as JSON. This will allow many applications
that require time-series data to efficiently query agERA5 data.

.. _Copernicus Climate Data Store: https://cds.climate.copernicus.eu/#!/home