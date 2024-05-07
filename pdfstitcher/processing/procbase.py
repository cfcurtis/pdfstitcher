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

    def __init__(self, params: dict = {}, doc: Union[Pdf, str, Path] = None) -> None:
        self.p = None
        self._in_doc = None
        self._page_range = None

        self.params = params
        self.load_doc(doc)

        # keep track of whether the unit needs to run
        self.needs_run = True

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
            }

    def load_doc(self, doc: Union[Pdf, str, Path], password: str = "") -> None:
        if isinstance(doc, Pdf):
            self.in_doc = doc
        elif isinstance(doc, str):
            # let the calling scope handle exceptions if it doesn't open
            self.in_doc = Pdf.open(doc, password=password)

    @property
    def page_range(self) -> list:
        return self._page_range

    @page_range.setter
    def page_range(self, page_range: Union[str, list]) -> None:
        if isinstance(page_range, list):
            parsed_range = page_range
        elif isinstance(page_range, str):
            parsed_range = utils.parse_page_range(page_range)
        elif self.page_range is None and self.in_doc is not None:
            print(_("No page range specified, defaulting to all"))
            parsed_range = list(range(1, len(self.in_doc.pages) + 1))
        else:
            parsed_range = []

        if parsed_range != self._page_range:
            self.needs_run = True
            self._page_range = parsed_range

    @abstractmethod
    def run(self, progress_win=None):
        pass
