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

from os import write
import pikepdf
from wx import Yield, ProgressDialog
import pdf_operators as pdf_ops
from decimal import Decimal
import utils 

# helper functions to dump page to file for debugging
def write_page(fname,stream):
    with open(fname,'w') as f:
        f.write(stream.decode())

class LayerFilter():
    def __init__(self,doc = None):
        self.pdf = doc
        self.keep_ocs = 'all'
        self.keep_non_oc = True
        self.delete_ocgs = True
        self.page_range = []

        self.line_props = {}
        self.colour_type = None
    
    def convert_layer_props(self,layer_props):
        # convert the line properties from the GUI to what the PDF needs
        layer_mod = {}

        w = 1
        if 'thickness' in layer_props.keys():
            layer_mod['w'] = [round(Decimal(layer_props['thickness']),1)]
            w = layer_mod['w'][0]
        
        if 'style' in layer_props.keys():
            layer_mod['d'] = list(pdf_ops.line_style_arr[layer_props['style']])
            # list is needed to make sure this is a copy
            # scale the line style
            layer_mod['d'][0] = [d*w for d in layer_mod['d'][0]]

        # assign the colour based on colour type
        if 'rgb' in layer_props.keys():
            if self.colour_type is None or self.colour_type == 'RG':
                layer_mod['RG'] = [round(Decimal(rg),3) for rg in layer_props['rgb']]
            elif self.colour_type == 'K':
                layer_mod['K'] = [round(Decimal(k),3) for k in pdf_ops.rgb_to_cmyk(layer_props['rgb'])]
        
        # create the dictionary keeping track of modifications
        mod_applied = {key: False for key in layer_mod.keys()}
        
        return layer_mod, mod_applied
    
    def check_colour(self,operator,operands):
        operator = str(operator)
        # check to see what type of colour is defined in this PDF
        if operator in ('CS','K','RG','SC','SCN'):
            if operator in ('K','RG'):
                self.colour_type = operator
            else:
                print('Found colour command ' + operator + ' with operands ', operands)
            return True
        else:
            return False

    def get_layer_names(self):
        # reads through the root to parse out the layers present in the file
        if '/OCProperties' not in self.pdf.Root.keys():
            return None 

        names = [str(oc.Name) for oc in self.pdf.Root.OCProperties.OCGs]
        ordered_names = [str(o.Name) for o in self.pdf.Root.OCProperties.D.Order]
        for n in names:
            if n not in ordered_names:
                ordered_names.append(n)
        return ordered_names
    
    def find_page_keep(self,res):
        if '/Properties' in res.keys():
            if self.delete_ocgs:
                page_ocs = {key:str(val.Name) for key, val in res.Properties.items() if 
                    '/Type' in val.keys() 
                    and str(val.Type) == '/OCG'
                    and str(val.Name) in self.keep_ocs}
            else:
                page_ocs = {key:str(val.Name) for key, val in res.Properties.items() if 
                    '/Type' in val.keys() 
                    and str(val.Type) == '/OCG'}
            return page_ocs
        else:
            return {}

    def filter_content(self,content,layer=None):
        # content can be either a page or an xobject
        if '/Resources' in content.keys():
            page_keep = self.find_page_keep(content.Resources)
        else:
            page_keep = {}
        
        commands = pikepdf.parse_content_stream(content)
        show_ops = [pikepdf.Operator(k) for k,v in pdf_ops.ops.items() if v[0] == 'show'] 
        stroke_ops = [pikepdf.Operator(k) for k,v in pdf_ops.ops.items() if v[0] == 'show' and v[1] == 'stroke'] 
        new_content = []
        in_oc = False
        currently_copying = self.keep_non_oc
        gs_mod = []
        new_q = False

        if layer is not None:
            layer_mod,mod_applied = self.convert_layer_props(self.line_props[layer])
            in_oc = True
            currently_copying = True
        else:
            layer_mod = None
            mod_applied = None

        for operands, operator in commands:
            # check to see if this pdf has CMYK or RGB colour definitions
            if not self.colour_type:
                self.check_colour(operator,operands)

            # look for optional content
            if layer is None and operator == pikepdf.Operator('BDC'):
                # BDC/BMC doesn't necessarily mean optional content block
                # check the operands for the /OC flag
                if len(operands) > 1 and operands[0] == '/OC':
                    in_oc = True
                    if operands[1] in page_keep.keys():
                        currently_copying = True

                        # get a link to the current line property modifications requested
                        if page_keep[operands[1]] in self.line_props.keys():
                            layer_mod,mod_applied = self.convert_layer_props(self.line_props[page_keep[operands[1]]])
                    else:
                        currently_copying = False

            # all kinds of crazy stuff going on behind the scenes, so to select layers we can't just delete everything.
            # Just copy the non-showing operations
            if currently_copying or operator not in show_ops:
                new_command = [operands,operator]
                
                if in_oc and layer_mod is not None:
                    op_string = str(operator)

                    # if we need to modify graphics state dictionaries, we need to retrieve that from the resources
                    if op_string == 'gs' and str(operands) not in gs_mod:
                        gs_mod.append(operands)

                    # check for one of the line property modification operators
                    if op_string in layer_mod.keys():
                        new_command[0] = layer_mod[op_string]
                        mod_applied[op_string] = True

                    # check if we're drawing but haven't applied all mods yet
                    if operator in stroke_ops and not all(mod_applied.values()):
                        needs_mod = [k for k, v in mod_applied.items() if not v]
                        for key in needs_mod:
                            new_content.append([layer_mod[key],pikepdf.Operator(key)])
                            mod_applied[key] = True
                    
                    if op_string == 'Q':
                        # reset the dictionary if we're in a new q/Q block
                        if all(mod_applied.values()):
                            mod_applied = {key: False for key in mod_applied.keys()}
                
                new_content.append(new_command)

                # q is the only command that needs to go after the current command
                if new_q:
                    new_content.append([[],pikepdf.Operator('q')])
                    new_q = False

            if in_oc and operator == pikepdf.Operator('EMC'):
                currently_copying = self.keep_non_oc
                in_oc = False
                layer_mod = None
        
        if len(gs_mod) > 0:
            print('Found graphics state dictionary, layer modification may not work as expected')

        return pikepdf.unparse_content_stream(new_content)

    def filter_ocg_order(self,input):
        if input._type_name == 'array':
            # create a copy of the array and filter the items
            output = pikepdf.Array([])
            for item in input:
                f_item = self.filter_ocg_order(item)
                if f_item is not None:
                    output.append(f_item)
            
            return output
            
        elif input._type_name == 'dictionary':
            if '/Type' in input.keys():
                if input.Type == pikepdf.Name.OCG:
                    # found the OCG entry, delete it if it's not in our keep array
                    if any([input.Name == oc for oc in self.keep_ocs]):
                        return input
                    else:
                        return None
        else:
            return input

    def run(self,progress_dlg):
        # open a new copy of the input
        output = pikepdf.Pdf.open(self.pdf.filename)
        self.colour_type = None

        if self.keep_ocs == 'all' and len(self.line_props) == 0:
            return output
        
        if self.keep_ocs is None and self.keep_non_oc == False:
            print(_('No layers selected, generated PDF would be blank.'))
            return None

        if len(self.page_range) == 0:
            # human input page range is 1-indexed
            page_range = range(1,len(output.pages)+1)
        else:
            # get rid of duplicates and zeros in the page range
            page_range = list(set([p for p in self.page_range if p > 0]))

        n_page = len(page_range)
        progress_dlg.SetRange(n_page)
        Yield()

        # change the decimal precision because it's really high
        for p in page_range:
            # print(_('Processing layers in page {}...'.format(p)))
            # apply the filter and reassign the page contents
            newstream = self.filter_content(output.pages[p-1])
            output.pages[p-1].Contents = output.make_stream(newstream)

            # check if there are form xobjects, and if so, filter them as well
            if '/XObject' in output.pages[p-1].Resources.keys():
                for k in output.pages[p-1].Resources.XObject.keys():
                    xobj = output.pages[p-1].Resources.XObject[k]
                    if '/OC' in xobj.keys():
                        oc = None
                        if '/Name' in xobj.OC.keys():
                            oc = str(xobj.OC.Name)
                        
                        elif '/OCGs' in xobj.OC.keys() and '/Name' in xobj.OC.OCGs.keys():
                            oc = str(xobj.OC.OCGs.keys())
                        
                        if oc in self.keep_ocs:
                            if oc in self.line_props.keys():
                                newstream = self.filter_content(xobj,layer=oc)
                                xobj.write(newstream)
                        else:
                            # if we don't want to keep it, just blank it out
                            newstream = b''
                            xobj.write(newstream)
                    else:
                        if xobj.Subtype == pikepdf.Name('/Form'):
                            newstream = self.filter_content(xobj)
                            xobj.write(newstream)
            
            progress_dlg.Update(page_range.index(p))
            Yield()
            
            if progress_dlg.WasCancelled():
                return None
        
        # edit the OCG listing in the root
        OCGs = [oc for oc in output.Root.OCProperties.OCGs if str(oc.Name) in self.keep_ocs]
        Off = [oc for oc in output.Root.OCProperties.OCGs if str(oc.Name) not in self.keep_ocs]
        if self.delete_ocgs:
            output.Root.OCProperties.OCGs = OCGs
        else:
            output.Root.OCProperties.D.ON = OCGs
            output.Root.OCProperties.D.OFF = Off

        # by default, unlock all layers and show all OCGs
        output.Root.OCProperties.D.Locked = []
        if self.delete_ocgs:
            output.Root.OCProperties.D.Order = self.filter_ocg_order(output.Root.OCProperties.D.Order)

        output.remove_unreferenced_resources()

        return output
