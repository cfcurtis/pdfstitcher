# PDFStitcher
PDFSticher is a utility for stitching together many PDF pages from one document into a single page. This is also called "N-Up" or page imposition. This program was created in order to convert sewing patterns into a convenient format for projecting, though it could be used to stitch together any PDF.

Since version 0.4, it is also possible to select layers for inclusion/exclusion in the final output. Additionally, line properties can be modified for each layer if the input PDF is compatible.

For up-to-date information, also check out https://www.pdfstitcher.org.

## Download the latest release
* [Windows (7 or 10, 64-bit)](https://github.com/cfcurtis/pdfstitcher/releases/latest/download/pdfstitcher.exe)
* [macOS - Intel Processor](https://github.com/cfcurtis/pdfstitcher/releases/latest/download/PDFStitcher-InstallerX64.dmg)
* [macOS - M1/M2 Processor](https://github.com/cfcurtis/pdfstitcher/releases/latest/download/PDFStitcher-InstallerARM64.dmg)
* <a href='https://flathub.org/apps/details/com.github.cfcurtis.pdfstitcher'><img width='120' alt='Download on Flathub' src='https://flathub.org/assets/badges/flathub-badge-en.svg'/></a>
* Using pip: `pip install pdfstitcher[gui]` **Requires Python between 3.8 and 3.12**. 
    * Running `pip installl pdfstitcher` without the `[gui]` option will install the command line version only. The `pdfstitcher` command is installed as a command line script, while the GUI is installed as a separate script called `pdfstitcher-gui`.
    * To run as a Python module, use `python -m pdfstitcher.cli` or `python -m pdfstitcher.gui`
    * As of June 2024, there is a known issue with building the wxPython wheel on systems with GCC 14 (e.g. Fedora 40). If the installation fails, try using Python 3.11 and installing a wheel manually from https://wxpython.org/pages/downloads/index.html.


> Previous versions can be found by clicking on the "releases" link to the right.

## Translations:

<a href="https://hosted.weblate.org/engage/pdfstitcher/">
<img src="https://hosted.weblate.org/widgets/pdfstitcher/-/287x66-grey.png" alt="Translation status" /></a>

PDFStitcher will detect system language settings and change localisation if supported. The default language can be changed in the settings menu ("Preferences" in the menu bar on macOS).

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
$ pip install -e ".[dev,gui]"
```

## Help!
Found a bug, or have an idea for a great new feature? Check out the [Issues](https://github.com/cfcurtis/pdfstitcher/issues) tab to see if it's an open issue, or submit a new one if it's not on the list.
