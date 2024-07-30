# PDFStitcher is a utility to work with PDF sewing patterns.
# Copyright (C) 2021 Charlotte Curtis
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from typing import Union

from pdfstitcher.processing.procbase import ProcessingBase
from pdfstitcher.processing.pagetiler import PageTiler
from pdfstitcher.processing.pagefilter import PageFilter
from pdfstitcher.processing.layerfilter import LayerFilter

from pdfstitcher import utils
from pdfstitcher.utils import Config


class MainProcess(ProcessingBase):
    """
    Class to manage processing units and communicate with GUI.
    """

    def __init__(self, *args, **kw) -> None:
        super().__init__(*args, **kw)

        self.pipeline = {
            "LayerFilter": LayerFilter(),
            "PageTiler": PageTiler(),
            "PageFilter": PageFilter(),
        }
        self.active = {
            "LayerFilter": False,
            "PageTiler": False,
            "PageFilter": False,
        }

    @ProcessingBase.page_range.setter
    def page_range(self, pr: str) -> None:
        """
        Override the page range setter of the base class to update processing units.
        """
        ProcessingBase.page_range.fset(self, pr)

        # Page range validation should only be done for the MainProcess,
        # so we can update the private attribute directly.
        # Also flag the units to run if the page range has changed.
        for unit in self.pipeline.values():
            if unit._page_range != self._page_range:
                unit._page_range = self._page_range
                unit.needs_run = True

    def toggle(self, name: str, active: bool) -> None:
        """
        Switches the active state of the given processing unit.
        """
        if name not in self.pipeline:
            print("Unknown processing unit: {}".format(name))
            return

        self.active[name] = active

        # Enforce mutual exclusivity between PageTiler and PageFilter
        if name == "PageTiler":
            self.active["PageFilter"] = not active

        elif name == "PageFilter":
            self.active["PageTiler"] = not active

    def set_params(self, name: str, params: dict) -> bool:
        """
        Updates the pipeline with the given parameters.
        Returns true if successfully added or updated.
        """
        if name not in self.pipeline:
            print("Unknown processing unit: {}".format(name))
            return False

        self.pipeline[name].params = params

    def run(self, progress_win=None) -> bool:
        """
        Pass the document through the pipeline. Returns true if successful.
        """
        if not self.pipeline:
            return False

        # First, go through the pages and normalize the various boxes
        for page in self.in_doc.pages:
            utils.normalize_boxes(page)

        # Pass the document from one unit to the next
        output = self.in_doc
        for name in filter(self.active.get, self.active):
            unit = self.pipeline[name]
            unit.in_doc = output

            # run the unit if necessary and check if cancelled
            if unit.needs_run and not unit.run(progress_win=progress_win):
                return False

            output = unit.out_doc

        # update the final output
        self.out_doc = output
        self.needs_run = False
        return True

    def save(self, out_path: str) -> None:
        if self.out_doc is None:
            return

        # handle exceptions in the calling scope
        self.out_doc.save(out_path)
