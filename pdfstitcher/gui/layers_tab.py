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


class LayersTab(scrolled.ScrolledPanel):
    """
    UI elements for the layer modification tab.
    """

    def __init__(self, parent):
        super(LayersTab, self).__init__(parent)

        vert_sizer = wx.BoxSizer(wx.VERTICAL)

        # Status text
        self.status_txt = wx.StaticText(self, label=_("Load PDF to view layers."))
        vert_sizer.Add(
            self.status_txt,
            flag=wx.TOP | wx.LEFT | wx.RIGHT,
            border=self.FromDIP(utils.BORDER * 2),
        )

        # the main splitter for the layer stuff
        self.layer_splitter = wx.SplitterWindow(self, style=wx.SP_LIVE_UPDATE)
        self.layer_pane = wx.Panel(self.layer_splitter)
        layer_sizer = wx.BoxSizer(wx.VERTICAL)
        self.layer_pane.SetSizer(layer_sizer)

        # delete or hide deselected layers
        self.delete_ocgs = wx.RadioBox(
            self.layer_pane, label=_("Deselected layers:"), choices=[_("Delete"), _("Hide")]
        )
        layer_sizer.Add(
            self.delete_ocgs,
            flag=wx.LEFT | wx.RIGHT | wx.BOTTOM,
            border=self.FromDIP(utils.BORDER),
        )

        # check all, background, etc
        self.include_nonoc = wx.CheckBox(self.layer_pane, label=_("Include non-optional content"))
        self.include_nonoc.SetValue(1)
        layer_sizer.Add(
            self.include_nonoc,
            flag=wx.TOP | wx.LEFT | wx.RIGHT,
            border=self.FromDIP(utils.BORDER),
        )

        self.select_all = wx.CheckBox(self.layer_pane, label=_("Deselect all"))
        self.select_all.Bind(wx.EVT_CHECKBOX, self.on_select_all)
        layer_sizer.Add(
            self.select_all,
            flag=wx.TOP | wx.LEFT | wx.RIGHT,
            border=self.FromDIP(utils.BORDER),
        )

        # the main list box for layers
        self.layer_list = wx.ListCtrl(self.layer_pane, style=wx.LC_REPORT | wx.LC_SINGLE_SEL)
        self.layer_list.EnableCheckBoxes(True)
        self.layer_list.InsertColumn(0, _("Layer Name"))
        self.layer_list.InsertColumn(1, _("Line Properties"))
        self.layer_list.SetBackgroundColour(wx.Colour(180, 180, 180))
        self.layer_list.SetForegroundColour(wx.Colour(0, 0, 0))
        layer_sizer.Add(
            self.layer_list,
            proportion=1,
            flag=wx.EXPAND | wx.LEFT | wx.TOP,
            border=self.FromDIP(utils.BORDER),
        )
        self.layer_list.Bind(wx.EVT_LIST_ITEM_SELECTED, self.on_layer_selected)

        # build the set of controls for line properties
        self.line_prop_pane = wx.Panel(self.layer_splitter)
        line_prop_sizer = wx.BoxSizer(wx.VERTICAL)
        self.line_prop_pane.SetSizer(line_prop_sizer)

        # line properties
        # colour
        line_prop_sizer.Add(
            wx.StaticText(self.line_prop_pane, label=_("Select line properties to modify"))
        )
        newline = wx.BoxSizer(wx.HORIZONTAL)
        self.enable_colour = wx.CheckBox(self.line_prop_pane, label=_("Line Colour") + ":")
        self.enable_colour.SetValue(Config.line_props["colour"]["enable"])
        newline.Add(
            self.enable_colour,
            flag=wx.LEFT | wx.ALIGN_CENTER_VERTICAL,
            border=self.FromDIP(utils.BORDER * 2),
        )
        self.line_colour_ctrl = wx.ColourPickerCtrl(
            self.line_prop_pane, colour=Config.line_props["colour"]["value"]
        )
        newline.Add(
            self.line_colour_ctrl,
            flag=wx.LEFT | wx.ALIGN_CENTER_VERTICAL,
            border=self.FromDIP(utils.BORDER),
        )
        line_prop_sizer.Add(newline, flag=wx.TOP, border=self.FromDIP(utils.BORDER * 2))

        # Fill colour
        self.do_fill_colour = wx.CheckBox(self.line_prop_pane, label=_("Also modify fill colour"))
        self.do_fill_colour.SetValue(Config.line_props["colour"]["fill"])
        line_prop_sizer.AddSpacer(self.FromDIP(utils.BORDER * 2))
        line_prop_sizer.Add(
            self.do_fill_colour, flag=wx.LEFT, border=self.FromDIP(utils.BORDER * 5)
        )

        # thickness
        newline = wx.BoxSizer(wx.HORIZONTAL)
        self.enable_thickness = wx.CheckBox(self.line_prop_pane, label=_("Line Thickness") + ":")
        self.enable_thickness.SetValue(Config.line_props["thickness"]["enable"])
        newline.Add(
            self.enable_thickness,
            flag=wx.LEFT | wx.ALIGN_CENTER_VERTICAL,
            border=self.FromDIP(utils.BORDER * 2),
        )
        self.line_thick_ctrl = wx.TextCtrl(
            self.line_prop_pane,
            size=self.FromDIP(utils.NUM_ENTRY_SIZE),
            value=Config.line_props["thickness"]["value"],
        )
        newline.Add(
            self.line_thick_ctrl,
            flag=wx.LEFT | wx.ALIGN_CENTER_VERTICAL,
            border=self.FromDIP(utils.BORDER),
        )

        # Extra note for pybabel to make translations make sense (particularly for inches)
        # translation_note: pt = "points", in = "inches", cm = "centimeters"
        unit_choice = [_("in"), _("cm"), _("pt")]
        self.line_thick_units = wx.ComboBox(self.line_prop_pane, choices=unit_choice)
        self.line_thick_units.SetSelection(Config.line_props["thickness"]["units"])

        newline.Add(
            self.line_thick_units,
            flag=wx.LEFT | wx.ALIGN_CENTER_VERTICAL,
            border=self.FromDIP(utils.BORDER),
        )
        line_prop_sizer.Add(newline, flag=wx.TOP, border=self.FromDIP(utils.BORDER * 2))

        # style
        newline = wx.BoxSizer(wx.HORIZONTAL)
        self.enable_style = wx.CheckBox(self.line_prop_pane, label=_("Line Style") + ":")
        self.enable_style.SetValue(Config.line_props["style"]["enable"])
        newline.Add(
            self.enable_style,
            flag=wx.LEFT | wx.ALIGN_CENTER_VERTICAL,
            border=self.FromDIP(utils.BORDER * 2),
        )
        self.style_names = (_("Solid"), _("Dashed"), _("Dotted"))
        self.line_style_ctrl = wx.ComboBox(
            self.line_prop_pane,
            choices=self.style_names,
            style=wx.CB_READONLY,
        )
        self.line_style_ctrl.SetSelection(Config.line_props["style"]["value"])
        newline.Add(
            self.line_style_ctrl,
            flag=wx.LEFT | wx.ALIGN_CENTER_VERTICAL,
            border=self.FromDIP(utils.BORDER),
        )
        line_prop_sizer.Add(newline, flag=wx.TOP, border=self.FromDIP(utils.BORDER * 2))

        # apply/reset buttons
        self.apply_reset_pane = wx.Panel(self.line_prop_pane)
        apply_sizer = wx.BoxSizer(wx.VERTICAL)
        newline = wx.BoxSizer(wx.HORIZONTAL)
        self.apply_ls_btn = wx.Button(self.apply_reset_pane, label=_("Apply"))
        self.apply_ls_btn.Bind(wx.EVT_BUTTON, self.apply_ls_pressed)
        self.reset_ls_btn = wx.Button(self.apply_reset_pane, label=_("Reset"))
        self.reset_ls_btn.Bind(wx.EVT_BUTTON, self.reset_ls_pressed)
        newline.Add(
            self.apply_ls_btn,
            proportion=1,
            flag=wx.EXPAND | wx.LEFT,
            border=self.FromDIP(utils.BORDER),
        )
        newline.Add(
            self.reset_ls_btn,
            proportion=1,
            flag=wx.EXPAND | wx.LEFT,
            border=self.FromDIP(utils.BORDER),
        )
        apply_sizer.Add(newline, flag=wx.TOP | wx.EXPAND, border=self.FromDIP(utils.BORDER * 2))

        # apply to checked
        newline = wx.BoxSizer(wx.HORIZONTAL)
        self.apply_ls_all = wx.Button(self.apply_reset_pane, label=_("Apply to checked"))
        self.apply_ls_all.Bind(wx.EVT_BUTTON, self.apply_all_pressed)
        self.reset_all = wx.Button(self.apply_reset_pane, label=_("Reset checked"))
        self.reset_all.Bind(wx.EVT_BUTTON, self.reset_all_pressed)
        newline.Add(self.apply_ls_all, flag=wx.LEFT, border=self.FromDIP(utils.BORDER))
        newline.Add(self.reset_all, flag=wx.LEFT, border=self.FromDIP(utils.BORDER))
        apply_sizer.Add(newline, flag=wx.TOP, border=self.FromDIP(utils.BORDER))
        self.apply_reset_pane.SetSizer(apply_sizer)
        line_prop_sizer.Add(
            self.apply_reset_pane, flag=wx.TOP | wx.EXPAND, border=self.FromDIP(utils.BORDER * 2)
        )

        # Final assembly
        self.layer_splitter.SetSashGravity(0.5)
        self.layer_splitter.SplitVertically(self.layer_pane, self.line_prop_pane)
        vert_sizer.Add(
            self.layer_splitter,
            proportion=1,
            flag=wx.TOP | wx.LEFT | wx.RIGHT | wx.EXPAND,
            border=self.FromDIP(utils.BORDER * 2),
        )

        self.SetSizer(vert_sizer)
        self.SetupScrolling()
        self.SetBackgroundColour(parent.GetBackgroundColour())
        self._line_props = {}

    @property
    def line_props(self):
        if self.apply_reset_pane.IsShown():
            return self._line_props
        else:
            # No layers, but pass on selections
            self.apply_ls("no_ocgs")
            return self._line_props

    def apply_ls(self, layer):
        line_str = ""
        self._line_props[layer] = {}

        if self.enable_thickness.IsChecked():
            line_thick = utils.txt_to_float(self.line_thick_ctrl.GetValue())

            if line_thick is None:
                return "", None

            units = utils.UNITS(self.line_thick_units.GetSelection())
            line_str += f"{line_thick} {units} "
            line_thick = units.units_to_pts(line_thick)
            self._line_props[layer]["thickness"] = line_thick

        if self.enable_style.IsChecked():
            line_str += f"{self.style_names[self.line_style_ctrl.GetSelection()]}"
            self._line_props[layer]["style"] = self.line_style_ctrl.GetSelection()

        if self.enable_colour.IsChecked():
            colour = self.line_colour_ctrl.GetColour()
            # ignore alpha
            rgb = [val / 255 for val in colour.Get()[:3]]
            self._line_props[layer]["rgb"] = rgb
            self._line_props[layer]["fill_colour"] = self.do_fill_colour.IsChecked()
        else:
            colour = None

        return line_str, colour

    def apply_ls_pressed(self, event):
        sel = self.layer_list.GetFirstSelected()

        if sel == -1:
            return

        layer = self.layer_list.GetItemText(sel, 0)
        line_str, colour = self.apply_ls(layer)
        self.layer_list.SetItem(sel, 1, line_str)

        if colour is not None:
            if self.do_fill_colour.IsChecked():
                self.layer_list.SetItem(sel, 1, "\u25A0 " + line_str)
            else:
                self.layer_list.SetItem(sel, 1, "\u25A1 " + line_str)
            self.layer_list.SetItemTextColour(sel, colour)

    def apply_all_pressed(self, event):
        n_layers = self.layer_list.GetItemCount()

        for sel in range(n_layers):
            if self.layer_list.IsItemChecked(sel):
                layer = self.layer_list.GetItemText(sel, 0)
                line_str, colour = self.apply_ls(layer)
                self.layer_list.SetItem(sel, 1, line_str)

                if colour is not None:
                    self.layer_list.SetItem(sel, 1, "\u25A0 " + line_str)
                    self.layer_list.SetItemTextColour(sel, colour)

    def reset_ls_pressed(self, event):
        sel = self.layer_list.GetFirstSelected()
        if sel == -1:
            return

        layer = self.layer_list.GetItemText(sel, 0)

        if layer in self._line_props:
            del self._line_props[layer]

        self.layer_list.SetItem(sel, 1, "")
        self.layer_list.SetItemTextColour(sel, wx.Colour(0, 0, 0))

    def reset_all_pressed(self, event):
        n_layers = self.layer_list.GetItemCount()

        for sel in range(n_layers):
            if self.layer_list.IsItemChecked(sel):
                layer = self.layer_list.GetItemText(sel, 0)

                if layer in self._line_props:
                    del self._line_props[layer]

                self.layer_list.SetItem(sel, 1, "")
                self.layer_list.SetItemTextColour(sel, wx.Colour(0, 0, 0))

    def on_layer_selected(self, event):
        self.apply_ls_btn.SetLabel(_("Apply to") + " " + event.Label)
        self.reset_ls_btn.SetLabel(_("Reset") + " " + event.Label)

    def load_new(self, layers):
        maybe_spacer = self.line_prop_pane.GetSizer().GetItem(0)
        if not layers:
            self.status_txt.SetLabel(
                _("No layers found in input document.")
                + "\n"
                + _("Selected properties will apply to all lines in the document.")
            )
            self.layer_splitter.Unsplit(self.layer_pane)
            if maybe_spacer.IsSpacer():
                self.line_prop_pane.GetSizer().Remove(0)
            self.apply_reset_pane.Hide()
            self.Layout()
            return False

        self.layer_list.DeleteAllItems()
        for i, l in enumerate(layers):
            self.layer_list.InsertItem(i, l)

        self.layer_list.SetColumnWidth(0, wx.LIST_AUTOSIZE_USEHEADER)
        self.layer_list.SetColumnWidth(1, wx.LIST_AUTOSIZE_USEHEADER)
        self.set_all_checked(True)

        self.status_txt.SetLabel(_("Select layers to include in output document."))
        self.layer_splitter.SplitVertically(self.layer_pane, self.line_prop_pane)
        if not maybe_spacer.IsSpacer():
            self.line_prop_pane.GetSizer().InsertSpacer(0, 100)
        self.apply_reset_pane.Show()
        self.Layout()

        # reset the line properties dictionary
        self._line_props = {}
        return True

    def set_all_checked(self, select=True):
        self.select_all.SetValue(select)
        for i in range(self.layer_list.GetItemCount()):
            self.layer_list.CheckItem(i, select)

    def on_select_all(self, event):
        is_checked = event.GetSelection()
        self.set_all_checked(event.GetSelection())

        if is_checked:
            self.select_all.SetLabel(_("Deselect all"))
        else:
            self.select_all.SetLabel(_("Select all"))

    def get_selected_layers(self):
        if not self.apply_reset_pane.IsShown():
            return []

        n_layers = self.layer_list.GetItemCount()
        selected = []
        for i in range(n_layers):
            if self.layer_list.IsItemChecked(i):
                selected.append(self.layer_list.GetItemText(i, col=0))

        if n_layers == len(selected) and len(self._line_props) == 0:
            return "all"

        return selected
