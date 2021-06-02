# PDFStitcher is a utility to work with PDF sewing patterns.
# Copyright (C) 2021 Charlotte Curtis
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from os import write
import pikepdf
import pdf_operators as pdf_ops
from decimal import Decimal
import utils 
import sys
import traceback
import copy
        
STATE_OPS = [k for k,v in pdf_ops.ops.items() if v[0] == 'state']
SKIP_TYPES = ['/Font','/ExtGState']
SKIP_KEYS = ['/Parent','/Thumb']

# helper functions to dump page to file for debugging
def write_page(fname,page):
    with open(fname,'w') as f:
        if isinstance(page.Contents,pikepdf.Array):
            for s in page.Contents:
                stream = s.read_bytes()
                f.write(stream.decode())
        elif isinstance(page.Contents,pikepdf.Stream):
            stream = page.Contents.read_bytes()
            f.write(stream.decode())

class LayerFilter():
    def __init__(self,doc = None):
        self.pdf = doc
        self.keep_ocs = 'all'
        self.keep_non_oc = True
        self.delete_ocgs = True
        self.page_range = []

        self.line_props = {}
        self.clean_line_props = {}
        self.colour_type = None
        self.properties = {}

        # keep state of lines in streams we are keeping in if we are in a ocg. For some reason some pdfs have ocgs across streams
        self.keeping = True 
        self.in_oc = False
        self.current_layer_name = ''



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
                if self.properties:
                    page_stream = self.remove_ocgs_from_stream(output.pages[p-1])
                    if page_stream:
                        output.pages[p-1].Contents = output.make_stream(page_stream)
                
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

    def get_properties(self, page, properties=None, depth = 0):
        self.properties = {}
        if '/Resources' in page.keys():
            r = page.Resources
            if '/Properties' in r.keys():
                self.properties = r.Properties

    def clean_line_options(self):
        for l in self.line_props:
            w = 1
            lp = copy.copy(self.line_props[l])
            if 'thickness' in lp.keys():
                w = round(Decimal(lp['thickness']), 1)
                lp['thickness'] = [w]
            if 'rgb' in lp.keys():
                lp['cmyk'] = [round(Decimal(k),3) for k in pdf_ops.rgb_to_cmyk(lp['rgb'])]
                lp['rgb'] = [round(Decimal(rg), 3) for rg in lp['rgb']]
            if 'style' in lp.keys():
                lp['style'] = list(pdf_ops.line_style_arr[lp['style']])
                # list is needed to make sure this is a copy
                # scale the line style
                lp['style'][0] = [d*w for d in lp['style'][0]]
            
            self.clean_line_props[l] = lp


    def append_layer_property(self, prop, commands):
        if prop == 'rgb':
            op = 'RG'
        elif prop == 'cmyk':
            op = 'K'
        elif prop == 'thickness':
            op = 'w'
        else:
            op = 'd'
        if self.current_layer_name in self.clean_line_props.keys():
            lp = self.clean_line_props[self.current_layer_name]
            if prop in lp.keys():
                commands.append([lp[prop], op])

    def append_layer_properties(self, commands):
        self.append_layer_property('rgb', commands)
        self.append_layer_property('thickness', commands)
        self.append_layer_property('style', commands)
      
    def remove_ocgs_from_stream(self, ob):
        # skip over anything we have already seen
        if not isinstance(ob, pikepdf.Object):
            return

        obid = ob.unparse()
        if obid in self.found_objects:
            return
        else:
            self.found_objects.add(obid)

        color_stroke_ops = ['CS', 'RG', 'SC', 'SCN', 'K']

        if isinstance(ob, pikepdf.Array):
            for i in range(len(ob)):
                newstream = self.remove_ocgs_from_stream(ob[i])
                if newstream:
                    ob[i].write(newstream)

        is_page = False
        if isinstance(ob, pikepdf.Dictionary):
            if '/Type' in ob.keys():
                ob_type = str(ob.Type)
                if ob_type == '/Page':
                    is_page = True
                
                elif ob_type in SKIP_TYPES:
                    return None
            
            for o in ob.keys():
                if o not in SKIP_KEYS and not (is_page and o == '/Contents'):
                    newstream = self.remove_ocgs_from_stream(ob[o])
                    if newstream:
                        ob[0].write(newstream)

        if isinstance(ob, pikepdf.Stream) or is_page:
            if '/Subtype' in ob.keys():
                if ob.Subtype == '/Image':
                    return None
            
            if '/Filter' in ob.keys():
                #don't parse jpeg-type streams
                if ob.Filter == '/DCTDecode':
                    return None

            commands = []
            # the whole stream is a layer
            if '/OC' in ob.keys():
                if '/Name' in ob.OC.keys():
                    self.current_layer_name = str(ob.OC.Name)
                    if self.current_layer_name in self.off_ocs:
                        return b''
                    else:
                        try:
                            for operands, operator in pikepdf.parse_content_stream(ob):
                                self.append_layer_properties(commands)
                                commands.append([operands, operator])
                                op = str(operator)
                                if op in ['Q', 'gs']:
                                    self.append_layer_properties(commands)
                                elif op == 'd':
                                    self.append_layer_property('style', commands)
                                elif op in color_stroke_ops:
                                    commands.pop()
                                    if op == 'K':
                                        self.append_layer_property('cmyk', commands)
                                    else:
                                        self.append_layer_property('rgb', commands)
                                elif op == 'w': # and operands[0] != 0:
                                    self.append_layer_property('thickness', commands)
                            return pikepdf.unparse_content_stream(commands)

                        except:
                            #traceback.print_exc()
                            #print("couldn't open stream ", sys.exc_info()[0] )
                            #print("couldn't open stream")
                            #ignore - probably not a content stream. Print an error when debugging
                            ignore = 1
                            return None


            # the layers may be in the stream
            try:

                stream_has_layers = False
                for operands, operator in pikepdf.parse_content_stream(ob, "BDC"):
                    if len(operands) > 1 and str(operands[0]) == "/OC":
                        stream_has_layers = True
                        break

                if stream_has_layers or self.in_oc:
                    previous_operator = ''
                    for operands, operator in pikepdf.parse_content_stream(ob):
                        op = str(operator)
                        if op == "BDC" and len(operands) > 1 and str(operands[0]) == "/OC":
                            
                            self.in_oc = True
                            self.keeping = True
                            oc = str(operands[1])
                            if self.properties != None:
                                if oc in self.properties.keys():
                                    ocg = self.properties[oc]
                                    self.current_layer_name = str(ocg.Name)
                                    if ocg.Name in self.off_ocs:
                                        self.keeping = False
                                    else:
                                        self.append_layer_properties(commands)
                            #print([oc, self.current_layer_name, self.keeping])
                                
                        if self.keeping or not self.in_oc or op in STATE_OPS:
                            if previous_operator == 'q' and op == 'Q':
                                commands.pop()
                            else:
                                commands.append([operands, operator])
                            if self.in_oc and self.keeping:
                                # turn into a switch statement when python starts supporting them - 3.10?
                                if op in ['Q', 'gs']:
                                    self.append_layer_properties(commands)
                                elif op == 'd':
                                    self.append_layer_property('style', commands)
                                elif op in color_stroke_ops:
                                    self.append_layer_property('rgb', commands)
                                elif op == 'w': # and operands[0] != 0:
                                    self.append_layer_property('thickness', commands)
                            previous_operator = operator
                            #if(in_oc):
                            #print(f"Op {operator}, operands {operands}")
                        if str(operator) == 'EMC':
                            #print(["EMC", self.keeping])
                            self.in_oc = False
                            self.current_layer_name = ''


                    return pikepdf.unparse_content_stream(commands)

            except AttributeError:
                traceback.print_exc()
                ignore = 1
            except ValueError:
                traceback.print_exc()
                ignore = 1
            except NameError:
                traceback.print_exc()
                ignore = 1
            except:
                traceback.print_exc()
                #print("couldn't open stream ", sys.exc_info()[0] )
                print("couldn't open stream")
                #ignore - probably not a content stream. Print an error when debugging
                # ignore = 1
