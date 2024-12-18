What's new
==========

Version 2.1
-----------

Version 2.1 has two major updates:

- It was migrated to the new CDS toolbox and the CDS API.
- The local setup now prefers to use `DuckDB`_ instead of `SQLite`_.

DuckDB integrates very well with pandas dataframes which allows to dump
dataframes directly towards DuckDB tables. This avoids the overhead of going through
SQL INSERT() statements or through intermediate CSV files for database loading.
In fact, this works so well that duckdb is now the default setup. If there is
no specific need for a relational client/server database (like MySQL, PostgreSQL),
I suggest to stay with DuckDB as it performs extremely well and simplifies things a lot.

.. _DuckDB: https://duckdb.org/
.. _SQLite: https://www.sqlite.org/index.html

Version 2.0
-----------

Version 2.0 of AgERA5tools is completely restructured and can be used to set up
a local mirror of AgERA5. The software will automatically download the requested AgERA5
data from the `Copernicus Climate Data Store`_, store it in a relational database
and make it available through a http API. A call to this API can be used to
retrieve a time-series of AgERA5 data as JSON. This will allow many applications
that require time-series data to efficiently query agERA5 data.

.. _Copernicus Climate Data Store: https://cds.climate.copernicus.eu/#!/home