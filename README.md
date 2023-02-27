# PDFStitcher
PDFSticher is a utility for stitching together many PDF pages from one document into a single page. This is also called "N-Up" or page imposition. This program was created in order to convert sewing patterns into a convenient format for projecting, though it could be used to stitch together any PDF.

Since version 0.4, it is also possible to select layers for inclusion/exclusion in the final output. Additionally, line properties can be modified for each layer if the input PDF is compatible.

For up-to-date information, also check out https://www.pdfstitcher.org.

## Download the latest release
* [Windows (7 or 10, 64-bit)](https://github.com/cfcurtis/pdfstitcher/releases/latest/download/pdfstitcher.exe)
* [macOS - Intel Processor](https://github.com/cfcurtis/pdfstitcher/releases/latest/download/PDFStitcher-InstallerX64.dmg)
* [macOS - M1/M2 Processor](https://github.com/cfcurtis/pdfstitcher/releases/latest/download/PDFStitcher-InstallerARM64.dmg)
* <a href='https://flathub.org/apps/details/com.github.cfcurtis.pdfstitcher'><img width='120' alt='Download on Flathub' src='https://flathub.org/assets/badges/flathub-badge-en.svg'/></a>
* Using pip: `pip install pdfstitcher` **Note: Requires Python <= 3.11**. As of November 2022, there is no wheel available for wxPython for 3.11+.

## Translations:

<a href="https://hosted.weblate.org/engage/pdfstitcher/">
<img src="https://hosted.weblate.org/widgets/pdfstitcher/-/287x66-grey.png" alt="Translation status" /></a>

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
Most people probably want to just use the executable links above. However, to edit the code, clone this repo and install in editable mode using the command:

```console
$ pip install -e ".[dev]"
```

## Help!
Found a bug, or have an idea for a great new feature? Check out the [Issues](https://github.com/cfcurtis/pdfstitcher/issues) tab to see if it's an open issue, or submit a new one if it's not on the list.
