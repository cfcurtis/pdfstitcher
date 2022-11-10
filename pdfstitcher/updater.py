# PDFStitcher is a utility to work with PDF sewing patterns.
# Copyright (C) 2021 Charlotte Curtis
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import sys
import importlib.metadata
import requests
from pdfstitcher import utils
import os

__version__ = importlib.metadata.version("pdfstitcher")

def is_flatpak() -> bool:
    """
    Returns True if the app is running in a Flatpak sandbox.
    """
    return "FLATPAK_ID" in os.environ

def update_available():
    """
    Checks whether there's a new release of PDFStitcher.
    """ 
    response = requests.get(utils.PYPI_HOME + "/json")
    if not response.ok:
        raise requests.HTTPError(response.status_code, response.url, response.reason)

    pypi_version = response.json()["info"]["version"]

    current = [int(num) for num in __version__.split(".")]
    pypi = [int(num) for num in pypi_version.split(".")]

    if len(current) == 2:
        current.append(0)
    if len(pypi) == 2:
        pypi.append(0)

    if any(pypi[i] > current[i] for i in range(3)):
        return pypi_version
    else:
        return None


def get_download_url():
    """
    Returns the platform-specific download link for the latest release.
    """
    gh_prefix = utils.GIT_HOME + "/releases/latest/download/"
    if sys.platform == "win32":
        return gh_prefix + "pdfstitcher.exe"
    elif sys.platform == "darwin":
        return gh_prefix + "PDFStitcher-Installer.dmg"
    else:
        return utils.FLATHUB_HOME
