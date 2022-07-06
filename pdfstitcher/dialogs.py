# PDFStitcher is a utility to work with PDF sewing patterns.
# Copyright (C) 2021 Charlotte Curtis
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import wx
from pdfstitcher import utils
from pdfstitcher.utils import Config


class PrefsDialog(wx.Dialog):
    """
    Small window to define user preferences.
    """

    def __init__(self, *args, **kw):
        super(PrefsDialog, self).__init__(*args, **kw)

        self.main_gui = kw["parent"]
        self.SetTitle(_("Preferences"))
        vert_sizer = wx.BoxSizer(wx.VERTICAL)

        # Language switcher
        newline = wx.BoxSizer(wx.HORIZONTAL)
        newline.Add(wx.StaticText(self, label=_("Language") + ":"), flag=wx.ALIGN_CENTER_VERTICAL)
        valid_langs = utils.get_valid_langs()
        self.lang_combo = wx.ComboBox(
            self, choices=valid_langs, value=Config.general["language"], style=wx.CB_READONLY
        )
        newline.Add(
            self.lang_combo,
            flag=wx.LEFT | wx.ALIGN_CENTER_VERTICAL,
            border=self.FromDIP(utils.BORDER),
        )

        vert_sizer.Add(
            newline, flag=wx.TOP | wx.LEFT | wx.RIGHT, border=self.FromDIP(utils.BORDER * 2)
        )
        self.SetSizer(vert_sizer)


class AboutDialog(wx.Dialog):
    """
    Small window to show about info.
    """
