# PDFStitcher is a utility to work with PDF sewing patterns.
# Copyright (C) 2021 Charlotte Curtis
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import wx
from pdfstitcher import utils
from pdfstitcher.utils import Config
from babel import Locale


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

        lang_names = [Locale(*l.split("_")).display_name for l in utils.valid_langs]
        self.lang_combo = wx.ComboBox(
            self, choices=lang_names, style=wx.CB_READONLY
        )
        self.lang_combo.SetSelection(utils.valid_langs.index(Config.general["language"]))
        newline.Add(
            self.lang_combo,
            flag=wx.LEFT | wx.ALIGN_CENTER_VERTICAL,
            border=self.FromDIP(utils.BORDER),
        )
        vert_sizer.Add(
            newline, flag=wx.TOP | wx.LEFT | wx.RIGHT, border=self.FromDIP(utils.BORDER * 2)
        )

        # Check for updates on startup
        self.check_updates = wx.CheckBox(self, label=_("Check for updates on startup"))
        self.check_updates.SetValue(Config.general["check_updates"])
        vert_sizer.Add(self.check_updates, flag=wx.TOP | wx.LEFT | wx.RIGHT, border=self.FromDIP(utils.BORDER * 2))

        # Checkbox to save current margin and unit settings
        self.save_margin_checkbox = wx.CheckBox(
            self,
            label=_("Save current margin and unit settings")
        )
        vert_sizer.Add(
            self.save_margin_checkbox,
            flag=wx.TOP | wx.LEFT | wx.RIGHT,
            border=self.FromDIP(utils.BORDER * 2)
        )
        self.save_margin_checkbox.SetValue(True)

        # Checkbox to save current line properties
        self.save_line_props = wx.CheckBox(
            self,
            label=_("Save current line properties")
        )
        self.save_line_props.SetValue(True)
        vert_sizer.Add(
            self.save_line_props,
            flag=wx.TOP | wx.LEFT | wx.RIGHT,
            border=self.FromDIP(utils.BORDER * 2)
        )

        # File chooser for open/save directories
        newline = wx.BoxSizer(wx.HORIZONTAL)
        open_dir_btn = wx.Button(self, label=_("Default open directory"))
        newline.Add(open_dir_btn, flag=wx.ALIGN_CENTRE_VERTICAL)
        self.open_dir_display = wx.TextCtrl(self, value=Config.general["open_dir"],  size=self.FromDIP(utils.PATH_ENTRY_SIZE))
        open_dir_btn.Bind(wx.EVT_BUTTON, lambda event: self.choose_dir(event, textctrl=self.open_dir_display))
        newline.Add(
            self.open_dir_display,
            flag=wx.ALIGN_CENTRE_VERTICAL | wx.LEFT,
            border=self.FromDIP(utils.BORDER),
        )
        vert_sizer.Add(
            newline, flag=wx.EXPAND | wx.TOP | wx.LEFT | wx.RIGHT, border=self.FromDIP(utils.BORDER * 2)
        )

        newline = wx.BoxSizer(wx.HORIZONTAL)
        save_dir_btn = wx.Button(self, label=_("Default save directory"))
        newline.Add(save_dir_btn, flag=wx.ALIGN_CENTRE_VERTICAL)
        self.save_dir_display = wx.TextCtrl(self, value=Config.general["save_dir"], size=self.FromDIP(utils.PATH_ENTRY_SIZE))
        save_dir_btn.Bind(wx.EVT_BUTTON, lambda event: self.choose_dir(event, textctrl=self.save_dir_display))
        newline.Add(
            self.save_dir_display,
            proportion=1,
            flag=wx.ALIGN_CENTRE_VERTICAL | wx.LEFT,
            border=self.FromDIP(utils.BORDER),
        )
        vert_sizer.Add(
            newline, flag=wx.EXPAND | wx.TOP | wx.LEFT | wx.RIGHT, border=self.FromDIP(utils.BORDER * 2)
        )

        # Button to save settings
        save_button = wx.Button(self, label=_("Save preferences"))
        save_button.Bind(wx.EVT_BUTTON, self.on_save)
        vert_sizer.Add(save_button, flag=wx.ALIGN_RIGHT | wx.ALL, border=self.FromDIP(utils.BORDER * 3))

        self.SetSizerAndFit(vert_sizer)
    
    def choose_dir(self, event, textctrl):
        """
        Opens a file dialog to choose a directory.
        """
        current_path = textctrl.GetValue()
        with wx.DirDialog(
            self, 
            _("Choose a directory"),
            defaultPath=current_path,
            style=wx.DD_DEFAULT_STYLE | wx.DD_DIR_MUST_EXIST
            ) as dlg:
            
            if dlg.ShowModal() == wx.ID_OK:
                textctrl.SetValue(dlg.GetPath())

    def on_save(self, event):
        """
        Update the current config and save.
        """
        if self.save_margin_checkbox.IsChecked():
            # retrieve margin and units from main gui
            Config.general["margin"] = self.main_gui.io.margin_txt.GetValue()
            Config.general["units"] = utils.UNITS(self.main_gui.io.unit_box.GetSelection())
        
        if self.save_line_props.IsChecked():
            # retrieve line property choices from main gui
            lp = Config.line_props
            lp["colour"]["enable"] = self.main_gui.lt.enable_colour.IsChecked()
            lp["colour"]["fill"] = self.main_gui.lt.do_fill_colour.IsChecked()
            lp["colour"]["value"] = self.main_gui.lt.line_colour_ctrl.GetColour().Get()[:3]
 
            lp["thickness"]["enable"] = self.main_gui.lt.enable_thickness.IsChecked()
            lp["thickness"]["value"] = self.main_gui.lt.line_thick_ctrl.GetValue()
            lp["thickness"]["units"] = utils.UNITS(self.main_gui.lt.line_thick_units.GetSelection())

            lp["style"]["enable"] = self.main_gui.lt.enable_style.IsChecked()
            lp["style"]["value"] = self.main_gui.lt.line_style_ctrl.GetSelection()
        
        # update language choice
        lang_choice = utils.valid_langs[self.lang_combo.GetSelection()]
        language_change = False
        if lang_choice != Config.general["language"]:
            Config.general["language"] = lang_choice
            language_change = True

        # update open and save directories
        Config.general["open_dir"] = self.open_dir_display.GetValue()
        Config.general["save_dir"] = self.save_dir_display.GetValue()

        # update update check
        Config.general["check_updates"] = self.check_updates.IsChecked()

        # save config
        Config.save()

        msg = _("Preferences saved to {}").format(Config.config_dir / Config.config_file)
        if language_change:
            msg += _("\n\nPlease restart to switch to {}.".format(self.lang_combo.GetValue()))

        wx.MessageBox(msg, _("Preferences saved"), wx.OK | wx.ICON_INFORMATION)
        self.Destroy()


class AboutDialog(wx.Dialog):
    """
    Small window to show about info.
    """
