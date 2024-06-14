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


class IOTab(scrolled.ScrolledPanel):
    """
    UI elements for the first tab displayed on startup (Options + I/O).
    """

    def __init__(self, parent, main_gui):
        super(IOTab, self).__init__(parent)

        self.main_gui = main_gui
        vert_sizer = wx.BoxSizer(wx.VERTICAL)

        # add the various parameter inputs
        # Display the selected PDF
        newline = wx.BoxSizer(wx.HORIZONTAL)
        in_doc_btn = wx.Button(self, label=_("Select input PDF"))
        in_doc_btn.Bind(wx.EVT_BUTTON, main_gui.on_open)
        newline.Add(in_doc_btn, flag=wx.ALIGN_CENTRE_VERTICAL)
        self.input_fname_display = wx.TextCtrl(self, value="", style=wx.TE_PROCESS_ENTER)
        self.input_fname_display.Bind(wx.EVT_TEXT_ENTER, main_gui.on_input_change)
        newline.Add(
            self.input_fname_display,
            proportion=1,
            flag=wx.ALIGN_CENTRE_VERTICAL | wx.LEFT,
            border=self.FromDIP(utils.BORDER),
        )
        vert_sizer.Add(
            newline,
            flag=wx.EXPAND | wx.TOP | wx.LEFT | wx.RIGHT,
            border=self.FromDIP(utils.BORDER * 2),
        )

        newline = wx.BoxSizer(wx.HORIZONTAL)
        out_doc_btn = wx.Button(self, label=_("Save output as"))
        out_doc_btn.Bind(wx.EVT_BUTTON, main_gui.on_output)
        newline.Add(out_doc_btn, flag=wx.ALIGN_CENTRE_VERTICAL)
        self.output_fname_display = wx.TextCtrl(self, value="", style=wx.TE_PROCESS_ENTER)
        self.output_fname_display.Bind(wx.EVT_TEXT_ENTER, main_gui.on_output_change)
        newline.Add(
            self.output_fname_display,
            proportion=1,
            flag=wx.ALIGN_CENTRE_VERTICAL | wx.LEFT,
            border=self.FromDIP(utils.BORDER),
        )
        vert_sizer.Add(
            newline,
            flag=wx.EXPAND | wx.TOP | wx.LEFT | wx.RIGHT,
            border=self.FromDIP(utils.BORDER * 2),
        )

        # Output options
        vert_sizer.Add(
            wx.StaticLine(self, -1),
            flag=wx.EXPAND | wx.TOP | wx.BOTTOM,
            border=self.FromDIP(utils.BORDER),
        )
        lbl = wx.StaticText(self, label=_("Output Options"))
        lbl.SetFont(lbl.GetFont().Bold())
        vert_sizer.Add(lbl, flag=wx.TOP | wx.LEFT, border=self.FromDIP(utils.BORDER))

        # Page Range
        newline = wx.BoxSizer(wx.HORIZONTAL)
        newline.Add(
            wx.StaticText(self, label=_("Page Range") + ":"),
            flag=wx.ALIGN_CENTRE_VERTICAL,
        )
        self.page_range_txt = wx.TextCtrl(self)
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
        vert_sizer.Add(
            wx.StaticText(
                self,
                label=_(
                    "Pages assemble in specified order. 0 inserts a blank page."
                    + "\n"
                    + _("Use - for ranges. Example: 1-3, 0, 4, 0, 5-10.")
                ),
            ),
            flag=wx.TOP | wx.LEFT | wx.RIGHT,
            border=self.FromDIP(utils.BORDER * 2),
        )

        # Margin, duplicated from TileTab
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

        # Unit selection
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

        # checklist of features to enable/disable
        self.do_layers = wx.CheckBox(self, label=_("Process Layers"))
        vert_sizer.Add(
            self.do_layers,
            flag=wx.TOP | wx.LEFT | wx.RIGHT,
            border=self.FromDIP(utils.BORDER * 2),
        )
        self.do_tile = wx.CheckBox(self, label=_("Tile pages"))
        self.do_layers.Bind(wx.EVT_CHECKBOX, self.on_option_checked)
        self.do_tile.Bind(wx.EVT_CHECKBOX, self.on_option_checked)
        vert_sizer.Add(
            self.do_tile,
            flag=wx.TOP | wx.LEFT | wx.RIGHT,
            border=self.FromDIP(utils.BORDER * 2),
        )

        # describe what the options mean
        self.output_description = wx.StaticText(self, label="")
        vert_sizer.Add(
            self.output_description,
            flag=wx.TOP | wx.LEFT | wx.RIGHT,
            border=self.FromDIP(utils.BORDER * 2),
        )

        self.SetSizer(vert_sizer)
        self.SetupScrolling()
        self.SetBackgroundColour(parent.GetBackgroundColour())

    def load_new(self, path: str, n_pages: int):
        self.input_fname_display.ChangeValue(path)
        self.output_fname_display.ChangeValue("")
        self.page_range_txt.SetValue("1-{}".format(n_pages))

    def on_option_checked(self, event):
        do_layers = bool(self.do_layers.GetValue())
        do_tile = bool(self.do_tile.GetValue())

        if do_layers and do_tile:
            self.output_description.SetLabel(_("Process layers then tile pages and save"))

        if do_layers and not do_tile:
            self.output_description.SetLabel(_("Process layers and save without tiling pages"))

        if do_tile and not do_layers:
            self.output_description.SetLabel(_("Tile pages and save without processing layers"))

        if not do_tile and not do_layers:
            self.output_description.SetLabel(
                _("Open the PDF and save selected page range without modifying")
                + "\n"
                + _("Optionally, add margins to each page")
            )

        self.main_gui.tt.Enable(do_tile)
        self.main_gui.lt.Enable(do_layers)
