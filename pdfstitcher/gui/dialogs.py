# PDFStitcher is a utility to work with PDF sewing patterns.
# Copyright (C) 2021 Charlotte Curtis
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import wx, wx.adv
from pdfstitcher import utils
from pdfstitcher.utils import Config
from pdfstitcher import updater
from pdfstitcher import bug_info
from pathlib import Path
from babel import Locale
import webbrowser
import yaml


class UpdateDialog(wx.Dialog):
    """
    Window to call update checker and display results.
    """

    def __init__(self, *args, **kw):
        super(UpdateDialog, self).__init__(*args, **kw)
        self.SetTitle(_("Checking for updates"))
        self.nothing_exciting = False

        self.vert_sizer = wx.BoxSizer(wx.VERTICAL)
        self.info_txt = wx.TextCtrl(
            self,
            value=_("Please wait..."),
            size=self.FromDIP((400, -1)),
            style=wx.TE_MULTILINE | wx.TE_READONLY | wx.NO_BORDER,
        )

        # Style it to look like static text
        self.info_txt.SetBackgroundColour(self.GetBackgroundColour())
        self.vert_sizer.Add(
            self.info_txt,
            proportion=1,
            flag=wx.TOP | wx.LEFT | wx.RIGHT,
            border=self.FromDIP(utils.BORDER * 2),
        )

        self.SetSizerAndFit(self.vert_sizer)
        self.check_updates()

    def check_updates(self):
        """
        Check for updates and show results.
        """
        if updater.is_flatpak():
            self.info_txt.ChangeValue(_("PDFStitcher is installed and managed via Flatpak."))
            self.nothing_exciting = True
            return

        try:
            pypi_version = updater.update_available()

            if pypi_version is None:
                self.info_txt.ChangeValue(
                    _("No updates available, {} is the current version.").format(
                        utils.VERSION_STRING
                    )
                )
                self.nothing_exciting = True
            else:
                self.info_txt.ChangeValue(
                    _("Update available!")
                    + "\n"
                    + _("Your version is {}, but the latest version is v{}.").format(
                        utils.VERSION_STRING, pypi_version
                    )
                )
                changelog = wx.adv.HyperlinkCtrl(
                    self, label=_("What's changed?"), url=utils.GIT_HOME + "/releases/latest"
                )
                download_link = wx.adv.HyperlinkCtrl(
                    self, label=_("Download Now"), url=updater.get_download_url()
                )
                newline = wx.BoxSizer(wx.HORIZONTAL)
                newline.Add(changelog, flag=wx.ALL, border=self.FromDIP(utils.BORDER))
                newline.AddStretchSpacer()
                newline.Add(download_link, flag=wx.ALL, border=self.FromDIP(utils.BORDER))
                self.vert_sizer.Add(
                    newline,
                    flag=wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM,
                    border=self.FromDIP(utils.BORDER * 2),
                )
        except Exception as e:
            self.info_txt.ChangeValue(_("Error checking for updates") + f"\n{e}")

        self.vert_sizer.Fit(self)


class BugReporter(wx.Dialog):
    """
    Dialog to help users submit a bug report.
    """

    def __init__(self, *args, **kw):
        super(BugReporter, self).__init__(
            *args, style=wx.RESIZE_BORDER | wx.CAPTION | wx.CLOSE_BOX, **kw
        )
        self.SetTitle(_("Report a bug"))
        self.main_gui = kw["parent"]

        # Grab the width of the main gui as a guideline for how big it should be
        width = self.main_gui.GetSize()[0]

        vert_sizer = wx.BoxSizer(wx.VERTICAL)

        instructions = wx.StaticText(
            self,
            label=_(
                "Describe the steps reproduce the problem below. Follow the buttons to open an issue via GitHub (preferred, but requires login), or send the report via email. Optionally, include a mangled version of the input document - it will be saved to your Desktop and can be attached to the issue."
            ),
        )
        instructions.Wrap(width)
        vert_sizer.Add(
            instructions,
            flag=wx.TOP | wx.LEFT | wx.RIGHT,
            border=self.FromDIP(utils.BORDER * 2),
        )

        # Text box for bug report with copy button
        horiz_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.bug_report = wx.TextCtrl(
            self,
            value="",
            size=self.FromDIP((width, int(width * 2 / 3))),
            style=wx.TE_MULTILINE | wx.TE_PROCESS_ENTER,
        )
        horiz_sizer.Add(
            self.bug_report,
            proportion=1,
            flag=wx.EXPAND | wx.TOP | wx.LEFT | wx.RIGHT,
            border=self.FromDIP(utils.BORDER * 2),
        )

        # Button to copy text
        self.copy_text = wx.Button(self, id=wx.ID_COPY)
        self.copy_text.Bind(wx.EVT_BUTTON, self.copy_to_clipboard)

        horiz_sizer.Add(
            self.copy_text,
            flag=wx.TOP | wx.LEFT | wx.RIGHT,
            border=self.FromDIP(utils.BORDER * 2),
        )
        vert_sizer.Add(
            horiz_sizer,
            proportion=1,
            flag=wx.EXPAND | wx.TOP | wx.LEFT | wx.RIGHT,
            border=self.FromDIP(utils.BORDER * 2),
        )

        # Add some boilerplate text
        self.bug_report.AppendText("## Steps to reproduce the problem\n\n")
        self.bug_report.AppendText("1. \n")
        self.bug_report.AppendText("2. \n")
        self.bug_report.AppendText("3. \n\n\n")
        self.populate_system_info()

        # scroll back up to the top
        self.bug_report.SetInsertionPoint(0)

        # button to create mangled pdf
        # translation_note: A "mangled" pdf is a version of the input that has been modified to
        # make the content meaningless, but still have the same structure for debugging purposes.
        self.include_pdf = wx.Button(self, label=_("Create mangled PDF (Beta)"))
        self.include_pdf.Bind(wx.EVT_BUTTON, self.create_mangled_pdf)
        vert_sizer.Add(
            self.include_pdf,
            proportion=0,
            flag=wx.TOP | wx.LEFT | wx.RIGHT,
            border=self.FromDIP(utils.BORDER * 2),
        )

        # Button to report via Github
        horiz_sizer = wx.BoxSizer(wx.HORIZONTAL)
        report_btn = wx.Button(self, label=_("Report Via GitHub"))
        report_btn.Bind(wx.EVT_BUTTON, self.open_issue)
        horiz_sizer.Add(
            report_btn,
            flag=wx.RIGHT,
            border=self.FromDIP(utils.BORDER * 2),
        )

        # Slightly dangerous, but send me an email
        email_btn = wx.Button(self, label=_("Email to ccurtis@mtroyal.ca"))
        email_btn.Bind(wx.EVT_BUTTON, self.email_issue)
        horiz_sizer.Add(
            email_btn,
            flag=wx.RIGHT,
            border=self.FromDIP(utils.BORDER * 2),
        )
        vert_sizer.Add(
            horiz_sizer,
            proportion=0,
            flag=wx.ALL,
            border=self.FromDIP(utils.BORDER * 2),
        )

        self.SetSizerAndFit(vert_sizer)

    def populate_system_info(self) -> None:
        """
        Populate the system info section of the bug report.
        """

        self.bug_report.AppendText(
            "## Program Output\n" + "```\n" + self.main_gui.log.GetValue() + "```\n\n"
        )

        self.bug_report.AppendText(
            "## Current Configuration\n" + "```\n" + yaml.dump(Config.combo) + "```\n\n"
        )

        self.bug_report.AppendText(
            "## System Info\n" + "```\n" + bug_info.get_system_info() + "```\n\n"
        )

    def copy_to_clipboard(self, event):
        """Copies the bug report to the clipboard."""
        if wx.TheClipboard.Open():
            wx.TheClipboard.SetData(wx.TextDataObject(self.bug_report.GetValue()))
            wx.TheClipboard.Close()
        else:
            wx.MessageBox(_("Could not copy to clipboard"), _("Error"))

    def create_mangled_pdf(self, event):
        """Creates a mangled version of the input PDF."""
        pdf = self.main_gui.main_process.in_doc
        if not pdf:
            wx.MessageBox(_("No PDF loaded"), _("Error"))
            return

        save_path = Path(pdf.filename).parent
        with wx.DirDialog(
            self,
            _("Choose a location to save the mangled PDF"),
            defaultPath=str(save_path),
            style=wx.DD_DEFAULT_STYLE | wx.DD_DIR_MUST_EXIST,
        ) as dlg:
            if dlg.ShowModal() == wx.ID_OK:
                save_path = Path(dlg.GetPath())
            else:
                return

        progress_win = wx.ProgressDialog(
            _("Mangling PDF with {} pages".format(len(pdf.pages))),
            _("This may take some time, please wait"),
            style=wx.PD_CAN_ABORT | wx.PD_AUTO_HIDE,
        )
        try:
            pdf_path = bug_info.mangle_pdf(pdf, save_path, progress_win)
        except InterruptedError:
            print("Mangling PDF cancelled by user.")
            progress_win.Update(progress_win.GetRange())
            return

        if pdf_path:
            wx.MessageBox(
                _("Mangled PDF saved to {}.".format(pdf_path))
                + "\n\n"
                + _("Please attach to GitHub issue or email."),
                _("Success"),
            )
        else:
            wx.MessageBox(_("Failed to mangle PDF"), _("Error"))

    def open_issue(self, event):
        """
        Open a new issue in GitHub.
        """
        webbrowser.open(utils.GIT_HOME + "/issues/new")

    def email_issue(self, event):
        """
        Send a new email with the bug report.
        """
        webbrowser.open(
            "mailto:ccurtis@mtroyal.ca?subject=PDFStitcher Bug Report&body="
            + self.bug_report.GetValue()
        )


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
        self.lang_combo = wx.ComboBox(self, choices=lang_names, style=wx.CB_READONLY)
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
        vert_sizer.Add(
            self.check_updates,
            flag=wx.TOP | wx.LEFT | wx.RIGHT,
            border=self.FromDIP(utils.BORDER * 2),
        )

        # Checkbox to save current margin and unit settings
        self.save_margin_checkbox = wx.CheckBox(
            self, label=_("Save current margin and unit settings")
        )
        vert_sizer.Add(
            self.save_margin_checkbox,
            flag=wx.TOP | wx.LEFT | wx.RIGHT,
            border=self.FromDIP(utils.BORDER * 2),
        )
        self.save_margin_checkbox.SetValue(True)

        # Checkbox to save current line properties
        self.save_line_props = wx.CheckBox(self, label=_("Save current line properties"))
        self.save_line_props.SetValue(True)
        vert_sizer.Add(
            self.save_line_props,
            flag=wx.TOP | wx.LEFT | wx.RIGHT,
            border=self.FromDIP(utils.BORDER * 2),
        )

        # File chooser for open/save directories
        newline = wx.BoxSizer(wx.HORIZONTAL)
        open_dir_btn = wx.Button(self, label=_("Default open directory"))
        newline.Add(open_dir_btn, flag=wx.ALIGN_CENTRE_VERTICAL)
        self.open_dir_display = wx.TextCtrl(
            self, value=Config.general["open_dir"], size=self.FromDIP(utils.PATH_ENTRY_SIZE)
        )
        open_dir_btn.Bind(
            wx.EVT_BUTTON, lambda event: self.choose_dir(event, textctrl=self.open_dir_display)
        )
        newline.Add(
            self.open_dir_display,
            flag=wx.ALIGN_CENTRE_VERTICAL | wx.LEFT,
            border=self.FromDIP(utils.BORDER),
        )
        vert_sizer.Add(
            newline,
            flag=wx.EXPAND | wx.TOP | wx.LEFT | wx.RIGHT,
            border=self.FromDIP(utils.BORDER * 2),
        )

        newline = wx.BoxSizer(wx.HORIZONTAL)
        save_dir_btn = wx.Button(self, label=_("Default save directory"))
        newline.Add(save_dir_btn, flag=wx.ALIGN_CENTRE_VERTICAL)
        self.save_dir_display = wx.TextCtrl(
            self, value=Config.general["save_dir"], size=self.FromDIP(utils.PATH_ENTRY_SIZE)
        )
        save_dir_btn.Bind(
            wx.EVT_BUTTON, lambda event: self.choose_dir(event, textctrl=self.save_dir_display)
        )
        newline.Add(
            self.save_dir_display,
            proportion=1,
            flag=wx.ALIGN_CENTRE_VERTICAL | wx.LEFT,
            border=self.FromDIP(utils.BORDER),
        )
        vert_sizer.Add(
            newline,
            flag=wx.EXPAND | wx.TOP | wx.LEFT | wx.RIGHT,
            border=self.FromDIP(utils.BORDER * 2),
        )

        # Button to save settings
        save_button = wx.Button(self, label=_("Save preferences"))
        save_button.Bind(wx.EVT_BUTTON, self.on_save)
        vert_sizer.Add(
            save_button, flag=wx.ALIGN_RIGHT | wx.ALL, border=self.FromDIP(utils.BORDER * 3)
        )

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
            style=wx.DD_DEFAULT_STYLE | wx.DD_DIR_MUST_EXIST,
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
            msg += "\n\n" + _("Please restart to switch to {}.".format(self.lang_combo.GetValue()))

        wx.MessageBox(msg, _("Preferences saved"), wx.OK | wx.ICON_INFORMATION)
        self.Destroy()
