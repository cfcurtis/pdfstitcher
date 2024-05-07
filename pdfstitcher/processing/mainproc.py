# PDFStitcher is a utility to work with PDF sewing patterns.
# Copyright (C) 2021 Charlotte Curtis
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

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
        super().__init__(self, *args, **kw)
        self.pipeline = []

    def add_unit(self, name: str, params: dict) -> None:
        """
        Build the pipeline with the given units and parameters.
        """
        if name == "PageTiler":
            self.pipeline.append(PageTiler(params))
        elif name == "PageFilter":
            self.pipeline.append(PageFilter(params))
        elif name == "LayerFilter":
            self.pipeline.append(LayerFilter(params))
        else:
            print(_("Unknown processing unit: {}".format(name)))

    def run(self, progress_win=None) -> bool:
        """
        Pass the document through the pipeline.
        """
        if not self.pipeline:
            return False

        # First, go through the pages and normalize the various boxes
        for page in self.in_doc.pages:
            utils.normalize_boxes(page)

        # Pass the document from one unit to the next
        output = self.in_doc
        for unit in self.pipeline:
            unit.in_doc = output
            try:
                if unit.run(progress_win):
                    output = unit.out_doc
                else:
                    return False
            except Exception as e:
                print(f"Error in {unit.__class__.__name__}: {e}")
                return False

        # update the final output
        self.out_doc = output
        return True

    def save(self, out_path: str) -> bool:
        if self.out_doc is None:
            return False

        try:
            self.out_doc.save(out_path)
        except Exception as e:
            print(f"Error saving document: {e}")
            return False

        return True
