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
from pdfstitcher.utils import Config, SW_ROTATION
from pdfstitcher.processing.procbase import ProcessingBase


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
        self, content_dict: pikepdf.Dictionary, p: int, info: list, user_rotation: int
    ) -> None:
        """
        Extracts page number p from the input document and adds it to the page_dict,
        performs trimming if requested, and stores (trimmed) page dimensions. Lots going on.
        """
        pagekey = f"/Page{p}"
        # Check if it's already been copied (in case of duplicate page numbers)
        if pagekey in content_dict.keys():
            # append a duplicate of this page's info
            for p_info in info:
                if p_info["pagekey"] == pagekey:
                    p_info = p_info.copy()
                    break
            # could be the same page with different rotation
            p_info["rotation"] = user_rotation
            info.append(p_info)
            return

        # get a convenient reference to the page
        in_doc_page = self.in_doc.pages[p - 1]

        # magic sauce to copy the info to the new document as an XOBject
        content_dict[pagekey] = self.out_doc.copy_foreign(
            in_doc_page.as_form_xobject(handle_transformations=True)
        )

        # get the page rotation and user unit
        page_rot = (
            in_doc_page.Rotate % 360
            if "/Rotate" in in_doc_page.keys()
            else self.doc_info["root_rotation"]
        )
        page_uu = float(in_doc_page.UserUnit) if "/UserUnit" in in_doc_page.keys() else 1

        # lowercase trimbox returns TrimBox if it exists, MediaBox otherwise
        # overriding trimbox will use the media box instead, sometimes fixes weird things
        if self.p["override_trim"]:
            bbox = copy.copy(in_doc_page.MediaBox)
        else:
            bbox = copy.copy(in_doc_page.trimbox)

        if self.p["actually_trim"]:
            # set the trim box to cut off content if requested
            # trim needs to be rotated as it's defined in the rotated space, but the bbox is not
            page_trim = self._get_page_trim(page_uu, page_rot)
            bbox = [
                float(bbox[0]) + page_trim[0],
                float(bbox[1]) + page_trim[1],
                float(bbox[2]) - page_trim[2],
                float(bbox[3]) - page_trim[3],
            ]
        content_dict[pagekey].BBox = bbox

        # define the matrix in case it doesn't exist (assumed identity)
        matrix = (
            pikepdf.Matrix(content_dict[pagekey].Matrix)
            if "/Matrix" in content_dict[pagekey].keys()
            else pikepdf.Matrix()
        )

        # Scale the matrix by the output user unit
        # Case 1: page UU and output UU are both 1 -> no scaling
        # Case 2: page UU is 1, output UU is 10 -> scale by 1/10
        # Case 3: page UU is 10, output UU is 1 -> no scaling (matrix is already scaled)
        # Case 4: page UU is 10, output UU is 10 -> scale by 1/10 (avoid double scaling)
        matrix = matrix.scaled(1 / self.output_uu, 1 / self.output_uu)

        # also translate the matrix by the non-rotated trim value (scaled to the output UU)
        page_trim = self._get_page_trim(self.output_uu, 0)
        content_dict[pagekey].Matrix = matrix.translated(-page_trim[0], -page_trim[1]).shorthand

        # update the info dictionary with the page dimensions
        # page rotation needs to be passed as global because it isn't copied into the XObject
        p_width, p_height = utils.get_page_dims(
            content_dict[pagekey],
            global_rotation=page_rot,
            page_uu=page_uu,
            output_uu=self.output_uu,
        )

        # if we're not actually trimming, subtract the trim from the page size
        if not self.p["actually_trim"]:
            p_width -= page_trim[0] + page_trim[2]
            p_height -= page_trim[1] + page_trim[3]

        # append the page info
        info.append(
            {"width": p_width, "height": p_height, "pagekey": pagekey, "rotation": user_rotation}
        )
        return

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
        prev_width = None
        prev_height = None

        for page_info in self.page_range_with_rotation:
            p = page_info["page"]
            # set the rotation as either page-specific or global
            user_rotation = (
                page_info["rotation"]
                if page_info["rotation"] != SW_ROTATION.UNSET
                else self.p["rotation"]
            )
            if p == 0:
                # blank page: append a placeholder to the info list
                info.append(
                    {
                        "width": prev_width,
                        "height": prev_height,
                        "pagekey": None,
                        "rotation": user_rotation,
                    }
                )
                continue

            self._process_page(content_dict, p, info, user_rotation)

            if prev_width is not None and (
                abs(info[-1]["width"] - prev_width) > 1 or abs(info[-1]["height"] - prev_height) > 1
            ):
                different_size.add(p)

            # update the reference handles to be the current page
            prev_width = info[-1]["width"]
            prev_height = info[-1]["height"]

        # go back and update any zero pages with the first non-zero dimension
        first_non_zero = next((p for p in self.page_range if p > 0), None)
        if first_non_zero is None:
            self.warn(_("No pages selected!"))
            return None

        for p_info in info:
            if p_info["width"] is None:
                p_info["width"] = info[first_non_zero]["width"]
                p_info["height"] = info[first_non_zero]["height"]

        if len(different_size) > 0:
            self._warn(
                _("Warning: pages {} have a different size than the page before").format(
                    different_size
                )
            )

        return content_dict, info

    def _get_page_trim(self, page_uu: float, rotation: int) -> list:
        """
        Rearranges the trim order based on (PDF-defined) page rotation.
        Provides the order in PDF format (left, bottom, right, top).
        Note that the rotation is in degrees as specified by the PDF (opaque to the user), NOT the requested rotation.
        """
        # things get tricky if there's rotation, because the user sees top/bottom as right/left
        # Rotation is in clockwise degrees, so we need to adjust the trim order accordingly
        # trim: left, right, top, bottom as defined visually
        # trimbox: left, bottom, right, top (absolute coordinates)
        page_trim = [Config.general["units"].units_to_pts(t, page_uu) for t in self.p["trim"]]

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
        pw, ph = list(zip(*[utils.get_apparent_page_dims(p_info) for p_info in info]))
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

    def _set_output_user_unit(self):
        """
        Find the maximum user_unit defined in the document, then use this for the new document.
        """
        self.output_uu = 1
        for p in self.page_range:
            page = self.in_doc.pages[p - 1]
            if "/UserUnit" in page.keys() and page.UserUnit > self.output_uu:
                self.output_uu = float(page.UserUnit)

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
                self._warn(
                    _("Warning: requested {} columns, but there are only {} pages").format(
                        self.cols, n_tiles
                    )
                )
                self.cols = n_tiles

        elif self.p["rows"] is not None and self.p["rows"] > 0:
            self.rows = self.p["rows"]
            self.cols = math.ceil(n_tiles / self.rows)
            if self.cols == 1 and self.rows > n_tiles:
                self._warn(
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

    def _calc_shift(
        self, col_width: float, row_height: float, page_info: dict, scale: float = 1
    ) -> tuple:
        """
        Calculates the shift needed to align the tile in the grid, accounting for rotation.
        Returns a tuple of (shift_right, shift_up).
        """

        h_align = self.p["horizontal_align"] if "horizontal_align" in self.p else SW_ALIGN_H.MID
        v_align = self.p["vertical_align"] if "vertical_align" in self.p else SW_ALIGN_V.MID

        # The gap is just the difference between the grid dimension and page dimensions
        width, height = utils.get_apparent_page_dims(page_info)
        h_space = col_width - width * scale
        v_space = row_height - height * scale

        shift_right = 0
        shift_up = 0
        if h_align == SW_ALIGN_H.MID:
            shift_right = h_space / 2
        elif h_align == SW_ALIGN_H.RIGHT:
            shift_right = h_space

        if v_align == SW_ALIGN_V.MID:
            shift_up = v_space / 2
        elif v_align == SW_ALIGN_V.TOP:
            shift_up = v_space

        # account for shift in origin if we are rotating
        if page_info["rotation"] == SW_ROTATION.CLOCKWISE:
            # CW/CCW seems backwards because we are rotating the coordinate system, not the object
            shift_up += page_info["width"]
        elif page_info["rotation"] == SW_ROTATION.COUNTERCLOCKWISE:
            shift_right += page_info["height"]
        elif page_info["rotation"] == SW_ROTATION.TURNAROUND:
            shift_up += height
            shift_right += width

        return shift_right, shift_up

    def _compute_T_matrix(
        self, i: int, col_width: list, row_height: list, page_info: dict, scale: float = 1
    ) -> list:
        """
        Calculates the transformation matrix for page i (zero indexed).
        Returns a list of 6 elements representing the matrix.
        """
        r, c = self._grid_position(i)

        # the origin is the sum of all the sizes before the current one
        # where should the top-left corner of the page be positioned?
        x0 = sum(col_width[:c])
        y0 = sum(row_height[r + 1 :])

        # might need to shift within the grid cell
        shift = self._calc_shift(col_width[c], row_height[r], page_info, scale)
        x0 += shift[0]
        y0 += shift[1]

        if page_info["rotation"] == SW_ROTATION.NONE:
            R = [1, 0, 0, 1]
        elif page_info["rotation"] == SW_ROTATION.CLOCKWISE:
            R = [0, -1, 1, 0]
        elif page_info["rotation"] == SW_ROTATION.COUNTERCLOCKWISE:
            R = [0, 1, -1, 0]
        elif page_info["rotation"] == SW_ROTATION.TURNAROUND:
            R = [-1, 0, 0, -1]

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

        size_warning = utils.print_media_box(media_box, self.output_uu)
        if size_warning:
            self._warn(size_warning)

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
