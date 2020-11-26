import wx
from tile_pages import *
import os
import gettext

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
        in_doc_btn = wx.Button(pnl, label='Select Input PDF')
        in_doc_btn.Bind(wx.EVT_BUTTON,self.on_open)
        newline.Add(in_doc_btn, flag=wx.ALIGN_CENTRE_VERTICAL)
        self.input_fname_display = wx.StaticText(pnl, label='None')
        newline.Add(self.input_fname_display, flag=wx.ALIGN_CENTRE_VERTICAL|wx.LEFT, border=5)
        vert_sizer.Add(newline,flag=wx.TOP|wx.LEFT|wx.RIGHT,border=10)
                
        newline = wx.BoxSizer(wx.HORIZONTAL)
        out_doc_btn = wx.Button(pnl, label='Select Output PDF')
        out_doc_btn.Bind(wx.EVT_BUTTON,self.on_output)
        newline.Add(out_doc_btn, flag=wx.ALIGN_CENTRE_VERTICAL)
        self.output_fname_display = wx.StaticText(pnl, label='None')
        newline.Add(self.output_fname_display, flag=wx.ALIGN_CENTRE_VERTICAL|wx.LEFT, border=5)
        vert_sizer.Add(newline,flag=wx.TOP|wx.LEFT|wx.RIGHT,border=10)

        ## REQUIRED PARAMETERS
        vert_sizer.Add(wx.StaticLine(pnl, -1), flag=wx.EXPAND|wx.TOP|wx.BOTTOM, border=5)
        lbl = wx.StaticText(pnl, label='Required Parameters')
        lbl.SetFont(lbl.GetFont().Bold())
        vert_sizer.Add(lbl, flag=wx.TOP|wx.LEFT, border=5)

        # Page Range
        newline = wx.BoxSizer(wx.HORIZONTAL)
        newline.Add(wx.StaticText(pnl, label='Page Range:'), flag=wx.ALIGN_CENTRE_VERTICAL)
        self.page_range_txt = wx.TextCtrl(pnl)
        newline.Add(self.page_range_txt,flag=wx.ALIGN_CENTRE_VERTICAL|wx.LEFT, border=5)
        vert_sizer.Add(newline,flag=wx.TOP|wx.LEFT|wx.RIGHT,border=10)

        # Columns/Rows
        newline = wx.BoxSizer(wx.HORIZONTAL)
        newline.Add(wx.StaticText(pnl, label='Number of Columns:'), flag=wx.ALIGN_CENTRE_VERTICAL)
        self.columns_txt = wx.TextCtrl(pnl,size=(40,-1),style=wx.TE_RIGHT)
        newline.Add(self.columns_txt,flag=wx.ALIGN_CENTRE_VERTICAL|wx.LEFT, border=5)
        newline.Add(wx.StaticText(pnl, label='Number of Rows:'), flag=wx.ALIGN_CENTRE_VERTICAL|wx.LEFT, border=10)
        self.rows_txt = wx.TextCtrl(pnl,size=(40,-1),style=wx.TE_RIGHT)
        newline.Add(self.rows_txt,flag=wx.ALIGN_CENTRE_VERTICAL|wx.LEFT, border=5)
        vert_sizer.Add(newline,flag=wx.TOP|wx.LEFT|wx.RIGHT,border=10)

        newline = wx.BoxSizer(wx.HORIZONTAL)
        note = wx.StaticText(pnl,label='Note: if both columns and rows are specified, columns take precedence.')
        note.SetFont(note.GetFont().Italic())
        newline.Add(note)
        vert_sizer.Add(newline,flag=wx.ALL,border=10)

        ## OPTIONAL PARAMETERS
        vert_sizer.Add(wx.StaticLine(pnl, -1), flag=wx.EXPAND|wx.TOP|wx.BOTTOM, border=5)
        lbl = wx.StaticText(pnl, label='Optional Parameters')
        lbl.SetFont(lbl.GetFont().Bold())
        vert_sizer.Add(lbl, flag=wx.TOP|wx.LEFT, border=5)
        
        # rotation 
        newline = wx.BoxSizer(wx.HORIZONTAL)
        rotate_opts = ['None','Clockwise','Counterclockwise']
        newline.Add(wx.StaticText(pnl, label='Page Rotation:'), flag=wx.ALIGN_CENTRE_VERTICAL)
        self.rotate_combo = wx.ComboBox(pnl, choices=rotate_opts, value=rotate_opts[0], style=wx.CB_READONLY)
        newline.Add(self.rotate_combo, flag=wx.LEFT|wx.ALIGN_CENTRE_VERTICAL, border=5)

        # unit selection
        unit_opts = ['Inches','Centimetres']     
        self.unit_box = wx.RadioBox(pnl,label='Units',choices=unit_opts,style=wx.RA_SPECIFY_COLS)
        newline.Add(self.unit_box,flag=wx.LEFT|wx.ALIGN_CENTRE_VERTICAL, border=50)
        vert_sizer.Add(newline,flag=wx.TOP|wx.LEFT|wx.RIGHT,border=10)

        # Margin
        newline = wx.BoxSizer(wx.HORIZONTAL)
        newline.Add(wx.StaticText(pnl, label='Margin to add to final output:'),flag=wx.ALIGN_CENTRE_VERTICAL)
        self.margin_txt = wx.TextCtrl(pnl,size=(40,-1),style=wx.TE_RIGHT)
        newline.Add(self.margin_txt,flag=wx.ALIGN_CENTRE_VERTICAL|wx.LEFT, border=5)
        vert_sizer.Add(newline,flag=wx.TOP|wx.LEFT|wx.RIGHT,border=10)

        # Trim header
        newline = wx.BoxSizer(wx.HORIZONTAL)
        newline.Add(wx.StaticText(pnl, label='Amount to trim from each page:'))
        vert_sizer.Add(newline,flag=wx.TOP|wx.LEFT|wx.RIGHT,border=10)

        # Left trim
        newline = wx.BoxSizer(wx.HORIZONTAL)
        newline.Add(wx.StaticText(pnl, label='Left:'),flag=wx.ALIGN_CENTRE_VERTICAL|wx.LEFT, border=10)
        self.left_trim_txt = wx.TextCtrl(pnl,size=(40,-1),style=wx.TE_RIGHT)
        newline.Add(self.left_trim_txt,flag=wx.ALIGN_CENTRE_VERTICAL|wx.LEFT, border=5)

        # Right trim
        newline.Add(wx.StaticText(pnl, label='Right:'),flag=wx.ALIGN_CENTRE_VERTICAL|wx.LEFT, border=10)
        self.right_trim_txt = wx.TextCtrl(pnl,size=(40,-1),style=wx.TE_RIGHT)
        newline.Add(self.right_trim_txt,flag=wx.ALIGN_CENTRE_VERTICAL|wx.LEFT, border=5)
       
        # Top trim
        newline.Add(wx.StaticText(pnl, label='Top:'),flag=wx.ALIGN_CENTRE_VERTICAL|wx.LEFT, border=10)
        self.top_trim_txt = wx.TextCtrl(pnl,size=(40,-1),style=wx.TE_RIGHT)
        newline.Add(self.top_trim_txt,flag=wx.ALIGN_CENTRE_VERTICAL|wx.LEFT, border=5)

        # Bottom trim
        newline.Add(wx.StaticText(pnl, label='Bottom:'),flag=wx.ALIGN_CENTRE_VERTICAL|wx.LEFT, border=10)
        self.bottom_trim_txt = wx.TextCtrl(pnl,size=(40,-1),style=wx.TE_RIGHT)
        newline.Add(self.bottom_trim_txt,flag=wx.ALIGN_CENTRE_VERTICAL|wx.LEFT, border=5)
        vert_sizer.Add(newline,flag=wx.TOP|wx.LEFT|wx.RIGHT,border=10)

        # the go button
        vert_sizer.Add(wx.StaticLine(pnl, -1), flag=wx.EXPAND|wx.TOP|wx.BOTTOM, border=5)
        go_btn = wx.Button(pnl, label='Generate Tiled PDF')
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
        self.out_doc = None
        self.tiler = None

        self.working_dir = os.getcwd()
    
    def on_go_pressed(self,event):
        if self.out_doc is None:
            self.on_output(event)

        # set all the various options of the tiler
        # parse out the requested pages. Note that this allows for pages to be repeated and out of order.
        ptext = self.page_range_txt.GetValue().split(',')
        pages = []
        for r in [p.split('-') for p in ptext]:
            if len(r) == 1:
                pages.append(int(r[0]))
            else:
                pages += list(range(int(r[0]),int(r[-1])+1))
        
        if len(pages) == 0:
            pages = None
        
        self.tiler.set_page_range(pages)

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
            print('Tiling successful')
        except Exception as e:
            print('Something went wrong, tiling failed')
            print('Exception:')
            print(e)
        
        try:
            new_doc.Save(self.out_doc,SDFDoc.e_linearized)
            print('Successfully written to ' + self.out_doc)
        except:
            print('Something went wrong, unable to write to ' + self.out_doc)

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
        with wx.FileDialog(self, 'Save output as', defaultDir=self.working_dir,
                        wildcard='PDF files (*.pdf)|*.pdf',
                        style=wx.FD_SAVE|wx.FD_OVERWRITE_PROMPT) as fileDialog:

            if fileDialog.ShowModal() == wx.ID_CANCEL:
                return

            pathname = fileDialog.GetPath()
            try:
                self.out_doc = pathname
                self.output_fname_display.SetLabel(os.path.basename(pathname))

            except IOError:
                wx.LogError('Cannot output to file {}'.format(pathname))
    
    def on_open(self, event):
        with wx.FileDialog(self, 'Open PDF file', defaultDir=self.working_dir,
                        wildcard='PDF files (*.pdf)|*.pdf',
                        style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST) as fileDialog:

            if fileDialog.ShowModal() == wx.ID_CANCEL:
                return

            # Proceed loading the file chosen by the user
            pathname = fileDialog.GetPath()
            self.working_dir = os.path.dirname(pathname)
            try:
                self.in_doc = PDFDoc(pathname)
                self.tiler = PageTiler(self.in_doc)
                print('Opening {} with {} pages.'.format(pathname,self.in_doc.GetPageCount()))
                self.input_fname_display.SetLabel(os.path.basename(pathname))
                self.page_range_txt.SetValue('1-{}'.format(self.in_doc.GetPageCount()))

            except IOError:
                wx.LogError('Cannot open file {}'.format(pathname))

if __name__ == '__main__':
    # When this module is run (not imported) then create the app, the
    # frame, show it, and start the event loop.
    app = wx.App()
    frm = SewGUI(None, title='PDF Page Tiler',size=(600,800))
    frm.Show()
    app.MainLoop()