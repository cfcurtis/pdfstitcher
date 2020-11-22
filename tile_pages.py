from PDFNetPython3 import *
import subprocess
import argparse
import sys
import math

class PageTiler():
    def __init__(self,in_doc = None):
        self.in_doc = in_doc
        self.trim = [0,0,0,0]
        self.margin = 0

        self.import_pages = None
        self.page_width = []
        self.page_height = []

    def set_trim(self,trim):
        if len(trim) == 1:
            self.trim = [trim,trim,trim,trim]
        
        if len(trim) == 2:
            self.trim = [trim[0],trim[0],trim[1],trim[1]]
        
        if len(trim) == 4:
            self.trim = trim
        
        else:
            print('Invalid trim value specified, ignoring')
            self.trim = [0,0,0,0]
        
    def set_margin(self,margin):
        self.margin = margin

    def set_page_range(self,pages=None):
        if self.in_doc is None:
            print("Input document not loaded")
            return
        
        self.import_pages = VectorPage()
        self.page_width = []
        self.page_height = []

        page_count = self.in_doc.GetPageCount()

        if pages is None:
            pages = list(range(1,page_count+1))

        itr = self.in_doc.GetPageIterator(pages[0])    
        nzeros = 0
        
        for p in pages:
            if p > page_count:
                print('Only {} pages in document, skipping {}'.format(page_count,p))
                continue

            itr = self.in_doc.GetPageIterator(p)
            self.import_pages.push_back(itr.Current())

            if p > 0:
                self.page_width.append(itr.Current().GetPageWidth())
                self.page_height.append(itr.Current().GetPageHeight())
            else:
                self.page_width.append(0)
                self.page_height.append(0)
                nzeros += 1
            
        # replace the zero pages with the average height/width
        if nzeros > 0:
            mean_width = sum(self.page_width)/(len(self.page_width) - nzeros)
            mean_height = sum(self.page_height)/(len(self.page_height) - nzeros)
            self.page_width = [w if w > 0 else mean_width for w in self.page_width]
            self.page_height = [h if h > 0 else mean_height for h in self.page_height]

    def run(self,rows=0,cols=0):
        if self.import_pages is None:
            self.set_page_range(None)

        # create a new document with a page big enough to contain all the tiled pages, plus requested margin
        new_doc = PDFDoc()
        imported_pages = new_doc.ImportPages(self.import_pages)
        n_imported = len(imported_pages)

        # figure out how big it needs to be based on requested columns/rows
        if cols == 0 and rows == 0:
            # try for square
            cols = math.ceil(math.sqrt(n_imported))
            rows = cols

        # columns take priority if both are specified
        if rows > 0:
            cols = math.ceil(n_imported/rows)

        if cols > 0:
            rows = math.ceil(n_imported/cols)

        print('Tiling with {} rows and {} columns'.format(rows,cols))
        print('Options:')
        print('    Margins: {} pixels'.format(self.margin))
        print('    Trim: {} pixels'.format(self.trim))

        # define the media box with the final grid + margins
        # run through the width/height combos to find the maximum required
        width = 0
        height = 0
        row_height = [0]*rows
        for r in range(rows):
            width = max(width,sum(self.page_width[r*cols:r*cols+cols]))
            row_height[r] = max(self.page_height[r*cols:r*cols+cols])
        
        width -= (self.trim[0] + self.trim[1])*cols
        height = sum(row_height) - (self.trim[2] + self.trim[3])*rows

        media_box = Rect(0,0,width + 2*self.margin,height + 2*self.margin)
        new_page = new_doc.PageCreate(media_box)

        builder = ElementBuilder()
        writer = ElementWriter()
        writer.Begin(new_page)

        i = 0    
        while i < n_imported:
            element = builder.CreateForm(imported_pages[i])

            # left to right, top to bottom is assumed
            r = math.floor(i/cols)
            c = i % cols
            
            x0 = self.margin - self.trim[0] + sum(self.page_width[r*cols:r*cols + c]) - c*(self.trim[0] + self.trim[1])
            y0 = self.margin - self.trim[3] + sum(row_height[r+1:]) - (rows-r-1)*(self.trim[2] + self.trim[3])

            # don't scale, just shift
            element.GetGState().SetTransform(1, 0, 0, 1, x0, y0)
            writer.WritePlacedElement(element)
            i += 1

        writer.End()
        new_doc.PagePushBack(new_page)

        return new_doc

def main(args):
    PDFNet.Initialize()
    # first try opening the document
    try:
        in_doc = PDFDoc(args.input)
    except:
        print("Unable to open " + args.input)
        sys.exit()
    
    tiler = PageTiler(in_doc)

    if args.pages is not None:
        # parse out the requested pages. Note that this allows for pages to be repeated and out of order.
        ptext = args.pages.split(',')
        pages = []
        for r in [p.split('-') for p in ptext]:
            if len(r) == 1:
                pages.append(int(r[0]))
            else:
                pages += list(range(int(r[0]),int(r[-1])+1))
        
        if len(pages) == 0:
            pages = None
        
        tiler.set_page_range(pages)

    if args.margins is not None:
        # all the docs/examples seem to assume 72 dpi all the time
        margin = float(args.margins)*72
        tiler.set_margin(margin)

    if args.trim is not None:
        trim = [float(t)*72 for t in args.trim.split(',')]
        tiler.set_trim(trim)

    cols = None
    rows = None
    if args.columns is not None:
        cols = int(args.columns)

    if args.rows is not None:
        rows = int(args.rows)
    
    # run it!
    new_doc = tiler.run(rows,cols)
        
    try:
        new_doc.Save(args.output,SDFDoc.e_linearized)
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

    return parser.parse_args()

if __name__ == "__main__":
    args = parse_arguments()
    new_doc, success = main(args)
    new_doc.Close()
    
    view = PDFView()
    doc = PDFDoc(args.output)
    view.SetDoc(doc)
    # subprocess.call(args.output,shell=True)
