# PDFStitcher
This is a utility for stitching together many PDF pages from one document into a single page. This is also called "N-Up" or page imposition. This program was created in order to convert sewing patterns into a convenient format for projecting, though it could be used to stitch together any PDF.

Since version 0.4, it is also possible to select layers for inclusion/exclusion in the final output. Additionally, line properties can be modified for each layer if the input PDF is compatible.

For up-to-date information, also check out https://www.pdfstitcher.org.

## Download the latest release
* [Windows (7 or 10, 64-bit)](https://github.com/cfcurtis/pdfstitcher/releases/latest/download/pdfstitcher.exe)
* [macOS (High Sierra or higher)](https://github.com/cfcurtis/pdfstitcher/releases/latest/download/PDFStitcher-Installer.dmg)
* <a href='https://flathub.org/apps/details/com.github.cfcurtis.pdfstitcher'><img width='120' alt='Download on Flathub' src='https://flathub.org/assets/badges/flathub-badge-en.svg'/></a>

## Translations:
PDFStitcher will detect system language settings and change localisation if supported. 

Previous versions can be found by clicking on the "releases" link to the right.

Want to contribute a translation? PDFStitcher is now on [weblate!](https://hosted.weblate.org/engage/pdfstitcher/).

## Features
* Stitch together pages in any order with specified number of rows/columns
* Rotate pages for stitching
* Add a margin around the final output
* Trim or overlap the edges of each page by a specified amount
* Add blank pages by including zeros in the page list (e.g. 1-5,0,6-10)
* Layers are automatically preserved if present in the source document
* Exclude layers (either deactivate or remove)
* Modify line properties (colour, thickness, style (solid, dashed, dotted))

## Development Installation
Most people probably want to just use the executable links above. However, if you intend to run the program from source, you'll need the following:

* [Python 3.6-3.9](https://www.python.org/downloads/) and `pip`. Testing was done with 64-bit Python 3.8.5 provided by [Anaconda](https://www.anaconda.com/) on Windows 10 and Python 3.9.1 provided by [homebrew](https://brew.sh/) on macOS High Sierra 10.13.6. Python 3.10+ may work, but there at the time of writing there is no wheel for wxPython for 3.10.

* [pikepdf](https://github.com/pikepdf/pikepdf) can be installed by running `pip install pikepdf` **Note:** For macOS less than 10.15, pikepdf v2.8.0 is the latest supported version. Specify with `pip install pikepdf==2.8.0` or [build it from source](https://pikepdf.readthedocs.io/en/latest/installation.html#building-from-source) if you're feeling adventurous.

* [wxPython 4.1+](https://www.wxpython.org/) can be installed by running `pip install wxpython` **Note:** For Linux, the installtion of wxPython can be tricky if your distribution does not provide a recent enough version. I recommend checking out the instructions [here](https://wxpython.org/pages/downloads/index.html).

## Usage
<a href="url"><img src="resources/stitcher_screenshot.png" width="400" ></a>

"Select input PDF" launches a file browser allowing you to choose the print at home PDF. "Save output as" launches a file browser to select the name of the document to write. If you don't specify a filename here, you will be asked to choose one when you click "Generate Tiled PDF". By default, the page range box will include all the pages in the document. The other required field is the number of rows or columns defining your desired grid. You can specify both, but if they don't agree with the number of pages, the columns field takes precendence (for example if you have 20 pages and request 3 columns and 5 rows, it will tile with 3 columns and 7 rows in order to fit all 20 pages).

The test document "testdoc.pdf" is a simple 20 page document with one label per page representing rows 1-5 and columns A-D (A1, A2, A3, A4, B1, B2, B3, B4, etc). The following images show the original PDF and the tiled output generated with the options above.

<a href="url"><img src="resources/testdoc.png" width="300" ></a>
<a href="url"><img src="resources/test_tiled.png" width="300" ></a>

## Fancy stuff
Some PDFs require trimming pages, assembling with gaps, tiling with columns first, etc. The following options allow for *most* patterns to be assembled.
* Page range: this field can take arbitrary ranges (e.g. 3-10), a comma separated list, or a combination (e.g. 3-10, 4, 11-12). Page repetition is allowed, and adding a "0" inserts a blank page. The following example would be constructed by specifying 3 columns and/or 3 rows and the page range `1-4,0,5-6,0,7-8`

<a href="url"><img src="resources/blank-page-example.png" width="300" ></a>

* Page order: most PDFs are assembled row by row, left to right, top to bottom. The page order options allow for columns first, right to left, or bottom to top, in any combination.

* Rotation: The pages can be rotated either clockwise or counterclockwise prior to assembly. Note that when rotation is enabled, the trim values (left/right/top/bottom) refer to the original non-rotated page.

* Overlap or trim: By default, the pages are overlapped by the trim amount specified. In some cases (e.g. if the background is white instead of transparent) this results in gaps between pages, and selecting "trim" might give better results.

## Not supported yet
* Different trim for each page
* Mixed orientation of pages

At this time, the GUI does not display the input or output PDF. You will need to use an external PDF viewer such as [Adobe Reader](https://get.adobe.com/uk/reader/otherversions/) or [Okular](https://okular.kde.org/) for this. **Note:** If you are using Windows, remember to close the output PDF if you want to re-generate it with different options, otherwise the file will be locked for writing.

## Help!
Found a bug, or have an idea for a great new feature? Check out the [Issues](https://github.com/cfcurtis/pdfstitcher/issues) tab to see if it's an open issue, or submit a new one if it's not on the list.
