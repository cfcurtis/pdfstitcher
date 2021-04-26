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
# along with this program. If not, see <https://www.gnu.org/licenses/>.


import pikepdf
from pikepdf import _cpphelpers
import argparse
import sys
import math
import copy
import types
import utils

SW_UNITS = types.SimpleNamespace()
SW_UNITS.INCHES = 0
SW_UNITS.CENTIMETERS = 1

SW_ROTATION = types.SimpleNamespace()
SW_ROTATION.NONE = 0
SW_ROTATION.CLOCKWISE = 1
SW_ROTATION.COUNTERCLOCKWISE = 2
SW_ROTATION.TURNAROUND = 3


class PageTiler:
    def __init__(
            self,
            in_doc = None,
            page_range = None,
            units = SW_UNITS.INCHES,
            trim = [0,0,0,0],
            margin = 0,
            rotation = SW_ROTATION.NONE,
            actually_trim = False,
            override_trim = False,
            col_major = False,
            right_to_left = False,
            bottom_to_top = False,
            rows = None,
            cols = None,
            target_width = None,
            target_height = None,
            center_content = None,
        ):
        
        utils.setup_locale()
        
        self.in_doc = in_doc
        
        if page_range:
            self.page_range = utils.parse_page_range(page_range)
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
        
        self.center_content = center_content

    def units_to_px(self,val):
        pxval = val*72
        if self.units == SW_UNITS.INCHES:
            return pxval
        else:
            return pxval/2.54
        
    def px_to_units(self,val):
        inch_val = val/72
        if self.units == SW_UNITS.INCHES:
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

    def run(
            self,
            rows = None,
            cols = None,
            target_width = None,
            target_height = None,
            center_content = None,
        ):
        
        if rows is not None:
            self.rows = rows
        if cols is not None:
            self.cols = cols
        
        if target_width is not None:
            self.target_width = self.units_to_px(target_width)
        if target_height is not None:
            self.target_height = self.units_to_px(target_height)
        
        if center_content is not None:
            self.center_content = center_content
        
        if self.in_doc is None:
            print(_('Input document not loaded'))
            return
        
        # initialize a new document
        new_doc = utils.init_new_doc(self.in_doc)

        content_dict = pikepdf.Dictionary({})
        page_names = []
        pw = []
        ph = []
        page_size_ref = 0
        
        page_count = len(self.in_doc.pages)
        trim = [self.units_to_px(t) for t in self.trim]
        
        # initialize the width/height indices based on page rotation
        page_rot = 0
        
        if '/Rotate' in self.in_doc.Root.Pages.keys():
            page_rot = self.in_doc.Root.Pages.Rotate
        
        ref_p = self.page_range[0]
        refmbox = self.in_doc.pages[ref_p-1].MediaBox
        
        different_size = set()
        
        for p in self.page_range:
            if p > page_count:
                print(_('Only {} pages in document, skipping {}').format(page_count,p))
                continue
            
            if p > 0:
                pagekey = f'/Page{p}'
                pagembox = self.in_doc.pages[p-1].MediaBox
                
                if pagekey not in content_dict.keys():
                    # copy the page over as an xobject
                    # pikepdf.pages is zero indexed, so subtract one
                    localpage = new_doc.copy_foreign(self.in_doc.pages[p-1])
                    
                    if self.override_trim:
                        localpage.TrimBox = copy.copy(localpage.MediaBox)
                    
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

                pw.append(float(pagembox[2]))
                ph.append(float(pagembox[3]))
                page_names.append(pagekey)

                if abs(pagembox[2] - refmbox[2]) > 1 or abs(pagembox[3] - refmbox[3]) > 1:
                    different_size.add(p)
                
                refmbox = pagembox
            else:
                page_names.append(None)
                pw.append(float(refmbox[2]))
                ph.append(float(refmbox[3]))
        
        print(_('Warning: The size of page(s) {} is different from {}').format(str(different_size)[1:-1], ref_p))
        
        n_tiles = len(page_names)
        
        # create a new document with a page big enough to contain all the tiled pages, plus requested margin
        # figure out how big it needs to be based on requested columns/rows
        if self.cols == 0 and self.rows == 0:
            # try for square
            self.cols = math.ceil(math.sqrt(n_tiles))
            self.rows = self.cols
        
        # columns take priority if both are specified
        if self.cols > 0:
            rrows = self.rows
            self.rows = math.ceil(n_tiles/self.cols)
            if rrows != self.rows and rrows != 0:
                print(_('Warning: requested {} columns and {} rows, but {} rows are needed with {} pages').format(self.cols,rrows,self.rows,n_tiles))
        else:
            self.cols = math.ceil(n_tiles/self.rows)
        
        # convert the margin and trim options into pixels
        unitstr = _('cm') if self.units == SW_UNITS.CENTIMETERS else _('in')
        margin = self.units_to_px(self.margin)
        trim = [self.units_to_px(t) for t in self.trim]

        rotstr = _('None')
        
        if self.rotation == SW_ROTATION.CLOCKWISE:
            rotstr = _('Clockwise')
        elif self.rotation == SW_ROTATION.COUNTERCLOCKWISE:
            rotstr = _('Counterclockwise')
        elif self.rotation == SW_ROTATION.TURNAROUND:
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

        print(_('Tiling with {} rows and {} columns').format(self.rows,self.cols))
        print(_('Options') + ':')
        print('    ' + _('Margins') + ': {} {}'.format(self.margin,unitstr))
        print('    ' + _('Trim') + ': {} {}'.format(self.trim,unitstr))
        print('    ' + _('Rotation') + ': {}'.format(rotstr))
        print('    ' + _('Page order') + ': {}, {}, {}'.format(orderstr, lrstr, btstr))
        
        # swap the trim order
        if self.rotation == SW_ROTATION.NONE:
            # default: left,right,top,bottom
            order = [0,1,2,3]
        if self.rotation == SW_ROTATION.CLOCKWISE:
            order = [3,2,0,1]
        if self.rotation == SW_ROTATION.COUNTERCLOCKWISE:
            order = [2,3,1,0]
        if self.rotation == SW_ROTATION.TURNAROUND:
            order = [1,0,3,2]
        trim = [trim[o] for o in order]
        
        if (self.rotation == SW_ROTATION.CLOCKWISE) or (self.rotation == SW_ROTATION.COUNTERCLOCKWISE):
            # swap width and height of pages
            ph, pw = pw, ph
        
        row_height = [0]*self.rows
        width = 0
        height = 0
                
        if self.target_width and self.target_height:
            width = self.target_width
            height = self.target_height
            row_height = [self.target_width for i in range(self.rows)]
            page_box_width = self.target_width / self.cols
            page_box_height = self.target_height / self.rows
            page_box_defined = True
        else:
            for r in range(self.rows):
                width = max(width,sum(pw[r*self.cols:r*self.cols+self.cols]))
                row_height[r] = max(ph[r*self.cols:r*self.cols+self.cols])
            
            width -= (trim[0] + trim[1])*self.cols
            height = sum(row_height) - (trim[2] + trim[3])*self.rows
            page_box_defined = False
        
        media_box = [0,0,width + 2*margin,height + 2*margin]
        
        max_size_px = 14400
        if media_box[2] > max_size_px or media_box[3] > max_size_px:
            print (62 * '*')
            print(_('Warning! Output is larger than {} {}, may not open correctly.').format(round(self.px_to_units(max_size_px)), unitstr))
            print (62 * '*')
        
        print(_('Output size:') + ' {:0.2f} x {:0.2f} {}'.format(self.px_to_units(width + 2*margin), 
            self.px_to_units(height + 2*margin),unitstr))
        
        i = 0
        content_txt = ''
        performed_scale = False
        
        for i in range(n_tiles):
            if not page_names[i]:
                continue

            if self.col_major:
                c = math.floor(i/self.rows)
                r = i % self.rows
            else:
                r = math.floor(i/self.cols)
                c = i % self.cols
            
            if self.right_to_left:
                c = self.cols - c - 1
            
            if self.bottom_to_top:
                r = self.rows - r - 1
                        
            scale_factor = 1
            scale_shift_right = 0
            scale_shift_up = 0
            
            if page_box_defined:
                # calculate scaling factors based on source page size
                source_width = pw[i]
                source_height = ph[i]
                scalef_width = page_box_width / source_width
                scalef_height = page_box_height / source_height
                # take the smaller scaling factor so that the page will fit into its box
                if scalef_width <= scalef_height:
                    scale_factor = scalef_width
                else:
                    scale_factor = scalef_height
            
            if page_box_defined:
                cpos_x0 = c*page_box_width
                cpos_y0 = (self.rows-r-1)*page_box_height
            else:
                cpos_x0 = sum(pw[r*self.cols:r*self.cols + c])
                cpos_y0 = sum(row_height[r+1:])
            
            x0 = margin - trim[0] + cpos_x0 - c*(trim[0] + trim[1])
            y0 = margin - trim[3] + cpos_y0 - (self.rows-r-1)*(trim[2] + trim[3])
            
            if page_box_defined and self.center_content:
                # center pages in their box
                scaled_width = pw[i] * scale_factor
                scaled_height = ph[i] * scale_factor
                # unless we are using round here, there is no content - for whatever reason
                shift_right = round((page_box_width-scaled_width)/2)
                shift_up = round((page_box_height-scaled_height)/2)
                # invert shift if we are rotating
                if self.rotation == SW_ROTATION.CLOCKWISE:
                    shift_up *= -1
                elif self.rotation == SW_ROTATION.COUNTERCLOCKWISE:
                    shift_right *= -1
                elif self.rotation == SW_ROTATION.TURNAROUND:
                    shift_right *= -1
                    shift_up *= -1
                x0 += shift_right
                y0 += shift_up
            
            if scale_factor != 1:
                performed_scale = True
            
            # We need to account for the shift in origin if page rotation is applied
            o_shift = [0,0]
            
            if self.rotation == SW_ROTATION.NONE:
                # define the media box with the final grid + margins
                # run through the width/height combos to find the maximum required
                # R is the rotation matrix (default to identity)
                R = [1,0,0,1]
            else:
                if self.rotation == SW_ROTATION.CLOCKWISE:
                    R = [0,-1,1,0]
                    if page_box_defined:
                        o_shift = [0,page_box_height]
                    else:
                        o_shift = [0,ph[i]]
                elif self.rotation == SW_ROTATION.COUNTERCLOCKWISE:
                    if page_box_defined:
                        o_shift = [page_box_width,0]
                    else:
                        o_shift = [pw[i],0]
                    R = [0,1,-1,0]
                elif self.rotation == SW_ROTATION.TURNAROUND:
                    R = [-1,0,0,-1]
                    if page_box_defined:
                        o_shift = [page_box_width,page_box_height]
                    else:
                        o_shift = [pw[i],ph[i]]
            
            if performed_scale:
                # not quite matrix multiplication but works for a scalar scale factor
                R = [R[i]*scale_factor for i in range(len(R))]
            
            # scale, shift and rotate
            # first shift to origin, then rotate, then shift to final destination
            content_txt += f'q {R[0]} {R[1]} {R[2]} {R[3]} {x0+o_shift[0]} {y0+o_shift[1]} cm '
            content_txt += f'{page_names[i]} Do Q '
        
        if performed_scale:
            print(_("Warning: Some pages have been scaled because a target size was set. You should not see this warning if using the PDFStitcher GUI, since scaling is unsuitable for sewing patterns."))
        
        newpage = pikepdf.Dictionary(
            Type=pikepdf.Name.Page, 
            MediaBox=media_box,
            Resources=pikepdf.Dictionary(XObject=content_dict),
            Contents=pikepdf.Stream(new_doc,content_txt.encode())
        )
        
        new_doc.pages.append(newpage)
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


def parse_arguments():
    parser = argparse.ArgumentParser(description='Tile pdf pages into one document.',
                                 epilog='Note: If both rows and columns are specified, rows are ignored. ' + 
                                        'To insert a blank page, include a zero in the page list.')

    parser.add_argument('input',help='Input filename (pdf)')
    parser.add_argument('output',help='Output filename (pdf)')
    parser.add_argument('-p','--pages',help='Pages to tile. May be range or list (e.g. 1-5 or 1,3,5-7, etc). Default: entire document.')
    parser.add_argument('-r','--rows',help='Number of rows in tiled grid.')
    parser.add_argument('-c','--columns',help='Number of columns in tiled grid.')
    parser.add_argument('-m','--margins',help='Margin size in inches.')
    parser.add_argument('-t','--trim',help='Amount to trim from edges ' +
                        'given as left,right,top,bottom (e.g. 0.5,0,0.5,0 would trim half an inch from left and top)')
    parser.add_argument('-R','--rotate',help='Rotate pages (0 for none, 1 for clockwise, 2 for counterclockwise)')

    return parser.parse_args()


if __name__ == "__main__":
    
    import subprocess
    
    args = parse_arguments()
    new_doc, success = main(args)

    subprocess.call(args.output,shell=True)
