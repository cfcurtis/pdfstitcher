# PDFStitcher
This is a utility for stitching together many PDF pages from a single document into one single page. This is also called "N-Up" or page imposition. Originally, this utility was created in order to convert sewing patterns into a convenient format for projecting.

## Features
* Stitch together pages in any order with specified number of rows or columns
* Add blank pages by including zeros in the page list (e.g. 1-5,0,6-10)
* Add margins around the final output
* Trim the edges of each page by a specified amount

## Prerequisites
Most people probably want to just use the executable (TODO: add link). However, if you want to run the script directly, you'll need the following:

* [Python](https://www.python.org/downloads/) and `pip`. Testing was done with 64-bit Python 3.9.0 provided by [Anaconda](https://www.anaconda.com/) on Windows 10.

* [pikepdf](https://github.com/pikepdf/pikepdf) - can be installed by running `pip install pikepdf`

* [wxPython](https://www.wxpython.org/) - can be installed by running `pip install wxpython`

## Usage
<a href="url"><img src="resources/stitcher_screenshot.png" width="400" ></a>

"Select input PDF" launches a file browser allowing you to choose the print at home PDF. "Save output as" launches a file browser to select the name of the document to write. If you don't specify a filename here, you will be asked to choose one when you click "Generate Tiled PDF".

The GUI does not display the input or output PDF. You will need to use an external PDF viewer such as Adobe Reader for this. Remember to close your output PDF if you want to re-generate with different options, otherwise it will be locked for writing.

The test document "testdoc.pdf" is a simple 20 page document with one label per page representing rows 1-5 and columns A-D (A1, A2, A3, A4, B1, B2, B3, B4, etc). The following images show the original PDF and the tiled output generated with the options above.

<a href="url"><img src="resources/testdoc.png" width="300" ></a>
<a href="url"><img src="resources/test_tiled.png" width="300" ></a>
