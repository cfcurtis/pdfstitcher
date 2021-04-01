# PDFStitcher is a utility to work with PDF sewing patterns.
# Copyright (C) 2021 Charlotte Curtis
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

import sys
import os
import pikepdf

# localization stuff
import gettext
import locale

version_string = 'v0.4'


def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    if hasattr(sys,'_MEIPASS'):
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    else:
        base_path = os.path.abspath('.')

    return os.path.join(base_path, relative_path)

def setup_locale():
    language_warning = None

    lc = locale.getdefaultlocale()

    try:
        lang = lc[0][:2]
    except:
        lang = 'en'
        language_warning = 'Could not detect system language, defaulting to English'

    if lang not in ('de','es','fr','nl','en'):
        language_warning = 'System language code ' + lang + ' is not supported, defaulting to English.'

    try:
        translate = gettext.translation('pdfstitcher', resource_path('locale'), 
            languages=[lang], fallback=True)
        translate.install()
    except Exception as e:
        global _
        def _(text):
            return text
            
        language_warning = e
    
    return language_warning

def txt_to_float(txt):
    if txt is None or not txt.strip():
        return 0

    try:
        txtnum = float(txt.replace(',','.'))
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
                page_range += list(range(int(r[0]),int(r[-1])+1))
    
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