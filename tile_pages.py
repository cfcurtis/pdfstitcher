# PDFStitcher is a utility to work with PDF sewing patterns.
# Copyright (C) 2021 Charlotte Curtis
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.


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

    def show_options(self):
        # convert the margin and trim options into pixels
        unitstr = _('cm') if self.units == SW_UNITS.CENTIMETERS else _('in')
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

        return unitstr

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

        # define the dictionary to store xobjects, unless we're just trimming/adding margins to one page
        if len(self.page_range) > 1:
            content_dict = pikepdf.Dictionary({})
        else:
            content_dict = None

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
        
        for p in self.page_range:
            if p > 0:
                ref_p = p
                break
        refmbox = self.in_doc.pages[ref_p-1].MediaBox
        
        different_size = set()
        
        for p in self.page_range:
            if p > page_count:
                print(_('Only {} pages in document, skipping {}').format(page_count,p))
                continue
            
            if p > 0:
                pagekey = f'/Page{p}'
                pagembox = self.in_doc.pages[p-1].MediaBox
                
                if content_dict is None or pagekey not in content_dict.keys():
                    # copy the page over as an xobject
                    # pikepdf.pages is zero indexed, so subtract one
                    localpage = new_doc.copy_foreign(self.in_doc.pages[p-1])
                    
                    if '/Rotate' in localpage.keys():
                        page_rot = localpage.Rotate
                    
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
 
                    if content_dict is not None:
                        content_dict[pagekey] = pikepdf.Page(localpage).as_form_xobject()

                if page_rot == 90 or page_rot == -90:
                    pw.append(float(localpage.MediaBox[3]))
                    ph.append(float(localpage.MediaBox[2]))
                else:
                    pw.append(float(localpage.MediaBox[2]))
                    ph.append(float(localpage.MediaBox[3]))
                
                page_names.append(pagekey)

                if abs(pagembox[2] - refmbox[2]) > 1 or abs(pagembox[3] - refmbox[3]) > 1:
                    different_size.add(p)
                
                refmbox = pagembox
                ref_p = p
                
            else:
                page_names.append(None)
                
                if page_rot == 90 or page_rot == -90:
                    pw.append(float(refmbox[3]))
                    ph.append(float(refmbox[2]))
                else:
                    pw.append(float(refmbox[2]))
                    ph.append(float(refmbox[3]))
        
        if len(different_size) > 0:
            print(_('Warning: The pages {} have a different size than the page before').format(different_size))
        
        n_tiles = len(page_names)
        
        # figure out how big the output needs to be based on requested columns/rows
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
        
        # after calculating rows/cols but before reordering trim, show the user the selected options
        unitstr = self.show_options()
        
        # swap the trim order
        # default: left,right,top,bottom
        order = [0,1,2,3]

        if self.rotation == SW_ROTATION.CLOCKWISE:
            order = [3,2,0,1]
        if self.rotation == SW_ROTATION.COUNTERCLOCKWISE:
            order = [2,3,1,0]
        if self.rotation == SW_ROTATION.TURNAROUND:
            order = [1,0,3,2]

        trim = [self.units_to_px(t) for t in self.trim]
        trim = [trim[o] for o in order]
        
        if (self.rotation == SW_ROTATION.CLOCKWISE) or (self.rotation == SW_ROTATION.COUNTERCLOCKWISE):
            # swap width and height of pages
            ph, pw = pw, ph
        
        width = 0
        height = 0
        col_width = [0]*self.cols
        row_height = [0]*self.rows
        
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
                    col_width[c] = max(pw[c*self.rows:c*self.rows+self.rows]) - (trim[0] + trim[1])
                
                for r in range(self.rows):
                    row_height[r] = max(ph[r:n_tiles:self.cols]) - (trim[2] + trim[3])
            else: 
                for r in range(self.rows):
                    row_height[r] = max(ph[r*self.cols:r*self.cols+self.cols]) - (trim[2] + trim[3])
                
                for c in range(self.cols):
                    col_width[c] = max(pw[c:n_tiles:self.rows]) - (trim[0] + trim[1])

            if self.right_to_left:
                col_width.reverse()
            
            if self.bottom_to_top:
                row_height.reverse()

            width = sum(col_width)
            height = sum(row_height)
            page_box_defined = False
                
        # create a new document with a page big enough to contain all the tiled pages, plus requested margin
        margin = self.units_to_px(self.margin)
        media_box = [0,0,width + 2*margin,height + 2*margin]
        
        # check if it exceeds Adobe's 200 inch maximum size
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
        
        # loop through all the page xobjects and place the non-empty ones
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
            
            if page_box_defined:
                # calculate scaling factors based on source page size
                source_width = pw[i]
                source_height = ph[i]
                scalef_width = page_box_width / source_width
                scalef_height = page_box_height / source_height
                # take the smaller scaling factor so that the page will fit into its box
                scale_factor = min(scalef_width, scalef_height)
                cpos_x0 = c*page_box_width - c*(trim[0] + trim[1])
                cpos_y0 = (self.rows-r-1)*page_box_height - (self.rows-r-1)*(trim[2] + trim[3])
            else:
                cpos_x0 = sum(col_width[:c]) - trim[0]
                cpos_y0 = sum(row_height[r+1:]) - trim[3]

                # store the page box height/width for convenience if rotation is needed
                page_box_height = ph[i]
                page_box_width = pw[i]
            
            # define the xobject position with reference to the origin at bottom left of page.
            x0 = margin + cpos_x0 
            y0 = margin + cpos_y0
            
            if self.center_content:
                if page_box_defined:
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
                else:
                    shift_up = round((row_height[r]-ph[i])/2)
                    shift_right = round((col_width[c]-pw[i])/2)
                
                x0 += shift_right
                y0 += shift_up
            
            if self.rotation == SW_ROTATION.NONE:
                # R is the rotation matrix (default to identity)
                R = [1,0,0,1]
            else:
                # We need to account for the shift in origin if page rotation is applied
                if self.rotation == SW_ROTATION.CLOCKWISE:
                    R = [0,-1,1,0]
                    y0 += page_box_height
                elif self.rotation == SW_ROTATION.COUNTERCLOCKWISE:
                    R = [0,1,-1,0]
                    x0 += page_box_width
                elif self.rotation == SW_ROTATION.TURNAROUND:
                    R = [-1,0,0,-1]
                    x0 += page_box_width
                    y0 += page_box_height
            
            if scale_factor != 1:
                # if we scale any of the pages, keep track of it so we can warn afterwards
                performed_scale = True
                # not quite matrix multiplication but works for a scalar scale factor
                R = [R[i]*scale_factor for i in range(len(R))]
            
            # scale, shift and rotate
            content_txt += f'q {R[0]} {R[1]} {R[2]} {R[3]} {x0} {y0} cm '

            if content_dict is not None:
                content_txt += f'{page_names[i]} Do Q '
            else:
                # just one page: redefine the coordinate system and wrap the contents in q/Q
                localpage.page_contents_add(new_doc.make_stream(content_txt.encode()),prepend=True)
                localpage.page_contents_add(new_doc.make_stream(b'Q'))
        
        if performed_scale:
            print(_("Warning: Some pages have been scaled because a target size was set. "
                    "You should not see this warning if using the PDFStitcher GUI."))
        
        if content_dict:
            newpage = pikepdf.Dictionary(
                Type=pikepdf.Name.Page, 
                MediaBox=media_box,
                Resources=pikepdf.Dictionary(XObject=content_dict),
                Contents=pikepdf.Stream(new_doc,content_txt.encode())
            )
            new_doc.pages.append(newpage)
        else:
            localpage.MediaBox = media_box
            localpage.CropBox = media_box
            new_doc.pages.append(localpage)
            
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
