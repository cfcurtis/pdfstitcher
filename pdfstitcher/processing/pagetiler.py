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
import math
import copy
import pdfstitcher.utils as utils
from pdfstitcher.utils import Config
from pdfstitcher.processing.procbase import ProcessingBase


class SW_ROTATION(IntEnum):
    def __str__(self) -> str:
        if self == SW_ROTATION.NONE:
            return _("None")
        elif self == SW_ROTATION.CLOCKWISE:
            return _("Clockwise")
        elif self == SW_ROTATION.COUNTERCLOCKWISE:
            return _("Counterclockwise")
        elif self == SW_ROTATION.TURNAROUND:
            # translation_note: Rotates 180 degrees. Not exposed in PDFStitcher GUI
            return _("Turn Around")
        else:
            return _("Unknown")

    NONE = 0
    CLOCKWISE = 1
    COUNTERCLOCKWISE = 2
    TURNAROUND = 3


class SW_ALIGN_V(IntEnum):
    def __str__(self) -> str:
        if self == SW_ALIGN_V.BOTTOM:
            return _("Bottom")
        elif self == SW_ALIGN_V.MID:
            return _("Middle")
        elif self == SW_ALIGN_V.TOP:
            return _("Top")
        else:
            return _("Unknown")

    BOTTOM = 0
    MID = 1
    TOP = 2


class SW_ALIGN_H(IntEnum):
    def __str__(self) -> str:
        if self == SW_ALIGN_H.LEFT:
            return _("Left")
        elif self == SW_ALIGN_H.MID:
            return _("Middle")
        elif self == SW_ALIGN_H.RIGHT:
            return _("Right")
        else:
            return _("Unknown")

    LEFT = 0
    MID = 1
    RIGHT = 2


class PageTiler(ProcessingBase):
    """
    Class to handle tiling pages into a single document.
    """

    def __init__(self, *args, **kw) -> None:
        super().__init__(*args, **kw)

    def show_options(self):
        """
        Display the options selected for tiling.
        """
        orderstr = _("Rows then columns")
        if self.p["col_major"]:
            orderstr = _("Columns then rows")

        lrstr = _("Left to right")
        if self.p["right_to_left"]:
            lrstr = _("Right to left")

        btstr = _("Top to bottom")
        if self.p["bottom_to_top"]:
            btstr = _("Bottom to top")

        print(_("Tiling with {} rows and {} columns").format(self.rows, self.cols))
        print(_("Options") + ":")
        print("    " + _("Margins") + ": {} {}".format(self.p["margin"], Config.general["units"]))
        print("    " + _("Trim") + ": {} {}".format(self.p["trim"], Config.general["units"]))
        print("    " + _("Rotation") + ": {}".format(str(self.p["rotation"])))
        print("    " + _("Page order") + ": {}, {}, {}".format(orderstr, lrstr, btstr))

        # alignment options only set outside of PDFStitcher GUI
        if "vertical_align" in self.p:
            print("    " + _("Vertical alignment") + ": {}".format(str(self.p["vertical_align"])))
        if "horizontal_align" in self.p:
            print(
                "    " + _("Horizontal alignment") + ": {}".format(str(self.p["horizontal_align"]))
            )

    def process_page(self, content_dict: dict, p: int) -> str:
        """
        Extracts page number p from the input document and adds it to the page_dict,
        trimming if requested and storing page dimensions.
        Returns the pagekey if a new page was added, None if it already exists.
        """
        pagekey = f"/Page{p}"
        # Check if it's already been copied (in case of duplicate page numbers)
        if pagekey in content_dict.keys():
            return None

        # get a copy of the input page
        new_page = copy.copy(self.in_doc.pages[p - 1])

        if "/Rotate" in new_page.keys():
            page_rot = new_page.Rotate % 360

        if self.p["override_trim"]:
            new_page.TrimBox = copy.copy(new_page.MediaBox)

        # set the trim box to cut off content if requested
        if self.p["actually_trim"]:
            # things get tricky if there's rotation, because the user sees top/bottom as right/left
            # trim: left, right, top, bottom as defined visually
            # trimbox: left, bottom, right, top (absolute coordinates)
            rtrim = [self.pt_trim[0], self.pt_trim[3], self.pt_trim[1], self.pt_trim[2]]
            if page_rot == 90:
                rtrim = [self.pt_trim[2], self.pt_trim[0], self.pt_trim[3], self.pt_trim[1]]
            elif page_rot == 180:
                rtrim = [self.pt_trim[3], self.pt_trim[0], self.pt_trim[2], self.pt_trim[1]]
            elif page_rot == 270:
                rtrim = [self.pt_trim[3], self.pt_trim[1], self.pt_trim[2], self.pt_trim[0]]

            # lowercase trimbox returns TrimBox if it exists, MediaBox otherwise
            in_trim = [float(t) for t in new_page.trimbox]
            new_page.TrimBox = [
                in_trim[0] + rtrim[0],
                in_trim[1] + rtrim[1],
                in_trim[2] - rtrim[2],
                in_trim[3] - rtrim[3],
            ]

        # magic sauce to copy the info to the new document as an XOBject
        content_dict[pagekey] = self.out_doc.copy_foreign(new_page.as_form_xobject())

        # scale the form xobject by the target user unit
        if self.user_unit != 1:
            if "/Matrix" in content_dict[pagekey].keys():
                xobj_matrix = pikepdf.PdfMatrix(content_dict[pagekey].Matrix)
            else:
                xobj_matrix = pikepdf.PdfMatrix.identity()
            content_dict[pagekey].Matrix = xobj_matrix.scaled(
                1 / self.user_unit, 1 / self.user_unit
            ).shorthand

        return pagekey

    def build_pagelist(self) -> tuple:
        """
        Loops through the pages and constructs the list of pages, their length/width, and XObjects.
        Returns a tuple containing the content dictionary (PDF format) and a list of info dictionaries.
        """
        if not self.in_doc:
            print(_("No input document loaded"))
            return None

        # define the dictionary to store xobjects and the corresponding names (e.g. MC0, MC1, etc.)
        content_dict = pikepdf.Dictionary({})
        info = []
        page_count = len(self.in_doc.pages)

        # initialize the width/height indices based on page rotation
        page_rot = 0

        if "/Rotate" in self.in_doc.Root.Pages.keys():
            page_rot = self.in_doc.Root.Pages.Rotate % 360

        # find the first non-zero page number
        for p in self.page_range:
            if p > 0:
                break

        # get a pointer to the reference page and parse out the width and height
        ref_page = self.in_doc.pages[p - 1]
        prev_width, prev_height = utils.get_page_dims(ref_page, page_rot, self.user_unit)

        # keep track of any pages that are different from the first
        different_size = set()

        for p in self.page_range:
            if p > page_count:
                print(_("Only {} pages in document, skipping {}").format(page_count, p))
                continue

            if p == 0:
                # blank page: append a placeholder to the info list
                info.append({"width": prev_width, "height": prev_height, "pagekey": None})
                continue

            # if we've already added this page to the dictionary, skip it
            pagekey = self.process_page(content_dict, p)
            if pagekey is None:
                continue

            p_width, p_height = utils.get_page_dims(
                self.in_doc.pages[p - 1], page_rot, self.user_unit
            )

            if abs(p_width - prev_width) > 1 or abs(p_height - prev_height) > 1:
                different_size.add(p)

            # update the reference handles to be the current page
            prev_width = p_width
            prev_height = p_height

            # append the page info
            info.append({"width": p_width, "height": p_height, "pagekey": pagekey})

        if len(different_size) > 0:
            print(
                _("Warning: The pages {} have a different size than the page before").format(
                    different_size
                )
            )

        return content_dict, info

    def adjust_trim_order(self) -> None:
        """
        Rearranges the trim order based on requested rotation.
        """
        # swap the trim order
        # default: left,right,top,bottom
        order = [0, 1, 2, 3]

        if self.p["rotation"] == SW_ROTATION.CLOCKWISE:
            order = [3, 2, 0, 1]
        if self.p["rotation"] == SW_ROTATION.COUNTERCLOCKWISE:
            order = [2, 3, 1, 0]
        if self.p["rotation"] == SW_ROTATION.TURNAROUND:
            order = [1, 0, 3, 2]

        self.pt_trim = [self.pt_trim[o] for o in order]

    def compute_target_size(self, n_tiles: int, pw: list, ph: list) -> tuple:
        """
        Find the grid that contains the maximum page size for each row/col.
        Returns the grid dimensions as a tuple of two lists.
        """
        col_width = [0] * self.cols
        row_height = [0] * self.rows

        if self.p["col_major"]:
            for c in range(self.cols):
                col_width[c] = max(pw[c * self.rows : c * self.rows + self.rows]) - (
                    self.pt_trim[0] + self.pt_trim[1]
                )

            for r in range(self.rows):
                row_height[r] = max(ph[r : n_tiles : self.cols]) - (
                    self.pt_trim[2] + self.pt_trim[3]
                )
        else:
            for r in range(self.rows):
                row_height[r] = max(ph[r * self.cols : r * self.cols + self.cols]) - (
                    self.pt_trim[2] + self.pt_trim[3]
                )

            for c in range(self.cols):
                col_width[c] = max(pw[c : n_tiles : self.rows]) - (
                    self.pt_trim[0] + self.pt_trim[1]
                )

        if self.p["right_to_left"]:
            col_width.reverse()

        if self.p["bottom_to_top"]:
            row_height.reverse()

        return col_width, row_height

    def calc_rows_cols(self, n_tiles: int) -> bool:
        """
        Calculate the number of rows/columns requested based on the number of pages to tile.
        Returns True if the result is valid, False otherwise.
        """
        if self.p["cols"] is not None and self.p["cols"] > 0:
            self.cols = self.p["cols"]
            self.rows = math.ceil(n_tiles / self.cols)
            if self.rows == 1 and self.cols > n_tiles:
                print(
                    _("Warning: requested {} columns, but there are only {} pages").format(
                        self.cols, n_tiles
                    )
                )
                self.cols = n_tiles

        elif self.p["rows"] is not None and self.p["rows"] > 0:
            self.rows = self.p["rows"]
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
        if self.p["col_major"]:
            doable = self.cols * self.rows - n_tiles < self.rows
        else:
            doable = self.cols * self.rows - n_tiles < self.cols

        if not doable:
            error_msg = _(
                "Error: cannot tile {} pages with {} rows and {} columns".format(
                    n_tiles, self.rows, self.cols
                )
            )
            if self.p["col_major"]:
                error_msg += "\n" + _("filling columns first, the last column would be empty.")
            else:
                error_msg += "\n" + _("filling rows first, the last row would be empty.")
            print(error_msg)

        return doable

    def grid_position(self, tile_i: int) -> tuple:
        """
        Determines the placement of the tile in the grid, returning a tuple of (row, col).
        """
        if self.p["col_major"]:
            c = math.floor(tile_i / self.rows)
            r = tile_i % self.rows
        else:
            r = math.floor(tile_i / self.cols)
            c = tile_i % self.cols

        if self.p["right_to_left"]:
            c = self.cols - c - 1

        if self.p["bottom_to_top"]:
            r = self.rows - r - 1

        return r, c

    def calc_shift(self, horizontal_space: float, vertical_space: float) -> tuple:
        """
        Calculates the shift needed to align the tile in the grid.
        Returns a tuple of (shift_right, shift_up).
        Only used if a tile is smaller than the grid space.
        """

        if "horizontal_align" in self.p:
            h_align = self.p["horizontal_align"]
        else:
            h_align = SW_ALIGN_H.MID

        if "vertical_align" in self.p:
            v_align = self.p["vertical_align"]
        else:
            v_align = SW_ALIGN_V.MID

        if h_align is SW_ALIGN_H.LEFT:
            shift_right = 0
        elif h_align is SW_ALIGN_H.MID:
            shift_right = round(horizontal_space / 2)
        elif h_align is SW_ALIGN_H.RIGHT:
            shift_right = round(horizontal_space)
        if v_align is SW_ALIGN_V.BOTTOM:
            shift_up = 0
        elif v_align is SW_ALIGN_V.MID:
            shift_up = round(vertical_space / 2)
        elif v_align is SW_ALIGN_V.TOP:
            shift_up = round(vertical_space)

        # invert shift if we are rotating
        if self.p["rotation"] == SW_ROTATION.CLOCKWISE:
            shift_up *= -1
        elif self.p["rotation"] == SW_ROTATION.COUNTERCLOCKWISE:
            shift_right *= -1
        elif self.p["rotation"] == SW_ROTATION.TURNAROUND:
            shift_right *= -1
            shift_up *= -1

        return shift_right, shift_up

    def set_user_unit(self):
        """
        Find the maximum user_unit defined in the document, then use this for the new document.
        """

        self.user_unit = 1
        for p in self.page_range:
            page = self.in_doc.pages[p - 1]
            if "/UserUnit" in page.keys() and page.UserUnit > self.user_unit:
                self.user_unit = float(page.UserUnit)

    def compute_T_matrix(
        self, i: int, col_width: list, row_height: list, page_info: dict, scale: float = 1
    ) -> list:
        """
        Calculates the transformation matrix for the specified page.
        Returns a list of 6 elements representing the matrix.
        """

        if self.p["rotation"] in (SW_ROTATION.CLOCKWISE, SW_ROTATION.COUNTERCLOCKWISE):
            # swap width and height of pages if rotated
            page_info["width"], page_info["height"] = page_info["height"], page_info["width"]

        r, c = self.grid_position(i)

        # the origin is the sum of all the sizes before the current one
        x0 = sum(col_width[:c]) - self.pt_trim[0]
        y0 = sum(row_height[r + 1 :]) - self.pt_trim[3]

        # the XObject may be smaller than the grid space, so calculate the shift needed
        horizontal_space = col_width[c] - page_info["width"] * scale
        vertical_space = row_height[r] - page_info["height"] * scale

        # apply shift
        shift_right, shift_up = self.calc_shift(horizontal_space, vertical_space)
        x0 += shift_right
        y0 += shift_up

        if self.p["rotation"] == SW_ROTATION.NONE:
            # R is the rotation matrix (default to identity)
            R = [1, 0, 0, 1]
        else:
            # We need to account for the shift in origin if page rotation is applied
            if self.p["rotation"] == SW_ROTATION.CLOCKWISE:
                R = [0, -1, 1, 0]
                y0 += page_info["height"]
            elif self.p["rotation"] == SW_ROTATION.COUNTERCLOCKWISE:
                R = [0, 1, -1, 0]
                x0 += page_info["width"]
            elif self.p["rotation"] == SW_ROTATION.TURNAROUND:
                R = [-1, 0, 0, -1]
                x0 += page_info["width"]
                y0 += page_info["height"]

        # not quite matrix multiplication but works for a scalar scale factor
        R = [R[i] * scale for i in range(len(R))]

        return R + [x0, y0]

    def layout_scaled(self, content_dict: pikepdf.Dictionary, info: list) -> tuple:
        """
        Constructs the content stream defining the page placement within the target dimensions.
        Returns a tuple containing the content text and the media box.
        Should never be called by the PDFStitcher GUI.
        """

        if not (self.target_width and self.target_height):
            print(_("Target height and width must be specified in scale-to-fit mode"))
            return False

        # Define the target dimensions in points
        self.target_width = Config.general["units"].units_to_pts(self.target_height)
        self.target_height = Config.general["units"].units_to_pts(self.target_width)

        # determine size of each page based on requested dimensions
        page_box_width = self.target_width / self.cols
        page_box_height = self.target_height / self.rows

        # loop through all the page xobjects and place the non-empty ones
        content_txt = ""
        for i, page_info in enumerate(info):
            if page_info["pagekey"] is None:
                # blank page, just carry on
                continue

            # calculate scaling factors
            scalef_width = page_box_width / page_info["width"]
            scalef_height = page_box_height / page_info["height"]

            # take the smaller scaling factor so that the page will fit into its box
            scale_factor = min(scalef_width, scalef_height)
            T = self.compute_T_matrix(
                i,
                [page_box_width] * self.cols,
                [page_box_height] * self.rows,
                page_info,
                scale_factor,
            )

            content_txt += "q " + " ".join([str(t) for t in T]) + " cm "
            content_txt += f"{page_info['pagekey']} Do Q "

        return content_txt, (self.target_width, self.target_height)

    def layout_no_scaling(self, content_dict: pikepdf.Dictionary, info: list) -> tuple:
        """
        Constructs the content stream defining the page placement. No scaling is applied.
        Returns a tuple containing the content text and the media box.
        This is the behaviour called by the PDFStitcher GUI.
        """

        # ugly list comprehension to get the width and height for each row/column
        col_width, row_height = self.compute_target_size(
            len(content_dict), [i["width"] for i in info], [i["height"] for i in info]
        )
        width = sum(col_width)
        height = sum(row_height)

        # loop through all the page xobjects and place the non-empty ones
        content_txt = ""
        for i, page_info in enumerate(info):
            if page_info["pagekey"] is None:
                # blank page, just carry on
                continue

            T = self.compute_T_matrix(i, col_width, row_height, page_info)
            content_txt += "q " + " ".join([str(t) for t in T]) + " cm "
            content_txt += f"{page_info['pagekey']} Do Q "

        return content_txt, (width, height)

    def run(self, progress_win=None, scaling=False) -> bool:
        """
        Create a new document for the output and place the pages in a tiled grid.
        Returns true if processing was successful, false otherwise.
        """

        if self.in_doc is None:
            print(_("Input document not loaded"))
            return

        # initialize the output
        self.out_doc = utils.init_new_doc(self.in_doc)

        # define the trim in pdf units, then build the page list
        self.set_user_unit()
        self.pt_trim = [
            Config.general["units"].units_to_pts(t, self.user_unit) for t in self.p["trim"]
        ]
        content_dict, info = self.build_pagelist()
        n_tiles = len(info)

        # Make sure the requested rows and columns are valid
        if not self.calc_rows_cols(n_tiles):
            return False

        # after calculating rows/cols but before reordering trim, show the user the selected options
        self.show_options()
        self.adjust_trim_order()

        if scaling:
            content_txt, dims = self.layout_scaled(content_dict, info)
        else:
            content_txt, dims = self.layout_no_scaling(content_dict, info)

        # create a new document with a page big enough to contain all the tiled pages, plus requested margin
        margin = Config.general["units"].units_to_pts(self.p["margin"], self.user_unit)
        # Note: change in behaviour! The origin is now inside the margin, not at 0,0.
        media_box = [
            -margin,
            -margin,
            dims[0] + margin,
            dims[1] + margin,
        ]

        utils.print_media_box(media_box, self.user_unit)

        # add the new page to the document
        tiled_page = pikepdf.Dictionary(
            Type=pikepdf.Name.Page,
            MediaBox=media_box,
            Resources=pikepdf.Dictionary(XObject=content_dict),
            Contents=pikepdf.Stream(self.out_doc, content_txt.encode()),
            UserUnit=self.user_unit,
        )
        self.out_doc.pages.append(pikepdf.Page(tiled_page))
        self.needs_run = False

        return True


def main(args: argparse.Namespace) -> None:
    utils.setup_locale()

    # define the tiler
    tiler = PageTiler(args.input)

    if args.units == "cm":
        Config.general["units"] = utils.UNITS.CENTIMETERS
    else:
        Config.general["units"] = utils.UNITS.INCHES

    params = {
        "rows": args.rows,
        "cols": args.columns,
        "col_major": args.col_major,
        "right_to_left": args.right_to_left,
        "bottom_to_top": args.bottom_to_top,
        "rotation": SW_ROTATION(args.rotate // 90),
        "margin": utils.txt_to_float(args.margin),
        "trim": args.trim,
        "override_trim": args.trimbox_to_mediabox,
        "actually_trim": args.actually_trim,
    }

    tiler.params = params
    tiler.page_range = args.pages

    scaling = False
    if args.target_height:
        tiler.target_height = args.target_height
        scaling = True

    if args.target_width:
        tiler.target_width = args.target_width
        scaling = True

    # run it!
    success = tiler.run(scaling=scaling)
    if success:
        tiler.out_doc.save(args.output)
        print(_("Successfully written to") + " " + args.output)
    else:
        print(_("Something went wrong"))


def parse_arguments() -> argparse.Namespace:
    """
    Helper function to parse command line arguments.
    """
    parser = argparse.ArgumentParser(
        description=_("Tile PDF pages into one document."),
        epilog=_("Note: If both rows and columns are specified, rows are ignored.")
        + " "
        + _("To insert a blank page, include a zero in the page list."),
    )

    # Required arguments
    parser.add_argument(
        "input",
        help=_("Input filename (pdf)"),
    )
    parser.add_argument(
        "output",
        help=_("Output filename (pdf)"),
    )
    group = parser.add_argument_group(
        _("Grid layout"), _("Number of Columns") + " " + _("OR Number of Rows")
    )
    m_group = group.add_mutually_exclusive_group(required=True)
    m_group.add_argument(
        "-r",
        "--rows",
        type=int,
        help=_("Number of rows in tiled grid."),
    )
    m_group.add_argument(
        "-c",
        "--columns",
        type=int,
        help=_("Number of columns in tiled grid."),
    )

    parser.add_argument(
        "-p",
        "--pages",
        help=_(
            "Pages to tile. May be range or list (e.g. 1-5 or 1,3,5-7, etc). Default: entire document."
        ),
    )
    parser.add_argument(
        "-u",
        "--units",
        choices=[_("in"), _("cm")],
        default=_("in"),
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
        default="0,0,0,0",
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
    parser.add_argument(
        "--right-to-left",
        type=bool,
        default=False,
        help=_("Fill columns right to left (default is left to right)"),
    )
    parser.add_argument(
        "--bottom-to-top",
        type=bool,
        default=False,
        help=_("Fill rows bottom to top (default is top to bottom)"),
    )
    parser.add_argument(
        "--target-height",
        type=float,
        help=_("Height of output document in selected units.")
        + " "
        + _("Caution: results in scaling of pages"),
        default=None,
    )
    parser.add_argument(
        "--target-width",
        type=float,
        help=_("Width of output document in selected units.")
        + " "
        + _("Caution: results in scaling of pages"),
        default=None,
    )
    parser.add_argument(
        "--trimbox-to-mediabox",
        action="store_true",
        help=_("Override trimbox with mediabox"),
        default=False,
    )
    parser.add_argument(
        "--actually-trim",
        action="store_true",
        help=_("Actually trim the pages (default is overlap)"),
        default=False,
    )

    args = parser.parse_args()

    # validate the trim values
    trim = [utils.txt_to_float(t) for t in args.trim.split(",")]
    if len(trim) == 1:
        args.trim = [trim[0], trim[0], trim[0], trim[0]]
    elif len(trim) == 2:
        args.trim = [trim[0], trim[0], trim[1], trim[1]]
    elif len(trim) == 4:
        args.trim = trim
    else:
        print(_("Invalid trim value specified, ignoring"))
        args.trim = [0, 0, 0, 0]

    return args


if __name__ == "__main__":
    utils.setup_locale()
    args = parse_arguments()
    main(args)
