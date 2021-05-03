from pathlib import Path

import xarray as xr


def dump_grid():
    """Exports the AgeRA5 grid that is embedded in the agera5tools packages

    :return: a dataframe with the grid definition
    """
    agera5_grid = Path(__file__).parent / "grid_elevation_landfraction.nc"
    ds = xr.open_dataset(agera5_grid)
    df = ds.to_dataframe()
    df = df[df.idgrid_era5 != -999]
    df.reset_index(inplace=True)
    df["lat_centre"] = df.lat + 0.05
    df["lon_centre"] = df.lon + 0.05
    ix = df.land_fraction == 0
    df.loc[ix, "elevation"] = 0.

    return df
