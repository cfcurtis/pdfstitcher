# PDFStitcher is a utility to work with PDF sewing patterns.
# Copyright (C) 2021 Charlotte Curtis
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import pikepdf
import pdfstitcher.pdf_operators as pdf_ops
from decimal import Decimal
import traceback
import copy

# from os import write
# import sys
# import utils

STATE_OPS = [k for k, v in pdf_ops.ops.items() if v[0] == 'state']
STATE_OPS += [
    k for k, v in pdf_ops.ops.items() if v[0] in ['begin', 'end'] and v[1] != 'image'
]
STROKE_OPS = [k for k, v in pdf_ops.ops.items() if v[0] == 'show' and v[1] == 'stroke']
SKIP_TYPES = ['/Font', '/ExtGState']
SKIP_KEYS = ['/Parent', '/Thumb', '/PieceInfo']
DEBUG = False

# helper functions to dump page to file for debugging
def write_page(fname, page):
    with open(fname, 'w') as f:
        commands = pikepdf.parse_content_stream(page)
        f.write(pikepdf.unparse_content_stream(commands).decode('pdfdoc'))


class LayerFilter:
    def __init__(
        self,
        pdf=None,
        keep_ocs='all',
        keep_non_oc=True,
        delete_ocgs=True,
        page_range=[],
        line_props={},
    ):

        self.pdf = pdf
        self.keep_ocs = keep_ocs
        self.keep_non_oc = keep_non_oc
        self.delete_ocgs = delete_ocgs
        self.page_range = page_range

        self.line_props = line_props
        self.clean_line_props = {}
        self.colour_type = None
        self.current_layer_name = ''

        self.initialize_state()

    @staticmethod
    def _fix_utf16(string):
        new_string = string.replace('\x00', '')
        if new_string.startswith('ÿþ'):
            new_string = new_string[2:]
        return new_string

    @staticmethod
    def _search_names(ordered_names, name_object, depth=0):
        if depth > 1:
            return
        for o in name_object:
            if '/Name' in o.keys():
                name = LayerFilter._fix_utf16(str(o.Name))
                if name not in ordered_names:
                    ordered_names.append(name)
            else:
                LayerFilter._search_names(ordered_names, o, depth=depth + 1)

    @staticmethod
    def get_layer_names(doc):
        """
        reads through the root to parse out the layers present in the file.
        
        Args:
            doc (pikepdf.Document): the document to parse
        
        Returns:
            list: a list of layer names, or None if there are no layers
        """
        if '/OCProperties' in doc.Root.keys() and '/OCGs' in doc.Root.OCProperties.keys():
            ocp = doc.Root.OCProperties
        else:
            return None
            
        names = [str(oc.Name) for oc in ocp.OCGs]
        ordered_names = []
        if '/D' in ocp.keys() and '/Order' in ocp.D.keys():
            LayerFilter._search_names(ordered_names, ocp.D.Order)
        for n in names:
            real_n = LayerFilter._fix_utf16(n)
            if real_n not in ordered_names:
                ordered_names.append(real_n)
        return ordered_names

    def filter_ocg_order(self, input):
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

    def run(
        self, progress_range=None, progress_update=None, progress_was_cancelled=None
    ):
        self.found_objects = set()

        if '/OCProperties' not in self.pdf.Root.keys():
            return self.pdf

        if self.keep_ocs == 'all' and len(self.line_props) == 0:
            return self.pdf

        if self.keep_ocs is None and self.keep_non_oc == False:
            print(_('No layers selected, generated PDF would be blank.'))
            return self.pdf

        self.off_ocs = []

        # open a new copy of the input
        output = pikepdf.Pdf.open(self.pdf.filename)
        self.colour_type = None

        if len(self.page_range) == 0:
            # human input page range is 1-indexed
            page_range = range(1, len(output.pages) + 1)
        else:
            # get rid of duplicates and zeros in the page range
            page_range = list(set([p for p in self.page_range if p > 0]))

        n_page = len(page_range)
        progress_range and progress_range(n_page)  # don't run if the callback is None

        parse_streams = False
        if self.keep_ocs != 'all':
            # edit the OCG listing in the root
            On = [
                oc
                for oc in output.Root.OCProperties.OCGs
                if str(oc.Name) in self.keep_ocs
            ]
            Off = [
                oc
                for oc in output.Root.OCProperties.OCGs
                if str(oc.Name) not in self.keep_ocs
            ]

            if self.delete_ocgs:
                parse_streams = True
                for o in Off:
                    self.off_ocs.append(o.Name)
                output.Root.OCProperties.OCGs = On
                output.Root.OCProperties.D.ON = On
                output.Root.OCProperties.D.Order = self.filter_ocg_order(
                    output.Root.OCProperties.D.Order
                )
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
                page_stream = self.filter_content(output.pages[p - 1])
                if page_stream is not None:
                    output.pages[p - 1].Contents = output.make_stream(page_stream)

                progress_update and progress_update(page_range.index(p))
                if progress_was_cancelled and progress_was_cancelled():
                    return None

        progress_update and progress_update(n_page)

        # by default, unlock all layers
        output.Root.OCProperties.D.Locked = []
        output.remove_unreferenced_resources()

        return output

    def convert_layer_props(self):
        # convert the line properties from the GUI to what the PDF needs
        self.clean_line_props = {}
        for layer, lp in self.line_props.items():
            w = 1
            clp = {}
            if 'thickness' in lp.keys():
                clp['w'] = [round(Decimal(lp['thickness']), 1)]
                w = clp['w'][0]

            if 'style' in lp.keys():
                clp['d'] = list(pdf_ops.line_style_arr[lp['style']])
                # list is needed to make sure this is a copy
                # scale the line style
                clp['d'][0] = [d * w for d in clp['d'][0]]

            # assign the colour for both cmyk and rgb
            if 'rgb' in lp.keys():
                clp['RG'] = [round(Decimal(rg), 3) for rg in lp['rgb']]
                clp['K'] = [
                    round(Decimal(k), 3) for k in pdf_ops.rgb_to_cmyk(lp['rgb'])
                ]
                clp['rg'] = clp['RG']
                clp['k'] = clp['K']

            self.clean_line_props[layer] = clp

    def append_layer_properties(self, commands):
        for op, operands in self.clean_line_props[self.current_layer_name].items():
            if self.current_state[-1][op] != operands:
                commands.append((operands, pikepdf.Operator(op)))
                self.current_state[-1][op] = operands

    def initialize_state(self):
        # maintain a running list of line state
        # defaults from PDF reference v1.4
        self.current_state = [
            {
                'w': [1.0],
                'RG': [0, 0, 0],
                'rg': [0, 0, 0],
                'K': pdf_ops.rgb_to_cmyk([0, 0, 0]),
                'k': pdf_ops.rgb_to_cmyk([0, 0, 0]),
                'd': pdf_ops.line_style_arr[0],
            }
        ]

    def add_q_state(self):
        self.current_state.append(copy.copy(self.current_state[-1]))

    def remove_q_state(self):
        self.current_state.pop()
        if not self.current_state:
            self.initialize_state()

    def restore_state(self, commands):
        self.remove_q_state()
        for op, operands in self.current_state[-1].items():
            commands.append((operands, pikepdf.Operator(op)))

    def filter_stream(self, ob, page_props, oc_forms, in_oc):
        previous_operator = ''
        commands = []
        placed_forms = {}
        # initialize copying with keep_non_oc
        keeping = self.keep_non_oc or in_oc
        for operands, operator in pikepdf.parse_content_stream(ob):
            op = str(operator)
            if op == "BDC" and len(operands) > 1 and str(operands[0]) == "/OC":
                keeping = True
                oc = str(operands[1])
                if page_props is not None:
                    if oc in page_props.keys():
                        ocg = page_props[oc]
                        self.current_layer_name = str(ocg.Name)
                        if ocg.Name in self.off_ocs:
                            keeping = False

            if op == 'Do':
                # Special case where we need to place a form even if it's not defined
                # with the standard /OC BDC block
                ob_name = str(operands[0])
                if ob_name in oc_forms.keys() and not oc_forms[ob_name]['keep']:
                    continue

                if ob_name in oc_forms.keys() and oc_forms[ob_name]['keep']:
                    placed_forms[ob_name] = {
                        'layer': oc_forms[ob_name]['layer'],
                        'state': copy.copy(self.current_state),
                    }
                    commands.append((operands, operator))
                    previous_operator = op
                    continue

                elif keeping:
                    placed_forms[ob_name] = {
                        'layer': self.current_layer_name,
                        'state': copy.copy(self.current_state),
                    }

            if keeping or op in STATE_OPS:
                if previous_operator == 'q' and op == 'Q':
                    commands.pop()
                    self.remove_q_state()
                else:
                    if self.current_layer_name in self.clean_line_props:
                        if op == 'gs' or op in STROKE_OPS:
                            self.append_layer_properties(commands)
                        # and check if the current operator is one we need to modify
                        elif (
                            op in self.clean_line_props[self.current_layer_name].keys()
                        ):
                            operands = self.clean_line_props[self.current_layer_name][
                                op
                            ]

                    # no matter what, update the state
                    if op in self.current_state[-1].keys():
                        self.current_state[-1][op] = operands
                    if op == 'q':
                        self.add_q_state()
                    elif op == 'Q':
                        self.remove_q_state()

                    commands.append((operands, operator))
                    previous_operator = op

            if op == 'EMC':
                keeping = self.keep_non_oc or in_oc
                self.current_layer_name = ''
                self.restore_state(commands)

        return commands, placed_forms

    def filter_content(self, page, in_oc=False):
        obid = page.unparse()
        if obid in self.found_objects:
            return
        else:
            self.found_objects.add(obid)

        self.initialize_state()
        page_props = {}
        oc_forms = {}
        placed_forms = {}
        other_forms = []
        if '/Resources' in page.keys():
            r = page.Resources
            if '/Properties' in r.keys():
                page_props = r.Properties
            elif '/XObject' in r.keys():
                for key, ob in r.XObject.items():
                    if '/Subtype' in ob.keys() and ob.Subtype == '/Form':
                        if '/OC' in ob.keys():
                            oc_name = str(ob.OC.Name)
                            oc_forms[key] = {
                                'layer': oc_name,
                                'keep': oc_name not in self.off_ocs,
                            }
                        else:
                            other_forms.append(ob)

        # try going through the list of other forms and processing those.
        # Useful for the situation where someone is re-running PDFStitcher.
        for ob in other_forms:
            form_stream = self.filter_content(ob)
            if form_stream is not None:
                ob.write(form_stream)

        if not in_oc and not page_props and not oc_forms:
            return None

        try:
            if oc_forms is None:
                do_filter = False
                for operands, _ in pikepdf.parse_content_stream(page, "BDC"):
                    if len(operands) > 1 and str(operands[0]) == "/OC":
                        do_filter = True
                        break
            else:
                do_filter = True

            if do_filter:
                commands, placed_forms = self.filter_stream(
                    page, page_props, oc_forms, in_oc
                )
                if commands:
                    page_stream = pikepdf.unparse_content_stream(commands)
            elif not self.keep_non_oc:
                page_stream = b''

            # loop through the form xobjects and delete or filter as needed
            if '/XObject' in page.Resources:
                for key, ob in page.Resources.XObject.items():
                    if key in placed_forms.keys():
                        if '/Subtype' in ob.keys() and ob.Subtype == '/Form':
                            self.current_layer_name = placed_forms[key]['layer']
                            saved_state = copy.copy(self.current_state)
                            self.current_state = placed_forms[key]['state']
                            form_stream = self.filter_content(ob, in_oc=True)
                            if form_stream is not None:
                                ob.write(form_stream)
                            self.current_state = saved_state
                            self.current_layer_name = ''
                        elif '/Subtype' in ob.keys() and ob.Subtype == '/PS':
                            print('Postscript XObject detected, not currently handled.')
                    else:
                        del page.Resources.XObject[key]

            return page_stream

        except AttributeError:
            traceback.print_exc()
            ignore = 1
        except ValueError:
            traceback.print_exc()
            ignore = 1
        except NameError:
            traceback.print_exc()
            ignore = 1
        except Exception:
            traceback.print_exc()
            # print("couldn't open stream ", sys.exc_info()[0] )
            print("couldn't open stream")
            # ignore - probably not a content stream. Print an error when debugging
            # ignore = 1
