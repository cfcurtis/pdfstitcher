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
import re
import pdf_operators

def match_nested(s_idx,e_idx,names):
    if len(s_idx) != len(e_idx):
        print(_('Mismatched start and end blocks, cannot process layers.'))
        return []
         
    matches = []

    # iterate the indices to match start/ends. This isn't quite as straightforward as it might
    # seem because the blocks could be nested.
    while len(e_idx) > 0:
        min_dist = 1e6
        match = 0
        for i, s in enumerate(s_idx):
            dist = e_idx[0] - s
            if dist <= 0:
                break

            if dist < min_dist:
                min_dist = dist
                match = i

        matches.append([names.pop(match),s_idx.pop(match),e_idx.pop(0)])
        # matches is in order of ending blocks, reasonable for now
    
    return matches

class LayerFilter():
    def __init__(self,doc = None):
        self.pdf = doc
        self.keep_ocs = 'all'
        self.keep_non_oc = True

    def set_input(self,doc):
        self.pdf = doc
    
    def set_keep_ocs(self,keeplist):
        self.keep_ocs = keeplist
    
    def set_keep_non_oc(self,keep):
        self.keep_non_oc = keep
        
    def get_layer_names(self):
        # reads through the root to parse out the layers present in the file
        if '/OCProperties' not in self.pdf.Root.keys():
            return None 

        return [str(oc.Name) for oc in self.pdf.Root.OCProperties.OCGs]
        
    
    def find_page_keep(self,res):
        if '/Properties' in res.keys():
            page_ocs = {key:str(val.Name) for key, val in res.Properties.items() if '/Type' in val.keys() and str(val.Type) == '/OCG'}
            page_keep = [k for k,v in page_ocs.items() if v in self.keep_ocs]
            return page_keep
        else:
            return []

    def filter_content(self,content):
        # content can be either a page or an xobject
        if '/Resources' in content.keys():
            page_keep = self.find_page_keep(content.Resources)
        else:
            page_keep = []
        
        if len(page_keep) == 0:
            if self.keep_non_oc:
                # nothing to be done if there's no layers in this object
                return None
            else:
                # otherwise replace it with an empty stream
                return b''

        commands = pikepdf.parse_content_stream(content)
        show_ops = [pikepdf.Operator(k) for k,v in pdf_operators.ops.items() if v[0] == 'show'] 
        new_content = []
        in_oc = False
        currently_copying = self.keep_non_oc

        for operands, operator in commands:
            # look for optional content
            if operator == pikepdf.Operator('BDC'):
                # BDC/BMC doesn't necessarily mean optional content block
                # check the operands for the /OC flag
                if len(operands) > 1 and operands[0] == '/OC':
                    in_oc = True
                    if operands[1] in page_keep:
                        currently_copying = True
                    else:
                        currently_copying = False

            elif not in_oc and self.keep_non_oc and not currently_copying:
                # check if we're outside the OCs and need to start a new range
                copy_range.append([i,None])

            if currently_copying or operator not in show_ops:
                new_content.append([operands,operator])

            if in_oc and operator == pikepdf.Operator('EMC'):
                currently_copying = self.keep_non_oc
                in_oc = False

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

        if self.keep_ocs == 'all':
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