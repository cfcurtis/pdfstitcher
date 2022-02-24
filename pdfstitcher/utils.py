# PDFStitcher is a utility to work with PDF sewing patterns.
# Copyright (C) 2021 Charlotte Curtis
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import sys
import os
import pikepdf

# localization stuff
import gettext
import locale
from pathlib import Path

from pdfstitcher.version import __version__

version_string = 'v' + __version__

def resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller"""
    if hasattr(sys, '_MEIPASS'):
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    else:
        base_path = str(Path(__file__).parent.absolute())

    return os.path.join(base_path, relative_path)


def setup_locale():
    language_warning = None
    lc = locale.getdefaultlocale()   

    try:
        if lc[0] is None:
            lc = os.getenv('LANG')[:4]
        else:
            lang = lc[0]
    except:
        try:
            # try the Apple way
            from Foundation import NSUserDefaults

            defaults = NSUserDefaults.standardUserDefaults()
            globalDomain = defaults.persistentDomainForName_("NSGlobalDomain")
            languages = globalDomain.objectForKey_("AppleLanguages")

            # just take the first one
            lang = languages[0]
        except Exception as e:
            language_warning = 'Could not detect system language, defaulting to English'
            lang = 'en'

    try:
        translate = gettext.translation(
            'pdfstitcher', resource_path('locale'), languages=[lang], fallback=False
        )
        translate.install()
    except:
        # try just the first two letters
        try:
            translate = gettext.translation(
                'pdfstitcher', resource_path('locale'), languages=[lang[:2]], fallback=True
            )
            translate.install()
        except Exception as e:
            language_warning = e

    return language_warning


def txt_to_float(txt):
    if txt is None or not txt.strip():
        return 0

    try:
        txtnum = float(txt.replace(',', '.'))
    except:
        print(_('Invalid input') + txt + ' , ' + _('only numeric values allowed'))
        return None

    return txtnum


def parse_page_range(ptext=""):
    # parse out the requested pages. Note that this allows for pages to be repeated and out of order.
    page_range = []
    if ptext:
        for r in [p.split('-') for p in ptext.split(',')]:
            if len(r) == 1:
                page_range.append(int(r[0]))
            else:
                page_range += list(range(int(r[0]), int(r[-1]) + 1))

    else:
        print(_('Please specify a page range'))
        return None

    return page_range


def init_new_doc(pdf):
    # initialize a new document and copy over the layer info (OCGs) if it exists
    new_doc = pikepdf.Pdf.new()

    local_root = new_doc.copy_foreign(pdf.Root)

    if '/OCProperties' in local_root:
        new_doc.Root.OCProperties = local_root.OCProperties

    if '/Metadata' in local_root:
        for k in pdf.Root.Metadata.keys():
            new_doc.Root.Metadata = local_root.Metadata

    with new_doc.open_metadata() as meta:
        # update the creator info
        meta['xmp:CreatorTool'] = 'PDFStitcher ' + version_string

    return new_doc


def get_page_dims(page, global_rotation=0):
    # Helper function to calculate the page dimensions
    # Returns width, height as observed by the user
    # (taking rotation into account)

    # The mediabox is typically specified as
    # [lower left x, lower left y, upper left x, upper left y],
    # but per PDF reference any two opposite corners can be defined
    mbox = page.MediaBox
    page_width = float(abs(mbox[2] - mbox[0]))
    page_height = float(abs(mbox[3] - mbox[1]))

    # global_rotation is defined by the document root, but
    # may be overridden on a specific page
    if '/Rotate' in page.keys():
        rotation = page.Rotate
    else:
        rotation = global_rotation

    # swap height and width if there is rotation
    if (rotation // 90) % 2 != 0:
        page_width, page_height = page_height, page_width

    return page_width, page_height
