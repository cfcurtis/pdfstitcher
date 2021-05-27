# PDFStitcher is a utility to work with PDF sewing patterns.
# Copyright (C) 2021 Charlotte Curtis
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import pikepdf
from layerfilter_abstract import AbstractLayerFilter
from wx import Yield, ProgressDialog


class WxLayerFilter (AbstractLayerFilter):
    
    def __init__(self, doc):
        super(WxLayerFilter, self).__init__(doc)

    def wxrun(self,progress_dlg):
        
        c = 0
        
        for x in self.run():
            
            if progress_dlg.WasCancelled() or x is None:
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
