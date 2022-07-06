# PDFStitcher is a utility to work with PDF sewing patterns.
# Copyright (C) 2021 Charlotte Curtis
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from appdirs import user_config_dir
import yaml
from pdfstitcher.utils import UNITS
from pathlib import Path


general = {
    "units": UNITS.INCHES,
    "language": None,
    "check_updates": True,
    "open_dir": None,
    "save_dir": None,
    "margin": "0",
}
line_props = {
    "colour": {"enable": True, "value": (0, 0, 0), "fill": False},
    "thickness": {"enable": True, "value": "4", "units": UNITS.POINTS},
    "style": {"enable": True, "value": 0}
}

combo = {"general": general, "line_props": line_props}
config_file = Path(user_config_dir("pdfstitcher")) / "config.yml"

def load():
    """
    Defines defaults, then loads configuration file to make any changes.
    """
    try:
        with open(config_file, "r") as f:
            prefs = yaml.safe_load(f)
    except OSError:
        # write the defaults for next time
        save()
        prefs = {}
    
    try:
        # merge the defaults with the loaded prefs
        for key in prefs["general"].keys():
            general[key] = prefs["general"][key]
        for key in prefs["line_props"].keys():
            line_props[key] = prefs["line_props"][key]
    except KeyError:
        pass


def save():
    """
    Save the current configuration for next time.
    """
    try:
        with open(config_file, "w") as f:
            yaml.dump(combo, f)
    except OSError:
        print("Could not save configuration file.")