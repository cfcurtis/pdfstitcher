# PDFStitcher is a utility to work with PDF sewing patterns.
# Copyright (C) 2021 Charlotte Curtis
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import pikepdf
import pdfstitcher.utils as utils


class PageFilter:
    def __init__(self, doc=None):
        self.pdf = doc
        self.page_range = []
        self.margins = None

    def run(self):
        # not sure what this means, so just return the pdf as is
        if len(self.page_range) == 0:
            return self.pdf

        # if all of them are selected, we don't need to do anything
        if self.page_range == list(range(1, len(self.pdf.pages) + 1)):
            return self.pdf

        # otherwise, copy the selected pages to a new document
        new_doc = utils.init_new_doc(self.pdf)

        for p in self.page_range:
            if p == 0:
                mbox = self.pdf.pages[-1].MediaBox
                new_doc.add_blank_page(page_size=(mbox[2], mbox[3]))
            else:
                new_doc.pages.extend([self.pdf.pages[p - 1]])

            if '/UserUnit' in self.pdf.pages[-1].keys():
                new_doc.pages[-1].UserUnit = self.pdf.pages[-1].UserUnit

        return new_doc
