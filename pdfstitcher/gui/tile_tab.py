#! /usr/bin/env python3

# PDFStitcher is a utility to work with PDF sewing patterns.
# Copyright (C) 2021 Charlotte Curtis
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import wx
import wx.lib.scrolledpanel as scrolled
from pdfstitcher import utils
from pdfstitcher.utils import Config


class TileTab(scrolled.ScrolledPanel):
    """
    UI elements for the page tiling tab.
    """

    def __init__(self, parent, main_gui):
        super(TileTab, self).__init__(parent, -1)

        vert_sizer = wx.BoxSizer(wx.VERTICAL)

        ## REQUIRED PARAMETERS
        vert_sizer.Add(
            wx.StaticLine(self, -1),
            flag=wx.EXPAND | wx.TOP | wx.BOTTOM,
            border=self.FromDIP(utils.BORDER),
        )
        lbl = wx.StaticText(self, label=_("Required Parameters"))
        lbl.SetFont(lbl.GetFont().Bold())
        vert_sizer.Add(lbl, flag=wx.TOP | wx.LEFT, border=self.FromDIP(utils.BORDER))

        # Number of columns
        newline = wx.BoxSizer(wx.HORIZONTAL)
        newline.Add(
            wx.StaticText(self, label=_("Number of Columns") + ":"),
            flag=wx.ALIGN_CENTRE_VERTICAL,
        )
        self.columns_txt = wx.TextCtrl(
            self, size=self.FromDIP(utils.NUM_ENTRY_SIZE), style=wx.TE_RIGHT
        )
        self.columns_txt.Bind(wx.EVT_TEXT, self.on_col_row_entered)
        newline.Add(
            self.columns_txt,
            flag=wx.ALIGN_CENTRE_VERTICAL | wx.LEFT,
            border=self.FromDIP(utils.BORDER),
        )

        # OR number of rows
        newline.Add(
            wx.StaticText(self, label=_("OR Number of Rows") + ":"),
            flag=wx.ALIGN_CENTRE_VERTICAL | wx.LEFT,
            border=self.FromDIP(utils.BORDER * 2),
        )
        self.rows_txt = wx.TextCtrl(
            self, size=self.FromDIP(utils.NUM_ENTRY_SIZE), style=wx.TE_RIGHT
        )
        self.rows_txt.Bind(wx.EVT_TEXT, self.on_col_row_entered)
        newline.Add(
            self.rows_txt,
            flag=wx.ALIGN_CENTRE_VERTICAL | wx.LEFT,
            border=self.FromDIP(utils.BORDER),
        )
        vert_sizer.Add(
            newline, flag=wx.TOP | wx.LEFT | wx.RIGHT, border=self.FromDIP(utils.BORDER * 2)
        )

        # page order
        newline = wx.BoxSizer(wx.HORIZONTAL)
        col_row_order_opts = [_("Rows then columns"), _("Columns then rows")]
        left_right_opts = [_("Left to right"), _("Right to left")]
        top_bottom_opts = [_("Top to bottom"), _("Bottom to top")]

        newline.Add(
            wx.StaticText(self, label=_("Page order") + ":"),
            flag=wx.ALIGN_CENTRE_VERTICAL,
        )
        self.col_row_order_combo = wx.ComboBox(
            self,
            choices=col_row_order_opts,
            value=col_row_order_opts[0],
            style=wx.CB_READONLY,
        )
        newline.Add(
            self.col_row_order_combo,
            flag=wx.LEFT | wx.ALIGN_CENTRE_VERTICAL,
            border=self.FromDIP(utils.BORDER),
        )
        self.left_right_combo = wx.ComboBox(
            self,
            choices=left_right_opts,
            value=left_right_opts[0],
            style=wx.CB_READONLY,
        )
        newline.Add(
            self.left_right_combo,
            flag=wx.LEFT | wx.ALIGN_CENTRE_VERTICAL,
            border=self.FromDIP(utils.BORDER),
        )
        self.top_bottom_combo = wx.ComboBox(
            self,
            choices=top_bottom_opts,
            value=top_bottom_opts[0],
            style=wx.CB_READONLY,
        )
        newline.Add(
            self.top_bottom_combo,
            flag=wx.LEFT | wx.ALIGN_CENTRE_VERTICAL,
            border=self.FromDIP(utils.BORDER),
        )
        vert_sizer.Add(
            newline, flag=wx.TOP | wx.LEFT | wx.RIGHT, border=self.FromDIP(utils.BORDER * 2)
        )

        # rotation
        newline = wx.BoxSizer(wx.HORIZONTAL)
        rotate_opts = [
            _("None"),
            _("Clockwise"),
            _("Counterclockwise"),
            _("Turn Around"),
        ]
        newline.Add(
            wx.StaticText(self, label=_("Page Rotation") + ":"),
            flag=wx.ALIGN_CENTRE_VERTICAL,
        )
        self.rotate_combo = wx.ComboBox(
            self, choices=rotate_opts, value=rotate_opts[0], style=wx.CB_READONLY
        )
        newline.Add(
            self.rotate_combo,
            flag=wx.LEFT | wx.ALIGN_CENTRE_VERTICAL,
            border=self.FromDIP(utils.BORDER),
        )
        vert_sizer.Add(
            newline, flag=wx.TOP | wx.LEFT | wx.RIGHT, border=self.FromDIP(utils.BORDER * 2)
        )

        # duplicate the page range textbox here
        newline = wx.BoxSizer(wx.HORIZONTAL)
        newline.Add(
            wx.StaticText(self, label=_("Page Range") + ":"),
            flag=wx.ALIGN_CENTRE_VERTICAL,
        )
        self.page_range_txt = wx.TextCtrl(self)
        self.page_range_txt.SetToolTip(
            wx.ToolTip(_("Pages assemble in specified order. 0 inserts a blank page."))
        )
        self.page_range_txt.Bind(wx.EVT_TEXT, main_gui.page_range_updated)
        newline.Add(
            self.page_range_txt,
            proportion=1,
            flag=wx.ALIGN_CENTRE_VERTICAL | wx.LEFT,
            border=self.FromDIP(utils.BORDER),
        )
        vert_sizer.Add(
            newline,
            flag=wx.EXPAND | wx.TOP | wx.LEFT | wx.RIGHT,
            border=self.FromDIP(utils.BORDER * 2),
        )

        ## OPTIONAL PARAMETERS
        vert_sizer.Add(
            wx.StaticLine(self, -1),
            flag=wx.EXPAND | wx.TOP | wx.BOTTOM,
            border=self.FromDIP(utils.BORDER),
        )
        lbl = wx.StaticText(self, label=_("Optional Parameters"))
        lbl.SetFont(lbl.GetFont().Bold())
        vert_sizer.Add(lbl, flag=wx.TOP | wx.LEFT | wx.RIGHT, border=self.FromDIP(utils.BORDER * 2))

        # Margin - mirrored from options tab
        newline = wx.BoxSizer(wx.HORIZONTAL)
        newline.Add(
            wx.StaticText(self, label=_("Margin to add to final output") + ":"),
            flag=wx.ALIGN_CENTRE_VERTICAL,
        )
        self.margin_txt = wx.TextCtrl(
            self, size=self.FromDIP(utils.NUM_ENTRY_SIZE), style=wx.TE_RIGHT
        )
        self.margin_txt.Bind(wx.EVT_TEXT, main_gui.margin_updated)
        self.margin_txt.ChangeValue(Config.general["margin"])
        newline.Add(
            self.margin_txt,
            flag=wx.ALIGN_CENTRE_VERTICAL | wx.LEFT,
            border=self.FromDIP(utils.BORDER),
        )
        vert_sizer.Add(
            newline, flag=wx.TOP | wx.LEFT | wx.RIGHT, border=self.FromDIP(utils.BORDER * 2)
        )

        # Unit selection - mirrored from options tab
        unit_opts = [_("Inches"), _("Centimetres")]
        self.unit_box = wx.RadioBox(
            self, label=_("Units"), choices=unit_opts, style=wx.RA_SPECIFY_COLS
        )
        self.unit_box.SetSelection(Config.general["units"])
        vert_sizer.Add(
            self.unit_box,
            flag=wx.TOP | wx.LEFT | wx.RIGHT,
            border=self.FromDIP(utils.BORDER * 2),
        )
        self.unit_box.Bind(wx.EVT_RADIOBOX, main_gui.unit_changed)

        # override trimbox - sometimes needed for wonky PDFs
        # translation_note: TrimBox and MediaBox are PDF elements, so they likely won't translate nicely.
        self.override_trim = wx.CheckBox(self, label=_("Set TrimBox to MediaBox"))
        self.override_trim.SetToolTip(
            wx.ToolTip(_("May help fix things when output is not as expected"))
        )
        vert_sizer.Add(
            self.override_trim,
            flag=wx.TOP | wx.LEFT | wx.RIGHT,
            border=self.FromDIP(utils.BORDER * 2),
        )

        # Trim header
        newline = wx.BoxSizer(wx.HORIZONTAL)
        newline.Add(
            wx.StaticText(self, label=_("Amount to trim from each page") + ":"),
            flag=wx.ALIGN_CENTRE_VERTICAL,
        )
        trim_overlap_opts = [_("Overlap"), _("Trim")]
        self.trim_overlap_combo = wx.ComboBox(
            self,
            choices=trim_overlap_opts,
            value=trim_overlap_opts[0],
            style=wx.CB_READONLY,
        )
        newline.Add(
            self.trim_overlap_combo,
            flag=wx.ALIGN_CENTRE_VERTICAL | wx.LEFT,
            border=self.FromDIP(utils.BORDER * 3),
        )
        vert_sizer.Add(
            newline, flag=wx.TOP | wx.LEFT | wx.RIGHT, border=self.FromDIP(utils.BORDER * 2)
        )

        # Left trim
        newline = wx.BoxSizer(wx.HORIZONTAL)
        newline.Add(
            wx.StaticText(self, label=_("Left") + ":"),
            flag=wx.ALIGN_CENTRE_VERTICAL | wx.LEFT,
            border=self.FromDIP(utils.BORDER * 2),
        )
        self.left_trim_txt = wx.TextCtrl(
            self, size=self.FromDIP(utils.NUM_ENTRY_SIZE), style=wx.TE_RIGHT
        )
        newline.Add(
            self.left_trim_txt,
            flag=wx.ALIGN_CENTRE_VERTICAL | wx.LEFT,
            border=self.FromDIP(utils.BORDER),
        )

        # Right trim
        newline.Add(
            wx.StaticText(self, label=_("Right") + ":"),
            flag=wx.ALIGN_CENTRE_VERTICAL | wx.LEFT,
            border=self.FromDIP(utils.BORDER * 2),
        )
        self.right_trim_txt = wx.TextCtrl(
            self, size=self.FromDIP(utils.NUM_ENTRY_SIZE), style=wx.TE_RIGHT
        )
        newline.Add(
            self.right_trim_txt,
            flag=wx.ALIGN_CENTRE_VERTICAL | wx.LEFT,
            border=self.FromDIP(utils.BORDER),
        )

        # Top trim
        newline.Add(
            wx.StaticText(self, label=_("Top") + ":"),
            flag=wx.ALIGN_CENTRE_VERTICAL | wx.LEFT,
            border=self.FromDIP(utils.BORDER * 2),
        )
        self.top_trim_txt = wx.TextCtrl(
            self, size=self.FromDIP(utils.NUM_ENTRY_SIZE), style=wx.TE_RIGHT
        )
        newline.Add(
            self.top_trim_txt,
            flag=wx.ALIGN_CENTRE_VERTICAL | wx.LEFT,
            border=self.FromDIP(utils.BORDER),
        )

        # Bottom trim
        newline.Add(
            wx.StaticText(self, label=_("Bottom") + ":"),
            flag=wx.ALIGN_CENTRE_VERTICAL | wx.LEFT,
            border=self.FromDIP(utils.BORDER * 2),
        )
        self.bottom_trim_txt = wx.TextCtrl(
            self, size=self.FromDIP(utils.NUM_ENTRY_SIZE), style=wx.TE_RIGHT
        )
        newline.Add(
            self.bottom_trim_txt,
            flag=wx.ALIGN_CENTRE_VERTICAL | wx.LEFT,
            border=self.FromDIP(utils.BORDER),
        )
        vert_sizer.Add(
            newline, flag=wx.TOP | wx.LEFT | wx.RIGHT, border=self.FromDIP(utils.BORDER * 2)
        )

        self.SetSizer(vert_sizer)
        self.SetupScrolling()
        self.SetBackgroundColour(parent.GetBackgroundColour())

    def on_col_row_entered(self, event):
        # enforces just one of row or column entered
        if event.GetId() == self.columns_txt.GetId():
            self.rows_txt.ChangeValue("")
        if event.GetId() == self.rows_txt.GetId():
            self.columns_txt.ChangeValue("")
