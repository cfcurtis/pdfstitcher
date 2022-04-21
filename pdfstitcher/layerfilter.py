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

    def get_layer_names(self):
        """
        reads through the root to parse out the layers present in the file.

        Returns:
            list: a list of layer names, or None if there are no layers
        """
        if '/OCProperties' in self.pdf.Root.keys() and '/OCGs' in self.pdf.Root.OCProperties.keys():
            ocp = self.pdf.Root.OCProperties
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

    def filter_ocg_order(self, ocg_list=None):
        """
        Recursively filters the ocg list to only include those in the keep_ocs list.
        """

        if ocg_list is None:
            ocg_list = self.out_pdf.Root.OCProperties.D.Order
        
        if ocg_list._type_name == 'array':
            to_delete = []
            for i, item in enumerate(ocg_list):
                if self.filter_ocg_order(item):
                    to_delete.append(i)
            
            # delete the items in reverse order so we don't mess up the indices
            for i in reversed(to_delete):
                del ocg_list[i]
            
            return len(ocg_list) == 0

        elif ocg_list._type_name == 'dictionary':
            if '/Type' in ocg_list.keys():
                if ocg_list.Type == pikepdf.Name.OCG and ocg_list.Name not in self.keep_ocs:
                    # found the OCG entry, delete it if it's not in our keep array
                    return True
        
        return False

    def update_ocs(self):
        """
        Updates the OCProperties dictionary to only include the layers we want.
        """
        if self.keep_ocs == 'all':
            return

        # edit the OCG listing in the root
        On = [
            oc
            for oc in self.out_pdf.Root.OCProperties.OCGs
            if str(oc.Name) in self.keep_ocs
        ]
        Off = [
            oc
            for oc in self.out_pdf.Root.OCProperties.OCGs
            if str(oc.Name) not in self.keep_ocs
        ]

        # Delete requires parsing
        if self.delete_ocgs:
            for o in Off:
                self.off_ocs.append(o.Name)
            self.out_pdf.Root.OCProperties.OCGs = On
            self.out_pdf.Root.OCProperties.D.ON = On
            self.filter_ocg_order()
        else:
            # just switch them off
            self.out_pdf.Root.OCProperties.D.ON = On
            self.out_pdf.Root.OCProperties.D.OFF = Off
        
        # by default, unlock all layers
        self.out_pdf.Root.OCProperties.D.Locked = []
    
    def process_page_range(self):
        """
        Convert the page range into a 1-indexed unique set.
        Defaults to all pages if nothing entered.
        """
        if len(self.page_range) == 0:
            return list(range(1, len(self.out_pdf.pages) + 1))
        else:
            # get rid of duplicates and zeros in the page range
            return list(set([p for p in self.page_range if p > 0]))
        

    def run(
        self, set_progress_range=None, update_progress=None, progress_was_cancelled=None
    ):
        """
        The primary method to run the filter.
        If called from pdfstitcher.py, the progress window will be updated.
        Returns:
            pikepdf.Pdf: the filtered PDF
        """
        self.processed_objects = set()

        if '/OCProperties' not in self.pdf.Root.keys():
            return self.pdf

        if self.keep_ocs == 'all' and len(self.line_props) == 0:
            return self.pdf

        if len(self.keep_ocs) == 0 and self.keep_non_oc == False:
            print(_('No layers selected, generated PDF would be blank.'))
            return self.pdf

        self.off_ocs = []

        # open a new copy of the input
        self.out_pdf = pikepdf.Pdf.open(self.pdf.filename)
        page_range = self.process_page_range()
        n_page = len(page_range)

        # initialize the progress window
        set_progress_range and set_progress_range(n_page)  # don't run if the callback is None

        # update the OC dictionaries
        self.update_ocs()
        parse_streams = self.delete_ocgs and self.keep_ocs != 'all'

        # TODO: actually detect colour space
        self.colour_type = 'RG'
        if self.line_props != {}:
            self.convert_layer_props()
            parse_streams = True

        # Either deleting content or modifying line properties requires parsing streams
        if parse_streams:
            for p in page_range:
                self.filter_content(self.out_pdf.pages[p - 1])
                # update the progress bar for each page, then check if user cancelled
                update_progress and update_progress(page_range.index(p))
                if progress_was_cancelled and progress_was_cancelled():
                    return None

        # done, update progress and strip out unused stuff
        update_progress and update_progress(n_page)
        self.out_pdf.remove_unreferenced_resources()
        return self.out_pdf

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
        """
        Filters the stream itself (page or form)

        Args:
            ob (Pikepdf object): The object to filter
            page_props (pikepdf dictionary): object property dictionary
            oc_forms (_type_): _description_
            in_oc (_type_): _description_

        Returns:
            _type_: _description_
        """
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
        """
        Perform the actual filtering of a page.

        Args:
            page (_type_): pdf page object
            in_oc (bool, optional): True if we're currently "in" an optional content block. Defaults to False.

        Returns:
            bstr: The filtered page stream
        """
        # First check the id of the page and don't re-filter if we've seen it before
        obid = page.unparse()
        if obid in self.processed_objects:
            return
        else:
            self.processed_objects.add(obid)

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
            self.filter_content(ob)

        if not in_oc and not page_props and not oc_forms:
            return

        if oc_forms is None:
            do_filter = False
            for operands, _ in pikepdf.parse_content_stream(page, "BDC"):
                if len(operands) > 1 and str(operands[0]) == "/OC":
                    do_filter = True
                    break
        else:
            do_filter = True
            
        # initialize empty stream, then try to filter
        page_stream = None
        if do_filter:
            commands, placed_forms = self.filter_stream(
                page, page_props, oc_forms, in_oc
            )
            if commands:
                page_stream = pikepdf.unparse_content_stream(commands)
        # if we're not filtering and not keeping non-optional content, obliterate the stream
        elif not self.keep_non_oc:
            page.write(b'')

        # loop through the form xobjects and delete or filter as needed
        if '/XObject' in page.Resources:
            for key, ob in page.Resources.XObject.items():
                if key in placed_forms.keys():
                    if '/Subtype' in ob.keys() and ob.Subtype == '/Form':
                        self.current_layer_name = placed_forms[key]['layer']
                        saved_state = copy.copy(self.current_state)
                        self.current_state = placed_forms[key]['state']
                        self.filter_content(ob, in_oc=True)
                        self.current_state = saved_state
                        self.current_layer_name = ''
                    elif '/Subtype' in ob.keys() and ob.Subtype == '/PS':
                        print('Postscript XObject detected, not currently handled.')
                else:
                    del page.Resources.XObject[key]

        # finally, write the stream
        if page_stream is not None:
            if isinstance(page, pikepdf.Page):
                page.Contents = self.out_pdf.make_stream(page_stream)
            else:
                page.write(page_stream)