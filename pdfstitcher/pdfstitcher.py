#! /usr/bin/env python3

# PDFStitcher is a utility to work with PDF sewing patterns.
# Copyright (C) 2021 Charlotte Curtis
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import wx
import wx.lib.scrolledpanel as scrolled
from pdfstitcher.tile_pages import PageTiler
from pdfstitcher.layerfilter import LayerFilter
from pdfstitcher.pagefilter import PageFilter
import os
import sys
import pikepdf
from pdfstitcher import utils
import traceback

# Constant widget sizes - used for all the different panels
BORDER = 5
TXT_ENTRY_SIZE = (40, -1)


class IOTab(scrolled.ScrolledPanel):
    def __init__(self, parent, main_gui):
        super(IOTab, self).__init__(parent)

        vert_sizer = wx.BoxSizer(wx.VERTICAL)

        # add the various parameter inputs
        # Display the selected PDF
        newline = wx.BoxSizer(wx.HORIZONTAL)
        in_doc_btn = wx.Button(self, label=_('Select input PDF'))
        in_doc_btn.Bind(wx.EVT_BUTTON, main_gui.on_open)
        newline.Add(in_doc_btn, flag=wx.ALIGN_CENTRE_VERTICAL)
        self.input_fname_display = wx.StaticText(self, label=_('None'))
        newline.Add(
            self.input_fname_display,
            flag=wx.ALIGN_CENTRE_VERTICAL | wx.LEFT,
            border=self.FromDIP(BORDER),
        )
        vert_sizer.Add(
            newline, flag=wx.TOP | wx.LEFT | wx.RIGHT, border=self.FromDIP(BORDER * 2)
        )

        newline = wx.BoxSizer(wx.HORIZONTAL)
        out_doc_btn = wx.Button(self, label=_('Save output as'))
        out_doc_btn.Bind(wx.EVT_BUTTON, main_gui.on_output)
        newline.Add(out_doc_btn, flag=wx.ALIGN_CENTRE_VERTICAL)
        self.output_fname_display = wx.StaticText(self, label=_('None'))
        newline.Add(
            self.output_fname_display,
            flag=wx.ALIGN_CENTRE_VERTICAL | wx.LEFT,
            border=self.FromDIP(BORDER),
        )
        vert_sizer.Add(
            newline, flag=wx.TOP | wx.LEFT | wx.RIGHT, border=self.FromDIP(BORDER * 2)
        )

        # Output options
        vert_sizer.Add(
            wx.StaticLine(self, -1),
            flag=wx.EXPAND | wx.TOP | wx.BOTTOM,
            border=self.FromDIP(BORDER),
        )
        lbl = wx.StaticText(self, label=_('Output Options'))
        lbl.SetFont(lbl.GetFont().Bold())
        vert_sizer.Add(lbl, flag=wx.TOP | wx.LEFT, border=self.FromDIP(BORDER))

        # Page Range
        newline = wx.BoxSizer(wx.HORIZONTAL)
        newline.Add(
            wx.StaticText(self, label=_('Page Range') + ':'),
            flag=wx.ALIGN_CENTRE_VERTICAL,
        )
        self.page_range_txt = wx.TextCtrl(self)
        self.page_range_txt.SetToolTip(
            wx.ToolTip(_('Pages assemble in specified order. 0 inserts a blank page.'))
        )
        self.page_range_txt.Bind(wx.EVT_TEXT, main_gui.page_range_updated)
        newline.Add(
            self.page_range_txt,
            proportion=1,
            flag=wx.ALIGN_CENTRE_VERTICAL | wx.LEFT,
            border=self.FromDIP(BORDER),
        )
        vert_sizer.Add(
            newline,
            flag=wx.EXPAND | wx.TOP | wx.LEFT | wx.RIGHT,
            border=self.FromDIP(BORDER * 2),
        )

        # Margin, duplicated from TileTab
        newline = wx.BoxSizer(wx.HORIZONTAL)
        newline.Add(
            wx.StaticText(self, label=_('Margin to add to final output') + ':'),
            flag=wx.ALIGN_CENTRE_VERTICAL,
        )
        self.margin_txt = wx.TextCtrl(
            self, size=self.FromDIP(TXT_ENTRY_SIZE), style=wx.TE_RIGHT
        )
        self.margin_txt.Bind(wx.EVT_TEXT, main_gui.margin_updated)
        newline.Add(
            self.margin_txt,
            flag=wx.ALIGN_CENTRE_VERTICAL | wx.LEFT,
            border=self.FromDIP(BORDER),
        )
        vert_sizer.Add(
            newline, flag=wx.TOP | wx.LEFT | wx.RIGHT, border=self.FromDIP(BORDER * 2)
        )

        # checklist of features to enable/disable
        self.do_layers = wx.CheckBox(self, label=_('Process Layers'))
        self.do_layers.SetValue(1)
        vert_sizer.Add(
            self.do_layers,
            flag=wx.TOP | wx.LEFT | wx.RIGHT,
            border=self.FromDIP(BORDER * 2),
        )
        self.do_tile = wx.CheckBox(self, label=_('Tile pages'))
        self.do_tile.SetValue(1)
        self.do_layers.Bind(wx.EVT_CHECKBOX, self.on_option_checked)
        self.do_tile.Bind(wx.EVT_CHECKBOX, self.on_option_checked)
        vert_sizer.Add(
            self.do_tile,
            flag=wx.TOP | wx.LEFT | wx.RIGHT,
            border=self.FromDIP(BORDER * 2),
        )

        # describe what the options mean
        self.output_description = wx.StaticText(self, label='')
        vert_sizer.Add(
            self.output_description,
            flag=wx.TOP | wx.LEFT | wx.RIGHT,
            border=self.FromDIP(BORDER * 2),
        )
        self.on_option_checked(event=None)

        self.SetSizer(vert_sizer)
        self.SetupScrolling()
        self.SetBackgroundColour(parent.GetBackgroundColour())

    def load_new(self, in_doc):
        self.input_fname_display.SetLabel(in_doc.filename)
        self.output_fname_display.SetLabel(label=_('None'))
        self.page_range_txt.SetValue('1-{}'.format(len(in_doc.pages)))

    def on_option_checked(self, event):
        do_layers = bool(self.do_layers.GetValue())
        do_tile = bool(self.do_tile.GetValue())

        if do_layers and do_tile:
            self.output_description.SetLabel(
                _('Process layers then tile pages and save')
            )

        if do_layers and not do_tile:
            self.output_description.SetLabel(
                _('Process layers and save without tiling pages')
            )

        if do_tile and not do_layers:
            self.output_description.SetLabel(
                _('Tile pages and save without processing layers')
            )

        if not do_tile and not do_layers:
            self.output_description.SetLabel(
                _('Open the PDF and save selected page range without modifying')
            )


class TileTab(scrolled.ScrolledPanel):
    def __init__(self, parent, main_gui):
        super(TileTab, self).__init__(parent, -1)

        vert_sizer = wx.BoxSizer(wx.VERTICAL)

        ## REQUIRED PARAMETERS
        vert_sizer.Add(
            wx.StaticLine(self, -1),
            flag=wx.EXPAND | wx.TOP | wx.BOTTOM,
            border=self.FromDIP(BORDER),
        )
        lbl = wx.StaticText(self, label=_('Required Parameters'))
        lbl.SetFont(lbl.GetFont().Bold())
        vert_sizer.Add(lbl, flag=wx.TOP | wx.LEFT, border=self.FromDIP(BORDER))

        # Number of columns
        newline = wx.BoxSizer(wx.HORIZONTAL)
        newline.Add(
            wx.StaticText(self, label=_('Number of Columns') + ':'),
            flag=wx.ALIGN_CENTRE_VERTICAL,
        )
        self.columns_txt = wx.TextCtrl(
            self, size=self.FromDIP(TXT_ENTRY_SIZE), style=wx.TE_RIGHT
        )
        self.columns_txt.Bind(wx.EVT_TEXT, self.on_col_row_entered)
        newline.Add(
            self.columns_txt,
            flag=wx.ALIGN_CENTRE_VERTICAL | wx.LEFT,
            border=self.FromDIP(BORDER),
        )

        # OR number of rows
        newline.Add(
            wx.StaticText(self, label=_('OR Number of Rows') + ':'),
            flag=wx.ALIGN_CENTRE_VERTICAL | wx.LEFT,
            border=self.FromDIP(BORDER * 2),
        )
        self.rows_txt = wx.TextCtrl(
            self, size=self.FromDIP(TXT_ENTRY_SIZE), style=wx.TE_RIGHT
        )
        self.rows_txt.Bind(wx.EVT_TEXT, self.on_col_row_entered)
        newline.Add(
            self.rows_txt,
            flag=wx.ALIGN_CENTRE_VERTICAL | wx.LEFT,
            border=self.FromDIP(BORDER),
        )
        vert_sizer.Add(
            newline, flag=wx.TOP | wx.LEFT | wx.RIGHT, border=self.FromDIP(BORDER * 2)
        )

        # page order
        newline = wx.BoxSizer(wx.HORIZONTAL)
        col_row_order_opts = [_('Rows then columns'), _('Columns then rows')]
        left_right_opts = [_('Left to right'), _('Right to left')]
        top_bottom_opts = [_('Top to bottom'), _('Bottom to top')]

        newline.Add(
            wx.StaticText(self, label=_('Page order') + ':'),
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
            border=self.FromDIP(BORDER),
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
            border=self.FromDIP(BORDER),
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
            border=self.FromDIP(BORDER),
        )
        vert_sizer.Add(
            newline, flag=wx.TOP | wx.LEFT | wx.RIGHT, border=self.FromDIP(BORDER * 2)
        )

        # rotation
        newline = wx.BoxSizer(wx.HORIZONTAL)
        rotate_opts = [
            _('None'),
            _('Clockwise'),
            _('Counterclockwise'),
            _('Turn Around'),
        ]
        newline.Add(
            wx.StaticText(self, label=_('Page Rotation') + ':'),
            flag=wx.ALIGN_CENTRE_VERTICAL,
        )
        self.rotate_combo = wx.ComboBox(
            self, choices=rotate_opts, value=rotate_opts[0], style=wx.CB_READONLY
        )
        newline.Add(
            self.rotate_combo,
            flag=wx.LEFT | wx.ALIGN_CENTRE_VERTICAL,
            border=self.FromDIP(BORDER),
        )
        vert_sizer.Add(
            newline, flag=wx.TOP | wx.LEFT | wx.RIGHT, border=self.FromDIP(BORDER * 2)
        )

        # duplicate the page range textbox here
        newline = wx.BoxSizer(wx.HORIZONTAL)
        newline.Add(
            wx.StaticText(self, label=_('Page Range') + ':'),
            flag=wx.ALIGN_CENTRE_VERTICAL,
        )
        self.page_range_txt = wx.TextCtrl(self)
        self.page_range_txt.SetToolTip(
            wx.ToolTip(_('Pages assemble in specified order. 0 inserts a blank page.'))
        )
        self.page_range_txt.Bind(wx.EVT_TEXT, main_gui.page_range_updated)
        newline.Add(
            self.page_range_txt,
            proportion=1,
            flag=wx.ALIGN_CENTRE_VERTICAL | wx.LEFT,
            border=self.FromDIP(BORDER),
        )
        vert_sizer.Add(
            newline,
            flag=wx.EXPAND | wx.TOP | wx.LEFT | wx.RIGHT,
            border=self.FromDIP(BORDER * 2),
        )

        ## OPTIONAL PARAMETERS
        vert_sizer.Add(
            wx.StaticLine(self, -1),
            flag=wx.EXPAND | wx.TOP | wx.BOTTOM,
            border=self.FromDIP(BORDER),
        )
        lbl = wx.StaticText(self, label=_('Optional Parameters'))
        lbl.SetFont(lbl.GetFont().Bold())
        vert_sizer.Add(
            lbl, flag=wx.TOP | wx.LEFT | wx.RIGHT, border=self.FromDIP(BORDER * 2)
        )

        # unit selection
        unit_opts = [_('Inches'), _('Centimetres')]
        self.unit_box = wx.RadioBox(
            self, label=_('Units'), choices=unit_opts, style=wx.RA_SPECIFY_COLS
        )
        vert_sizer.Add(
            self.unit_box,
            flag=wx.TOP | wx.LEFT | wx.RIGHT,
            border=self.FromDIP(BORDER * 2),
        )

        # override trimbox - sometimes needed for wonky PDFs
        # translation_note: TrimBox and MediaBox are PDF elements, so they likely won't translate nicely.
        self.override_trim = wx.CheckBox(self, label=_('Set TrimBox to MediaBox'))
        self.override_trim.SetToolTip(
            wx.ToolTip(_('May help fix things when output is not as expected'))
        )
        vert_sizer.Add(
            self.override_trim,
            flag=wx.TOP | wx.LEFT | wx.RIGHT,
            border=self.FromDIP(BORDER * 2),
        )

        # Margin
        newline = wx.BoxSizer(wx.HORIZONTAL)
        newline.Add(
            wx.StaticText(self, label=_('Margin to add to final output') + ':'),
            flag=wx.ALIGN_CENTRE_VERTICAL,
        )
        self.margin_txt = wx.TextCtrl(
            self, size=self.FromDIP(TXT_ENTRY_SIZE), style=wx.TE_RIGHT
        )
        self.margin_txt.Bind(wx.EVT_TEXT, main_gui.margin_updated)
        newline.Add(
            self.margin_txt,
            flag=wx.ALIGN_CENTRE_VERTICAL | wx.LEFT,
            border=self.FromDIP(BORDER),
        )
        vert_sizer.Add(
            newline, flag=wx.TOP | wx.LEFT | wx.RIGHT, border=self.FromDIP(BORDER * 2)
        )

        # Trim header
        newline = wx.BoxSizer(wx.HORIZONTAL)
        newline.Add(
            wx.StaticText(self, label=_('Amount to trim from each page') + ':'),
            flag=wx.ALIGN_CENTRE_VERTICAL,
        )
        trim_overlap_opts = [_('Overlap'), _('Trim')]
        self.trim_overlap_combo = wx.ComboBox(
            self,
            choices=trim_overlap_opts,
            value=trim_overlap_opts[0],
            style=wx.CB_READONLY,
        )
        newline.Add(
            self.trim_overlap_combo,
            flag=wx.ALIGN_CENTRE_VERTICAL | wx.LEFT,
            border=self.FromDIP(BORDER * 3),
        )
        vert_sizer.Add(
            newline, flag=wx.TOP | wx.LEFT | wx.RIGHT, border=self.FromDIP(BORDER * 2)
        )

        # Left trim
        newline = wx.BoxSizer(wx.HORIZONTAL)
        newline.Add(
            wx.StaticText(self, label=_('Left') + ':'),
            flag=wx.ALIGN_CENTRE_VERTICAL | wx.LEFT,
            border=self.FromDIP(BORDER * 2),
        )
        self.left_trim_txt = wx.TextCtrl(
            self, size=self.FromDIP(TXT_ENTRY_SIZE), style=wx.TE_RIGHT
        )
        newline.Add(
            self.left_trim_txt,
            flag=wx.ALIGN_CENTRE_VERTICAL | wx.LEFT,
            border=self.FromDIP(BORDER),
        )

        # Right trim
        newline.Add(
            wx.StaticText(self, label=_('Right') + ':'),
            flag=wx.ALIGN_CENTRE_VERTICAL | wx.LEFT,
            border=self.FromDIP(BORDER * 2),
        )
        self.right_trim_txt = wx.TextCtrl(
            self, size=self.FromDIP(TXT_ENTRY_SIZE), style=wx.TE_RIGHT
        )
        newline.Add(
            self.right_trim_txt,
            flag=wx.ALIGN_CENTRE_VERTICAL | wx.LEFT,
            border=self.FromDIP(BORDER),
        )

        # Top trim
        newline.Add(
            wx.StaticText(self, label=_('Top') + ':'),
            flag=wx.ALIGN_CENTRE_VERTICAL | wx.LEFT,
            border=self.FromDIP(BORDER * 2),
        )
        self.top_trim_txt = wx.TextCtrl(
            self, size=self.FromDIP(TXT_ENTRY_SIZE), style=wx.TE_RIGHT
        )
        newline.Add(
            self.top_trim_txt,
            flag=wx.ALIGN_CENTRE_VERTICAL | wx.LEFT,
            border=self.FromDIP(BORDER),
        )

        # Bottom trim
        newline.Add(
            wx.StaticText(self, label=_('Bottom') + ':'),
            flag=wx.ALIGN_CENTRE_VERTICAL | wx.LEFT,
            border=self.FromDIP(BORDER * 2),
        )
        self.bottom_trim_txt = wx.TextCtrl(
            self, size=self.FromDIP(TXT_ENTRY_SIZE), style=wx.TE_RIGHT
        )
        newline.Add(
            self.bottom_trim_txt,
            flag=wx.ALIGN_CENTRE_VERTICAL | wx.LEFT,
            border=self.FromDIP(BORDER),
        )
        vert_sizer.Add(
            newline, flag=wx.TOP | wx.LEFT | wx.RIGHT, border=self.FromDIP(BORDER * 2)
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


class LayersTab(scrolled.ScrolledPanel):
    def __init__(self, parent):
        super(LayersTab, self).__init__(parent)

        vert_sizer = wx.BoxSizer(wx.VERTICAL)

        # Status text
        self.status_txt = wx.StaticText(self, label=_('Load PDF to view layers.'))
        vert_sizer.Add(
            self.status_txt,
            flag=wx.TOP | wx.LEFT | wx.RIGHT,
            border=self.FromDIP(BORDER * 2),
        )

        # the main splitter for the layer stuff
        self.layer_splitter = wx.SplitterWindow(self, style=wx.SP_LIVE_UPDATE)
        layer_pane = wx.Panel(self.layer_splitter)
        layer_sizer = wx.BoxSizer(wx.VERTICAL)
        layer_pane.SetSizer(layer_sizer)

        # delete or hide deselected layers
        self.delete_ocgs = wx.RadioBox(
            layer_pane, label=_('Deselected layers:'), choices=[_('Delete'), _('Hide')]
        )
        layer_sizer.Add(
            self.delete_ocgs,
            flag=wx.LEFT | wx.RIGHT | wx.BOTTOM,
            border=self.FromDIP(BORDER),
        )

        # check all, background, etc
        self.include_nonoc = wx.CheckBox(
            layer_pane, label=_('Include non-optional content')
        )
        self.include_nonoc.SetValue(1)
        layer_sizer.Add(
            self.include_nonoc,
            flag=wx.TOP | wx.LEFT | wx.RIGHT,
            border=self.FromDIP(BORDER),
        )

        self.select_all = wx.CheckBox(layer_pane, label=_('Deselect all'))
        self.select_all.Bind(wx.EVT_CHECKBOX, self.on_select_all)
        layer_sizer.Add(
            self.select_all,
            flag=wx.TOP | wx.LEFT | wx.RIGHT,
            border=self.FromDIP(BORDER),
        )

        # the main list box for layers
        self.layer_list = wx.ListCtrl(layer_pane, style=wx.LC_REPORT | wx.LC_SINGLE_SEL)
        self.layer_list.EnableCheckBoxes(True)
        self.layer_list.InsertColumn(0, _('Layer Name'))
        self.layer_list.InsertColumn(1, _('Line Properties'))
        layer_sizer.Add(
            self.layer_list,
            proportion=1,
            flag=wx.EXPAND | wx.LEFT | wx.TOP,
            border=self.FromDIP(BORDER),
        )
        self.layer_list.Bind(wx.EVT_LIST_ITEM_SELECTED, self.on_layer_selected)

        # build the set of controls for layer options
        layer_opt_pane = wx.Panel(self.layer_splitter)
        layer_opt_sizer = wx.BoxSizer(wx.VERTICAL)
        layer_opt_pane.SetSizer(layer_opt_sizer)

        # line properties
        # colour
        layer_opt_sizer.AddSpacer(100)
        layer_opt_sizer.Add(
            wx.StaticText(layer_opt_pane, label=_('Select line properties to modify'))
        )
        newline = wx.BoxSizer(wx.HORIZONTAL)
        self.enable_colour = wx.CheckBox(layer_opt_pane, label=_('Line Colour') + ':')
        self.enable_colour.SetValue(1)
        newline.Add(self.enable_colour, flag=wx.LEFT, border=self.FromDIP(BORDER * 2))
        self.line_colour_ctrl = wx.ColourPickerCtrl(layer_opt_pane)
        newline.Add(self.line_colour_ctrl, flag=wx.LEFT, border=self.FromDIP(BORDER))
        layer_opt_sizer.Add(newline, flag=wx.TOP, border=self.FromDIP(BORDER * 2))

        # thickness
        newline = wx.BoxSizer(wx.HORIZONTAL)
        self.enable_thickness = wx.CheckBox(
            layer_opt_pane, label=_('Line Thickness') + ':'
        )
        self.enable_thickness.SetValue(1)
        newline.Add(
            self.enable_thickness,
            flag=wx.LEFT | wx.ALIGN_CENTER_VERTICAL,
            border=self.FromDIP(BORDER * 2),
        )
        self.line_thick_ctrl = wx.TextCtrl(
            layer_opt_pane, size=self.FromDIP(TXT_ENTRY_SIZE), value='1'
        )
        newline.Add(
            self.line_thick_ctrl,
            flag=wx.LEFT | wx.ALIGN_CENTER_VERTICAL,
            border=self.FromDIP(BORDER),
        )

        # Extra note for pybabel to make translations make sense (particularly for inches)
        # translation_note: pt = "points", in = "inches", cm = "centimeters"
        unit_choice = [_('pt'), _('in'), _('cm')]
        self.line_thick_units = wx.ComboBox(
            layer_opt_pane, value=unit_choice[0], choices=unit_choice
        )
        newline.Add(
            self.line_thick_units,
            flag=wx.LEFT | wx.ALIGN_CENTER_VERTICAL,
            border=self.FromDIP(BORDER),
        )
        layer_opt_sizer.Add(newline, flag=wx.TOP, border=self.FromDIP(BORDER * 2))

        # style
        newline = wx.BoxSizer(wx.HORIZONTAL)
        self.enable_style = wx.CheckBox(layer_opt_pane, label=_('Line Style') + ':')
        self.enable_style.SetValue(1)
        newline.Add(
            self.enable_style,
            flag=wx.LEFT | wx.ALIGN_CENTER_VERTICAL,
            border=self.FromDIP(BORDER * 2),
        )
        self.style_names = (_('Solid'), _('Dashed'), _('Dotted'))
        self.line_style_ctrl = wx.ComboBox(
            layer_opt_pane,
            choices=self.style_names,
            value=self.style_names[0],
            style=wx.CB_READONLY,
        )
        newline.Add(
            self.line_style_ctrl,
            flag=wx.LEFT | wx.ALIGN_CENTER_VERTICAL,
            border=self.FromDIP(BORDER),
        )
        layer_opt_sizer.Add(newline, flag=wx.TOP, border=self.FromDIP(BORDER * 2))

        # apply/reset buttons
        newline = wx.BoxSizer(wx.HORIZONTAL)
        self.apply_ls_btn = wx.Button(layer_opt_pane, label=_('Apply'))
        self.apply_ls_btn.Bind(wx.EVT_BUTTON, self.apply_ls_pressed)
        self.reset_ls_btn = wx.Button(layer_opt_pane, label=_('Reset'))
        self.reset_ls_btn.Bind(wx.EVT_BUTTON, self.reset_ls_pressed)
        newline.Add(
            self.apply_ls_btn,
            proportion=1,
            flag=wx.EXPAND | wx.LEFT,
            border=self.FromDIP(BORDER),
        )
        newline.Add(
            self.reset_ls_btn,
            proportion=1,
            flag=wx.EXPAND | wx.LEFT,
            border=self.FromDIP(BORDER),
        )
        layer_opt_sizer.Add(
            newline, flag=wx.TOP | wx.EXPAND, border=self.FromDIP(BORDER * 2)
        )

        # apply to checked
        newline = wx.BoxSizer(wx.HORIZONTAL)
        self.apply_ls_all = wx.Button(layer_opt_pane, label=_('Apply to checked'))
        self.apply_ls_all.Bind(wx.EVT_BUTTON, self.apply_all_pressed)
        self.reset_all = wx.Button(layer_opt_pane, label=_('Reset checked'))
        self.reset_all.Bind(wx.EVT_BUTTON, self.reset_all_pressed)
        newline.Add(self.apply_ls_all, flag=wx.LEFT, border=self.FromDIP(BORDER))
        newline.Add(self.reset_all, flag=wx.LEFT, border=self.FromDIP(BORDER))
        layer_opt_sizer.Add(newline, flag=wx.TOP, border=self.FromDIP(BORDER))

        # Final assembly
        self.layer_splitter.SplitVertically(layer_pane, layer_opt_pane)
        self.layer_splitter.SetSashGravity(0.5)
        vert_sizer.Add(
            self.layer_splitter,
            proportion=1,
            flag=wx.TOP | wx.LEFT | wx.RIGHT | wx.EXPAND,
            border=self.FromDIP(BORDER * 2),
        )

        # hide controls until a PDF with layers is loaded
        self.layer_splitter.Hide()

        self.SetSizer(vert_sizer)
        self.SetupScrolling()
        self.SetBackgroundColour(parent.GetBackgroundColour())
        self.line_props = {}

    def apply_ls(self, layer):
        line_str = ''
        self.line_props[layer] = {}

        if self.enable_thickness.IsChecked():
            line_thick = utils.txt_to_float(self.line_thick_ctrl.GetValue())

            if line_thick is None:
                return '', None

            units = self.line_thick_units.GetStringSelection()
            if units == '':
                units = _('pt')

            line_str += f'{line_thick} {units} '

            if units == _('in'):
                line_thick = line_thick * 72
            elif units == _('cm'):
                line_thick = line_thick * 72 / 2.54

            self.line_props[layer]['thickness'] = line_thick

        if self.enable_style.IsChecked():
            line_str += f'{self.style_names[self.line_style_ctrl.GetSelection()]}'
            self.line_props[layer]['style'] = self.line_style_ctrl.GetSelection()

        if self.enable_colour.IsChecked():
            colour = self.line_colour_ctrl.GetColour()
            # ignore alpha
            rgb = [val / 255 for val in colour.Get()[:3]]
            self.line_props[layer]['rgb'] = rgb
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
            self.layer_list.SetItem(sel, 1, u'\u25A0 ' + line_str)
            self.layer_list.SetItemTextColour(sel, colour)

    def apply_all_pressed(self, event):
        n_layers = self.layer_list.GetItemCount()

        for sel in range(n_layers):
            if self.layer_list.IsItemChecked(sel):
                layer = self.layer_list.GetItemText(sel, 0)
                line_str, colour = self.apply_ls(layer)
                self.layer_list.SetItem(sel, 1, line_str)

                if colour is not None:
                    self.layer_list.SetItem(sel, 1, u'\u25A0 ' + line_str)
                    self.layer_list.SetItemTextColour(sel, colour)

    def reset_ls_pressed(self, event):
        sel = self.layer_list.GetFirstSelected()
        if sel == -1:
            return

        layer = self.layer_list.GetItemText(sel, 0)

        if layer in self.line_props:
            del self.line_props[layer]

        self.layer_list.SetItem(sel, 1, '')
        self.layer_list.SetItemTextColour(sel, wx.Colour(0, 0, 0))

    def reset_all_pressed(self, event):
        n_layers = self.layer_list.GetItemCount()

        for sel in range(n_layers):
            if self.layer_list.IsItemChecked(sel):
                layer = self.layer_list.GetItemText(sel, 0)

                if layer in self.line_props:
                    del self.line_props[layer]

                self.layer_list.SetItem(sel, 1, '')
                self.layer_list.SetItemTextColour(sel, wx.Colour(0, 0, 0))

    def on_layer_selected(self, event):
        self.apply_ls_btn.SetLabel(_('Apply to') + ' ' + event.Label)
        self.reset_ls_btn.SetLabel(_('Reset') + ' ' + event.Label)

    def load_new(self, layers):
        if not layers:
            self.layer_splitter.Hide()
            self.status_txt.SetLabel(_('No layers found in input document.'))
            return

        self.layer_list.DeleteAllItems()
        for i, l in enumerate(layers):
            self.layer_list.InsertItem(i, l)

        self.layer_list.SetColumnWidth(0, wx.LIST_AUTOSIZE_USEHEADER)
        self.layer_list.SetColumnWidth(1, wx.LIST_AUTOSIZE_USEHEADER)
        self.set_all_checked(True)

        self.status_txt.SetLabel(_('Select layers to include in output document.'))
        self.layer_splitter.Show()
        self.Layout()

    def set_all_checked(self, select=True):
        self.select_all.SetValue(select)
        for i in range(self.layer_list.GetItemCount()):
            self.layer_list.CheckItem(i, select)

    def on_select_all(self, event):
        is_checked = event.GetSelection()
        self.set_all_checked(event.GetSelection())

        if is_checked:
            self.select_all.SetLabel(_('Deselect all'))
        else:
            self.select_all.SetLabel(_('Select all'))

    def get_selected_layers(self):
        n_layers = self.layer_list.GetItemCount()
        selected = []
        for i in range(n_layers):
            if self.layer_list.IsItemChecked(i):
                selected.append(self.layer_list.GetItemText(i, col=0))

        if n_layers == len(selected) and len(self.line_props) == 0:
            return 'all'

        if len(selected) == 0:
            return None

        return selected


class SewGUI(wx.Frame):
    def __init__(self, *args, **kw):
        # ensure the parent's __init__ is called
        super(SewGUI, self).__init__(*args, **kw)
        self.progress = None

        # split the bottom half from the notebook top
        self.splitter = wx.SplitterWindow(self, style=wx.SP_LIVE_UPDATE)

        # create the notebook for the various tab panes
        nb = wx.Notebook(self.splitter)
        self.io = IOTab(nb, self)
        nb.AddPage(self.io, _('Options'))
        self.tt = TileTab(nb, self)
        nb.AddPage(self.tt, _('Tile Pages'))
        self.lt = LayersTab(nb)
        nb.AddPage(self.lt, _('Layers'))

        # create a panel for the go button and log window
        pnl = wx.Panel(self.splitter)
        vert_sizer = wx.BoxSizer(wx.VERTICAL)
        pnl.SetSizer(vert_sizer)

        # the go button
        go_btn = wx.Button(pnl, label=_('Generate PDF'))
        go_btn.SetFont(go_btn.GetFont().Bold())
        go_btn.Bind(wx.EVT_BUTTON, self.on_go_pressed)
        vert_sizer.Add(go_btn, flag=wx.ALL, border=self.FromDIP(BORDER))

        # create a log window and redirect console output
        self.log = wx.TextCtrl(pnl, style=wx.TE_MULTILINE | wx.TE_READONLY | wx.HSCROLL)
        vert_sizer.Add(
            self.log, proportion=1, flag=wx.EXPAND | wx.ALL, border=self.FromDIP(BORDER)
        )
        sys.stdout = self.log
        sys.stderr = self.log

        self.splitter.SplitHorizontally(nb, pnl)
        self.splitter.SetMinimumPaneSize(40)

        self.in_doc = None
        self.out_doc_path = None
        self.tiler = None
        self.layer_filter = None

        self.working_dir = os.getcwd()
        self.make_menu_bar()

        if sys.platform == 'win32' or sys.platform == 'linux':
            self.SetIcon(wx.Icon(utils.resource_path('resources/stitcher-icon.ico')))

        if len(sys.argv) > 1:
            self.load_file(sys.argv[1])

        if len(sys.argv) > 2:
            self.out_doc_path = sys.argv[2]
            self.io.output_fname_display.SetLabel(sys.argv[2])

    def reset_sash_position(self):
        # Sets the output panel to occupy just 1/3 of the height
        # Needs to be called after construction for high DPI display.
        self.splitter.SetSashPosition(self.Size[1] * 2 // 3)

    def page_range_updated(self, event):
        if event.GetId() == self.io.page_range_txt.GetId():
            self.tt.page_range_txt.ChangeValue(self.io.page_range_txt.GetValue())
        elif event.GetId() == self.tt.page_range_txt.GetId():
            self.io.page_range_txt.ChangeValue(self.tt.page_range_txt.GetValue())

    def margin_updated(self, event):
        if event.GetId() == self.io.margin_txt.GetId():
            self.tt.margin_txt.ChangeValue(self.io.margin_txt.GetValue())
        elif event.GetId() == self.tt.margin_txt.GetId():
            self.io.margin_txt.ChangeValue(self.tt.margin_txt.GetValue())

    def on_go_pressed(self, event):
        # retrieve the selected options
        do_tile = bool(self.io.do_tile.GetValue())
        do_layers = bool(self.io.do_layers.GetValue())

        if (do_tile and self.tiler is None) or (
            do_layers and self.layer_filter is None
        ):
            return

        if self.out_doc_path is None:
            self.on_output(event)

            if self.out_doc_path is None:
                return

        # global options
        page_range = utils.parse_page_range(self.io.page_range_txt.GetValue())

        if page_range is None:
            print(_('No page range specified, defaulting to all'))
            page_range = list(range(1, len(self.in_doc.pages) + 1))

        if do_layers:
            # set up the layer filter
            self.layer_filter.keep_ocs = self.lt.get_selected_layers()
            self.layer_filter.line_props = self.lt.line_props
            self.layer_filter.keep_non_oc = bool(self.lt.include_nonoc.GetValue())
            self.layer_filter.delete_ocgs = bool(
                self.lt.delete_ocgs.GetSelection() == 0
            )
            self.layer_filter.page_range = page_range

        if do_tile:
            # set all the various options of the tiler
            # define the page order
            self.tiler.col_major = bool(self.tt.col_row_order_combo.GetSelection())
            self.tiler.right_to_left = bool(self.tt.left_right_combo.GetSelection())
            self.tiler.bottom_to_top = bool(self.tt.top_bottom_combo.GetSelection())
            self.tiler.page_range = page_range

            # set the optional stuff
            self.tiler.units = self.tt.unit_box.GetSelection()
            self.tiler.rotation = self.tt.rotate_combo.GetSelection()

            # margins
            self.tiler.margin = utils.txt_to_float(self.tt.margin_txt.GetValue())

            # trim
            trim = [0.0] * 4
            trim[0] = utils.txt_to_float(self.tt.left_trim_txt.GetValue())
            trim[1] = utils.txt_to_float(self.tt.right_trim_txt.GetValue())
            trim[2] = utils.txt_to_float(self.tt.top_trim_txt.GetValue())
            trim[3] = utils.txt_to_float(self.tt.bottom_trim_txt.GetValue())
            self.tiler.set_trim(trim)
            self.tiler.actually_trim = bool(self.tt.trim_overlap_combo.GetSelection())
            self.tiler.override_trim = self.tt.override_trim.GetValue()

            # rows/cols
            cols = self.tt.columns_txt.GetValue().strip()
            cols = int(cols) if cols else None
            rows = self.tt.rows_txt.GetValue().strip()
            rows = int(rows) if rows else None

        # do it
        try:
            if do_layers:
                self.progress = wx.ProgressDialog(
                    'Processing layers',
                    'Processing layers, please wait',
                    style=wx.PD_CAN_ABORT,
                )
                filtered = self.layer_filter.run(
                    self.progress_range,
                    self.progress_update,
                    self.progress_was_cancelled,
                )
            else:
                filtered = self.in_doc

            if self.progress:
                self.progress_update(self.progress.GetRange())

            if filtered is None:
                return

            if do_tile:
                self.tiler.in_doc = filtered
                new_doc = self.tiler.run(rows, cols)
                print(_('Tiling successful'))
            else:
                # extract the requested pages
                page_filter = PageFilter(filtered)
                page_filter.page_range = page_range
                new_doc = page_filter.run()

        except Exception as e:
            print(_('Something went wrong'))
            traceback.print_exc()
            return

        try:
            new_doc.save(self.out_doc_path)
            print(_('Successfully written to') + ' ' + self.out_doc_path)
        except Exception as e:
            print(
                _('Something went wrong') + ', '
                + _('unable to write to') + ' '
                + self.out_doc_path
            )
            print(e)
            print(
                _("Make sure " + self.out_doc_path + " isn't open in another program")
            )

    def progress_was_cancelled(self):
        if self.progress != None:
            return self.progress.WasCancelled()

    def progress_update(self, val):
        if self.progress != None:
            r = self.progress.GetRange()
            if r:
                if val == r:
                    self.progress = None
                else:
                    self.progress.Update(val)

    def progress_range(self, val):
        if self.progress != None:
            self.progress.SetRange(val)

    def make_menu_bar(self):
        # Make a file menu with load and exit items
        fileMenu = wx.Menu()
        openItem = fileMenu.Append(wx.ID_OPEN)
        saveAsItem = fileMenu.Append(wx.ID_SAVE)
        exitItem = fileMenu.Append(wx.ID_EXIT)
        menuBar = wx.MenuBar()
        menuBar.Append(fileMenu, '&File')
        self.SetMenuBar(menuBar)
        self.Bind(wx.EVT_MENU, self.on_open, openItem)
        self.Bind(wx.EVT_MENU, self.on_output, saveAsItem)
        self.Bind(wx.EVT_MENU, self.on_exit, exitItem)

    def on_exit(self, event):
        self.Close(True)

    def on_output(self, event):
        with wx.FileDialog(
            self,
            _('Save output as'),
            defaultDir=self.working_dir,
            wildcard='PDF files (*.pdf)|*.pdf',
            style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT,
        ) as fileDialog:

            if fileDialog.ShowModal() == wx.ID_CANCEL:
                return

            pathname = fileDialog.GetPath()
            if pathname == self.in_doc.filename:
                wx.MessageBox(
                    _(
                        "Can't overwrite input file, " +
                        "please select a different file for output"
                    ),
                    'Error',
                    wx.OK | wx.ICON_ERROR,
                )
                self.on_output(event)
            try:
                self.out_doc_path = pathname
                self.io.output_fname_display.SetLabel(pathname)

            except IOError:
                wx.LogError(_('unable to write to') + pathname)

    def on_open(self, event):
        with wx.FileDialog(
            self,
            _('Select input PDF'),
            defaultDir=self.working_dir,
            wildcard='PDF files (*.pdf)|*.pdf',
            style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST,
        ) as fileDialog:

            if fileDialog.ShowModal() == wx.ID_CANCEL:
                return

            # Proceed loading the file chosen by the user
            pathname = fileDialog.GetPath()
            self.load_file(pathname)

    def load_file(self, pathname):
        self.working_dir = os.path.dirname(pathname)
        pdf_has_password = False
        password = ""

        while True:
            try:
                if pdf_has_password:
                    password_dialog = wx.PasswordEntryDialog(
                        self, _("Password"), _("PDF file is locked"), "")
                    if password_dialog.ShowModal() == wx.ID_OK:
                        password = password_dialog.GetValue()
                        password_dialog.Destroy()
                    else:
                        wx.LogError(
                            _("PDF will not open as you canceled the operation."))
                        password_dialog.Destroy()
                        break

                # open the pdf
                print(_("Opening") + " " + pathname)
                self.in_doc = pikepdf.Pdf.open(pathname, password=password)
                self.io.load_new(self.in_doc)

                # create the processing objects
                self.layer_filter = LayerFilter(self.in_doc)
                self.lt.load_new(
                    self.layer_filter.get_layer_names(self.layer_filter.pdf)
                )

                self.tiler = PageTiler()

                # clear the output if it's already set
                self.out_doc_path = None

            except pikepdf.PasswordError:
                pdf_has_password = True
                print(_("PDF locked! Enter the correct password."))

            except IOError:
                wx.LogError(_("Cannot open file") + pathname)

            else:
                print(_("PDF file loaded without errors."))
                break

def main():
    # When this module is run (not imported) then create the app, the
    # frame, show it, and start the event loop.
    language_warning = utils.setup_locale()
    app = wx.App()

    # Fix the size for high-resolution displays on windows
    if sys.platform.startswith('win32'):
        from ctypes import OleDLL
        OleDLL('shcore').SetProcessDpiAwareness(1)

    disp_size = wx.DisplaySize()
    app_size = wx.Size(
        min(int(disp_size[0] * 0.6), 700), min(int(disp_size[1] * 0.85), 800)
    )

    frm = SewGUI(None, title='PDF Stitcher' + ' ' + utils.version_string, size=app_size)
    frm.SetSize(frm.FromDIP(app_size))
    frm.reset_sash_position()

    if language_warning:
        print(language_warning)

    frm.Show()
    app.MainLoop()

if __name__ == '__main__':
    main()
