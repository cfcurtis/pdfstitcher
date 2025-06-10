# PDFStitcher is a utility to work with PDF sewing patterns.
# Copyright (C) 2021 Charlotte Curtis
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from abc import ABC, abstractmethod
from pikepdf import Pdf
from pdfstitcher import utils
from pathlib import Path
from typing import Union


class ProcessingBase(ABC):
    """
    Base class for processing units.
    """

    def __init__(
        self, params: dict = {}, doc: Union[Pdf, str, Path] = None, warning_win=None
    ) -> None:
        self.p = None
        self._in_doc = None
        self._page_range = None

        self.params = params
        self.load_doc(doc)

        # keep track of whether the unit needs to run
        self.needs_run = True
        self.warning_win = warning_win

    # ---------------------------------------------------------------------
    # Property getters and setters
    # ---------------------------------------------------------------------

    @property
    def params(self) -> dict:
        return self.p

    @params.setter
    def params(self, params: dict) -> None:
        if self.p == params:
            return

        self.p = params
        self.needs_run = True

    @property
    def in_doc(self) -> Pdf:
        return self._in_doc

    @in_doc.setter
    def in_doc(self, doc: Pdf) -> None:
        if self.in_doc == doc:
            return

        self.needs_run = True
        self._in_doc = doc

        # update the document info
        with self.in_doc.open_metadata() as xmp:
            self.doc_info = {
                "title": xmp["dc:title"] if "dc:title" in xmp else Path(self.in_doc.filename).stem,
                "author": xmp["dc:creator"] if "dc:creator" in xmp else "Unknown",
                "n_pages": len(self.in_doc.pages),
                "layers": utils.get_layer_names(self.in_doc),
                "first_page_dims": utils.get_page_dims(self.in_doc.pages[0]),
            }

        if not self.page_range:
            self._validate_page_range()

    @property
    def page_range(self) -> list:
        """Returns list of page numbers for backward compatibility"""
        if self._page_range is None:
            return None
        return [p["page"] if isinstance(p, dict) else p for p in self._page_range]

    @property
    def page_range_with_rotation(self) -> list:
        """Returns full page range with rotation info"""
        if self._page_range is None:
            return None
        # Ensure all entries are in dict format
        result = []
        for p in self._page_range:
            if isinstance(p, dict):
                result.append(p)
            else:
                result.append({"page": p, "rotation": 0})
        return result

    @page_range.setter
    def page_range(self, pr: Union[str, list]) -> None:
        if isinstance(pr, str):
            # Use the new parser that supports rotation
            parsed_range = utils.parse_page_range_with_rotation(pr)
        elif isinstance(pr, list):
            # Handle both old format (list of ints) and new format (list of dicts)
            if pr and all(isinstance(p, int) for p in pr):
                # Convert old format to new format
                parsed_range = [{"page": p, "rotation": 0} for p in pr]
            else:
                parsed_range = pr
        elif self.page_range is None and self.in_doc is not None:
            print(_("No page range specified, defaulting to all"))
            parsed_range = [{"page": p, "rotation": 0} for p in range(1, len(self.in_doc.pages) + 1)]
        else:
            parsed_range = []

        if parsed_range != self._page_range:
            self.needs_run = True
            self._page_range = parsed_range
            self._validate_page_range()

    # ---------------------------------------------------------------------
    # Methods
    # ---------------------------------------------------------------------

    def _validate_page_range(self) -> None:
        """
        Compares the page range to the number of pages in the document.
        If any pages are out of range, removes them and warns the user.
        """
        if not self._page_range or not self.in_doc:
            return

        n_pages = len(self.in_doc.pages)
        no_good = []
        
        for i, p in enumerate(self._page_range):
            # Handle both dict and int formats
            page_num = p["page"] if isinstance(p, dict) else p
            if page_num < 0 or page_num > n_pages:
                no_good.append(i)
                print(_("Page {} is out of range. Removing from page list.".format(page_num)))
        
        # Remove invalid pages in reverse order to maintain indices
        for i in reversed(no_good):
            self._page_range.pop(i)

    def _warn(self, message: str) -> None:
        """
        Displays a warning message to the user.
        Assumes either a wx.MessageDialog or console output.
        """
        if self.warning_win:
            self.warning_win.SetMessage(message)
            self.warning_win.ShowModal()
        else:
            print(message)

    def load_doc(self, doc: Union[Pdf, str, Path], password: str = "") -> None:
        if isinstance(doc, Pdf):
            self.in_doc = doc
        elif isinstance(doc, str):
            # let the calling scope handle exceptions if it doesn't open
            self.in_doc = Pdf.open(doc, password=password)

    @abstractmethod
    def run(self, progress_win=None):
        pass
