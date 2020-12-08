import wx
from tile_pages import *
import os

# localization stuff
import gettext

# testing French
# os.environ['LANG'] = 'fr'

translate = gettext.translation('sewingutils', 'locale', fallback=True)
translate.install()

class SewGUI(wx.Frame):
    def __init__(self, *args, **kw):
        # ensure the parent's __init__ is called
        super(SewGUI, self).__init__(*args, **kw)

        # create a panel in the frame
        pnl = wx.Panel(self)
         
        # pack them all in
        vert_sizer = wx.BoxSizer(wx.VERTICAL)

        # add the various parameter inputs
        # Display the selected PDF
        newline = wx.BoxSizer(wx.HORIZONTAL)
        in_doc_btn = wx.Button(pnl, label=_('Select input PDF'))
        in_doc_btn.Bind(wx.EVT_BUTTON,self.on_open)
        newline.Add(in_doc_btn, flag=wx.ALIGN_CENTRE_VERTICAL)
        self.input_fname_display = wx.StaticText(pnl, label=_('None'))
        newline.Add(self.input_fname_display, flag=wx.ALIGN_CENTRE_VERTICAL|wx.LEFT, border=5)
        vert_sizer.Add(newline,flag=wx.TOP|wx.LEFT|wx.RIGHT,border=10)
                
        newline = wx.BoxSizer(wx.HORIZONTAL)
        out_doc_btn = wx.Button(pnl, label=_('Save output as'))
        out_doc_btn.Bind(wx.EVT_BUTTON,self.on_output)
        newline.Add(out_doc_btn, flag=wx.ALIGN_CENTRE_VERTICAL)
        self.output_fname_display = wx.StaticText(pnl, label=_('None'))
        newline.Add(self.output_fname_display, flag=wx.ALIGN_CENTRE_VERTICAL|wx.LEFT, border=5)
        vert_sizer.Add(newline,flag=wx.TOP|wx.LEFT|wx.RIGHT,border=10)

        ## REQUIRED PARAMETERS
        vert_sizer.Add(wx.StaticLine(pnl, -1), flag=wx.EXPAND|wx.TOP|wx.BOTTOM, border=5)
        lbl = wx.StaticText(pnl, label=_('Required Parameters'))
        lbl.SetFont(lbl.GetFont().Bold())
        vert_sizer.Add(lbl, flag=wx.TOP|wx.LEFT, border=5)

        # Page Range
        newline = wx.BoxSizer(wx.HORIZONTAL)
        newline.Add(wx.StaticText(pnl, label=_('Page Range' + ':')), flag=wx.ALIGN_CENTRE_VERTICAL)
        self.page_range_txt = wx.TextCtrl(pnl)
        self.page_range_txt.SetToolTip(wx.ToolTip(_('Pages assemble in specified order. 0 inserts a blank page.')))
        newline.Add(self.page_range_txt,flag=wx.ALIGN_CENTRE_VERTICAL|wx.LEFT, border=5)
        vert_sizer.Add(newline,flag=wx.TOP|wx.LEFT|wx.RIGHT,border=10)

        # Columns/Rows
        newline = wx.BoxSizer(wx.HORIZONTAL)
        newline.Add(wx.StaticText(pnl, label=_('Number of Columns' + ':')), flag=wx.ALIGN_CENTRE_VERTICAL)
        self.columns_txt = wx.TextCtrl(pnl,size=(40,-1),style=wx.TE_RIGHT)
        newline.Add(self.columns_txt,flag=wx.ALIGN_CENTRE_VERTICAL|wx.LEFT, border=5)
        newline.Add(wx.StaticText(pnl, label=_('Number of Rows') + ':'), flag=wx.ALIGN_CENTRE_VERTICAL|wx.LEFT, border=10)
        self.rows_txt = wx.TextCtrl(pnl,size=(40,-1),style=wx.TE_RIGHT)
        newline.Add(self.rows_txt,flag=wx.ALIGN_CENTRE_VERTICAL|wx.LEFT, border=5)
        vert_sizer.Add(newline,flag=wx.TOP|wx.LEFT|wx.RIGHT,border=10)

        # page order
        newline = wx.BoxSizer(wx.HORIZONTAL)
        col_row_order_opts = [_('Rows then columns'),_('Columns then rows')]
        left_right_opts = [_('Left to right'),_('Right to left')]
        top_bottom_opts = [_('Top to bottom'),_('Bottom to top')]

        newline.Add(wx.StaticText(pnl, label=_('Page order') + ':'), flag=wx.ALIGN_CENTRE_VERTICAL)
        self.col_row_order_combo = wx.ComboBox(pnl, choices=col_row_order_opts, value=col_row_order_opts[0], style=wx.CB_READONLY)
        newline.Add(self.col_row_order_combo, flag=wx.LEFT|wx.ALIGN_CENTRE_VERTICAL, border=5)
        self.left_right_combo = wx.ComboBox(pnl, choices=left_right_opts, value=left_right_opts[0], style=wx.CB_READONLY)
        newline.Add(self.left_right_combo, flag=wx.LEFT|wx.ALIGN_CENTRE_VERTICAL, border=5)
        self.top_bottom_combo = wx.ComboBox(pnl, choices=top_bottom_opts, value=top_bottom_opts[0], style=wx.CB_READONLY)
        newline.Add(self.top_bottom_combo, flag=wx.LEFT|wx.ALIGN_CENTRE_VERTICAL, border=5)
        vert_sizer.Add(newline,flag=wx.TOP|wx.LEFT|wx.RIGHT,border=10)
        
        # rotation 
        newline = wx.BoxSizer(wx.HORIZONTAL)
        rotate_opts = [_('None'),_('Clockwise'),_('Counterclockwise')]
        newline.Add(wx.StaticText(pnl, label=_('Page Rotation') + ':'), flag=wx.ALIGN_CENTRE_VERTICAL)
        self.rotate_combo = wx.ComboBox(pnl, choices=rotate_opts, value=rotate_opts[0], style=wx.CB_READONLY)
        newline.Add(self.rotate_combo, flag=wx.LEFT|wx.ALIGN_CENTRE_VERTICAL, border=5)
        vert_sizer.Add(newline,flag=wx.TOP|wx.LEFT|wx.RIGHT,border=10)

        ## OPTIONAL PARAMETERS
        vert_sizer.Add(wx.StaticLine(pnl, -1), flag=wx.EXPAND|wx.TOP|wx.BOTTOM, border=5)
        newline = wx.BoxSizer(wx.HORIZONTAL)
        lbl = wx.StaticText(pnl, label=_('Optional Parameters'))
        lbl.SetFont(lbl.GetFont().Bold())
        newline.Add(lbl, flag=wx.TOP|wx.LEFT, border=5)

        # unit selection
        unit_opts = [_('Inches'),_('Centimetres')]     
        self.unit_box = wx.RadioBox(pnl,label=_('Units'),choices=unit_opts,style=wx.RA_SPECIFY_COLS)
        newline.Add(self.unit_box,flag=wx.LEFT|wx.ALIGN_CENTRE_VERTICAL, border=50)
        vert_sizer.Add(newline,flag=wx.TOP|wx.LEFT|wx.RIGHT,border=10)

        # Margin
        newline = wx.BoxSizer(wx.HORIZONTAL)
        newline.Add(wx.StaticText(pnl, label=_('Margin to add to final output' + ':')),flag=wx.ALIGN_CENTRE_VERTICAL)
        self.margin_txt = wx.TextCtrl(pnl,size=(40,-1),style=wx.TE_RIGHT)
        newline.Add(self.margin_txt,flag=wx.ALIGN_CENTRE_VERTICAL|wx.LEFT, border=5)
        vert_sizer.Add(newline,flag=wx.TOP|wx.LEFT|wx.RIGHT,border=10)

        # Trim header
        newline = wx.BoxSizer(wx.HORIZONTAL)
        newline.Add(wx.StaticText(pnl, label=_('Amount to trim from each page') + ':'))
        vert_sizer.Add(newline,flag=wx.TOP|wx.LEFT|wx.RIGHT,border=10)

        # Left trim
        newline = wx.BoxSizer(wx.HORIZONTAL)
        newline.Add(wx.StaticText(pnl, label=_('Left' + ':')),flag=wx.ALIGN_CENTRE_VERTICAL|wx.LEFT, border=10)
        self.left_trim_txt = wx.TextCtrl(pnl,size=(40,-1),style=wx.TE_RIGHT)
        newline.Add(self.left_trim_txt,flag=wx.ALIGN_CENTRE_VERTICAL|wx.LEFT, border=5)

        # Right trim
        newline.Add(wx.StaticText(pnl, label=_('Right' + ':')),flag=wx.ALIGN_CENTRE_VERTICAL|wx.LEFT, border=10)
        self.right_trim_txt = wx.TextCtrl(pnl,size=(40,-1),style=wx.TE_RIGHT)
        newline.Add(self.right_trim_txt,flag=wx.ALIGN_CENTRE_VERTICAL|wx.LEFT, border=5)
       
        # Top trim
        newline.Add(wx.StaticText(pnl, label=_('Top' + ':')),flag=wx.ALIGN_CENTRE_VERTICAL|wx.LEFT, border=10)
        self.top_trim_txt = wx.TextCtrl(pnl,size=(40,-1),style=wx.TE_RIGHT)
        newline.Add(self.top_trim_txt,flag=wx.ALIGN_CENTRE_VERTICAL|wx.LEFT, border=5)

        # Bottom trim
        newline.Add(wx.StaticText(pnl, label=_('Bottom' + ':')),flag=wx.ALIGN_CENTRE_VERTICAL|wx.LEFT, border=10)
        self.bottom_trim_txt = wx.TextCtrl(pnl,size=(40,-1),style=wx.TE_RIGHT)
        newline.Add(self.bottom_trim_txt,flag=wx.ALIGN_CENTRE_VERTICAL|wx.LEFT, border=5)
        vert_sizer.Add(newline,flag=wx.TOP|wx.LEFT|wx.RIGHT,border=10)

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

        pnl.SetSizer(vert_sizer)

        self.in_doc = None
        self.out_doc_path = None
        self.tiler = None

        self.working_dir = os.getcwd()
    
    def on_go_pressed(self,event):
        if self.tiler is None:
            return

        if self.out_doc_path is None:
            self.on_output(event)

        # set all the various options of the tiler
        
        # define the page order
        self.tiler.set_col_major(self.col_row_order_combo.GetSelection())
        self.tiler.set_right_left(self.left_right_combo.GetSelection())
        self.tiler.set_bottom_top(self.top_bottom_combo.GetSelection())
        
        self.tiler.set_page_range(self.page_range_txt.GetValue())

        # set the optional stuff
        self.tiler.set_units(self.unit_box.GetSelection())
        self.tiler.set_rotation(self.rotate_combo.GetSelection())

        # margins
        self.tiler.set_margin(txt_to_float(self.margin_txt.GetValue()))

        # trim
        trim = [0.0]*4
        trim[0] = txt_to_float(self.left_trim_txt.GetValue())
        trim[1] = txt_to_float(self.right_trim_txt.GetValue())
        trim[2] = txt_to_float(self.top_trim_txt.GetValue())
        trim[3] = txt_to_float(self.bottom_trim_txt.GetValue())
        self.tiler.set_trim(trim)

        # rows/cols
        cols = self.columns_txt.GetValue().strip()
        cols = int(cols) if cols else 0
        rows = self.rows_txt.GetValue().strip()
        rows = int(rows) if rows else 0

        # do it
        try:
            new_doc = self.tiler.run(rows,cols)
            print(_('Tiling successful'))
        except Exception as e:
            print(_('Something went wrong') + ', ' + _('tiling failed'))
            print(_('Exception') + ':')
            print(e)
        
        try:
            new_doc.save(self.out_doc_path)
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
            try:
                self.out_doc_path = pathname
                self.output_fname_display.SetLabel(os.path.basename(pathname))

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
            self.working_dir = os.path.dirname(pathname)
            try:
                # open the pdf
                print(_('Opening') + ' ' + pathname)
                self.in_doc = pikepdf.Pdf.open(pathname)
                self.tiler = PageTiler(self.in_doc)
                self.input_fname_display.SetLabel(os.path.basename(pathname))
                self.page_range_txt.SetValue('1-{}'.format(len(self.in_doc.pages)))

                # clear the output if it's already set
                self.out_doc_path = None
                self.output_fname_display.SetLabel(_('None'))

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