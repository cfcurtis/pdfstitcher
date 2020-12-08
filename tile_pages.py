import pikepdf
from pikepdf import _cpphelpers
import subprocess
import argparse
import sys
import math

def txt_to_float(txt):
    if txt is None or not txt.strip():
        return 0
    
    try:
        txtnum = float(txt.replace(',','.'))
    except:
        print(_('Invalid input ') + txt + ', ' + _('only numeric values allowed'))
    
    return txtnum

class PageTiler():
    def __init__(self,in_doc = None):
        self.in_doc = in_doc
        self.page_range = []

        # 0 = inches, 1 = centimetres
        self.units = 0
        self.trim = [0,0,0,0]
        self.margin = 0
        self.rotation = 0

        self.col_major = False
        self.right_to_left = False
        self.bottom_to_top = False
    
    def set_col_major(self,val):
        self.col_major = bool(val)
    
    def set_right_left(self,val):
        self.right_to_left = bool(val)
    
    def set_bottom_top(self,val):
        self.bottom_to_top = bool(val)

    def set_units(self,units=0):
        self.units = units
    
    def set_rotation(self,rot):
        # 0 = None, 1 = Clockwise, 2 = Counter Clockwise
        self.rotation = rot

    def units_to_px(self,val):
        pxval = val*72
        if self.units == 0:
            return pxval
        else:
            return pxval/2.54

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
        
    def set_margin(self,margin):
        self.margin = margin

    def set_page_range(self,ptext=""):
        # parse out the requested pages. Note that this allows for pages to be repeated and out of order.
        self.page_range = []
        
        if ptext:
            for r in [p.split('-') for p in ptext.split(',')]:
                if len(r) == 1:
                    self.page_range.append(int(r[0]))
                else:
                    self.page_range += list(range(int(r[0]),int(r[-1])+1))
            
        if len(self.page_range) == 0:
            self.page_range = list(range(1,len(self.in_doc.pages)+1))

    def run(self,rows=0,cols=0):
        if self.in_doc is None:
            print(_('Input document not loaded'))
            return

        if len(self.page_range) == 0:
            self.set_page_range()
        
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
                    content_dict[pagekey] = pikepdf.Page(localpage).as_form_xobject()

                    # only get the width/height for the first page
                    if pw is None:
                        pw = float(localpage.MediaBox[2])
                        ph = float(localpage.MediaBox[3])
                        page_size_ref = p
                    elif abs(pw - float(localpage.MediaBox[2])) > 1 or abs(ph - float(localpage.MediaBox[3])) > 1:
                        print(_('Warning: page {} is a different size from {}, output may be unpredictable'.format(p,page_size_ref)))

                page_names.append(pagekey)
            else:
                page_names.append(None)
        
        # take the most common page width/height
        
        
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
        trim = [self.units_to_px(t) for t in self.trim]

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
        print('    ' + _('Margins' + ': {} {}').format(self.margin,unitstr))
        print('    ' + _('Trim' + ': {} {}').format(self.trim,unitstr))
        print('    ' + _('Rotation') + ': {}'.format(rotstr))
        print('    ' + _('Page order' + ': {}, {}, {}'.format(orderstr, lrstr, btstr)))

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
            
            x0 = margin - trim[0] + c*(pw - trim[0] - trim[1])
            y0 = margin - trim[3] + r*(ph - trim[2] - trim[3])

            # don't scale, just shift and rotate
            # first shift to origin, then rotate, then shift to final destination
            content_txt += f'q {R[0]} {R[1]} {R[2]} {R[3]} {x0+o_shift[0]} {y0+o_shift[1]} cm '
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
        margin = txt_to_float(args.margins)
        tiler.set_margin(margin)

    if args.trim is not None:
        trim = [txt_to_float(t) for t in args.trim.split(',')]
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
    args = parse_arguments()
    new_doc, success = main(args)

    subprocess.call(args.output,shell=True)
