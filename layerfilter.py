# PDFStitcher is a utility to work with PDF sewing patterns.
# Copyright (C) 2021 Charlotte Curtis
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import pikepdf
import pdf_operators as pdf_ops
from decimal import Decimal
import traceback
import copy
# from os import write
# import sys
# import utils
        
STATE_OPS = [k for k,v in pdf_ops.ops.items() if v[0] == 'state']
STROKE_OPS = [k for k,v in pdf_ops.ops.items() if v[0] == 'show' and v[1] == 'stroke'] 
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

class LayerFilter:
    def __init__(
            self,
            doc = None,
            keep_ocs = 'all',
            keep_non_oc = True,
            delete_ocgs = True,
            page_range = [],
            line_props = {},
        ):
        
        self.pdf = doc
        self.keep_ocs = keep_ocs
        self.keep_non_oc = keep_non_oc
        self.delete_ocgs = delete_ocgs
        self.page_range = page_range

        self.line_props = line_props
        self.clean_line_props = {}
        self.colour_type = None
        self.properties = {}
        self.current_layer_name = ''

        # maintain a running list of line state 
        # defaults from PDF reference v1.4
        self.current_state = [{
            'w':  1.0,
            'RG': [0,0,0],
            'K': pdf_ops.rgb_to_cmyk([0,0,0]),
            'd': pdf_ops.line_style_arr[0]
        }]
        self.q_depth = 0

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
        self.off_ocs = []
        
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
        
        parse_streams = False
        if self.keep_ocs != 'all':
            # edit the OCG listing in the root
            On = [oc for oc in output.Root.OCProperties.OCGs if str(oc.Name) in self.keep_ocs]
            Off = [oc for oc in output.Root.OCProperties.OCGs if str(oc.Name) not in self.keep_ocs]

            if self.delete_ocgs:
                parse_streams = True
                for o in Off:
                    self.off_ocs.append(o.Name)
                output.Root.OCProperties.OCGs = On
                output.Root.OCProperties.D.ON = On
                output.Root.OCProperties.D.Order = self.filter_ocg_order(output.Root.OCProperties.D.Order)
            else:
                output.Root.OCProperties.D.ON = On
                output.Root.OCProperties.D.OFF = Off
        
        if self.line_props != {}:
            self.convert_layer_props()
            # TODO: actually detect colour space
            self.colour_type = 'RG' 
            parse_streams = True

        if parse_streams:
            for p in page_range:
                self.get_properties(output.pages[p-1])
                if self.properties:
                    page_stream = self.filter_content(output.pages[p-1])
                    if page_stream:
                        output.pages[p-1].Contents = output.make_stream(page_stream)
                elif not self.keep_non_oc:
                    # no OCGs on the page and we don't want to keep non-optional content
                    output.pages[p-1].Contents = output.make_stream(b'')
                
                progress_update and progress_update(page_range.index(p))
                if progress_was_cancelled and progress_was_cancelled():
                    return None

            progress_update and progress_update(n_page)

        # by default, unlock all layers
        output.Root.OCProperties.D.Locked = []
        output.remove_unreferenced_resources()

        return output

    def get_properties(self, page, properties=None, depth = 0):
        self.properties = {}
        if '/Resources' in page.keys():
            r = page.Resources
            if '/Properties' in r.keys():
                self.properties = r.Properties

    def convert_layer_props(self):
        # convert the line properties from the GUI to what the PDF needs
        self.clean_line_props = {}
        for layer,lp in self.line_props.items():
            w = 1
            clp = {}
            if 'thickness' in lp.keys():
                clp['w'] = [round(Decimal(lp['thickness']),1)]
                w = clp['w'][0]
            
            if 'style' in lp.keys():
                clp['d'] = list(pdf_ops.line_style_arr[lp['style']])
                # list is needed to make sure this is a copy
                # scale the line style
                clp['d'][0] = [d*w for d in clp['d'][0]]

            # assign the colour for both cmyk and rgb
            if 'rgb' in lp.keys():
                clp['RG'] = [round(Decimal(rg),3) for rg in lp['rgb']]
                clp['K'] = [round(Decimal(k),3) for k in pdf_ops.rgb_to_cmyk(lp['rgb'])]
            
            self.clean_line_props[layer] = clp

    def append_layer_properties(self,commands):
        for op,operands in self.clean_line_props[self.current_layer_name].items():
            if self.current_state[-1][op] != operands:
                commands.append([operands,pikepdf.Operator(op)])
                self.current_state[-1][op] = operands
    
    def add_q_state(self):
        self.current_state.append(copy.copy(self.current_state[-1]))
        self.q_depth += 1
    
    def remove_q_state(self):
        self.current_state.pop()
        self.q_depth -= 1
    
    def restore_state(self,commands):
        for op, operands in self.current_state[-1].items():
            commands.append([operands,pikepdf.Operator(op)])

    def filter_stream(self,ob,in_oc):
        previous_operator = ''
        commands = []
        # initialize copying with keep_non_oc
        keeping = self.keep_non_oc or in_oc
        for operands, operator in pikepdf.parse_content_stream(ob):
            op = str(operator)
            if op == "BDC" and len(operands) > 1 and str(operands[0]) == "/OC":
                keeping = True
                oc = str(operands[1])
                if self.properties != None:
                    if oc in self.properties.keys():
                        ocg = self.properties[oc]
                        self.current_layer_name = str(ocg.Name)
                        if ocg.Name in self.off_ocs:
                            keeping = False
                    
            if keeping or op in STATE_OPS:
                if previous_operator == 'q' and op == 'Q':
                    commands.pop()

                if self.current_layer_name in self.clean_line_props:
                    if op == 'gs' or op in STROKE_OPS:
                        self.append_layer_properties(commands)
                    # and check if the current operator is one we need to modify
                    elif op in self.clean_line_props[self.current_layer_name].keys():
                        operands = self.clean_line_props[self.current_layer_name][op]
                
                # no matter what, update the state
                if op in self.current_state[-1].keys():
                    self.current_state[-1][op] = commands[-1][0]
                if op == 'q':
                    self.add_q_state()
                elif op == 'Q':
                    self.remove_q_state()
                
                commands.append([operands,operator])
                previous_operator = op
                
            if str(operator) == 'EMC':
                keeping = self.keep_non_oc or in_oc
                self.current_layer_name = ''
                # self.restore_state(commands)

        return commands
      
    def filter_content(self, ob):
        # skip over anything we have already seen
        if not isinstance(ob, pikepdf.Object):
            return

        obid = ob.unparse()
        if obid in self.found_objects:
            return
        else:
            self.found_objects.add(obid)

        if isinstance(ob, pikepdf.Array):
            for i in range(len(ob)):
                newstream = self.filter_content(ob[i])
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
                    newstream = self.filter_content(ob[o])
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
                            commands = self.filter_stream(ob,in_oc = True)
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

                if stream_has_layers:
                    commands = self.filter_stream(ob,in_oc = False)
                    return pikepdf.unparse_content_stream(commands)
                
                elif not self.keep_non_oc:
                    return b''

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
