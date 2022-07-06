# PDFStitcher is a utility to work with PDF sewing patterns.
# Copyright (C) 2021 Charlotte Curtis
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import wx
from pdfstitcher import utils

class PrefsDialog(wx.Dialog):
    """
    Small window to define user preferences.
    """

    def __init__(self, *args, **kw):
        super(PrefsDialog, self).__init__(*args, **kw)

        self.SetTitle(_("Preferences"))
        vert_sizer = wx.BoxSizer(wx.VERTICAL)

        # Language switcher
        newline = wx.BoxSizer(wx.HORIZONTAL)
        newline.Add(wx.StaticText(self, label=_("Language") + ":"), flag=wx.ALIGN_CENTER_VERTICAL)
        valid_langs = [lang for lang in gettext.find('pdfstitcher') if lang != 'pdfstitcher']



class AboutDialog(wx.Dialog):
    """
    Small window to show about info.
    """