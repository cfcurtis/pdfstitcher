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
            rotation = page_info["rotation"]
            user_unit = 1
            
            if p == 0:
                mbox = self.in_doc.pages[-1].MediaBox
                self.out_doc.add_blank_page(page_size=(mbox[2], mbox[3]))
            else:
                self.out_doc.pages.extend([self.in_doc.pages[p - 1]])
                if "/UserUnit" in self.in_doc.pages[p - 1].keys():
                    user_unit = float(self.in_doc.pages[p - 1].UserUnit)

            # Apply rotation if specified
            if rotation != 0:
                self._apply_rotation_to_page(self.out_doc.pages[-1], rotation, user_unit)

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

                size_warning = utils.print_media_box(media_box, user_unit)
                if size_warning:
                    self._warn(size_warning)

                self.out_doc.pages[-1].MediaBox = media_box
                self.out_doc.pages[-1].CropBox = media_box

        return self.out_doc

    def _apply_rotation_to_page(self, page: pikepdf.Page, rotation_degrees: int, user_unit: float) -> None:
        """
        Apply rotation to a page by converting it to XObject and applying transformation matrix.
        """
        # Convert degrees to SW_ROTATION enum
        sw_rotation = utils.degrees_to_sw_rotation(rotation_degrees)
        
        # Get rotation matrix
        rotation_matrix = utils.get_rotation_matrix(sw_rotation)
        
        # Get page dimensions
        media_box = page.MediaBox
        width = float(media_box[2] - media_box[0])
        height = float(media_box[3] - media_box[1])
        
        # Calculate new dimensions after rotation
        new_width, new_height = utils.apply_rotation_to_dimensions(width, height, sw_rotation)
        
        # Convert page to XObject
        xobj = page.as_form_xobject()
        
        # Calculate translation based on rotation
        from pdfstitcher.processing.pagetiler import SW_ROTATION
        if sw_rotation == SW_ROTATION.CLOCKWISE:
            tx, ty = new_width, 0
        elif sw_rotation == SW_ROTATION.COUNTERCLOCKWISE:
            tx, ty = 0, new_height
        elif sw_rotation == SW_ROTATION.TURNAROUND:
            tx, ty = new_width, new_height
        else:
            tx, ty = 0, 0
        
        # Create transformation matrix (rotation + translation)
        cm_matrix = rotation_matrix + [tx, ty]
        
        # Create new page content with transformation
        cm_op = pikepdf.Stream(page._f, b" ".join([str(val).encode() for val in cm_matrix]) + b" cm")
        do_op = pikepdf.Stream(page._f, b"/Page Do")
        q_op = pikepdf.Stream(page._f, b"q")
        Q_op = pikepdf.Stream(page._f, b"Q")
        
        # Replace page content
        page.Contents = pikepdf.Array([q_op, cm_op, do_op, Q_op])
        page.Resources["/XObject"] = pikepdf.Dictionary({"/Page": xobj})
        
        # Update MediaBox and CropBox with new dimensions
        page.MediaBox = [0, 0, new_width, new_height]
        page.CropBox = [0, 0, new_width, new_height]
