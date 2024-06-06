# PDFStitcher is a utility to work with PDF sewing patterns.
# Copyright (C) 2021 Charlotte Curtis
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import pikepdf
import pdfstitcher.utils as utils
from pdfstitcher.utils import Config
from pdfstitcher.processing.procbase import ProcessingBase


class PageFilter(ProcessingBase):
    """
    Simple class to pass through the selected pages
    """

    def run(self, **kwargs) -> None:
        """
        The main method to run the filter. This one just filters to a selected page range
        with an optional margin added to each.
        """
        # copy the selected pages to a new document
        self.out_doc = utils.init_new_doc(self.in_doc)

        for p in self.page_range:
            user_unit = 1
            if p == 0:
                mbox = self.in_doc.pages[-1].MediaBox
                self.out_doc.add_blank_page(page_size=(mbox[2], mbox[3]))
            else:
                self.out_doc.pages.extend([self.in_doc.pages[p - 1]])

            if "/UserUnit" in self.in_doc.pages[p - 1].keys():
                user_unit = float(self.in_doc.pages[p - 1].UserUnit)

            if self.p["margin"]:
                # if margins were added, expand the new page boxes
                margin = Config.general["units"].units_to_pts(self.p["margin"], user_unit)
                media_box = [
                    float(self.out_doc.pages[-1].MediaBox[0]) - margin,
                    float(self.out_doc.pages[-1].MediaBox[1]) - margin,
                    float(self.out_doc.pages[-1].MediaBox[2]) + margin,
                    float(self.out_doc.pages[-1].MediaBox[3]) + margin,
                ]
                print(_("Page" + f" {p}: "), end="")
                utils.print_media_box(media_box, user_unit)

                self.out_doc.pages[-1].MediaBox = media_box
                self.out_doc.pages[-1].CropBox = media_box

        return self.out_doc
