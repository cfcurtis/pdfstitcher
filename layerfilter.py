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
import pdf_operators as pdf_ops
from decimal import Decimal
import utils 
import sys
import traceback

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
        self.properties = {}

    

    def get_layer_names(self):
        # reads through the root to parse out the layers present in the file
        if '/OCProperties' not in self.pdf.Root.keys():
            return None 

        names = [str(oc.Name) for oc in self.pdf.Root.OCProperties.OCGs]
        ordered_names = []
        for o in self.pdf.Root.OCProperties.D.Order:
            if '/Name' in o.keys():
                if o.Name not in ordered_names:
                    ordered_names.append(str(o.Name))
            else:
                for o2 in o:
                    if '/Name' in o2.keys():
                        if o2.Name not in ordered_names:
                            ordered_names.append(str(o2.Name))
        for n in names:
            if n not in ordered_names:
                ordered_names.append(n)
        return ordered_names
    

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

    def run(self,progress_range = None, progress_update = None, progress_was_cancelled = None):
        self.found_objects = set()
        self.property_search_objects = set()
        
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
        progress_range and progress_range(n_page) # don't run if the callback is None

        # edit the OCG listing in the root
        OCGs = [oc for oc in output.Root.OCProperties.OCGs if str(oc.Name) in self.keep_ocs]
        Off = [oc for oc in output.Root.OCProperties.OCGs if str(oc.Name) not in self.keep_ocs]
        self.off_ocs = []
        for o in Off:
            self.off_ocs.append(o.Name)
        if self.delete_ocgs:
            output.Root.OCProperties.OCGs = OCGs
            output.Root.OCProperties.D.ON = OCGs
            self.clean_line_options()
            for p in page_range:
                self.get_properties(output.pages[p-1])
                self.remove_ocgs_from_stream(output.pages[p-1])
                progress_update and progress_update(page_range.index(p))
                if progress_was_cancelled and progress_was_cancelled():
                    return None
            progress_update and progress_update(n_page)
            output.Root.OCProperties.D.Order = self.filter_ocg_order(output.Root.OCProperties.D.Order)
        else:
            output.Root.OCProperties.D.ON = OCGs
            output.Root.OCProperties.D.OFF = Off

        # by default, unlock all layers and show all OCGs
        output.Root.OCProperties.D.Locked = []

        output.remove_unreferenced_resources()

        return output

    def get_properties(self, ob, properties=None, depth = 0):
        if not isinstance(ob, pikepdf.Object):
            return

        #skip over anything we have already seen
        obid = ob.unparse()
        if obid in self.property_search_objects:
            return
        else:
            self.property_search_objects.add(obid)

        if isinstance(ob, pikepdf.Array):
            for i in range(len(ob)):
                p = self.get_properties(ob[i], properties, depth)

        if isinstance(ob, pikepdf.Dictionary):
            for o in ob.keys():
                if o == '/Resources':
                    r = ob[o]
                    if '/Properties' in r.keys():
                        p = r['/Properties']
                        for k in p.keys():
                            self.properties[k] = p[k]
                if o != '/Parent':
                    p = self.get_properties(ob[o], properties, depth)

    def clean_line_options(self):
        for l in self.line_props:
            w = 1
            lp = self.line_props[l]
            if 'thickness' in lp.keys():
                w = round(Decimal(lp['thickness']), 1)
                lp['thickness'] = [w]
            if 'rgb' in lp.keys():
                lp['rgb'] = [round(Decimal(rg), 3) for rg in lp['rgb']]
            if 'style' in lp.keys():
                lp['style'] = list(pdf_ops.line_style_arr[lp['style']])
                # list is needed to make sure this is a copy
                # scale the line style
                lp['style'][0] = [d*w for d in lp['style'][0]]
            self.line_props[l] = lp


    def append_layer_property(self, prop, commands, layer_name):
        if prop == 'rgb':
            op = 'RG'
        elif prop == 'thickness':
            op = 'w'
        else:
            op = 'd'
        if layer_name in self.line_props.keys():
            lp = self.line_props[layer_name]
            if prop in lp.keys():
                commands.append([lp[prop], op])

    def append_layer_properties(self, commands, layer_name):
        self.append_layer_property('rgb', commands, layer_name)
        self.append_layer_property('thickness', commands, layer_name)
        self.append_layer_property('style', commands, layer_name)
      
    def remove_ocgs_from_stream(self, ob, in_oc = False, keeping = True):
        # skip over anything we have already seen
        if not isinstance(ob, pikepdf.Object):
            return

        obid = ob.unparse()
        if obid in self.found_objects:
            return
        else:
            self.found_objects.add(obid)

        keep_operators = ['Tc', 'Tw', 'Tz', 'TL', 'Tf', 'Tr', 'Ts', 'Td', 'TD', 'Tm', 'd0', 'd1', 'CS', 'cs', 'SC', 'SCN', 'sc', 'scn',
        'G', 'g', 'RG', 'rg', 'K', 'k', 'BX', 'EX', 'q', 'Q']
        color_stroke_ops = ['CS', 'RG', 'SC', 'SCN', 'K']

        if isinstance(ob, pikepdf.Array):
            for i in range(len(ob)):
                self.remove_ocgs_from_stream(ob[i], in_oc, keeping)

        if isinstance(ob, pikepdf.Dictionary):
            for o in ob.keys():
                if o != '/Parent':
                    self.remove_ocgs_from_stream(ob[o], in_oc, keeping)

        if isinstance(ob, pikepdf.Stream):
            commands = []
            # the whole stream is a layer
            if '/OC' in ob.keys():
                layer_name = str(ob.OC.Name)
                if layer_name in self.off_ocs:
                    empty = pikepdf.unparse_content_stream([])
                    ob.write(empty)
                    return
                else:
                    try:
                        for operands, operator in pikepdf.parse_content_stream(ob):
                            self.append_layer_properties(commands, layer_name)
                            commands.append([operands, operator])
                            op = str(operator)
                            if op in ['Q', 'gs']:
                                self.append_layer_properties(commands, layer_name)
                            elif op == 'd':
                                self.append_layer_property('style', commands, layer_name)
                            elif op in color_stroke_ops:
                                self.append_layer_property('rgb', commands, layer_name)
                            elif op == 'w': # and operands[0] != 0:
                                self.append_layer_property('thickness', commands, layer_name)
                        newstream = pikepdf.unparse_content_stream(commands)
                        ob.write(newstream)
                        return

                    except:
                        #traceback.print_exc()
                        #print("couldn't open stream ", sys.exc_info()[0] )
                        #print("couldn't open stream")
                        #ignore - probably not a content stream. Print an error when debugging
                        ignore = 1
                        return


            # the layers may be in the stream
            in_oc = False
            try:
                stream_has_layers = False
                for operands, operator in pikepdf.parse_content_stream(ob, "BDC"):
                    stream_has_layers = True
                
                if stream_has_layers:
                    previous_operator = ''
                    for operands, operator in pikepdf.parse_content_stream(ob):
                        op = str(operator)
                        if op == "BDC" and len(operands) > 1 and str(operands[0]) == "/OC":
                            
                            in_oc = True
                            keeping = True
                            oc = str(operands[1])
                            layer_name = ''
                            if self.properties != None:
                                if oc in self.properties.keys():
                                    ocg = self.properties[oc]
                                    layer_name = str(ocg.Name)
                                    if ocg.Name in self.off_ocs:
                                        keeping = False
                                    else:
                                        self.append_layer_properties(commands, layer_name)
                                
                        if keeping or not in_oc or op in keep_operators:
                            if previous_operator == 'q' and operator == 'Q':
                                commands.pop()
                            else:
                                commands.append([operands, operator])
                            if in_oc and keeping:
                                # turn into a switch statement when python starts supporting them - 3.10?
                                if op in ['Q', 'gs']:
                                    self.append_layer_properties(commands, layer_name)
                                elif op == 'd':
                                    self.append_layer_property('style', commands, layer_name)
                                elif op in color_stroke_ops:
                                    self.append_layer_property('rgb', commands, layer_name)
                                elif op == 'w': # and operands[0] != 0:
                                    self.append_layer_property('thickness', commands, layer_name)
                            previous_operator = operator
                            #if(in_oc):
                            #print(f"Op {operator}, operands {operands}")
                        if str(operator) == 'EMC':
                            in_oc = False


                    newstream = pikepdf.unparse_content_stream(commands)
                    ob.write(newstream)

            except AttributeError:
                #traceback.print_exc()
                ignore = 1
            except ValueError:
                #traceback.print_exc()
                ignore = 1
            except NameError:
                #traceback.print_exc()
                ignore = 1
            except:
                #traceback.print_exc()
                #print("couldn't open stream ", sys.exc_info()[0] )
                #print("couldn't open stream")
                #ignore - probably not a content stream. Print an error when debugging
                ignore = 1
