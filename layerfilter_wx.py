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

import pikepdf
from layerfilter_abstract import AbstractLayerFilter
from wx import Yield, ProgressDialog


class WxLayerFilter (AbstractLayerFilter):
    
    def __init__(self, doc):
        super(WxLayerFilter, self).__init__(doc)

    def wxrun(self,progress_dlg):
        
        c = 0
        
        for x in self.run():
            
            if progress_dlg.WasCancelled():
                # not perfect since it won't respond directly, only when we're through with one run of the loop
                return None
            if x is True:
                c += 1
                progress_dlg.Update(c)
                Yield()
            
            # it would be cleaner to do this separately before/after the loop
            elif isinstance(x, int):
                progress_dlg.SetRange(x)
                Yield()
            elif isinstance(x, pikepdf.Pdf):
                return x
