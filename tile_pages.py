# PDFStitcher is a utility to work with PDF sewing patterns.
# Copyright (C) 2021 Charlotte Curtis
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

import pikepdf
from pikepdf import _cpphelpers
import subprocess
import argparse
import sys
import math
import copy
import utils
from gettext import gettext as _

class PageTiler:
    def __init__(
            self,
            in_doc = None,
            page_range = [],
            units = 0,
            trim = [0,0,0,0],
            margin = 0,
            rotation = 0,
            actually_trim = False,
            override_trim = False,
            col_major = False,
            right_to_left = False,
            bottom_to_top = False,
        ):
        
        self.in_doc = in_doc
        self.page_range = page_range

        # 0 = inches, 1 = centimetres
        self.units = units
        self.trim = self.set_trim(trim)
        self.margin = margin
        self.rotation = rotation
        self.actually_trim = actually_trim
        self.override_trim = override_trim

        self.col_major = col_major
        self.right_to_left = right_to_left
        self.bottom_to_top = bottom_to_top

    def units_to_px(self,val):
        pxval = val*72
        if self.units == 0:
            return pxval
        else:
            return pxval/2.54
        
    def px_to_units(self,val):
        inch_val = val/72
        if self.units == 0:
            return inch_val
        else:
            return inch_val*2.54

    def set_trim(self,trim):
        if len(trim) == 1:
            self.trim = [trim,trim,trim,trim]
        
        if len(trim) == 2:
            self.trim = [trim[0],trim[0],trim[1],trim[1]]
        
        if len(trim) == 4:
            self.trim = trim
        
        else:
            print(_('Invalid trim value specified, ignoring'))
            self.trim = [0,0,0,0]

    def run(self,rows=0,cols=0):
        if self.in_doc is None:
            print(_('Input document not loaded'))
            return
        
        # initialize a new document and copy over the layer info (OCGs) if it exists
        new_doc = pikepdf.Pdf.new()

        if '/OCProperties' in self.in_doc.Root.keys():
            localRoot = new_doc.copy_foreign(self.in_doc.Root)
            new_doc.Root.OCProperties = localRoot.OCProperties

        content_dict = pikepdf.Dictionary({})
        page_names = []
        pw = None
        ph = None
        page_size_ref = 0

        page_count = len(self.in_doc.pages)
        trim = [self.units_to_px(t) for t in self.trim]

        # initialize the width/height indices based on page rotation
        page_rot = 0

        if '/Rotate' in self.in_doc.Root.Pages.keys():
            page_rot = self.in_doc.Root.Pages.Rotate   
        
        for p in self.page_range:
            if p > page_count:
                print(_('Only {} pages in document, skipping {}').format(page_count,p))
                continue

            if p > 0:
                pagekey = f'/Page{p}'
                
                if pagekey not in content_dict.keys():
                    # copy the page over as an xobject
                    # pikepdf.pages is zero indexed, so subtract one
                    localpage = new_doc.copy_foreign(self.in_doc.pages[p-1])

                    if self.override_trim:
                        localpage.TrimBox = copy.copy(localpage.MediaBox)
                    
                    # only get the width/height for the first page
                    if pw is None:
                        if '/Rotate' in localpage.keys():
                            page_rot = localpage.Rotate

                        if page_rot == 90 or page_rot == -90:
                            pw = float(localpage.MediaBox[3])
                            ph = float(localpage.MediaBox[2])
                        else:
                            pw = float(localpage.MediaBox[2])
                            ph = float(localpage.MediaBox[3])        
                        
                        # store which page we grabbed the size from
                        page_size_ref = p

                    else:
                        if page_rot == 90 or page_rot == -90:
                            this_pw = float(localpage.MediaBox[3])
                            this_ph = float(localpage.MediaBox[2])
                        else:
                            this_pw = float(localpage.MediaBox[2])
                            this_ph = float(localpage.MediaBox[3])
                        
                        if abs(pw - this_pw) > 1 or abs(ph - this_ph) > 1:
                            print(_('Warning: page {} is a different size from {}, output may be unpredictable'.format(p,page_size_ref)))
                    
                    # set the trim box to cut off content if requested
                    if self.actually_trim:
                        if '/TrimBox' not in localpage.keys():
                            localpage.TrimBox = copy.copy(localpage.MediaBox)

                        # things get tricky if there's rotation, because the user sees top/bottom as right/left
                        # trim: left, right, top, bottom as defined visually
                        # trimbox: left, bottom, width, height
                        if page_rot == 0:
                            localpage.TrimBox[0] = float(localpage.TrimBox[0]) + trim[0]
                            localpage.TrimBox[1] = float(localpage.TrimBox[1]) + trim[3]
                            localpage.TrimBox[2] = float(localpage.TrimBox[2]) - trim[1]
                            localpage.TrimBox[3] = float(localpage.TrimBox[3]) - trim[2]

                        elif page_rot == 90:
                            localpage.TrimBox[0] = float(localpage.TrimBox[0]) + trim[2]
                            localpage.TrimBox[1] = float(localpage.TrimBox[1]) + trim[0]
                            localpage.TrimBox[2] = float(localpage.TrimBox[2]) - trim[3]
                            localpage.TrimBox[3] = float(localpage.TrimBox[3]) - trim[1]

                        elif page_rot == -90:
                            localpage.TrimBox[0] = float(localpage.TrimBox[0]) + trim[3]
                            localpage.TrimBox[1] = float(localpage.TrimBox[1]) + trim[1]
                            localpage.TrimBox[2] = float(localpage.TrimBox[2]) - trim[2]
                            localpage.TrimBox[3] = float(localpage.TrimBox[3]) - trim[0]
 
                    content_dict[pagekey] = pikepdf.Page(localpage).as_form_xobject()

                page_names.append(pagekey)
            else:
                page_names.append(None)
        
        # create a new document with a page big enough to contain all the tiled pages, plus requested margin
        # figure out how big it needs to be based on requested columns/rows
        n_tiles = len(page_names)
        if cols == 0 and rows == 0:
            # try for square
            cols = math.ceil(math.sqrt(n_tiles))
            rows = cols
        
        # columns take priority if both are specified
        if cols > 0:
            rrows = rows
            rows = math.ceil(n_tiles/cols)
            if rrows != rows and rrows != 0:
                print(_('Warning: requested {} columns and {} rows, but {} rows are needed with {} pages').format(cols,rrows,rows,n_tiles))
        else:
            cols = math.ceil(n_tiles/rows)
        
        # convert the margin and trim options into pixels
        unitstr = 'cm' if self.units else 'in'
        margin = self.units_to_px(self.margin)

        rotstr = _('None')
        
        if self.rotation == 1:
            rotstr = _('Clockwise')

        if self.rotation == 2:
            rotstr = _('Counterclockwise')
        
        orderstr = _('Rows then columns')
        if self.col_major:
            orderstr = _('Columns then rows')
        
        lrstr = _('Left to right')
        if self.right_to_left:
            lrstr = _('Right to left')
        
        btstr = _('Top to bottom')
        if self.bottom_to_top:
            btstr = _('Bottom to top')

        print(_('Tiling with {} rows and {} columns').format(rows,cols))
        print(_('Options') + ':')
        print('    ' + _('Margins') + ': {} {}'.format(self.margin,unitstr))
        print('    ' + _('Trim') + ': {} {}'.format(self.trim,unitstr))
        print('    ' + _('Rotation') + ': {}'.format(rotstr))
        print('    ' + _('Page order') + ': {}, {}, {}'.format(orderstr, lrstr, btstr))

        # define the media box with the final grid + margins
        # run through the width/height combos to find the maximum required
        # R is the rotation matrix (default to identity)
        R = [1,0,0,1]

        # We need to account for the shift in origin if page rotation is applied
        o_shift = [0,0]

        if self.rotation != 0:
            # define the rotation transform and
            # swap the trim order
            if self.rotation == 1:
                R = [0,-1,1,0]
                o_shift = [0,pw]
                order = [3,2,0,1]

            if self.rotation == 2:
                R = [0,1,-1,0]
                o_shift = [ph,0]
                order = [2,3,1,0]
                       
            # swap width and height of pages
            tmp = ph
            ph = pw
            pw = tmp
            
            trim = [trim[o] for o in order]
        
        # define the output page media box
        width = (pw - trim[0] - trim[1])*cols
        height = (ph - trim[2] - trim[3])*rows
        media_box = [0,0,width + 2*margin,height + 2*margin]

        if media_box[2] > 14400 or media_box[3] > 14400:
            print ('**************************************')
            if self.units == 1:
                print(_('Warning! Output is larger than 508 cm, may not open correctly.'))
            else:
                print(_('Warning! Output is larger than 200 in, may not open correctly.'))
            print ('**************************************')
        print(_('Output size:') + ' {:0.2f} x {:0.2f} {}'.format(self.px_to_units(width + 2*margin), 
            self.px_to_units(height + 2*margin),unitstr))
        
        i = 0
        content_txt = ''
        
        for i in range(n_tiles):
            if not page_names[i]:
                continue

            if self.col_major:
                c = math.floor(i/rows)
                r = i % rows
            else:
                r = math.floor(i/cols)
                c = i % cols
            
            if self.right_to_left:
                c = cols - c - 1
            
            if not self.bottom_to_top:
                r = rows - r - 1
            
            x0 = margin - trim[0] + c*(pw - trim[0] - trim[1]) + o_shift[0]
            y0 = margin - trim[3] + r*(ph - trim[2] - trim[3]) + o_shift[1]

            # don't scale, just shift and rotate
            # first shift to origin, then rotate, then shift to final destination
            content_txt += f'q {R[0]} {R[1]} {R[2]} {R[3]} {x0} {y0} cm '
            content_txt += f'{page_names[i]} Do Q '

        newpage = pikepdf.Dictionary(
            Type=pikepdf.Name.Page, 
            MediaBox=media_box,
            Resources=pikepdf.Dictionary(XObject=content_dict),
            Contents=pikepdf.Stream(new_doc,content_txt.encode())
        )

        new_doc.pages.append(newpage)
        return new_doc

def main(args):
    # first try opening the document
    try:
        in_doc = pikepdf.Pdf.open(args.input)
    except:
        print(_('Unable to open') + ' ' + args.input)
        sys.exit()
    
    tiler = PageTiler(in_doc)

    if args.pages is not None:
        tiler.set_page_range(args.pages)

    if args.margins is not None:
        # all the docs/examples seem to assume 72 dpi all the time
        margin = utils.txt_to_float(args.margins)
        tiler.set_margin(margin)

    if args.trim is not None:
        trim = [utils.txt_to_float(t) for t in args.trim.split(',')]
        tiler.set_trim(trim)
    
    if args.rotate is not None:
        tiler.set_rotation(int(args.rotate))

    cols = 0
    rows = 0
    if args.columns is not None:
        cols = int(args.columns)

    if args.rows is not None:
        rows = int(args.rows)
    
    # run it!
    new_doc = tiler.run(rows,cols)
        
    try:
        new_doc.save(args.output)
        success = True
    except:
        success = False

    return new_doc, success
