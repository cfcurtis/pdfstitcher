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

from gettext import gettext as _

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
