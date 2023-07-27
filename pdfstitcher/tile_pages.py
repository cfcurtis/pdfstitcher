# PDFStitcher is a utility to work with PDF sewing patterns.
# Copyright (C) 2021 Charlotte Curtis
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import pikepdf
from pikepdf import _cpphelpers
from enum import IntEnum
import argparse
import sys
import math
import copy
import pdfstitcher.utils as utils
from pdfstitcher.utils import Config


class SW_ROTATION(IntEnum):
    NONE = 0
    CLOCKWISE = 1
    COUNTERCLOCKWISE = 2
    TURNAROUND = 3


class SW_ALIGN_V(IntEnum):
    BOTTOM = 0
    MID = 1
    TOP = 2


class SW_ALIGN_H(IntEnum):
    LEFT = 0
    MID = 1
    RIGHT = 2


class PageTiler:
    def __init__(
        self,
        in_doc=None,
        page_range=None,
        trim=[0, 0, 0, 0],
        margin=0,
        rotation=SW_ROTATION.NONE,
        actually_trim=False,
        override_trim=False,
        col_major=False,
        right_to_left=False,
        bottom_to_top=False,
        rows=None,
        cols=None,
        target_width=None,
        target_height=None,
        vertical_align=SW_ALIGN_V.BOTTOM,
        horizontal_align=SW_ALIGN_H.LEFT,
    ):
        self.in_doc = in_doc
        self.user_unit = 1

        if isinstance(page_range, str):
            self.page_range = utils.parse_page_range(page_range)
        elif isinstance(page_range, (list, tuple)):
            self.page_range = page_range
        else:
            self.page_range = []

        self.trim = trim
        self.margin = margin
        self.rotation = rotation
        self.actually_trim = actually_trim
        self.override_trim = override_trim

        self.col_major = col_major
        self.right_to_left = right_to_left
        self.bottom_to_top = bottom_to_top

        self.rows = rows
        self.cols = cols

        # Optional target width and height for scaling and placing pages
        self.target_height = target_height
        self.target_width = target_width

        if self.target_height:
            self.target_height = Config.general["units"].units_to_px(self.target_height)
        if self.target_width:
            self.target_width = Config.general["units"].units_to_px(self.target_width)

        # Optional vertical and horizontal alignment in case pages are non-uniform in size
        self.vertical_align = vertical_align
        self.horizontal_align = horizontal_align

    @property
    def trim(self):
        return self._trim

    @trim.setter
    def trim(self, trim):
        if len(trim) == 1:
            self._trim = [trim[0], trim[0], trim[0], trim[0]]
        elif len(trim) == 2:
            self._trim = [trim[0], trim[0], trim[1], trim[1]]
        elif len(trim) == 4:
            self._trim = trim
        else:
            print(_("Invalid trim value specified, ignoring"))
            self._trim = [0, 0, 0, 0]

    def show_options(self):
        # convert the margin and trim options into pixels
        # translation_note: in = "inches", cm = "centimetres"
        rotstr = _("None")

        if self.rotation == SW_ROTATION.CLOCKWISE:
            rotstr = _("Clockwise")
        elif self.rotation == SW_ROTATION.COUNTERCLOCKWISE:
            rotstr = _("Counterclockwise")
        elif self.rotation == SW_ROTATION.TURNAROUND:
            # translation_note: Rotates 180 degrees. Not exposed in PDFStitcher GUI
            rotstr = _("Turn Around")

        orderstr = _("Rows then columns")
        if self.col_major:
            orderstr = _("Columns then rows")

        lrstr = _("Left to right")
        if self.right_to_left:
            lrstr = _("Right to left")

        btstr = _("Top to bottom")
        if self.bottom_to_top:
            btstr = _("Bottom to top")

        if self.vertical_align is SW_ALIGN_V.BOTTOM:
            alvstr = _("Bottom")
        elif self.vertical_align is SW_ALIGN_V.MID:
            alvstr = _("Middle")
        elif self.vertical_align is SW_ALIGN_V.TOP:
            alvstr = _("Top")

        if self.horizontal_align is SW_ALIGN_H.LEFT:
            alhstr = _("Left")
        elif self.horizontal_align is SW_ALIGN_H.MID:
            alhstr = _("Middle")
        elif self.horizontal_align is SW_ALIGN_H.RIGHT:
            alhstr = _("Right")

        print(_("Tiling with {} rows and {} columns").format(self.rows, self.cols))
        print(_("Options") + ":")
        print("    " + _("Margins") + ": {} {}".format(self.margin, Config.general["units"]))
        print("    " + _("Trim") + ": {} {}".format(self.trim, Config.general["units"]))
        print("    " + _("Rotation") + ": {}".format(rotstr))
        print("    " + _("Page order") + ": {}, {}, {}".format(orderstr, lrstr, btstr))
        print("    " + _("Vertical alignment") + ": {}".format(alvstr))
        print("    " + _("Horizontal alignment") + ": {}".format(alhstr))

    def build_pagelist(self, new_doc: pikepdf.Pdf, trim: list) -> tuple:
        """
        Loops through the pages and constructs the list of pages, their length/width, and XObjects.
        Returns a tuple containing content_dict, pw, ph, page_names.
        Still too much going on in this function!
        """
        # define the dictionary to store xobjects and the corresponding names (e.g. MC0, MC1, etc.)
        content_dict = pikepdf.Dictionary({})
        page_names = []
        pw = []
        ph = []

        page_count = len(self.in_doc.pages)
        # initialize the width/height indices based on page rotation
        page_rot = 0

        if "/Rotate" in self.in_doc.Root.Pages.keys():
            page_rot = self.in_doc.Root.Pages.Rotate % 360

        for p in self.page_range:
            if p > 0:
                break

        # get a pointer to the reference page and parse out the width and height
        ref_page = self.in_doc.pages[p - 1]
        ref_width, ref_height = utils.get_page_dims(ref_page, page_rot, self.user_unit)

        different_size = set()

        for p in self.page_range:
            if p > page_count:
                print(_("Only {} pages in document, skipping {}").format(page_count, p))
                continue

            if p > 0:
                pagekey = f"/Page{p}"

                # Check if it's already been copied (in case of duplicate page numbers)
                if pagekey not in content_dict.keys():
                    # get a reference to the input document page. DO NOT MODIFY.
                    in_doc_page = self.in_doc.pages[p - 1]
                    new_page = copy.copy(in_doc_page)

                    if "/Rotate" in in_doc_page.keys():
                        page_rot = in_doc_page.Rotate % 360

                    if self.override_trim:
                        new_page.TrimBox = copy.copy(in_doc_page.MediaBox)

                    # set the trim box to cut off content if requested
                    if self.actually_trim:
                        # things get tricky if there's rotation, because the user sees top/bottom as right/left
                        # trim: left, right, top, bottom as defined visually
                        # trimbox: left, bottom, right, top (absolute coordinates)
                        rtrim = [trim[0], trim[3], trim[1], trim[2]]
                        if page_rot == 90:
                            rtrim = [trim[2], trim[0], trim[3], trim[1]]
                        elif page_rot == 180:
                            rtrim = [trim[3], trim[0], trim[2], trim[1]]
                        elif page_rot == 270:
                            rtrim = [trim[3], trim[1], trim[2], trim[0]]

                        # lowercase trimbox returns TrimBox if it exists, MediaBox otherwise
                        in_trim = [float(t) for t in in_doc_page.trimbox]
                        new_page.TrimBox = [
                            in_trim[0] + rtrim[0],
                            in_trim[1] + rtrim[1],
                            in_trim[2] - rtrim[2],
                            in_trim[3] - rtrim[3],
                        ]

                p_width, p_height = utils.get_page_dims(in_doc_page, page_rot, self.user_unit)
                pw.append(p_width)
                ph.append(p_height)
                page_names.append(pagekey)

                if abs(p_width - ref_width) > 1 or abs(p_height - ref_height) > 1:
                    different_size.add(p)

                # update the reference handles to be the current page
                ref_width = p_width
                ref_height = p_height

                # magic sauce to copy the info to the new document as an XOBject
                content_dict[pagekey] = new_doc.copy_foreign(new_page.as_form_xobject())

                # scale the form xobject by the target user unit
                if self.user_unit != 1:
                    if "/Matrix" in content_dict[pagekey].keys():
                        xobj_matrix = pikepdf.PdfMatrix(content_dict[pagekey].Matrix)
                    else:
                        xobj_matrix = pikepdf.PdfMatrix.identity()
                    content_dict[pagekey].Matrix = xobj_matrix.scaled(
                        1 / self.user_unit, 1 / self.user_unit
                    ).shorthand

            else:
                # blank page, use the reference for sizes and such
                page_names.append(None)
                pw.append(ref_width)
                ph.append(ref_height)

        if len(different_size) > 0:
            print(
                _("Warning: The pages {} have a different size than the page before").format(
                    different_size
                )
            )

        return content_dict, pw, ph, page_names

    def adjust_trim_order(self, px_trim: list) -> None:
        """
        Rearranges the trim order based on page rotation.
        """
        # swap the trim order
        # default: left,right,top,bottom
        order = [0, 1, 2, 3]

        if self.rotation == SW_ROTATION.CLOCKWISE:
            order = [3, 2, 0, 1]
        if self.rotation == SW_ROTATION.COUNTERCLOCKWISE:
            order = [2, 3, 1, 0]
        if self.rotation == SW_ROTATION.TURNAROUND:
            order = [1, 0, 3, 2]

        px_trim = [px_trim[o] for o in order]

    def compute_target_size(self, n_tiles: int, pw: list, ph: list, trim: list) -> tuple:
        """
        Find the grid that contains the maximum page size for each row/col.
        Returns the grid dimensions as a tuple of two lists.
        """
        col_width = [0] * self.cols
        row_height = [0] * self.rows

        if self.col_major:
            for c in range(self.cols):
                col_width[c] = max(pw[c * self.rows : c * self.rows + self.rows]) - (
                    trim[0] + trim[1]
                )

            for r in range(self.rows):
                row_height[r] = max(ph[r : n_tiles : self.cols]) - (trim[2] + trim[3])
        else:
            for r in range(self.rows):
                row_height[r] = max(ph[r * self.cols : r * self.cols + self.cols]) - (
                    trim[2] + trim[3]
                )

            for c in range(self.cols):
                col_width[c] = max(pw[c : n_tiles : self.rows]) - (trim[0] + trim[1])

        if self.right_to_left:
            col_width.reverse()

        if self.bottom_to_top:
            row_height.reverse()

        return col_width, row_height

    def calc_rows_cols(self, n_tiles: int) -> bool:
        """
        Calculate the number of rows/columns requested based on the number of pages to tile.
        Returns True if the result is valid, False otherwise.
        """
        if self.cols is not None and self.cols > 0:
            self.rows = math.ceil(n_tiles / self.cols)
            if self.rows == 1 and self.cols > n_tiles:
                print(
                    _("Warning: requested {} columns, but there are only {} pages").format(
                        self.cols, n_tiles
                    )
                )
                self.cols = n_tiles

        elif self.rows is not None and self.rows > 0:
            self.cols = math.ceil(n_tiles / self.rows)
            if self.cols == 1 and self.rows > n_tiles:
                print(
                    _("Warning: requested {} rows, but there are only {} pages").format(
                        self.rows, n_tiles
                    )
                )
                self.rows = n_tiles
        else:
            # try for square
            self.cols = math.ceil(math.sqrt(n_tiles))
            self.rows = math.ceil(n_tiles / self.cols)

        # Make sure there are no empty columns or rows
        if self.col_major:
            return self.cols * self.rows - n_tiles < self.rows
        else:
            return self.cols * self.rows - n_tiles < self.cols

    def grid_position(self, tile_i: int) -> tuple:
        """Determines the placement of the tile in the grid, returning a tuple of (row, col)"""
        if self.col_major:
            c = math.floor(tile_i / self.rows)
            r = tile_i % self.rows
        else:
            r = math.floor(tile_i / self.cols)
            c = tile_i % self.cols

        if self.right_to_left:
            c = self.cols - c - 1

        if self.bottom_to_top:
            r = self.rows - r - 1

        return r, c

    def calc_shift(self, horizontal_space: float, vertical_space: float) -> tuple:
        """
        Calculates the shift needed to align the tile in the grid.
        Returns a tuple of (shift_right, shift_up).
        Only used if a tile is smaller than the grid space.
        """
        if self.horizontal_align is SW_ALIGN_H.LEFT:
            shift_right = 0
        elif self.horizontal_align is SW_ALIGN_H.MID:
            shift_right = round(horizontal_space / 2)
        elif self.horizontal_align is SW_ALIGN_H.RIGHT:
            shift_right = round(horizontal_space)
        if self.vertical_align is SW_ALIGN_V.BOTTOM:
            shift_up = 0
        elif self.vertical_align is SW_ALIGN_V.MID:
            shift_up = round(vertical_space / 2)
        elif self.vertical_align is SW_ALIGN_V.TOP:
            shift_up = round(vertical_space)

        # invert shift if we are rotating
        if self.rotation == SW_ROTATION.CLOCKWISE:
            shift_up *= -1
        elif self.rotation == SW_ROTATION.COUNTERCLOCKWISE:
            shift_right *= -1
        elif self.rotation == SW_ROTATION.TURNAROUND:
            shift_right *= -1
            shift_up *= -1

        return shift_right, shift_up

    def set_user_unit(self):
        """
        Find the maximum user_unit defined in the document, then use this for the new document.
        """
        for p in self.page_range:
            page = self.in_doc.pages[p - 1]
            if "/UserUnit" in page.keys() and page.UserUnit > self.user_unit:
                self.user_unit = float(page.UserUnit)

    def run(
        self,
        rows=None,
        cols=None,
        target_width=None,
        target_height=None,
        vertical_align=None,
        horizontal_align=None,
    ):
        """
        The main function for tiling pages.
        """

        if self.in_doc is None:
            print(_("Input document not loaded"))
            return

        # First, go through the pages and normalize the various boxes
        for page in self.in_doc.pages:
            utils.normalize_boxes(page)

        if rows or cols:
            self.rows = rows
            self.cols = cols

        if target_width is not None:
            self.target_width = Config.general["units"].units_to_px(target_width)
        if target_height is not None:
            self.target_height = Config.general["units"].units_to_px(target_height)

        if vertical_align is not None:
            self.vertical_align = vertical_align
        if horizontal_align is not None:
            self.horizontal_align = horizontal_align

        # initialize a new document
        new_doc = utils.init_new_doc(self.in_doc)

        # define the trim in pdf units, then build the page list
        self.set_user_unit()
        px_trim = [Config.general["units"].units_to_px(t, self.user_unit) for t in self.trim]
        content_dict, pw, ph, page_names = self.build_pagelist(new_doc, px_trim)
        n_tiles = len(page_names)
        if not self.calc_rows_cols(n_tiles):
            error_msg = _(
                "Error: cannot tile {} pages with {} rows and {} columns".format(
                    n_tiles, self.rows, self.cols
                )
            )
            if self.col_major:
                error_msg += "\n" + _("filling columns first, the last column would be empty.")
            else:
                error_msg += "\n" + _("filling rows first, the last row would be empty.")
            print(error_msg)
            return

        # after calculating rows/cols but before reordering trim, show the user the selected options
        self.show_options()
        self.adjust_trim_order(px_trim)

        if self.rotation in (SW_ROTATION.CLOCKWISE, SW_ROTATION.COUNTERCLOCKWISE):
            # swap width and height of pages
            ph, pw = pw, ph

        if self.target_width and self.target_height:
            # determine size of each page based on requested dimensions
            width = self.target_width
            height = self.target_height
            page_box_width = self.target_width / self.cols
            page_box_height = self.target_height / self.rows
            page_box_defined = True
        else:
            col_width, row_height = self.compute_target_size(n_tiles, pw, ph, px_trim)
            width = sum(col_width)
            height = sum(row_height)
            page_box_defined = False

        # create a new document with a page big enough to contain all the tiled pages, plus requested margin
        first_page = self.in_doc.pages[self.page_range[0] - 1]
        margin = Config.general["units"].units_to_px(self.margin, self.user_unit)
        media_box = [
            float(first_page.MediaBox[0]),
            float(first_page.MediaBox[1]),
            width + 2 * margin,
            height + 2 * margin,
        ]

        utils.print_media_box(media_box, self.user_unit)

        # TODO: Refactor this giant loop into two functions (scale to fit and no scaling)
        i = 0
        content_txt = ""
        performed_scale = False

        # loop through all the page xobjects and place the non-empty ones
        for i in range(n_tiles):
            if not page_names[i]:
                continue

            r, c = self.grid_position(i)
            scale_factor = 1

            if page_box_defined:
                # calculate scaling factors based on source page size
                source_width = pw[i]
                source_height = ph[i]
                scalef_width = page_box_width / source_width
                scalef_height = page_box_height / source_height
                # take the smaller scaling factor so that the page will fit into its box
                scale_factor = min(scalef_width, scalef_height)
                cpos_x0 = c * page_box_width - c * (px_trim[0] + px_trim[1])
                cpos_y0 = (self.rows - r - 1) * page_box_height - (self.rows - r - 1) * (
                    px_trim[2] + px_trim[3]
                )
            else:
                cpos_x0 = sum(col_width[:c]) - px_trim[0]
                cpos_y0 = sum(row_height[r + 1 :]) - px_trim[3]

                # store the page box height/width for convenience if rotation is needed
                page_box_height = ph[i]
                page_box_width = pw[i]

            # define the xobject position with reference to the origin at bottom left of page.
            x0 = margin + cpos_x0
            y0 = margin + cpos_y0

            if page_box_defined:
                # determine scaled size
                scaled_width = pw[i] * scale_factor
                scaled_height = ph[i] * scale_factor
                horizontal_space = page_box_width - scaled_width
                vertical_space = page_box_height - scaled_height
            else:
                horizontal_space = col_width[c] - pw[i]
                vertical_space = row_height[r] - ph[i]

            # apply shift
            shift_right, shift_up = self.calc_shift(horizontal_space, vertical_space)
            x0 += shift_right
            y0 += shift_up

            if self.rotation == SW_ROTATION.NONE:
                # R is the rotation matrix (default to identity)
                R = [1, 0, 0, 1]
            else:
                # We need to account for the shift in origin if page rotation is applied
                if self.rotation == SW_ROTATION.CLOCKWISE:
                    R = [0, -1, 1, 0]
                    y0 += page_box_height
                elif self.rotation == SW_ROTATION.COUNTERCLOCKWISE:
                    R = [0, 1, -1, 0]
                    x0 += page_box_width
                elif self.rotation == SW_ROTATION.TURNAROUND:
                    R = [-1, 0, 0, -1]
                    x0 += page_box_width
                    y0 += page_box_height

            if scale_factor != 1:
                # if we scale any of the pages, keep track of it so we can warn afterwards
                performed_scale = True
                # not quite matrix multiplication but works for a scalar scale factor
                R = [R[i] * scale_factor for i in range(len(R))]

            # scale, shift and rotate
            content_txt += f"q {R[0]} {R[1]} {R[2]} {R[3]} {x0} {y0} cm "
            content_txt += f"{page_names[i]} Do Q "

        if performed_scale:
            print(
                _(
                    "Warning: Some pages have been scaled because a target size was set. "
                    "You should not see this warning if using the PDFStitcher GUI."
                )
            )

        tiled_page = pikepdf.Dictionary(
            Type=pikepdf.Name.Page,
            MediaBox=media_box,
            Resources=pikepdf.Dictionary(XObject=content_dict),
            Contents=pikepdf.Stream(new_doc, content_txt.encode()),
        )
        if self.user_unit != 1:
            tiled_page.UserUnit = self.user_unit

        new_doc.pages.append(tiled_page)

        return new_doc


def main(args):
    utils.setup_locale()

    # first try opening the document
    try:
        in_doc = pikepdf.Pdf.open(args.input)
    except:
        print(_("Unable to open") + " " + args.input)
        sys.exit()

    tiler = PageTiler(in_doc)

    if args.pages is not None:
        tiler.page_range = utils.parse_page_range(args.pages)
    else:
        tiler.page_range = [i + 1 for i in range(len(in_doc.pages))]

    if args.units == "cm":
        Config.general["units"] = utils.UNITS.CENTIMETERS

    if args.margin is not None:
        tiler.margin = utils.txt_to_float(args.margin)

    if args.trim is not None:
        trim = [utils.txt_to_float(t) for t in args.trim.split(",")]
        tiler.trim = trim

    r = int(args.rotate)
    if r == 0:
        tiler.rotation = SW_ROTATION.NONE
    elif r == 90:
        tiler.rotation = SW_ROTATION.CLOCKWISE
    elif r == 180:
        tiler.rotation = SW_ROTATION.TURNAROUND
    elif r == 270:
        tiler.rotation = SW_ROTATION.COUNTERCLOCKWISE

    tiler.cols = 0
    tiler.rows = 0
    if args.columns is not None:
        tiler.cols = int(args.columns)

    if args.rows is not None:
        tiler.rows = int(args.rows)

    # run it!
    new_doc = tiler.run()

    try:
        new_doc.save(args.output)
        success = True
    except:
        success = False

    return new_doc, success


def parse_arguments():
    parser = argparse.ArgumentParser(
        description=_("Tile PDF pages into one document."),
        epilog=_("Note: If both rows and columns are specified, rows are ignored.")
        + " "
        + _("To insert a blank page, include a zero in the page list."),
    )

    parser.add_argument(
        "input",
        help=_("Input filename (pdf)"),
    )
    parser.add_argument(
        "output",
        help=_("Output filename (pdf)"),
    )
    parser.add_argument(
        "-p",
        "--pages",
        help=_(
            "Pages to tile. May be range or list (e.g. 1-5 or 1,3,5-7, etc). Default: entire document."
        ),
    )
    parser.add_argument(
        "-r",
        "--rows",
        type=int,
        help=_("Number of rows in tiled grid."),
    )
    parser.add_argument(
        "-c",
        "--columns",
        type=int,
        help=_("Number of columns in tiled grid."),
    )
    parser.add_argument(
        "-u",
        "--units",
        choices=["in", "cm"],
        default="in",
        help=_("Units for margin and trim values."),
    )
    parser.add_argument(
        "-m",
        "--margin",
        help=_("Margin size in selected units."),
    )
    parser.add_argument(
        "-t",
        "--trim",
        help=_("Amount to trim from edges in selected units")
        + " "
        + _("given as left,right,top,bottom (e.g. 0.5,0,0.5,0 would trim 0.5 from left and top)"),
    )
    parser.add_argument(
        "-R",
        "--rotate",
        type=int,
        default=0,
        choices=[0, 90, 180, 270],
        help=_("Rotate pages"),
    )
    parser.add_argument(
        "--col-major",
        type=bool,
        default=False,
        help=_("Fill columns before rows (default is rows first)"),
    )

    return parser.parse_args()


if __name__ == "__main__":
    utils.setup_locale()
    args = parse_arguments()
    new_doc, success = main(args)
