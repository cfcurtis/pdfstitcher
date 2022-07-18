# PDFStitcher is a utility to work with PDF sewing patterns.
# Copyright (C) 2021 Charlotte Curtis
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import pikepdf
import pdfstitcher.utils as utils
from pdfstitcher.utils import Config


class PageFilter:
    """
    Simple class to pass through the selected pages
    """

    def __init__(self, doc=None):
        self.in_doc = doc
        self.page_range = []
        self.margin = None

    def run(self):
        """
        The main method to run the filter.
        """
        # not sure what this means, so just return the pdf as is
        if len(self.page_range) == 0:
            return self.in_doc

        # otherwise, copy the selected pages to a new document
        new_doc = utils.init_new_doc(self.in_doc)

        for p in self.page_range:
            user_unit = 1
            if p == 0:
                mbox = self.in_doc.pages[-1].MediaBox
                new_doc.add_blank_page(page_size=(mbox[2], mbox[3]))
            else:
                new_doc.pages.extend([self.in_doc.pages[p - 1]])

            if "/UserUnit" in self.in_doc.pages[-1].keys():
                new_doc.pages[-1].UserUnit = self.in_doc.pages[-1].UserUnit
                user_unit = self.in_doc.pages[-1].UserUnit

            if self.margin:
                # if margins were added, expand the new page boxes
                margin = Config.general["units"].units_to_px(self.margin / user_unit)
                new_page = new_doc.pages[-1]
                media_box = [
                    float(new_page.MediaBox[0]) - margin,
                    float(new_page.MediaBox[1]) - margin,
                    float(new_page.MediaBox[2]) + margin,
                    float(new_page.MediaBox[3]) + margin,
                ]
                utils.print_media_box(media_box)

                new_page.MediaBox = media_box
                new_page.CropBox = media_box

        return new_doc
