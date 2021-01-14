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

class LayerFilter():
    def __init__(self,in_doc = None):
        self.pdf = in_doc
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
        
        matches = []

        # iterate the indices to match start/ends. This isn't quite as straightforward as it might
        # seem because the BDC/EMC blocks could be nested.
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

            matches.append([oc_names[match],s_idx.pop(match),e_idx.pop(0)])
            # matches is in order of ending blocks, reasonable for now. 
            # Could also be dict with oc_names as keys.
        
        return matches
    
    def filter_obj(self,obj,is_xobj = False):
        # obj can be either a page or an xobject
        if '/Resources' in obj.keys():
            page_keep = self.find_page_keep(obj.Resources)
        else:
            page_keep = []
        
        if len(page_keep) == 0:
            if self.keep_non_oc:
                # nothing to be done if there's no layers in this oFbject
                return obj
            else:
                # otherwise replace it with an empty stream
                obj.write(b'')
                return obj
    
        if is_xobj:
            stream = obj.read_bytes()
        else:
            # Contents could be an array if it's part of a page, so squish them just in case
            obj.page_contents_coalesce()
            stream = obj.Contents.read_bytes()
        
        layer_ind = self.find_layer_indices(stream)

        # do some magic to apply layer filters

        if is_xobj:
            obj.write(stream)
        else:
            obj.Contents.write(stream)
        
        return obj

    def run(self,page_range = None):
        if self.keep_ocs == 'all':
            return self.pdf
        
        if self.keep_ocs is None and self.keep_non_oc == False:
            print(_('No layers selected, generated PDF woud be blank.'))
            return None

        if page_range is None:
            page_range = range(len(self.pdf.pages))

        for i in page_range:
            # apply the filter and reassign the page contents
            self.pdf.pages[i] = self.filter_obj(self.pdf.pages[i], is_xobj = False)

            # check if there are form xobjects, and if so, filter them as well
            if '/XObject' in self.pdf.pages[i].Resources.keys():
                for k in self.pdf.pages[i].Resources.XObject.keys():
                    if self.pdf.pages[i].Resources.XObject[k].Subtype == pikepdf.Name('/Form'):
                        self.pdf.pages[i].Resources.XObject[k] = self.filter_obj(self.pdf.pages[i].Resources.XObject[k], is_xobj = True)
        