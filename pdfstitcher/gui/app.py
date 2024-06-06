#! /usr/bin/env python3

# PDFStitcher is a utility to work with PDF sewing patterns.
# Copyright (C) 2021 Charlotte Curtis
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from pdfstitcher import utils
from pdfstitcher.utils import Config
from pdfstitcher.gui.main_frame import main as launch_gui


def main():
    """
    Configure and run the app.
    """
    Config.load()
    language_warning = utils.setup_locale(Config.general["language"])

    if language_warning:
        print(language_warning)

    launch_gui(language_warning)


if __name__ == "__main__":
    main()
