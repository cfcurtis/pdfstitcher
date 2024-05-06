# PDFStitcher is a utility to work with PDF sewing patterns.
# Copyright (C) 2021 Charlotte Curtis
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from abc import ABC, abstractmethod
from pikepdf import Pdf
from pdfstitcher import utils


class ProcessingBase(ABC):
    """
    Base class for processing units.
    """

    def __init__(self, in_doc: Pdf = None) -> None:
        self.in_doc = in_doc

    @property
    def page_range(self) -> list:
        return self.page_range

    @page_range.setter
    def page_range(self, page_range: str | list) -> None:
        if isinstance(page_range, str):
            self.page_range = utils.parse_page_range(page_range)
        elif isinstance(page_range, list):
            self.page_range = page_range

        if self.page_range is None and self.in_doc is not None:
            print(_("No page range specified, defaulting to all"))
            self.page_range = list(range(1, len(self.in_doc.pages) + 1))

    @abstractmethod
    def run(self, progress_win=None):
        pass
