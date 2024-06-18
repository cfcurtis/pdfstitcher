#! /usr/bin/env python3

# PDFStitcher is a utility to work with PDF sewing patterns.
# Copyright (C) 2021 Charlotte Curtis
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import wx
from pdfstitcher.processing.mainproc import MainProcess
from pdfstitcher import utils
from pdfstitcher.utils import Config
from pdfstitcher.gui.dialogs import PrefsDialog, UpdateDialog, BugReporter
from pdfstitcher.gui.io_tab import IOTab
from pdfstitcher.gui.tile_tab import TileTab
from pdfstitcher.gui.layers_tab import LayersTab
from pathlib import Path
import os
import sys
import pikepdf
import traceback
import webbrowser


class PDFStitcherFrame(wx.Frame):
    """
    Main application frame and app.
    """

    def __init__(self, *args, **kw):
        # ensure the parent's __init__ is called
        super(PDFStitcherFrame, self).__init__(*args, **kw)
        self.progress_win = None

        # split the bottom half from the notebook top
        self.splitter = wx.SplitterWindow(self, style=wx.SP_LIVE_UPDATE)

        # create the notebook for the various tab panes
        nb = wx.Notebook(self.splitter)
        self.io = IOTab(nb, self)
        nb.AddPage(self.io, _("Options"))
        self.tt = TileTab(nb, self)
        nb.AddPage(self.tt, _("Tile Pages"))
        self.lt = LayersTab(nb)
        nb.AddPage(self.lt, _("Layers"))

        # create a panel for the go button and log window
        pnl = wx.Panel(self.splitter)
        vert_sizer = wx.BoxSizer(wx.VERTICAL)
        pnl.SetSizer(vert_sizer)

        # the go button
        go_btn = wx.Button(pnl, label=_("Generate PDF"))
        go_btn.SetFont(go_btn.GetFont().Bold())
        go_btn.Bind(wx.EVT_BUTTON, self.on_go_pressed)
        vert_sizer.Add(go_btn, flag=wx.ALL, border=self.FromDIP(utils.BORDER))

        # create a log window and redirect console output
        self.log = wx.TextCtrl(pnl, style=wx.TE_MULTILINE | wx.TE_READONLY | wx.HSCROLL)
        vert_sizer.Add(
            self.log, proportion=1, flag=wx.EXPAND | wx.ALL, border=self.FromDIP(utils.BORDER)
        )
        sys.stdout = self.log
        sys.stderr = self.log

        self.splitter.SplitHorizontally(nb, pnl)
        self.splitter.SetMinimumPaneSize(40)

        self.main_process = MainProcess()

        self.make_menu_bar()
        # connect the on_close event
        self.Bind(wx.EVT_CLOSE, self.on_exit)

        if sys.platform == "win32" or sys.platform == "linux":
            ico = utils.resource_path("stitcher-icon.ico")
            if ico.exists():
                self.SetIcon(wx.Icon(str(ico)))

        if len(sys.argv) > 1:
            self.load_file(sys.argv[1])

        if len(sys.argv) > 2:
            self.out_doc_path = sys.argv[2]
            self.io.output_fname_display.SetValue(sys.argv[2])

    def reset_sash_position(self):
        # Sets the output panel to occupy just 1/3 of the height
        # Needs to be called after construction for high DPI display.
        self.splitter.SetSashPosition(self.Size[1] * 2 // 3)

    def page_range_updated(self, event):
        """
        Mirror the page range options on both tabs.
        """
        if event.GetId() == self.io.page_range_txt.GetId():
            self.tt.page_range_txt.ChangeValue(self.io.page_range_txt.GetValue())
        elif event.GetId() == self.tt.page_range_txt.GetId():
            self.io.page_range_txt.ChangeValue(self.tt.page_range_txt.GetValue())

    def margin_updated(self, event):
        """
        Mirror the margin options on both tabs.
        """
        if event.GetId() == self.io.margin_txt.GetId():
            self.tt.margin_txt.ChangeValue(self.io.margin_txt.GetValue())
        elif event.GetId() == self.tt.margin_txt.GetId():
            self.io.margin_txt.ChangeValue(self.tt.margin_txt.GetValue())

    def unit_changed(self, event):
        """
        Mirror the unit options on both tabs.
        """
        if event.GetId() == self.io.unit_box.GetId():
            self.tt.unit_box.SetSelection(self.io.unit_box.GetSelection())
        elif event.GetId() == self.tt.unit_box.GetId():
            self.io.unit_box.SetSelection(self.tt.unit_box.GetSelection())

    def get_tile_opts(self):
        """
        Helper function to pack up the tiling options
        """
        # define trim options
        trim = [0.0] * 4
        trim[0] = utils.txt_to_float(self.tt.left_trim_txt.GetValue())
        trim[1] = utils.txt_to_float(self.tt.right_trim_txt.GetValue())
        trim[2] = utils.txt_to_float(self.tt.top_trim_txt.GetValue())
        trim[3] = utils.txt_to_float(self.tt.bottom_trim_txt.GetValue())

        # rows/cols
        cols = self.tt.columns_txt.GetValue().strip()
        cols = int(cols) if cols else None
        rows = self.tt.rows_txt.GetValue().strip()
        rows = int(rows) if rows else None

        return {
            # The bare minimum rows/columns (only one should be defined)
            "rows": rows,
            "cols": cols,
            # set all the various options of the tiler
            "col_major": bool(self.tt.col_row_order_combo.GetSelection()),
            "right_to_left": bool(self.tt.left_right_combo.GetSelection()),
            "bottom_to_top": bool(self.tt.top_bottom_combo.GetSelection()),
            # set the optional stuff
            "rotation": self.tt.rotate_combo.GetSelection(),
            # margins, margins!
            "margin": utils.txt_to_float(self.tt.margin_txt.GetValue()),
            # trim related stuff
            "trim": trim,
            "actually_trim": bool(self.tt.trim_overlap_combo.GetSelection()),
            "override_trim": bool(self.tt.override_trim.GetValue()),
        }

    def get_layer_opts(self):
        """
        Helper function to pack up the layer options
        """
        # no layers in document
        if not self.main_process.doc_info["layers"]:
            layer_opts = {
                "keep_ocs": "no_ocgs",
                "line_props": self.lt.line_props,
                "keep_non_oc": True,
                "delete_ocgs": True,
            }
        else:
            layer_opts = {
                "keep_ocs": self.lt.get_selected_layers(),
                "line_props": self.lt.line_props,
                "keep_non_oc": bool(self.lt.include_nonoc.GetValue()),
                "delete_ocgs": bool(self.lt.delete_ocgs.GetSelection() == 0),
            }

        return layer_opts

    def on_go_pressed(self, event):
        if self.main_process.in_doc is None:
            print(_("No PDF loaded"))
            return

        # make sure an output path is defined
        if self.out_doc_path is None:
            self.on_output(event)

            if self.out_doc_path is None:
                # user probably cancelled?
                return

        # global options
        self.main_process.page_range = self.io.page_range_txt.GetValue()
        Config.general["units"] = utils.UNITS(self.io.unit_box.GetSelection())

        # define the selected processing options
        self.main_process.toggle("LayerFilter", bool(self.io.do_layers.GetValue()))
        self.main_process.toggle("PageTiler", bool(self.io.do_tile.GetValue()))
        # Page Filter is active if PageTiler is not active, and vice versa

        self.main_process.set_params("LayerFilter", self.get_layer_opts())
        self.main_process.set_params("PageTiler", self.get_tile_opts())
        self.main_process.set_params(
            "PageFilter", {"margin": utils.txt_to_float(self.io.margin_txt.GetValue())}
        )

        progress_win = None
        if self.main_process.active["LayerFilter"]:
            # create the progress window if layer processing is selected
            progress_win = wx.ProgressDialog(
                _("Processing"),
                _("Processing, please wait"),
                style=wx.PD_CAN_ABORT | wx.PD_AUTO_HIDE,
            )

        # run the processing
        try:
            complete = self.main_process.run(progress_win)
            if not complete:
                print(_("Processing cancelled"))
            else:
                self.main_process.save(self.out_doc_path)
                print(_("Successfully written to") + " " + self.out_doc_path)
        except IOError as e:
            print(
                _("Something went wrong") + ", " + _("unable to write to") + " " + self.out_doc_path
            )
            print(e)
            print(_("Make sure " + self.out_doc_path + " isn't open in another program"))
        except Exception as e:
            print(_("Something went wrong"))
            traceback.print_exc()

    def make_menu_bar(self):
        """
        Make and populate the menubar.
        """
        menu_bar = wx.MenuBar()

        # Make a file menu with load and exit items
        file_menu = wx.Menu()
        open_item = file_menu.Append(wx.ID_OPEN)
        save_as_item = file_menu.Append(wx.ID_SAVE)
        exit_item = file_menu.Append(wx.ID_EXIT)
        self.Bind(wx.EVT_MENU, self.on_open, open_item)
        self.Bind(wx.EVT_MENU, self.on_output, save_as_item)
        self.Bind(wx.EVT_MENU, self.on_exit, exit_item)
        menu_bar.Append(file_menu, "&" + _("File"))

        # Make the settings menu
        settings_menu = wx.Menu()
        prefs_item = settings_menu.Append(wx.ID_PREFERENCES)
        update_item = wx.MenuItem(settings_menu, wx.ID_ANY, text=_("Check for updates"))
        settings_menu.Append(update_item)
        self.Bind(wx.EVT_MENU, self.on_prefs, prefs_item)
        self.Bind(wx.EVT_MENU, self.on_update, update_item)
        menu_bar.Append(settings_menu, "&" + _("Settings"))

        # Make the help menu
        help_menu = wx.Menu()
        docs_item = wx.MenuItem(
            help_menu,
            wx.ID_HELP,
            text=_("Documentation"),
            helpString=_("Open the documentation in a web browser"),
        )
        help_menu.Append(docs_item)
        about_item = help_menu.Append(wx.ID_ABOUT)
        self.Bind(wx.EVT_MENU, self.on_docs, docs_item)
        self.Bind(wx.EVT_MENU, self.on_about, about_item)
        bug_item = wx.MenuItem(
            help_menu,
            wx.ID_ANY,
            text=_("Report a bug"),
            helpString=_("Open the dialog to report a bug"),
        )
        help_menu.Append(bug_item)
        self.Bind(wx.EVT_MENU, self.on_bug, bug_item)
        menu_bar.Append(help_menu, "&" + _("Help"))

        self.SetMenuBar(menu_bar)

    def on_bug(self, event):
        """
        Open the dialog to report a bug.
        """
        bug_dia = BugReporter(parent=self)
        bug_dia.Show()

    def on_prefs(self, event):
        """
        Create and show the preferences dialog.
        """
        prefs_dia = PrefsDialog(parent=self)
        prefs_dia.Show()

    def on_update(self, event):
        """
        Open the dialog to check for updates.
        """
        update_dia = UpdateDialog(parent=self)
        if event is None and update_dia.nothing_exciting:
            update_dia.Destroy()
        else:
            update_dia.Show()

    def on_docs(self, event):
        """
        Open docs in a web browser when menu item is clicked.
        """
        webbrowser.open(utils.DOCS_PAGE)

    def on_about(self, event):
        """
        Show the about info.
        """
        ico = utils.resource_path("stitcher-icon.ico")
        about_info = wx.adv.AboutDialogInfo()
        if ico.exists():
            about_info.SetIcon(wx.Icon(str(ico)))
        about_info.SetName("PDFStitcher")
        about_info.SetVersion(utils.VERSION_STRING)
        about_info.SetDescription(_("The PDF Stitching app for sewists, by sewists."))
        about_info.SetCopyright("(C) 2020-2022")
        about_info.SetWebSite(utils.WEB_HOME)
        about_info.AddDeveloper("Charlotte Curtis")
        about_info.AddDeveloper(
            "\n"
            + _("Contributors")
            + ": https://github.com/cfcurtis/pdfstitcher/graphs/contributors"
        )
        about_info.SetLicense(
            "Mozilla Public License Version 2.0\n" "https://www.mozilla.org/en-US/MPL/2.0/"
        )

        wx.adv.AboutBox(about_info)

    def on_exit(self, event):
        self.Destroy()

    def on_output(self, event):
        with wx.FileDialog(
            self,
            _("Save output as"),
            defaultDir=Config.general["save_dir"],
            wildcard="PDF files (*.pdf)|*.pdf",
            style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT,
        ) as fileDialog:
            if fileDialog.ShowModal() == wx.ID_CANCEL:
                return

            pathname = fileDialog.GetPath()
            self.set_output_filename(pathname)

    def set_output_filename(self, pathname):
        """
        Helper function to define output filename and directory.
        """
        if pathname is None:
            return

        pathname = pathname.strip()
        Config.general["save_dir"] = str(Path(pathname).parent)

        if self.main_process.in_doc and pathname == self.main_process.in_doc.filename:
            wx.MessageBox(
                _("Can't overwrite input file, " + "please select a different file for output"),
                "Error",
                wx.OK | wx.ICON_ERROR,
            )
            self.on_output(wx.EVT_BUTTON)
        else:
            try:
                self.out_doc_path = pathname
                self.io.output_fname_display.ChangeValue(pathname)
                print(_("File will be written to " + pathname))

            except IOError:
                print(_("unable to write to") + pathname)

    def on_input_change(self, event):
        """
        Load the file by editing the text box directly.
        """
        pathname = self.io.input_fname_display.GetValue()
        self.load_file(pathname)

    def on_output_change(self, event):
        """
        Define the save file by editing the text box directly.
        """
        pathname = self.io.output_fname_display.GetValue()
        self.set_output_filename(pathname)

    def on_open(self, event):
        with wx.FileDialog(
            self,
            _("Select input PDF"),
            defaultDir=Config.general["open_dir"],
            wildcard="PDF files (*.pdf)|*.pdf",
            style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST,
        ) as fileDialog:
            if fileDialog.ShowModal() == wx.ID_CANCEL:
                return

            # Proceed loading the file chosen by the user
            pathname = fileDialog.GetPath()
            self.load_file(pathname)

    def update_gui_options(self):
        """
        Update the GUI options based on the loaded file.
        """
        if not self.main_process.in_doc:
            return

        Config.general["open_dir"] = str(Path(self.main_process.in_doc.filename).parent)

        # update the page range
        self.io.page_range_txt.ChangeValue("1-{}".format(self.main_process.doc_info["n_pages"]))
        if self.main_process.doc_info["n_pages"] == 1:
            self.io.do_tile.SetValue(0)
            self.io.do_tile.Disable()
        else:
            self.io.do_tile.Enable()

            # check how big the pages are, and default to no tiling if they're over A3
            w, h = self.main_process.doc_info["first_page_dims"]
            if w > 11.7 * 72 or h > 16.5 * 72:
                self.io.do_tile.SetValue(0)
            else:
                self.io.do_tile.SetValue(1)

        # update the layer options
        self.io.do_layers.SetValue(self.lt.load_new(self.main_process.doc_info["layers"]))

        # update the processing description
        self.io.on_option_checked(None)

        # reset the output path
        self.out_doc_path = None

    def load_file(self, pathname, password=""):
        """
        Open the pdf and enable/disable options based on the file.
        """
        # open the pdf
        pathname = pathname.strip()
        try:
            self.main_process.load_doc(pathname, password=password)
        except pikepdf.PasswordError:
            print(_("PDF locked! Enter the correct password."))

            password_dialog = wx.PasswordEntryDialog(
                self, _("Password"), _("PDF file is locked"), ""
            )
            if password_dialog.ShowModal() == wx.ID_OK:
                password = password_dialog.GetValue()
                password_dialog.Destroy()
                self.load_file(pathname, password)
            else:
                print(_("PDF will not open as you canceled the operation."))
                password_dialog.Destroy()
                return

        except IOError as e:
            print(_("Cannot open file") + " " + pathname)
            print(_("Error message") + f": {e}")
            return

        print(_("Opening") + " " + pathname)
        self.io.load_new(self.main_process.in_doc.filename, self.main_process.doc_info["n_pages"])
        # If we got this far, we should be good
        print(_("PDF file loaded without errors."))

        # Check for permissions
        if self.main_process.in_doc.is_encrypted:
            permissions = self.main_process.in_doc.allow
            print(_("This PDF is encrypted with the following permissions:"))
            for perm, allowed in permissions._asdict().items():
                print(f"{perm}: {allowed}")

        print(_("Please be respectful of the author and only use this tool for personal use."))
        self.update_gui_options()


def main(language_warning: str):
    """
    Create the app and run it.
    """
    app = wx.App()

    # Fix the size for high-resolution displays on windows
    if sys.platform.startswith("win32"):
        try:
            from ctypes import OleDLL

            OleDLL("shcore").SetProcessDpiAwareness(1)
        except Exception:
            # Probably Windows 7, or some other non-DPI aware issue
            pass

    disp_size = wx.DisplaySize()
    app_size = wx.Size(min(int(disp_size[0] * 0.6), 700), min(int(disp_size[1] * 0.85), 800))

    frm = PDFStitcherFrame(None, title="PDF Stitcher" + " " + utils.VERSION_STRING, size=app_size)
    frm.SetSize(frm.FromDIP(app_size))
    frm.reset_sash_position()

    if language_warning:
        print(language_warning)

    frm.Show()

    if Config.general["check_updates"]:
        frm.on_update(None)

    app.MainLoop()
