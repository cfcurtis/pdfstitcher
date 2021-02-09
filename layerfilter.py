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

import pikepdf
import pdf_operators as pdf_ops

class LayerFilter():
    def __init__(self,doc = None):
        self.pdf = doc
        self.keep_ocs = 'all'
        self.keep_non_oc = True

        self.line_props = {}
        
    def get_layer_names(self):
        # reads through the root to parse out the layers present in the file
        if '/OCProperties' not in self.pdf.Root.keys():
            return None 

        return [str(oc.Name) for oc in self.pdf.Root.OCProperties.OCGs]
    
    def find_page_keep(self,res):
        if '/Properties' in res.keys():
            page_ocs = {key:str(val.Name) for key, val in res.Properties.items() if 
                '/Type' in val.keys() 
                and str(val.Type) == '/OCG'
                and val.Name in self.keep_ocs}
            return page_ocs
        else:
            return {}

    def filter_content(self,content):
        # content can be either a page or an xobject
        if '/Resources' in content.keys():
            page_keep = self.find_page_keep(content.Resources)
        else:
            page_keep = {}
        
        if len(page_keep) == 0:
            if self.keep_non_oc:
                # nothing to be done if there's no layers in this object
                return None
            else:
                # otherwise replace it with an empty stream
                return b''

        commands = pikepdf.parse_content_stream(content)
        show_ops = [pikepdf.Operator(k) for k,v in pdf_ops.ops.items() if v[0] == 'show'] 
        new_content = []
        in_oc = False
        currently_copying = self.keep_non_oc
        layer_mod = None
        mod_applied = None
        first_mod = None

        for operands, operator in commands:
            # look for optional content
            if operator == pikepdf.Operator('BDC'):
                # BDC/BMC doesn't necessarily mean optional content block
                # check the operands for the /OC flag
                if len(operands) > 1 and operands[0] == '/OC':
                    in_oc = True
                    if operands[1] in page_keep.keys():
                        currently_copying = True

                        # get a link to the current line property modifications requested
                        if page_keep[operands[1]] in self.line_props.keys():
                            layer_mod = self.line_props[page_keep[operands[1]]]
                            mod_applied = {v:False for v in layer_mod.keys()}
                    else:
                        currently_copying = False

            if currently_copying or operator not in show_ops:
                new_command = [operands,operator]
                if in_oc and layer_mod is not None:
                    # check for one of the line property modification operators
                    if operator == pikepdf.Operator('d'):
                       new_command[0] = pdf_ops.line_style_arr[layer_mod['style']]
                       mod_applied['style'] = True
                    
                    if operator == pikepdf.Operator('w'):
                        new_command[0] = [layer_mod['thickness']]
                        mod_applied['thickness'] = True
                    
                    if operator == pikepdf.Operator('RG'):
                        new_command[0] = layer_mod['rgb']
                        mod_applied['rgb'] = True
                    
                    if operator == pikepdf.Operator('K'):
                        new_command[0] = pdf_ops.rgb_to_cmyk(layer_mod['rgb'])
                        mod_applied['rgb'] = True
                    
                    if any(mod_applied.values()) and first_mod is None:
                        first_mod = len(new_content)
                
                new_content.append(new_command)

            if in_oc and operator == pikepdf.Operator('EMC'):
                currently_copying = self.keep_non_oc
                in_oc = False

                # make sure the various layer mods were applied. If not, insert them
                if layer_mod is not None and first_mod is not None:
                    if not mod_applied['style']:
                        new_content.insert(first_mod,[pdf_ops.line_style_arr[layer_mod['style']],pikepdf.Operator('d')])
                    
                    if not mod_applied['thickness']:
                        new_content.insert(first_mod,[[layer_mod['thickness']],pikepdf.Operator('w')])
                    
                    if not mod_applied['rgb']:
                        new_content.insert(first_mod,[layer_mod['rgb'],pikepdf.Operator('RG')])

                layer_mod = None
                mod_applied = None
                first_mod = None

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

    def run(self,page_range = None):
        # open a new copy of the input
        output = pikepdf.Pdf.open(self.pdf.filename)

        if self.keep_ocs == 'all' and len(self.line_props) == 0:
            return output
        
        if self.keep_ocs is None and self.keep_non_oc == False:
            print(_('No layers selected, generated PDF woud be blank.'))
            return None

        if page_range is None:
            # human input page range is 1-indexed
            page_range = range(1,len(output.pages)+1)
        else:
            # get rid of duplicates and zeros in the page range
            page_range = list(set([p for p in page_range if p > 0]))

        for p in page_range:
            print(_('Extracting layers for page {}...'.format(p)))
            # apply the filter and reassign the page contents
            newstream = self.filter_content(output.pages[p-1])
            if p == 2:
                with open('original.txt','w') as f:
                    f.write(pikepdf.unparse_content_stream(pikepdf.parse_content_stream(output.pages[p-1])).decode())
                
                with open('new.txt','w') as f:
                    f.write(newstream.decode())
            
            if newstream:
                output.pages[p-1].Contents = output.make_stream(newstream)

            # check if there are form xobjects, and if so, filter them as well
            if '/XObject' in output.pages[p-1].Resources.keys():
                for k in output.pages[p-1].Resources.XObject.keys():
                    if output.pages[p-1].Resources.XObject[k].Subtype == pikepdf.Name('/Form'):
                        newstream = self.filter_content(output.pages[p-1].Resources.XObject[k])
                        if newstream:
                            output.pages[p-1].Resources.XObject[k].write(newstream)
        
        # edit the OCG listing in the root
        OCGs = [oc for oc in output.Root.OCProperties.OCGs if str(oc.Name) in self.keep_ocs]
        output.Root.OCProperties.OCGs = OCGs

        # by default, unlock all layers and show all OCGs
        output.Root.OCProperties.D.Locked = []
        output.Root.OCProperties.D.Order = self.filter_ocg_order(output.Root.OCProperties.D.Order)

        output.remove_unreferenced_resources()

        return output