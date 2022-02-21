# PDFStitcher
PDFSticher is a utility for stitching together many PDF pages from one document into a single page. This is also called "N-Up" or page imposition. This program was created in order to convert sewing patterns into a convenient format for projecting, though it could be used to stitch together any PDF.

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

* [Python 3.6-3.9](https://www.python.org/downloads/) and `pip`. Python 3.10+ may work, but as of February 2022 there is no wheel for wxPython for 3.10.

* [pikepdf](https://github.com/pikepdf/pikepdf) can be installed by running `pip install pikepdf` **Note:** For macOS less than 10.15, pikepdf v2.8.0 is the latest supported version. Specify with `pip install pikepdf==2.8.0` or [build it from source](https://pikepdf.readthedocs.io/en/latest/installation.html#building-from-source) if you're feeling adventurous.

* [wxPython 4.1+](https://www.wxpython.org/) can be installed by running `pip install wxpython` **Note:** For Linux, the installtion of wxPython can be tricky if your distribution does not provide a recent enough version. I recommend checking out the instructions [here](https://wxpython.org/pages/downloads/index.html).


## Help!
Found a bug, or have an idea for a great new feature? Check out the [Issues](https://github.com/cfcurtis/pdfstitcher/issues) tab to see if it's an open issue, or submit a new one if it's not on the list.
