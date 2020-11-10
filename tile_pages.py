from PDFNetPython3 import *
import subprocess
import argparse
import sys
import math

parser = argparse.ArgumentParser(description='Tile pdf pages into one document.',
                                 epilog='Note: If both rows and columns are specified, rows are ignored.')

parser.add_argument('input',help='Input filename (pdf)')
parser.add_argument('output',help='Output filename (pdf)')
parser.add_argument('-p','--pages',help='Pages to tile. May be range or list (e.g. 1-5 or 1,3,5-7, etc). Default: entire document.')
parser.add_argument('-r','--rows',help='Number of rows in tiled grid.')
parser.add_argument('-c','--columns',help='Number of columns in tiled grid.')
parser.add_argument('-m','--margins',help='Margin size in inches.')

args = parser.parse_args()

# first try opening the document
try:
    in_doc = PDFDoc(args.input)
    
except:
    print("Unable to open " + args.input)
    sys.exit()

page_count = in_doc.GetPageCount()

if args.pages is None:
    pages = list(range(page_count+1))
else:
    # parse out the requested pages. Note that this allows for pages to be repeated and out of order.
    ptext = args.pages.split(',')
    pages = []
    for r in [p.split('-') for p in ptext]:
        if len(r) == 1:
            pages.append(int(r[0]))
            
        else:
            pages += list(range(int(r[0]),int(r[-1])+1))

import_pages = VectorPage()
itr = in_doc.GetPageIterator(pages[0])

# get the dimensions of the pages (assumes they're all the same)
# TODO: add the option to deal with inconsistent dimensions
# TODO: deal with margins for pages designed to be trimmed
width = itr.Current().GetPageWidth()
height = itr.Current().GetPageHeight()

if args.margins is None:
    m = 0.0

else:
    # all the docs/examples seem to assume 72 dpi all the time
    m = float(args.margins)*72

for p in pages:
    if p > page_count:
        print('Only {} pages in document, skipping {}'.format(page_count,p))
        continue

    itr = in_doc.GetPageIterator(p)
    import_pages.push_back(itr.Current())

# create a new document with a page big enough to contain all the tiled pages, plus requested margin
new_doc = PDFDoc()
imported_pages = new_doc.ImportPages(import_pages)
n_imported = len(imported_pages)

# figure out how big it needs to be based on requested columns/rows
if args.columns is None and args.rows is None:
    # try for square
    cols = math.ceil(math.sqrt(n_imported))
    rows = cols

# columns take priority if both are specified
if args.columns is not None:
    cols = int(args.columns)
    rows = math.ceil(n_imported/cols)

if args.rows is not None:
    rows = int(args.rows)
    cols = math.ceil(n_imported/rows)

print('Tiling with {} rows and {} columns'.format(rows,cols))

# define the media box with the final grid + margins
media_box = Rect(0,0,width*cols + 2*m,height*rows + 2*m)
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

    # print('Placing at {}, {}'.format(m+c*width, (n_imported-r-1)*height + m))
    # don't scale, just shift
    element.GetGState().SetTransform(1, 0, 0, 1,
        m + c*width,(rows-r-1)*height + m)
    writer.WritePlacedElement(element)
    i += 1

writer.End()
new_doc.PagePushBack(new_page)
    
new_doc.Save(args.output,SDFDoc.e_linearized)

in_doc.Close()
new_doc.Close()

subprocess.call(args.output,shell=True)