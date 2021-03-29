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
import utils

class PageFilter():
    def __init__(self,doc = None):
        self.pdf = doc
        self.page_range = []
    
    def run(self):
        # not sure what this means, so just return the pdf as is
        if len(self.page_range) == 0:
            return self.pdf
        
        # if all of them are selected, we don't need to do anything
        if self.page_range == list(range(1,len(self.pdf.pages)+1)):
            return self.pdf
        
        # otherwise, copy the selected pages to a new document
        new_doc = utils.init_new_doc(self.pdf)

        for p in self.page_range:
            if p == 0:
                mbox = self.pdf.pages[-1].MediaBox
                new_doc.add_blank_page(page_size=(mbox[2],mbox[3]))
            else:
                new_doc.pages.extend([self.pdf.pages[p-1]])

        return new_doc