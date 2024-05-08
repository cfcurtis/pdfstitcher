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
import packaging

__version__ = importlib.metadata.version("pdfstitcher")


def is_flatpak() -> bool:
    """
    Returns True if the app is running in a Flatpak sandbox.
    """
    return "FLATPAK_ID" in os.environ


def update_available() -> str:
    """
    Checks whether there's a new release of PDFStitcher.
    Returns a string containing the latest version if there's a new one,
    or None if the current version is up to date.
    """
    response = requests.get(utils.PYPI_HOME + "/json")
    if not response.ok:
        raise requests.HTTPError(response.status_code, response.url, response.reason)

    pypi_version = response.json()["info"]["version"]

    if packaging.version.parse(pypi_version) > packaging.version.parse(__version__):
        return pypi_version
    else:
        return None


def get_download_url() -> str:
    """
    Returns the platform-specific download link for the latest release.
    """
    gh_prefix = utils.GIT_HOME + "/releases/latest/download/"
    if sys.platform == "win32":
        return gh_prefix + "pdfstitcher.exe"
    elif sys.platform == "darwin":
        import platform

        if platform.machine() == "arm64":
            return gh_prefix + "PDFStitcher-InstallerARM64.dmg"
        else:
            return gh_prefix + "PDFStitcher-InstallerX64.dmg"
    else:
        return utils.FLATHUB_HOME
