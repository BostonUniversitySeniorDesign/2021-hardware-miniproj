#!/usr/bin/env python3

"""
plots data collected by wifi_scan.py

Typically run this on your laptop.
"""

from __future__ import annotations
import argparse
from pathlib import Path
import json
from datetime import datetime

import numpy as np
import pandas
import xarray
from matplotlib.pyplot import show

MAX_SSID = 100
FMT = "%Y-%m-%dT%H_%M_%S"


def load(filename) -> xarray.DataArray:
    """
    Loads data collected by wifi_scan.py
    """

    filename = Path(filename).expanduser()

    ddata = json.loads(filename.read_text())

    data = xarray.DataArray(
        dims=["time", "cell", "params"],
        coords=[
            (
                "time",
                pandas.to_datetime(list(ddata.keys()), format=FMT),
            ),
            ("cell", range(MAX_SSID)),
            ("params", ["essid", "bssid", "dbm"]),
        ],
        data=np.empty((len(ddata), MAX_SSID, 3), dtype="<U32"),
    )

    for time, bssids in ddata.items():
        for i, (bssid, v) in enumerate(bssids.items()):
            t = datetime.strptime(time, FMT)
            data.loc[t][i] = [v["essid"], bssid, v["signal_level_dBm"]]

    return data


def select(data: xarray.DataArray, max_seen_frac) -> xarray.DataArray:
    """
    Removes stationary stations from data, based on histogram of SSID.


    1. get a list of all the BSSIDs seen across time
    2. get SSIDs that are not seen persistently vs. time

    The code below is not necessarily the most efficient way to select the data.
    """

    df = data.loc[:, :, "bssid"].to_dataframe("ssid")
    bssid_counts = df.value_counts()
    Ntime = len(data.time)
    bssid_seen_frac = bssid_counts / Ntime

    i_mobile = (bssid_seen_frac < max_seen_frac).droplevel(0)
    mobile_bssids = i_mobile[i_mobile].index.values

    # %% iterate over time
    Nmobile = xarray.DataArray(
        dims=["time"],
        coords=[("time", data.time.data)],
        data=np.zeros(len(data.time), dtype=int),
    )
    for dt in data:
        Nmobile.loc[dt.time] = dt.loc[:, "bssid"].isin(mobile_bssids).sum()

    return Nmobile


if __name__ == "__main__":
    p = argparse.ArgumentParser(
        description="Plots data collected by wifi_scan.py"
    )
    p.add_argument("filename", help="JSON file containing wifi_scan.py data")
    p.add_argument(
        "fixed_frac",
        help="fraction of time device must be detected to be declared stationary.",
        type=float,
        default=0.5,
        nargs="?",
    )
    args = p.parse_args()

    data = load(args.filename)
    Nmobile = select(data, max_seen_frac=args.fixed_frac)

    Nmobile.plot()

    show()
