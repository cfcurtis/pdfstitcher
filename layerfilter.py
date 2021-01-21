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
import numpy as np
import copy

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

    def find_layer_indices(self,stream):
        s_pattern = rb'(.*)BDC|BMC\s+'
        e_pattern = rb'EMC\s+'
        s_iter = re.finditer(s_pattern,stream)
        e_iter = re.finditer(e_pattern,stream)

        s_idx = []
        e_idx = []
        oc_names = []
        oc_pattern = rb'/OC\s+(/?\w+)'

        # loop through the start iterator and find the name of the layer, plus the starting index
        for s in s_iter:
            s_idx.append(s.span()[0])
            oc_name = re.findall(oc_pattern,s.groups(0)[0])

            if len(oc_name) > 0:
                oc_names.append(oc_name[0].decode())
            else:
                oc_names.append(None)

        # ending just needs the index
        for e in e_iter:
            e_idx.append(e.span()[1])
        
        matches = match_nested(s_idx,e_idx,oc_names)

        return matches
    
    def filter_obj(self,obj,is_xobj = False):
        # obj can be either a page or an xobject
        if '/Resources' in obj.keys():
            page_keep = self.find_page_keep(obj.Resources)
        else:
            page_keep = []
        
        if len(page_keep) == 0:
            if self.keep_non_oc:
                # nothing to be done if there's no layers in this object
                return None
            else:
                # otherwise replace it with an empty stream
                return b''
    
        if is_xobj:
            stream = obj.read_bytes()
        else:
            # Contents could be an array if it's part of a page, so squish them just in case
            obj.page_contents_coalesce()
            stream = obj.Contents.read_bytes()
        
        layer_ind = self.find_layer_indices(stream)
        
        # the stream needs to be in a format that numpy can handle for masking
        np_stream = np.array(bytearray(stream))
        if self.keep_non_oc:           
            mask = np.ones(shape=(len(stream),),dtype=np.bool)
            # subtract non-selected layers from the original stream
            for layer in layer_ind:
                if layer[0] is not None and layer[0] not in page_keep:
                    mask[layer[1]:layer[2]] = 0
        else:
            mask = np.zeros(shape=(len(stream),),dtype=np.bool)
            # add only selected layers
            for layer in layer_ind:
                if layer[0] in page_keep:
                    mask[layer[1]:layer[2]] = 1

        newstream = b''.join([b for b in np_stream[mask]])
        
        return newstream

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
        copy_range = []
        # q_pos = []
        in_oc = False

        # helper function to check if we're currently copying the commands
        def currently_copying():
            return len(copy_range) > 0 and copy_range[-1][1] is None

        for i, ops in enumerate(commands):
            operator = ops[1]
            operands = ops[0]

            # look for optional content
            if operator == pikepdf.Operator('BDC'):
                # BDC/BMC doesn't necessarily mean optional content block
                if len(operands) > 1 and operands[0] == '/OC':
                    in_oc = True
                    if operands[1] in page_keep:
                        if not currently_copying():
                            # start a new range
                            copy_range.append([i,None])
                    else:
                        if currently_copying():
                            # stop copying, excluding the current line
                            copy_range[-1][1] = i

            if in_oc and operator == pikepdf.Operator('EMC'):
                in_oc = False
                if currently_copying():
                    # end this block, including this line
                    copy_range[-1][1] = i + 1
                
            elif not in_oc and self.keep_non_oc and not currently_copying():
                # check if we're outside the OCs and need to start a new range
                copy_range.append([i,None])
        
            # # finally, check the q/Q blocks
            # if operator == pikepdf.Operator('q'):
            #     q_pos.append([i,currently_copying()])
            
            # if operator == pikepdf.Operator('Q'):
            #     # if we're copying the Q but not the previous q, we have a problem
            #     if currently_copying() and not q_pos[-1][1]:
            #         copy_range[-1][0] = q_pos[-1][0]

            #     # if we copied the previous q but not the current Q, we also have a problem
            #     if not currently_copying() and q_pos[-1][1]:
            #         copy_range[-1][1] = i + 1

            #     # close out this q/Q block regardless of if we copy it or not
            #     q_pos.pop(-1)
        
        # close out if we copy to the end
        if currently_copying():
            copy_range[-1][1] = len(commands)

        new_content = []
        for r in copy_range:
            if None in r:
                print('Invalid range')
            
            new_content += commands[r[0]:r[1]]

        return  pikepdf.unparse_content_stream(new_content)

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