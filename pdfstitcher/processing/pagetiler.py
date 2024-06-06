# PDFStitcher is a utility to work with PDF sewing patterns.
# Copyright (C) 2021 Charlotte Curtis
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from typing import Union
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

        # define a few attributes that will be overwritten on run
        self.output_uu = 1
        self.cols = 0
        self.rows = 0

    def _show_options(self):
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

    def _process_page(
        self, content_dict: pikepdf.Dictionary, p: int, info: dict
    ) -> Union[None, str]:
        """
        Extracts page number p from the input document and adds it to the page_dict,
        performs trimming if requested, and stores page dimensions. Lots going on.
        """
        pagekey = f"/Page{p}"
        # Check if it's already been copied (in case of duplicate page numbers)
        if pagekey in content_dict.keys():
            return None

        # get a convenient reference to the page
        in_doc_page = self.in_doc.pages[p - 1]

        # magic sauce to copy the info to the new document as an XOBject
        content_dict[pagekey] = self.out_doc.copy_foreign(
            in_doc_page.as_form_xobject(handle_transformations=False)
        )

        # get the page rotation and user unit
        page_rot = 0
        if "/Rotate" in in_doc_page.keys():
            page_rot = in_doc_page.Rotate % 360

        page_uu = 1
        if "/UserUnit" in in_doc_page.keys():
            page_uu = float(in_doc_page.UserUnit)

        # lowercase trimbox returns TrimBox if it exists, MediaBox otherwise
        # overriding trimbox will use the media box instead, sometimes fixes weird things
        if self.p["override_trim"]:
            bbox = copy.copy(in_doc_page.MediaBox)
        else:
            bbox = copy.copy(in_doc_page.trimbox)

        # set the trim box to cut off content if requested
        page_trim = self._get_page_trim(page_uu, page_rot)
        if self.p["actually_trim"]:
            bbox = [
                float(bbox[0]) + page_trim[0],
                float(bbox[1]) + page_trim[1],
                float(bbox[2]) - page_trim[2],
                float(bbox[3]) - page_trim[3],
            ]
        content_dict[pagekey].BBox = bbox

        # also apply the rotation to the target matrix
        if "/Matrix" in content_dict[pagekey].keys():
            xobj_matrix = pikepdf.Matrix(content_dict[pagekey].Matrix).rotated(page_rot)
        else:
            xobj_matrix = pikepdf.Matrix().rotated(page_rot)

        # Scale the form xobject by the target document user unit relative to the page.
        # This is why we're not letting pikepdf handle the transformation!
        content_dict[pagekey].Matrix = xobj_matrix.scaled(
            page_uu / self.output_uu, page_uu / self.output_uu
        ).shorthand

        # update the info dictionary with the page dimensions
        p_width, p_height = utils.get_page_dims(
            content_dict[pagekey], page_rot, page_uu=page_uu, output_uu=self.output_uu
        )

        # if we're not actually trimming, subtract the trim from the page size
        if not self.p["actually_trim"]:
            page_trim = [p * page_uu / self.output_uu for p in page_trim]
            p_width -= page_trim[0] + page_trim[2]
            p_height -= page_trim[1] + page_trim[3]

        # append the page info
        info.append({"width": p_width, "height": p_height, "pagekey": pagekey})
        return pagekey

    def _get_first_page_dims(self) -> tuple:
        """
        Get the dimensions of the first page in the document. Returns a tuple of (width, height).
        Mainly useful if the first page specified is blank (0).
        """
        # initialize the width/height indices based on page rotation
        page_rot = 0

        if "/Rotate" in self.in_doc.Root.Pages.keys():
            page_rot = self.in_doc.Root.Pages.Rotate % 360

        # find the first non-zero page number
        p = None
        for p in self.page_range:
            if p > 0:
                break

        if not p:
            raise ValueError(_("No valid pages included in range"))

        # get a pointer to the reference page and parse out the width and height
        ref_page = self.in_doc.pages[p - 1]
        return utils.get_page_dims(ref_page, page_rot, output_uu=self.output_uu)

    def _build_pagelist(self) -> tuple:
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

        # keep track of any pages that are different from the previous one
        different_size = set()
        prev_width, prev_height = self._get_first_page_dims()

        for p in self.page_range:
            if p == 0:
                # blank page: append a placeholder to the info list
                info.append({"width": prev_width, "height": prev_height, "pagekey": None})
                continue

            # if we've already added this page to the dictionary, skip it
            pagekey = self._process_page(content_dict, p, info)
            if pagekey is None:
                continue

            if abs(info[-1]["width"] - prev_width) > 1 or abs(info[-1]["height"] - prev_height) > 1:
                different_size.add(p)

            # update the reference handles to be the current page
            prev_width = info[-1]["width"]
            prev_height = info[-1]["height"]

        if len(different_size) > 0:
            print(
                _("Warning: The pages {} have a different size than the page before").format(
                    different_size
                )
            )

        return content_dict, info

    def _get_trim(self, user_unit: float = 1) -> list:
        """
        Rearranges the trim order based on requested rotation, handling any necessary scaling.
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

        return [Config.general["units"].units_to_pts(self.p["trim"][o], user_unit) for o in order]

    def _get_page_trim(self, page_uu: float, rotation: int) -> list:
        """
        Rearranges the trim order based on page rotation.
        This is different from _get_trim because it provides the order in PDF format (left, bottom, right, top).
        Note that the rotation is in degrees as specified by the PDF (opaque to the user), NOT the requested rotation.
        """
        # things get tricky if there's rotation, because the user sees top/bottom as right/left
        # Rotation is in clockwise degrees, so we need to adjust the trim order accordingly
        # trim: left, right, top, bottom as defined visually
        # trimbox: left, bottom, right, top (absolute coordinates)
        page_trim = self._get_trim(page_uu)

        # PDF rotation should be in increments of 90 degrees, but I've actually seen 360
        rotation = rotation % 360
        if rotation == 0:
            order = [0, 3, 1, 2]
        elif rotation == 90:
            order = [3, 1, 2, 0]
        elif rotation == 180:
            order = [1, 2, 0, 3]
        elif rotation == 270:
            order = [2, 0, 3, 1]

        return [page_trim[o] for o in order]

    def _compute_target_size(self, info: list) -> tuple:
        """
        Find the grid that contains the maximum page size for each row/col
        based on the given list of page info.
        Returns the grid dimensions as a tuple of two lists.
        """
        col_width = [0] * self.cols
        row_height = [0] * self.rows

        # extract the page dimensions from the info list
        pw = [i["width"] for i in info]
        ph = [i["height"] for i in info]
        n_tiles = len(info)

        if self.p["col_major"]:
            for c in range(self.cols):
                col_width[c] = max(pw[c * self.rows : c * self.rows + self.rows])

            for r in range(self.rows):
                row_height[r] = max(ph[r : n_tiles : self.cols])
        else:
            for r in range(self.rows):
                row_height[r] = max(ph[r * self.cols : r * self.cols + self.cols])

            for c in range(self.cols):
                col_width[c] = max(pw[c : n_tiles : self.rows])

        if self.p["right_to_left"]:
            col_width.reverse()

        if self.p["bottom_to_top"]:
            row_height.reverse()

        return col_width, row_height

    def _calc_rows_cols(self, n_tiles: int) -> bool:
        """
        Calculate the number of rows/columns requested based on the number of pages to tile.
        Returns True if the result is valid, False otherwise.
        """
        if n_tiles == 0:
            print(_("No pages to tile"))
            return False

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

    def _grid_position(self, tile_i: int) -> tuple:
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

    def _calc_shift(self, horizontal_space: float, vertical_space: float) -> tuple:
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

        shift_right = 0
        shift_up = 0
        if h_align is SW_ALIGN_H.MID:
            shift_right = round(horizontal_space / 2)
        elif h_align is SW_ALIGN_H.RIGHT:
            shift_right = round(horizontal_space)

        if v_align is SW_ALIGN_V.MID:
            shift_up = round(vertical_space / 2)
        elif v_align is SW_ALIGN_V.TOP:
            shift_up = round(vertical_space)

        # invert shift if we are rotating
        if "rotation" in self.p:
            if self.p["rotation"] == SW_ROTATION.CLOCKWISE:
                shift_up *= -1
            elif self.p["rotation"] == SW_ROTATION.COUNTERCLOCKWISE:
                shift_right *= -1
            elif self.p["rotation"] == SW_ROTATION.TURNAROUND:
                shift_right *= -1
                shift_up *= -1

        return shift_right, shift_up

    def _set_output_user_unit(self):
        """
        Find the maximum user_unit defined in the document, then use this for the new document.
        """
        self.output_uu = 1
        for p in self.page_range:
            page = self.in_doc.pages[p - 1]
            if "/UserUnit" in page.keys() and page.UserUnit > self.output_uu:
                self.output_uu = float(page.UserUnit)

    def _compute_T_matrix(
        self, i: int, col_width: list, row_height: list, page_info: dict, scale: float = 1
    ) -> list:
        """
        Calculates the transformation matrix for page i (zero indexed).
        Returns a list of 6 elements representing the matrix.
        """

        if self.p["rotation"] in (SW_ROTATION.CLOCKWISE, SW_ROTATION.COUNTERCLOCKWISE):
            # swap width and height of pages if rotated
            page_info["width"], page_info["height"] = page_info["height"], page_info["width"]

        r, c = self._grid_position(i)

        # the origin is the sum of all the sizes before the current one
        x0 = sum(col_width[:c])
        y0 = sum(row_height[r + 1 :])

        # the XObject may be smaller than the grid space, so calculate the shift needed
        horizontal_space = col_width[c] - page_info["width"] * scale
        vertical_space = row_height[r] - page_info["height"] * scale

        # apply shift
        shift_right, shift_up = self._calc_shift(horizontal_space, vertical_space)
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

    def _layout_scaled(self, info: list) -> tuple:
        """
        Constructs the content stream defining the page placement within the target dimensions.
        Returns a tuple containing the content text and the media box.
        Should never be called by the PDFStitcher GUI.
        """

        # Define the target dimensions in points
        target_width_pts = Config.general["units"].units_to_pts(
            self.p["target_width"], self.output_uu
        )
        target_height_pts = Config.general["units"].units_to_pts(
            self.p["target_height"], self.output_uu
        )

        # determine size of each page based on requested dimensions
        page_box_width = target_width_pts / self.cols
        page_box_height = target_height_pts / self.rows

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
            T = self._compute_T_matrix(
                i,
                [page_box_width] * self.cols,
                [page_box_height] * self.rows,
                page_info,
                scale_factor,
            )

            content_txt += "q " + " ".join([str(t) for t in T]) + " cm "
            content_txt += f"{page_info['pagekey']} Do Q "

        return content_txt, (target_width_pts, target_height_pts)

    def _layout_no_scaling(self, info: list) -> tuple:
        """
        Constructs the content stream defining the page placement. No scaling is applied.
        Returns a tuple containing the content text and the media box.
        This is the behaviour called by the PDFStitcher GUI.
        """

        # get the width and height for each row/column based on the page info
        col_width, row_height = self._compute_target_size(info)
        width = sum(col_width)
        height = sum(row_height)

        # loop through all the page xobjects and place the non-empty ones
        content_txt = ""
        for i, page_info in enumerate(info):
            if page_info["pagekey"] is None:
                # blank page, just carry on
                continue

            T = self._compute_T_matrix(i, col_width, row_height, page_info)
            content_txt += "q " + " ".join([str(t) for t in T]) + " cm "
            content_txt += f"{page_info['pagekey']} Do Q "

        return content_txt, (width, height)

    def _get_process_function(self) -> callable:
        """
        Returns the processing function to use based on the requested scaling mode.
        """
        if (
            "target_height" in self.p
            and self.p["target_height"]
            or "target_width" in self.p
            and self.p["target_width"]
        ):
            if not (self.p["target_width"] and self.p["target_height"]):
                print(
                    _("Error")
                    + ": "
                    + _("Target height and width must be specified in scale-to-fit mode")
                )
                return None

            print(
                _(
                    "Target width and height specified, scaling pages to fit. Do not use this option for sewing patterns!"
                )
            )
            return self._layout_scaled
        else:
            return self._layout_no_scaling

    def run(self, progress_win=None) -> bool:
        """
        Create a new document for the output and place the pages in a tiled grid.
        Returns true if processing was successful, false otherwise.
        """

        if self.in_doc is None:
            print(_("Input document not loaded"))
            return

        process = self._get_process_function()
        if process is None:
            return False

        # initialize the output
        self.out_doc = utils.init_new_doc(self.in_doc)

        # set the target userunit
        self._set_output_user_unit()
        content_dict, info = self._build_pagelist()
        n_tiles = len(info)

        # Make sure the requested rows and columns are valid
        if not self._calc_rows_cols(n_tiles):
            return False

        # after calculating rows/cols but before reordering trim, show the user the selected options
        self._show_options()
        content_txt, dims = process(info)

        # create a new document with a page big enough to contain all the tiled pages, plus requested margin
        margin = Config.general["units"].units_to_pts(self.p["margin"], self.output_uu)
        # Note: change in behaviour from v0.9xx to v1.0! The origin is now inside the margin.
        media_box = [
            -margin,
            -margin,
            dims[0] + margin,
            dims[1] + margin,
        ]

        utils.print_media_box(media_box, self.output_uu)

        # add the new page to the document
        tiled_page = pikepdf.Dictionary(
            Type=pikepdf.Name.Page,
            MediaBox=media_box,
            Resources=pikepdf.Dictionary(XObject=content_dict),
            Contents=pikepdf.Stream(self.out_doc, content_txt.encode()),
            UserUnit=self.output_uu,
        )
        self.out_doc.pages.append(pikepdf.Page(tiled_page))
        self.needs_run = False

        return True
