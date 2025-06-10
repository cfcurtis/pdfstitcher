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
        with an optional margin added to each and applies per-page rotation if specified.
        """
        # copy the selected pages to a new document
        self.out_doc = utils.init_new_doc(self.in_doc)

        for page_info in self.page_range_with_rotation:
            p = page_info["page"]
            user_rotation = page_info["rotation"]
            user_unit = 1

            if p == 0:
                # make the new page the same size as the previous one
                if len(self.out_doc.pages) > 0:
                    mbox = self.out_doc.pages[-1].MediaBox
                else:
                    mbox = self._in_doc.pages[0].MediaBox
                self.out_doc.add_blank_page(
                    page_size=(abs(mbox[2] - mbox[0]), abs(mbox[3] - mbox[1]))
                )
            else:
                self.out_doc.pages.extend([self.in_doc.pages[p - 1]])

            # grab a convenient handle to the new page we just added
            new_page = self.out_doc.pages[-1]

            if "/UserUnit" in self.in_doc.pages[p - 1].keys():
                user_unit = float(self.in_doc.pages[p - 1].UserUnit)

            self._apply_rotation(new_page, self.in_doc.pages[p - 1], user_rotation)

            if self.p["margin"]:
                # if margins were added, expand the new page boxes
                margin = Config.general["units"].units_to_pts(self.p["margin"], user_unit)
                media_box = [
                    float(new_page.MediaBox[0]) - margin,
                    float(new_page.MediaBox[1]) - margin,
                    float(new_page.MediaBox[2]) + margin,
                    float(new_page.MediaBox[3]) + margin,
                ]
                print(_("Page" + f" {p}: "), end="")

                size_warning = utils.print_media_box(media_box, user_unit)
                if size_warning:
                    self._warn(size_warning)

                new_page.MediaBox = media_box
                new_page.CropBox = media_box

        return self.out_doc

    def _apply_rotation(
        self, new_page: pikepdf.Page, og_page: pikepdf.Page, user_rotation: utils.SW_ROTATION
    ) -> None:
        """
        Rotates the page relative to the user-perceived original rotation.
        We need to fetch rotation from the original page in case of duplicate page copies.
        """

        rotation = og_page.Rotate if "/Rotate" in og_page.keys() else self.doc_info["root_rotation"]
        if user_rotation == utils.SW_ROTATION.UNSET:
            new_page["/Rotate"] = rotation
        else:
            rotation += user_rotation.value % 360
            new_page["/Rotate"] = rotation
