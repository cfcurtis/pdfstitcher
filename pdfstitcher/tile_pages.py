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


MAX_SIZE_PX = 14400

class SW_UNITS(IntEnum):
    INCHES = 0
    CENTIMETERS = 1


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
        units=SW_UNITS.INCHES,
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

        if isinstance(page_range, str):
            self.page_range = utils.parse_page_range(page_range)
        elif isinstance(page_range, (list, tuple)):
            self.page_range = page_range
        else:
            self.page_range = []

        self.units = units
        self.set_trim(trim)
        self.margin = margin
        self.rotation = rotation
        self.actually_trim = actually_trim
        self.override_trim = override_trim

        self.col_major = col_major
        self.right_to_left = right_to_left
        self.bottom_to_top = bottom_to_top

        self.rows = rows
        self.cols = cols

        self.target_height = target_height
        self.target_width = target_width

        if self.target_height:
            self.target_height = self.units_to_px(self.target_height)
        if self.target_width:
            self.target_width = self.units_to_px(self.target_width)

        self.vertical_align = vertical_align
        self.horizontal_align = horizontal_align

    def units_to_px(self, val):
        pxval = val * 72
        if self.units == SW_UNITS.INCHES:
            return pxval
        else:
            return pxval / 2.54

    def px_to_units(self, val):
        inch_val = val / 72
        if self.units == SW_UNITS.INCHES:
            return inch_val
        else:
            return inch_val * 2.54

    def set_trim(self, trim):
        if len(trim) == 1:
            self.trim = [trim, trim, trim, trim]

        if len(trim) == 2:
            self.trim = [trim[0], trim[0], trim[1], trim[1]]

        if len(trim) == 4:
            self.trim = trim

        else:
            print(_('Invalid trim value specified, ignoring'))
            self.trim = [0, 0, 0, 0]

    def show_options(self):
        # convert the margin and trim options into pixels
        # translation_note: in = "inches", cm = "centimetres"
        unitstr = _('cm') if self.units == SW_UNITS.CENTIMETERS else _('in')
        rotstr = _('None')

        if self.rotation == SW_ROTATION.CLOCKWISE:
            rotstr = _('Clockwise')
        elif self.rotation == SW_ROTATION.COUNTERCLOCKWISE:
            rotstr = _('Counterclockwise')
        elif self.rotation == SW_ROTATION.TURNAROUND:
            # translation_note: Rotates 180 degrees. Not exposed in PDFStitcher GUI
            rotstr = _('Turn Around')

        orderstr = _('Rows then columns')
        if self.col_major:
            orderstr = _('Columns then rows')

        lrstr = _('Left to right')
        if self.right_to_left:
            lrstr = _('Right to left')

        btstr = _('Top to bottom')
        if self.bottom_to_top:
            btstr = _('Bottom to top')

        if self.vertical_align is SW_ALIGN_V.BOTTOM:
            alvstr = _('Bottom')
        elif self.vertical_align is SW_ALIGN_V.MID:
            alvstr = _('Middle')
        elif self.vertical_align is SW_ALIGN_V.TOP:
            alvstr = _('Top')

        if self.horizontal_align is SW_ALIGN_H.LEFT:
            alhstr = _('Left')
        elif self.horizontal_align is SW_ALIGN_H.MID:
            alhstr = _('Middle')
        elif self.horizontal_align is SW_ALIGN_H.RIGHT:
            alhstr = _('Right')

        print(_('Tiling with {} rows and {} columns').format(self.rows, self.cols))
        print(_('Options') + ':')
        print('    ' + _('Margins') + ': {} {}'.format(self.margin, unitstr))
        print('    ' + _('Trim') + ': {} {}'.format(self.trim, unitstr))
        print('    ' + _('Rotation') + ': {}'.format(rotstr))
        print('    ' + _('Page order') + ': {}, {}, {}'.format(orderstr, lrstr, btstr))
        print('    ' + _('Vertical alignment') + ': {}'.format(alvstr))
        print('    ' + _('Horizontal alignment') + ': {}'.format(alhstr))

        return unitstr

    def run(
        self,
        rows=None,
        cols=None,
        target_width=None,
        target_height=None,
        vertical_align=None,
        horizontal_align=None,
    ):

        if rows is not None:
            self.rows = rows
        if cols is not None:
            self.cols = cols

        if target_width is not None:
            self.target_width = self.units_to_px(target_width)
        if target_height is not None:
            self.target_height = self.units_to_px(target_height)

        if vertical_align is not None:
            self.vertical_align = vertical_align
        if horizontal_align is not None:
            self.horizontal_align = horizontal_align

        if self.in_doc is None:
            print(_('Input document not loaded'))
            return

        # initialize a new document
        new_doc = utils.init_new_doc(self.in_doc)

        # define the dictionary to store xobjects, unless we're just trimming/adding margins to one page
        if len(self.page_range) > 1:
            content_dict = pikepdf.Dictionary({})
        else:
            content_dict = None

        page_names = []
        pw = []
        ph = []

        page_count = len(self.in_doc.pages)
        trim = [self.units_to_px(t) for t in self.trim]

        # initialize the width/height indices based on page rotation
        page_rot = 0

        if '/Rotate' in self.in_doc.Root.Pages.keys():
            page_rot = self.in_doc.Root.Pages.Rotate

        for p in self.page_range:
            if p > 0:
                break

        # get a pointer to the reference page and parse out the width and height
        ref_page = self.in_doc.pages[p - 1]
        ref_width, ref_height = utils.get_page_dims(ref_page, page_rot)

        user_unit = 1
        if '/UserUnit' in ref_page.keys():
            user_unit = float(ref_page.UserUnit)

        different_size = set()

        for p in self.page_range:
            if p > page_count:
                print(_('Only {} pages in document, skipping {}').format(page_count, p))
                continue

            if p > 0:
                pagekey = f'/Page{p}'

                # Check if it's already been copied (in case of duplicate page numbers)
                if content_dict is None or pagekey not in content_dict.keys():
                    # get a reference to the input document page. DO NOT MODIFY.
                    in_doc_page = self.in_doc.pages[p - 1]
                    new_page = copy.copy(in_doc_page)

                    if '/Rotate' in in_doc_page.keys():
                        page_rot = in_doc_page.Rotate

                    if self.override_trim:
                        new_page.TrimBox = copy.copy(in_doc_page.MediaBox)

                    # set the trim box to cut off content if requested
                    if self.actually_trim:
                        # things get tricky if there's rotation, because the user sees top/bottom as right/left
                        # trim: left, right, top, bottom as defined visually
                        # trimbox: left, bottom, right, top (absolute coordinates)
                        if page_rot == 0:
                            rtrim = [trim[0], trim[3], trim[1], trim[2]]
                        elif page_rot == 90:
                            rtrim = [trim[2], trim[0], trim[3], trim[1]]
                        elif page_rot == 180:
                            rtrim = [trim[3], trim[0], trim[2], trim[1]]
                        elif page_rot in (-90, 270):
                            rtrim = [trim[3], trim[1], trim[2], trim[0]]
                        
                        # lowercase trimbox returns TrimBox if it exists, MediaBox otherwise
                        in_trim = [float(t) for t in in_doc_page.trimbox]
                        new_page.TrimBox = [in_trim[0] + rtrim[0],
                                            in_trim[1] + rtrim[1],
                                            in_trim[2] - rtrim[2],
                                            in_trim[3] - rtrim[3]]
                # get the input page height and width
                p_width, p_height = utils.get_page_dims(in_doc_page, page_rot)
                pw.append(p_width)
                ph.append(p_height)
                page_names.append(pagekey)

                if abs(p_width - ref_width) > 1 or abs(p_height - ref_height) > 1:
                    different_size.add(p)

                # update the reference handles to be the current page
                ref_width = p_width
                ref_height = p_height
                
                if content_dict is not None:
                    content_dict[pagekey] = new_doc.copy_foreign(
                        new_page.as_form_xobject()
                    )
                else:
                    new_doc.pages.append(new_page)
                    new_page = new_doc.pages[-1]

            else:
                # blank page, use the reference for sizes and such
                page_names.append(None)
                pw.append(ref_width)
                ph.append(ref_height)

        if len(different_size) > 0:
            print(
                _(
                    'Warning: The pages {} have a different size than the page before'
                ).format(different_size)
            )

        n_tiles = len(page_names)

        # check which one is specified
        if self.cols is not None and self.cols > 0:
            self.rows = math.ceil(n_tiles / self.cols)
            if self.rows == 1 and self.cols > n_tiles:
                print(
                    _(
                        'Warning: requested {} columns, but there are only {} pages'
                    ).format(self.cols, n_tiles)
                )
                self.cols = n_tiles

        elif self.rows is not None and self.rows > 0:
            self.cols = math.ceil(n_tiles / self.rows)
            if self.cols == 1 and self.rows > n_tiles:
                print(
                    _('Warning: requested {} rows, but there are only {} pages').format(
                        self.rows, n_tiles
                    )
                )
                self.rows = n_tiles
        else:
            # try for square
            self.cols = math.ceil(math.sqrt(n_tiles))
            self.rows = math.ceil(n_tiles / self.cols)

        # after calculating rows/cols but before reordering trim, show the user the selected options
        unitstr = self.show_options()

        # swap the trim order
        # default: left,right,top,bottom
        order = [0, 1, 2, 3]

        if self.rotation == SW_ROTATION.CLOCKWISE:
            order = [3, 2, 0, 1]
        if self.rotation == SW_ROTATION.COUNTERCLOCKWISE:
            order = [2, 3, 1, 0]
        if self.rotation == SW_ROTATION.TURNAROUND:
            order = [1, 0, 3, 2]

        trim = [self.units_to_px(t / user_unit) for t in self.trim]
        trim = [trim[o] for o in order]

        if self.rotation in (SW_ROTATION.CLOCKWISE, SW_ROTATION.COUNTERCLOCKWISE):
            # swap width and height of pages
            ph, pw = pw, ph

        width = 0
        height = 0
        col_width = [0] * self.cols
        row_height = [0] * self.rows

        if self.target_width and self.target_height:
            # determine size of each page based on requested dimensions
            width = self.target_width
            height = self.target_height
            page_box_width = self.target_width / self.cols
            page_box_height = self.target_height / self.rows
            page_box_defined = True
        else:
            # Find the grid that contains the maximum page size for each row/col
            if self.col_major:
                for c in range(self.cols):
                    col_width[c] = max(
                        pw[c * self.rows : c * self.rows + self.rows]
                    ) - (trim[0] + trim[1])

                for r in range(self.rows):
                    row_height[r] = max(ph[r : n_tiles : self.cols]) - (
                        trim[2] + trim[3]
                    )
            else:
                for r in range(self.rows):
                    row_height[r] = max(
                        ph[r * self.cols : r * self.cols + self.cols]
                    ) - (trim[2] + trim[3])

                for c in range(self.cols):
                    col_width[c] = max(pw[c : n_tiles : self.rows]) - (
                        trim[0] + trim[1]
                    )

            if self.right_to_left:
                col_width.reverse()

            if self.bottom_to_top:
                row_height.reverse()

            width = sum(col_width)
            height = sum(row_height)
            page_box_defined = False

        # create a new document with a page big enough to contain all the tiled pages, plus requested margin
        margin = self.units_to_px(self.margin / user_unit)

        if content_dict is None:        
            media_box = [
                new_page.MediaBox[0] - (margin - trim[0]),
                new_page.MediaBox[1] -(margin - trim[3]),
                new_page.MediaBox[0] + width + margin,
                new_page.MediaBox[1] + height + margin,
            ]
        else:
            media_box = [
                new_page.MediaBox[0], 
                new_page.MediaBox[1], 
                width + 2 * margin, 
                height + 2 * margin
            ]

        # check if it exceeds Adobe's 200 inch maximum size
        if media_box[2] > MAX_SIZE_PX or media_box[3] > MAX_SIZE_PX:
            print(62 * '*')
            print(
                _(
                    'Warning! Output is larger than {} {}, may not open correctly.'
                ).format(round(self.px_to_units(MAX_SIZE_PX)), unitstr)
            )
            print(62 * '*')

        print(
            _('Output size:')
            + ' {:0.2f} x {:0.2f} {}'.format(
                user_unit * self.px_to_units(width + 2 * margin),
                user_unit * self.px_to_units(height + 2 * margin),
                unitstr,
            )
        )

        if content_dict is None:
            # just expand the margins and return
            new_page.MediaBox = media_box
            new_page.CropBox = media_box
            return new_doc

        i = 0
        content_txt = ''
        performed_scale = False

        # loop through all the page xobjects and place the non-empty ones
        for i in range(n_tiles):
            if not page_names[i]:
                continue

            if self.col_major:
                c = math.floor(i / self.rows)
                r = i % self.rows
            else:
                r = math.floor(i / self.cols)
                c = i % self.cols

            if self.right_to_left:
                c = self.cols - c - 1

            if self.bottom_to_top:
                r = self.rows - r - 1

            scale_factor = 1

            if page_box_defined:
                # calculate scaling factors based on source page size
                source_width = pw[i]
                source_height = ph[i]
                scalef_width = page_box_width / source_width
                scalef_height = page_box_height / source_height
                # take the smaller scaling factor so that the page will fit into its box
                scale_factor = min(scalef_width, scalef_height)
                cpos_x0 = c * page_box_width - c * (trim[0] + trim[1])
                cpos_y0 = (self.rows - r - 1) * page_box_height - (
                    self.rows - r - 1
                ) * (trim[2] + trim[3])
            else:
                cpos_x0 = sum(col_width[:c]) - trim[0]
                cpos_y0 = sum(row_height[r + 1 :]) - trim[3]

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

            # calculate shift
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

            # apply shift
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
            content_txt += f'q {R[0]} {R[1]} {R[2]} {R[3]} {x0} {y0} cm '
            content_txt += f'{page_names[i]} Do Q '

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
        if user_unit != 1:
            tiled_page.UserUnit = user_unit

        new_doc.pages.append(tiled_page)

        return new_doc


def main(args):

    utils.setup_locale()

    # first try opening the document
    try:
        in_doc = pikepdf.Pdf.open(args.input)
    except:
        print(_('Unable to open') + ' ' + args.input)
        sys.exit()

    tiler = PageTiler(in_doc)

    if args.pages is not None:
        tiler.page_range = utils.parse_page_range(args.pages)
    else:
        tiler.page_range = [i + 1 for i in range(len(in_doc.pages))]

    if args.margin is not None:
        # all the docs/examples seem to assume 72 dpi all the time
        tiler.margin = utils.txt_to_float(args.margin)

    if args.trim is not None:
        trim = [utils.txt_to_float(t) for t in args.trim.split(',')]
        tiler.set_trim(trim)

    if args.rotate is not None:
        failed = False
        r = int(args.rotate)
        if r == 0:
            tiler.rotation = SW_ROTATION.NONE
        elif r == 90:
            tiler.rotation = SW_ROTATION.CLOCKWISE
        elif r == 180:
            tiler.rotation = SW_ROTATION.TURNAROUND
        elif r == 270:
            tiler.rotation = SW_ROTATION.COUNTERCLOCKWISE
        else:
            print(_("Invalid rotation value"))
            sys.exit()

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
        description=_('Tile PDF pages into one document.'),
        epilog=_('Note: If both rows and columns are specified, rows are ignored.')
        + ' '
        + _('To insert a blank page, include a zero in the page list.'),
    )

    parser.add_argument(
        'input',
        help=_('Input filename (pdf)'),
    )
    parser.add_argument(
        'output',
        help=_('Output filename (pdf)'),
    )
    parser.add_argument(
        '-p',
        '--pages',
        help=_(
            'Pages to tile. May be range or list (e.g. 1-5 or 1,3,5-7, etc). Default: entire document.'
        ),
    )
    parser.add_argument(
        '-r',
        '--rows',
        type=int,
        help=_('Number of rows in tiled grid.'),
    )
    parser.add_argument(
        '-c',
        '--columns',
        type=int,
        help=_('Number of columns in tiled grid.'),
    )
    parser.add_argument(
        '-m',
        '--margin',
        help=_('Margin size in inches.'),
    )
    parser.add_argument(
        '-t',
        '--trim',
        help=_('Amount to trim from edges')
        + ' '
        + _(
            'given as left,right,top,bottom (e.g. 0.5,0,0.5,0 would trim half an inch from left and top)'
        ),
    )
    parser.add_argument(
        '-R',
        '--rotate',
        type=int,
        help=_('Rotate pages (90, 180, or 270 degrees)'),
    )

    return parser.parse_args()


if __name__ == "__main__":

    utils.setup_locale()
    args = parse_arguments()
    new_doc, success = main(args)
