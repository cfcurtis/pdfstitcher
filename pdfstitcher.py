# PDFStitcher is a utility to work with PDF sewing patterns.
# Copyright (C) 2021 Charlotte Curtis
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

import wx
from tile_pages import *
from layerfilter import *
import os
import sys

# localization stuff
import gettext
import locale

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    if hasattr(sys,'_MEIPASS'):
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    else:
        base_path = os.path.abspath('.')

    return os.path.join(base_path, relative_path)

language_warning = None

lc = locale.getdefaultlocale()

try:
    lang = lc[0][:2]
except:
    lang = 'en'
    language_warning = 'Could not detect system language, defaulting to English'

if lang not in ('de','es','fr','nl','en'):
    language_warning = 'System language code ' + lang + ' is not supported, defaulting to English.'
else:
    try:
        translate = gettext.translation('pdfstitcher', resource_path('locale'), 
            languages=[lang], fallback=True)
        translate.install()
    except Exception as e:
        def _(text):
            return text
            
        language_warning = e

class TileTab(wx.Panel):
    def __init__(self,parent,main_gui):
        wx.Panel.__init__(self, parent)

        vert_sizer = wx.BoxSizer(wx.VERTICAL)

        # add the various parameter inputs
        # Display the selected PDF
        newline = wx.BoxSizer(wx.HORIZONTAL)
        in_doc_btn = wx.Button(self, label=_('Select input PDF'))
        in_doc_btn.Bind(wx.EVT_BUTTON,main_gui.on_open)
        newline.Add(in_doc_btn, flag=wx.ALIGN_CENTRE_VERTICAL)
        self.input_fname_display = wx.StaticText(self, label=_('None'))
        newline.Add(self.input_fname_display, flag=wx.ALIGN_CENTRE_VERTICAL|wx.LEFT, border=5)
        vert_sizer.Add(newline,flag=wx.TOP|wx.LEFT|wx.RIGHT,border=10)
                
        newline = wx.BoxSizer(wx.HORIZONTAL)
        out_doc_btn = wx.Button(self, label=_('Save output as'))
        out_doc_btn.Bind(wx.EVT_BUTTON,main_gui.on_output)
        newline.Add(out_doc_btn, flag=wx.ALIGN_CENTRE_VERTICAL)
        self.output_fname_display = wx.StaticText(self, label=_('None'))
        newline.Add(self.output_fname_display, flag=wx.ALIGN_CENTRE_VERTICAL|wx.LEFT, border=5)
        vert_sizer.Add(newline,flag=wx.TOP|wx.LEFT|wx.RIGHT,border=10)

        ## REQUIRED PARAMETERS
        vert_sizer.Add(wx.StaticLine(self, -1), flag=wx.EXPAND|wx.TOP|wx.BOTTOM, border=5)
        lbl = wx.StaticText(self, label=_('Required Parameters'))
        lbl.SetFont(lbl.GetFont().Bold())
        vert_sizer.Add(lbl, flag=wx.TOP|wx.LEFT, border=5)

        # Page Range
        newline = wx.BoxSizer(wx.HORIZONTAL)
        newline.Add(wx.StaticText(self, label=_('Page Range') + ':'), flag=wx.ALIGN_CENTRE_VERTICAL)
        self.page_range_txt = wx.TextCtrl(self)
        self.page_range_txt.SetToolTip(wx.ToolTip(_('Pages assemble in specified order. 0 inserts a blank page.')))
        newline.Add(self.page_range_txt,proportion=1,flag=wx.ALIGN_CENTRE_VERTICAL|wx.LEFT, border=5)
        vert_sizer.Add(newline,flag=wx.EXPAND|wx.TOP|wx.LEFT|wx.RIGHT,border=10)

        # Columns/Rows
        newline = wx.BoxSizer(wx.HORIZONTAL)
        newline.Add(wx.StaticText(self, label=_('Number of Columns') + ':'), flag=wx.ALIGN_CENTRE_VERTICAL)
        self.columns_txt = wx.TextCtrl(self,size=(40,-1),style=wx.TE_RIGHT)
        newline.Add(self.columns_txt,flag=wx.ALIGN_CENTRE_VERTICAL|wx.LEFT, border=5)
        newline.Add(wx.StaticText(self, label=_('Number of Rows') + ':'), flag=wx.ALIGN_CENTRE_VERTICAL|wx.LEFT, border=10)
        self.rows_txt = wx.TextCtrl(self,size=(40,-1),style=wx.TE_RIGHT)
        newline.Add(self.rows_txt,flag=wx.ALIGN_CENTRE_VERTICAL|wx.LEFT, border=5)
        vert_sizer.Add(newline,flag=wx.TOP|wx.LEFT|wx.RIGHT,border=10)

        # page order
        newline = wx.BoxSizer(wx.HORIZONTAL)
        col_row_order_opts = [_('Rows then columns'),_('Columns then rows')]
        left_right_opts = [_('Left to right'),_('Right to left')]
        top_bottom_opts = [_('Top to bottom'),_('Bottom to top')]

        newline.Add(wx.StaticText(self, label=_('Page order') + ':'), flag=wx.ALIGN_CENTRE_VERTICAL)
        self.col_row_order_combo = wx.ComboBox(self, choices=col_row_order_opts, value=col_row_order_opts[0], style=wx.CB_READONLY)
        newline.Add(self.col_row_order_combo, flag=wx.LEFT|wx.ALIGN_CENTRE_VERTICAL, border=5)
        self.left_right_combo = wx.ComboBox(self, choices=left_right_opts, value=left_right_opts[0], style=wx.CB_READONLY)
        newline.Add(self.left_right_combo, flag=wx.LEFT|wx.ALIGN_CENTRE_VERTICAL, border=5)
        self.top_bottom_combo = wx.ComboBox(self, choices=top_bottom_opts, value=top_bottom_opts[0], style=wx.CB_READONLY)
        newline.Add(self.top_bottom_combo, flag=wx.LEFT|wx.ALIGN_CENTRE_VERTICAL, border=5)
        vert_sizer.Add(newline,flag=wx.TOP|wx.LEFT|wx.RIGHT,border=10)
        
        # rotation 
        newline = wx.BoxSizer(wx.HORIZONTAL)
        rotate_opts = [_('None'),_('Clockwise'),_('Counterclockwise')]
        newline.Add(wx.StaticText(self, label=_('Page Rotation') + ':'), flag=wx.ALIGN_CENTRE_VERTICAL)
        self.rotate_combo = wx.ComboBox(self, choices=rotate_opts, value=rotate_opts[0], style=wx.CB_READONLY)
        newline.Add(self.rotate_combo, flag=wx.LEFT|wx.ALIGN_CENTRE_VERTICAL, border=5)
        vert_sizer.Add(newline,flag=wx.TOP|wx.LEFT|wx.RIGHT,border=10)

        ## OPTIONAL PARAMETERS
        vert_sizer.Add(wx.StaticLine(self, -1), flag=wx.EXPAND|wx.TOP|wx.BOTTOM, border=5)
        newline = wx.BoxSizer(wx.HORIZONTAL)
        lbl = wx.StaticText(self, label=_('Optional Parameters'))
        lbl.SetFont(lbl.GetFont().Bold())
        newline.Add(lbl)

        # unit selection
        unit_opts = [_('Inches'),_('Centimetres')]     
        self.unit_box = wx.RadioBox(self,label=_('Units'),choices=unit_opts,style=wx.RA_SPECIFY_COLS)
        newline.Add(self.unit_box,flag=wx.LEFT|wx.ALIGN_CENTRE_VERTICAL, border=50)
        vert_sizer.Add(newline,flag=wx.TOP|wx.LEFT|wx.RIGHT,border=5)

        # Margin
        newline = wx.BoxSizer(wx.HORIZONTAL)
        newline.Add(wx.StaticText(self, label=_('Margin to add to final output') + ':'),flag=wx.ALIGN_CENTRE_VERTICAL)
        self.margin_txt = wx.TextCtrl(self,size=(40,-1),style=wx.TE_RIGHT)
        newline.Add(self.margin_txt,flag=wx.ALIGN_CENTRE_VERTICAL|wx.LEFT, border=5)
        vert_sizer.Add(newline,flag=wx.TOP|wx.LEFT|wx.RIGHT,border=10)

        # Trim header
        newline = wx.BoxSizer(wx.HORIZONTAL)
        newline.Add(wx.StaticText(self, label=_('Amount to trim from each page') + ':'), flag=wx.ALIGN_CENTRE_VERTICAL)
        trim_overlap_opts = [_('Overlap'),_('Trim')]
        self.trim_overlap_combo = wx.ComboBox(self, choices=trim_overlap_opts, value=trim_overlap_opts[0], style=wx.CB_READONLY)
        newline.Add(self.trim_overlap_combo, flag=wx.ALIGN_CENTRE_VERTICAL|wx.LEFT, border=15)
        vert_sizer.Add(newline,flag=wx.TOP|wx.LEFT|wx.RIGHT,border=10)

        # Left trim
        newline = wx.BoxSizer(wx.HORIZONTAL)
        newline.Add(wx.StaticText(self, label=_('Left') + ':'),flag=wx.ALIGN_CENTRE_VERTICAL|wx.LEFT, border=10)
        self.left_trim_txt = wx.TextCtrl(self,size=(40,-1),style=wx.TE_RIGHT)
        newline.Add(self.left_trim_txt,flag=wx.ALIGN_CENTRE_VERTICAL|wx.LEFT, border=5)

        # Right trim
        newline.Add(wx.StaticText(self, label=_('Right') + ':'),flag=wx.ALIGN_CENTRE_VERTICAL|wx.LEFT, border=10)
        self.right_trim_txt = wx.TextCtrl(self,size=(40,-1),style=wx.TE_RIGHT)
        newline.Add(self.right_trim_txt,flag=wx.ALIGN_CENTRE_VERTICAL|wx.LEFT, border=5)
       
        # Top trim
        newline.Add(wx.StaticText(self, label=_('Top') + ':'),flag=wx.ALIGN_CENTRE_VERTICAL|wx.LEFT, border=10)
        self.top_trim_txt = wx.TextCtrl(self,size=(40,-1),style=wx.TE_RIGHT)
        newline.Add(self.top_trim_txt,flag=wx.ALIGN_CENTRE_VERTICAL|wx.LEFT, border=5)

        # Bottom trim
        newline.Add(wx.StaticText(self, label=_('Bottom') + ':'),flag=wx.ALIGN_CENTRE_VERTICAL|wx.LEFT, border=10)
        self.bottom_trim_txt = wx.TextCtrl(self,size=(40,-1),style=wx.TE_RIGHT)
        newline.Add(self.bottom_trim_txt,flag=wx.ALIGN_CENTRE_VERTICAL|wx.LEFT, border=5)
        vert_sizer.Add(newline,flag=wx.TOP|wx.LEFT|wx.RIGHT,border=10)

        self.SetSizer(vert_sizer)
        self.SetBackgroundColour(parent.GetBackgroundColour())

    def load_new(self,in_doc):
        self.input_fname_display.SetLabel(in_doc.filename)
        self.page_range_txt.SetValue('1-{}'.format(len(in_doc.pages)))
        self.output_fname_display.SetLabel(_('None'))

class LayersTab(wx.Panel):
    def __init__(self,parent):
        wx.Panel.__init__(self, parent)

        vert_sizer = wx.BoxSizer(wx.VERTICAL)

        # Status text
        self.status_txt = wx.StaticText(self, label=_('Load PDF to view layers.'))
        vert_sizer.Add(self.status_txt,flag=wx.TOP|wx.LEFT|wx.RIGHT,border=10)

        # the main splitter for the layer stuff
        self.layer_splitter = wx.SplitterWindow(self,style=wx.SP_LIVE_UPDATE)
        layer_pane = wx.Panel(self.layer_splitter)
        layer_sizer = wx.BoxSizer(wx.VERTICAL)
        layer_pane.SetSizer(layer_sizer)

        # check all, background, etc
        self.include_nonoc = wx.CheckBox(layer_pane,label=_('Include non-optional content'))
        self.include_nonoc.SetValue(1)
        layer_sizer.Add(self.include_nonoc,flag=wx.TOP|wx.LEFT|wx.RIGHT,border=5)

        self.select_all = wx.CheckBox(layer_pane,label=_('Select all'))
        self.select_all.Bind(wx.EVT_CHECKBOX, self.on_select_all)
        layer_sizer.Add(self.select_all,flag=wx.TOP|wx.LEFT|wx.RIGHT,border=5)
        
        # the main list box for layers
        self.layer_list = wx.ListCtrl(layer_pane,style=wx.LC_REPORT)
        self.layer_list.EnableCheckBoxes(True)
        self.layer_list.InsertColumn(0,_('Layer Name'))
        # self.layer_list.InsertColumn(1,_('Line Width'))
        # self.layer_list.InsertColumn(2,_('Line Colour'))
        # self.layer_list.InsertColumn(3,_('Line Style'))
        layer_sizer.Add(self.layer_list,proportion=1,flag=wx.EXPAND|wx.LEFT|wx.TOP, border=5)
        
        # build the set of controls for layer options
        layer_opt_pane = wx.Panel(self.layer_splitter)
        layer_opt_sizer = wx.BoxSizer(wx.VERTICAL)
        layer_opt_pane.SetSizer(layer_opt_sizer)
        # layer_opt_sizer.Add(wx.StaticText(layer_opt_pane,label=_('Selected layer') + ':'),flag=wx.LEFT,border=10)
        # line_style_opts = 
        # self.line_style_combo = 

        # Final assembly
        self.layer_splitter.SplitVertically(layer_pane,layer_opt_pane)
        self.layer_splitter.SetSashGravity(0.5)
        vert_sizer.Add(self.layer_splitter,proportion=1,flag=wx.TOP|wx.LEFT|wx.RIGHT|wx.EXPAND,border=10)

        # hide controls until a PDF with layers is loaded
        self.layer_splitter.Hide()

        self.SetSizer(vert_sizer)
        self.SetBackgroundColour(parent.GetBackgroundColour())
    
    def load_new(self,layers):
        if not layers:
            self.layer_splitter.Hide()
            self.status_txt.SetLabel(_('No layers found in input document.'))
            return

        self.layer_list.DeleteAllItems()
        for l in layers:
            self.layer_list.InsertItem(0,l)

        self.layer_list.SetColumnWidth(0,wx.LIST_AUTOSIZE)
        self.set_all_checked(True)

        self.status_txt.SetLabel(_('Select layers to include in output document.'))
        self.layer_splitter.Show()
        self.Layout()
    
    def set_all_checked(self,select=True):
        self.select_all.SetValue(select)
        for i in range(self.layer_list.GetItemCount()):
            self.layer_list.CheckItem(i,select)

    def on_select_all(self,event):
        self.set_all_checked(event.GetSelection())
    
    def get_selected_layers(self):
        n_layers = self.layer_list.GetItemCount()
        selected = []
        for i in range(n_layers):
            if self.layer_list.IsItemChecked(i):
                selected.append(self.layer_list.GetItemText(i,col=0))
        
        if n_layers == len(selected):
            return 'all'
        
        if len(selected) == 0:
            return None
        
        return selected

class SewGUI(wx.Frame):
    def __init__(self, *args, **kw):
        # ensure the parent's __init__ is called
        super(SewGUI, self).__init__(*args, **kw)

        # split the bottom half from the notebook top
        splitter = wx.SplitterWindow(self,style=wx.SP_LIVE_UPDATE)

        # create the notebook for the various tab panes
        nb = wx.Notebook(splitter)
        self.tt = TileTab(nb,self)
        nb.AddPage(self.tt,_('Layout'))
        self.lt = LayersTab(nb)
        nb.AddPage(self.lt,_('Layers'))

        # create a panel for the go button and log window
        pnl = wx.Panel(splitter)
        vert_sizer = wx.BoxSizer(wx.VERTICAL)
        pnl.SetSizer(vert_sizer)

        # the go button
        vert_sizer.Add(wx.StaticLine(pnl, -1), flag=wx.EXPAND|wx.TOP|wx.BOTTOM, border=5)
        go_btn = wx.Button(pnl, label=_('Generate PDF'))
        go_btn.SetFont(go_btn.GetFont().Bold())
        go_btn.Bind(wx.EVT_BUTTON,self.on_go_pressed)
        vert_sizer.Add(go_btn,flag=wx.ALL,border=10)
        
        # create a log window and redirect console ouput
        self.log = wx.TextCtrl(pnl, style=wx.TE_MULTILINE|wx.TE_READONLY|wx.HSCROLL)
        vert_sizer.Add(self.log,proportion=1,flag=wx.EXPAND|wx.ALL,border=10)
        sys.stdout = self.log
        sys.stderr = self.log

        splitter.SplitHorizontally(nb,pnl)
        splitter.SetSashPosition(int(kw['size'][1]*5/8))
        splitter.SetMinimumPaneSize(40)

        self.in_doc = None
        self.out_doc_path = None
        self.tiler = None
        self.layer_filter = None

        self.working_dir = os.getcwd()

        if language_warning:
            print(language_warning)
    
    def on_go_pressed(self,event):
        if self.tiler is None or self.layer_filter is None:
            return

        if self.out_doc_path is None:
            self.on_output(event)
            
            if self.out_doc_path is None:
                return

        # set up the layer filter
        selected_layers = self.lt.get_selected_layers()
        self.layer_filter.set_keep_ocs(selected_layers)
        self.layer_filter.set_keep_non_oc(self.lt.include_nonoc.GetValue())

        # set all the various options of the tiler
        # define the page order
        self.tiler.set_col_major(self.tt.col_row_order_combo.GetSelection())
        self.tiler.set_right_left(self.tt.left_right_combo.GetSelection())
        self.tiler.set_bottom_top(self.tt.top_bottom_combo.GetSelection())
        self.tiler.set_page_range(self.tt.page_range_txt.GetValue())

        # set the optional stuff
        self.tiler.set_units(self.tt.unit_box.GetSelection())
        self.tiler.set_rotation(self.tt.rotate_combo.GetSelection())

        # margins
        self.tiler.set_margin(txt_to_float(self.tt.margin_txt.GetValue()))

        # trim
        trim = [0.0]*4
        trim[0] = txt_to_float(self.tt.left_trim_txt.GetValue())
        trim[1] = txt_to_float(self.tt.right_trim_txt.GetValue())
        trim[2] = txt_to_float(self.tt.top_trim_txt.GetValue())
        trim[3] = txt_to_float(self.tt.bottom_trim_txt.GetValue())
        self.tiler.set_trim(trim)
        self.tiler.set_trim_overlap(bool(self.tt.trim_overlap_combo.GetSelection()))

        # rows/cols
        cols = self.tt.columns_txt.GetValue().strip()
        cols = int(cols) if cols else 0
        rows = self.tt.rows_txt.GetValue().strip()
        rows = int(rows) if rows else 0

        # do it
        filtered = self.layer_filter.run(self.tiler.page_range)
        try:
            self.tiler.set_input(filtered)
            new_doc = self.tiler.run(rows,cols)
            print(_('Tiling successful'))
        except Exception as e:
            print(_('Something went wrong') + ', ' + _('tiling failed'))
            print(_('Exception') + ':')
            print(e)
        
        try:
            new_doc.save(self.out_doc_path,normalize_content=True)
            filtered.close()
            new_doc.close()
            print(_('Successfully written to') + ' ' + self.out_doc_path)
        except Exception as e:
            print(_('Something went wrong') + ', ' + _('unable to write to') + ' ' + self.out_doc_path)
            print(e)

    def make_menu_bar(self):
        # Make a file menu with load and exit items
        fileMenu = wx.Menu()
        openItem = fileMenu.Append(wx.ID_OPEN)
        exitItem = fileMenu.Append(wx.ID_EXIT)
        menuBar = wx.MenuBar()
        menuBar.Append(fileMenu, '&File')
        self.SetMenuBar(menuBar)
        self.Bind(wx.EVT_MENU, self.on_open, openItem)
        self.Bind(wx.EVT_MENU, self.on_exit,  exitItem)

    def on_exit(self, event):
        self.in_doc.Close()
        self.Close(True)

    def on_output(self, event):
        with wx.FileDialog(self, _('Save output as'), defaultDir=self.working_dir,
                        wildcard='PDF files (*.pdf)|*.pdf',
                        style=wx.FD_SAVE|wx.FD_OVERWRITE_PROMPT) as fileDialog:

            if fileDialog.ShowModal() == wx.ID_CANCEL:
                return

            pathname = fileDialog.GetPath()
            if pathname == self.in_doc.filename:
                wx.MessageBox(_('Can''t overwrite input file, please select a different file for output'), 'Error', wx.OK | wx.ICON_ERROR)
                self.on_output(event)
            try:
                self.out_doc_path = pathname
                self.tt.output_fname_display.SetLabel(os.path.basename(pathname))

            except IOError:
                wx.LogError(_('unable to write to') + pathname)
    
    def on_open(self, event):
        with wx.FileDialog(self, _('Select input PDF'), defaultDir=self.working_dir,
                        wildcard='PDF files (*.pdf)|*.pdf',
                        style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST) as fileDialog:

            if fileDialog.ShowModal() == wx.ID_CANCEL:
                return

            # Proceed loading the file chosen by the user
            pathname = fileDialog.GetPath()
            self.load_file(pathname)
    
    def load_file(self,pathname):
        self.working_dir = os.path.dirname(pathname)
        try:
            # open the pdf
            print(_('Opening') + ' ' + pathname)
            self.in_doc = pikepdf.Pdf.open(pathname)

            # create the processing objects
            self.layer_filter = LayerFilter(self.in_doc)
            self.lt.load_new(self.layer_filter.get_layer_names())

            self.tiler = PageTiler()
            self.tt.load_new(self.in_doc)
            
            # clear the output if it's already set
            self.out_doc_path = None

        except IOError:
            wx.LogError(_('Cannot open file') + pathname)

if __name__ == '__main__':
    # When this module is run (not imported) then create the app, the
    # frame, show it, and start the event loop.
    app = wx.App()
    disp_h = wx.Display().GetGeometry().GetHeight()
    disp_w = wx.Display().GetGeometry().GetWidth()

    h = min(int(disp_h*0.8),800)
    w = min(int(disp_w*0.4),600)

    frm = SewGUI(None, title=_('PDF Stitcher'),size=(w,h))
    frm.Show()

    app.MainLoop()