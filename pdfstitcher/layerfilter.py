# PDFStitcher is a utility to work with PDF sewing patterns.
# Copyright (C) 2021 Charlotte Curtis
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import pikepdf
import pdfstitcher.pdf_operators as pdf_ops
from decimal import Decimal
import copy

STATE_OPS = [k for k, v in pdf_ops.ops.items() if v[0] == "state"]
STATE_OPS += [k for k, v in pdf_ops.ops.items() if v[0] in ["begin", "end"] and v[1] != "image"]
STROKE_OPS = [k for k, v in pdf_ops.ops.items() if v[0] == "show" and v[1] == "stroke"]
SKIP_TYPES = ["/Font", "/ExtGState"]
SKIP_KEYS = ["/Parent", "/Thumb", "/PieceInfo"]

DEFAULT_STATE = {
    # PDF defaults from v1.7 reference.
    "w": [1.0],
    "RG": [0, 0, 0],
    "rg": [0, 0, 0],
    "K": pdf_ops.rgb_to_cmyk([0, 0, 0]),
    "k": pdf_ops.rgb_to_cmyk([0, 0, 0]),
    "d": pdf_ops.line_style_arr[0],
}


# helper functions to dump page to file for debugging
def write_page(fname, page):
    with open(fname, "w") as f:
        commands = pikepdf.parse_content_stream(page)
        f.write(pikepdf.unparse_content_stream(commands).decode("pdfdoc"))


class LayerFilter:
    def __init__(
        self,
        pdf=None,
        keep_ocs="all",
        keep_non_oc=True,
        delete_ocgs=True,
        page_range=[],
        line_props={},
    ):
        self.pdf = pdf
        self.keep_ocs = keep_ocs
        self.keep_non_oc = keep_non_oc
        self.delete_ocgs = delete_ocgs
        self.objs_to_delete = []
        self.page_range = page_range

        self.line_props = line_props
        self.pdf_line_props = {}

    @staticmethod
    def _fix_utf16(string):
        new_string = string.replace("\x00", "")
        if new_string.startswith("ÿþ"):
            new_string = new_string[2:]
        return new_string

    @staticmethod
    def _search_names(ordered_names, name_object, depth=0):
        if depth > 1:
            return
        for o in name_object:
            if "/Name" in o.keys():
                name = LayerFilter._fix_utf16(str(o.Name))
                if name not in ordered_names:
                    ordered_names.append(name)
            else:
                LayerFilter._search_names(ordered_names, o, depth=depth + 1)

    @staticmethod
    def _get_page_forms(page):
        """
        Returns a list of forms on the page.
        """
        page_forms = []
        if "/Resources" not in page.keys():
            return None

        if "/XObject" not in page.Resources.keys():
            return None

        for ob in page.Resources.XObject.values():
            if "/Subtype" in ob.keys() and ob.Subtype == "/Form":
                page_forms.append(ob)

        return page_forms

    @staticmethod
    def _is_transparency_group(obj):
        """
        Returns true if the object is a transparency group.
        """
        if "/Group" in obj.keys():
            if obj.Group.S == "/Transparency":
                return True
        return False

    def get_layer_names(self):
        """
        reads through the root to parse out the layers present in the file.

        Returns:
            list: a list of layer names, or None if there are no layers
        """
        if "/OCProperties" in self.pdf.Root.keys() and "/OCGs" in self.pdf.Root.OCProperties.keys():
            ocp = self.pdf.Root.OCProperties
        else:
            return None

        names = [str(oc.Name) for oc in ocp.OCGs]
        ordered_names = []
        if "/D" in ocp.keys() and "/Order" in ocp.D.keys():
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

        if ocg_list._type_name == "array":
            to_delete = []
            for i, item in enumerate(ocg_list):
                if self.filter_ocg_order(item):
                    to_delete.append(i)

            # delete the items in reverse order so we don't mess up the indices
            for i in reversed(to_delete):
                del ocg_list[i]

            return len(ocg_list) == 0

        elif ocg_list._type_name == "dictionary":
            if "/Type" in ocg_list.keys():
                if ocg_list.Type == pikepdf.Name.OCG and ocg_list.Name not in self.keep_ocs:
                    # found the OCG entry, delete it if it's not in our keep array
                    return True

        return False

    def update_ocs(self):
        """
        Updates the OCProperties dictionary to only include the layers we want.
        """
        # If the list was 'all', modify so it includes all the layers
        if self.keep_ocs == "all":
            self.keep_ocs = self.get_layer_names()
            return

        # edit the OCG listing in the root
        On = [oc for oc in self.out_pdf.Root.OCProperties.OCGs if str(oc.Name) in self.keep_ocs]
        Off = [
            oc for oc in self.out_pdf.Root.OCProperties.OCGs if str(oc.Name) not in self.keep_ocs
        ]

        # Delete requires parsing
        if self.delete_ocgs:
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
        # This is different from the page range processing in tile_pages!
        if len(self.page_range) == 0:
            return list(range(1, len(self.out_pdf.pages) + 1))
        else:
            # get rid of duplicates and zeros in the page range
            return list(set([p for p in self.page_range if p > 0]))

    def convert_layer_props(self):
        """
        convert the line properties from the GUI to what the PDF needs
        """
        self.pdf_line_props = {}
        for layer, lp in self.line_props.items():
            w = 1
            clp = {}
            if "thickness" in lp.keys():
                clp["w"] = [Decimal(lp["thickness"])]
                w = clp["w"][0]

            if "style" in lp.keys():
                clp["d"] = list(pdf_ops.line_style_arr[lp["style"]])
                # list is needed to make sure this is a copy
                # scale the line style
                clp["d"][0] = [d * w for d in clp["d"][0]]

            # assign the colour for both cmyk and rgb
            if "rgb" in lp.keys():
                clp["RG"] = [Decimal(rg) for rg in lp["rgb"]]
                clp["K"] = [Decimal(k) for k in pdf_ops.rgb_to_cmyk(lp["rgb"])]
                # Modify the nonstroking colour if fill_colour is checked
                if lp["fill_colour"]:
                    clp["rg"] = clp["RG"]
                    clp["k"] = clp["K"]

            self.pdf_line_props[layer] = clp

    def override_state(self, commands, line_props, transparency=False):
        """
        Checks to see if the current state matches the desired line properties.
        If not, writes the state to the commands list and updates current state.
        """
        for op, operands in line_props.items():
            if transparency and op in ("rg", "k"):
                # transparency messes up fill colour modification
                continue
            if list(self.current_state[-1][op]) != operands:
                commands.append((operands, pikepdf.Operator(op)))
                self.current_state[-1][op] = operands

    def initialize_state(self, state=DEFAULT_STATE):
        """
        Initializes the list of relevant states.
        """
        self.current_state = [state]

    def add_q_state(self):
        """
        Create a copy of the current state and add to the list.
        """
        self.current_state.append(copy.copy(self.current_state[-1]))

    def remove_q_state(self):
        """
        Pop the last state off the list.
        """
        self.current_state.pop()

    def reset_to_previous_state(self, commands):
        """
        Reset the state to the previous state without a Q operation.
        Writes any differences to the commands list.
        """
        if len(self.current_state) > 1:
            prev_state = copy.copy(self.current_state[-2])
            for op, operands in prev_state.items():
                if list(self.current_state[-1][op]) != list(operands):
                    self.current_state[-1][op] = operands
                    commands.append((operands, pikepdf.Operator(op)))

    def get_oc_list(self, xobj):
        """
        Returns the list of OC names for the given XObject.
        """
        if "/OC" in xobj.keys() and "/Name" in xobj.OC.keys():
            return [str(xobj.OC.Name)]

        if "/Type" in xobj.keys() and xobj.Type == "/OCMD":
            return [str(ocg.Name) for ocg in xobj.OCGs]

    def get_priority_oc(self, oc_list):
        """
        In cases where there are multiple OCGs, return the first one with line
        property mods. Otherwise, return the first keeper, then empty.
        """
        f_list = [oc for oc in oc_list if oc in self.keep_ocs]
        if len(f_list) > 0:
            for oc in f_list:
                if oc in self.line_props.keys():
                    return oc
            return f_list[0]
        else:
            return ""

    def get_valid_obs(self, page):
        """
        Loops through the XOBjects on the given page.
        Checks if each is defined as an OC type.
        If so, checks if the name or membership dictionary is in the keep list.
        """
        oc_obs = {}
        other_obs = {}
        if "/Resources" in page.keys() and "/XObject" in page.Resources.keys():
            page_xobjs = page.Resources.XObject
        else:
            return oc_obs, other_obs

        for key, xobj in page_xobjs.items():
            oc_names = self.get_oc_list(xobj)
            if oc_names is None:
                other_obs[key] = xobj
            elif any(name in self.keep_ocs for name in oc_names):
                oc_obs[key] = xobj

        return oc_obs, other_obs

    def run(self, progress_win=None):
        """
        The primary method to run the filter.
        If called from PDFStitcher gui, the progress window will be updated.
        Returns:
            pikepdf.Pdf: the filtered PDF
        """
        self.processed_objects = set()

        if "/OCProperties" not in self.pdf.Root.keys():
            return self.pdf

        if self.keep_ocs == "all" and len(self.line_props) == 0:
            return self.pdf

        if len(self.keep_ocs) == 0 and self.keep_non_oc == False:
            print(_("No layers selected, generated PDF would be blank."))
            return self.pdf

        # open a new copy of the input
        self.out_pdf = pikepdf.Pdf.open(self.pdf.filename)
        page_range = self.process_page_range()
        n_page = len(page_range)

        # initialize the progress window
        progress_win and progress_win.SetRange(n_page)  # don't run if the callback is None

        # update the OC dictionaries
        parse_streams = self.delete_ocgs and self.keep_ocs != "all"
        # update_ocs modifies the keep_ocs list if it was previously 'all'!
        self.update_ocs()

        if self.line_props != {}:
            self.convert_layer_props()
            parse_streams = True

        # Either deleting content or modifying line properties requires parsing streams
        if parse_streams:
            for p in page_range:
                # reset the state before each page
                self.initialize_state()
                self.filter_content(self.out_pdf.pages[p - 1])
                # update the progress bar for each page, then check if user cancelled
                progress_win and progress_win.Update(page_range.index(p))
                if progress_win and progress_win.WasCancelled():
                    return None

        # done, update progress and strip out unused stuff
        progress_win and progress_win.Update(n_page)
        self.out_pdf.remove_unreferenced_resources()
        return self.out_pdf

    def filter_stream(self, ob, current_layer_name=""):
        """
        Filters the stream itself (page or form)

        Args:
            ob (Pikepdf object): The object to filter
            current_layer_name (str): The name of the optional content group
                currently "in" (only for forms)

        Returns:
            tuple: the new commands and a dictionary of placed forms
        """
        op = ""
        commands = []
        placed_forms = {}
        oc_obs, other_obs = self.get_valid_obs(ob)
        # if the current object (page or form) is defined with transparency,
        # things go wonky when we try to override the fill colour, so don't
        transparency = self._is_transparency_group(ob)
        # initialize copying with keep_non_oc
        keeping = self.keep_non_oc or current_layer_name in self.keep_ocs
        mc_list = []

        if "/Resources" in ob.keys() and "/Properties" in ob.Resources.keys():
            page_props = ob.Resources.Properties
        else:
            page_props = None

        for operands, operator in pikepdf.parse_content_stream(ob):
            previous_operator = op
            op = str(operator)

            # if there's an empty q/Q, just pop the state and last command
            if previous_operator == "q" and op == "Q":
                commands.pop()
                self.remove_q_state()
                continue

            if op == "Do":
                # check if the object to be placed is defined as optional content,
                # and if so, is it content we want to keep
                ob_name = str(operands[0])
                if ob_name in oc_obs.keys():
                    placed_forms[ob_name] = {
                        "state": copy.copy(self.current_state[-1]),
                        "xobj": oc_obs[ob_name],
                        "current_layer_name": self.get_priority_oc(
                            self.get_oc_list(oc_obs[ob_name])
                        ),
                    }
                elif keeping and ob_name in other_obs.keys():
                    # place any object that's not oc
                    placed_forms[ob_name] = {
                        "state": copy.copy(self.current_state[-1]),
                        "xobj": other_obs[ob_name],
                        "current_layer_name": current_layer_name,
                    }
                else:
                    # don't execute the Do command if it's not optional content
                    # and we're not in a keeping mood
                    continue

            if keeping and current_layer_name in self.pdf_line_props:
                if op == "gs" or op in STROKE_OPS:
                    # check to see if the state needs to be modified before drawing
                    self.override_state(
                        commands, self.pdf_line_props[current_layer_name], transparency
                    )
                elif op in self.pdf_line_props[current_layer_name].keys():
                    # and check if the current operator is one we need to modify
                    operands = self.pdf_line_props[current_layer_name][op]

            if keeping or op in STATE_OPS or op == "Do":
                # if we're keeping this command, write it out
                commands.append((operands, operator))

                # and update the state
                if op in self.current_state[-1].keys():
                    self.current_state[-1][op] = operands

                # check for q/Q
                if op == "q":
                    self.add_q_state()
                elif op == "Q":
                    self.remove_q_state()

            if op == "BDC" or op == "BMC":
                # add to the marked content list and indicate whether it's an OC block
                if len(operands) > 1 and str(operands[0]) == "/OC":
                    # we're entering a new layer (optional content group)
                    oc_label = str(operands[1])
                    if page_props is not None and oc_label in page_props.keys():
                        ocg = page_props[oc_label]
                        current_layer_name = str(ocg.Name)
                        keeping = current_layer_name in self.keep_ocs

                    mc_list.append(True)
                else:
                    # not an OC block, but still need to add to the marked content list
                    mc_list.append(False)

            if op == "EMC":
                # pop the marked content list
                is_oc_end = mc_list.pop()
                if is_oc_end:
                    # end of a BDC/EMC block, reset the state
                    self.reset_to_previous_state(commands)
                    keeping = self.keep_non_oc
                    current_layer_name = ""

        return commands, placed_forms

    def filter_content(self, page, current_layer_name="", do_filter=False):
        """
        Perform the actual filtering of a page.

        Args:
            page (pikepdf Page): pdf page object, or form xobject
            current_layer_name (str): The name of the optional content group
                currently "in" (only for forms)
            do_filter (bool): Whether to actually filter the page, can be overridden

        """
        # First check the id of the page and don't re-filter if we've seen it before
        obid = page.unparse()
        if obid in self.processed_objects:
            return
        else:
            self.processed_objects.add(obid)

        # the page is either an actual page, or a form xobject
        is_page = isinstance(page, pikepdf.Page)

        if is_page:
            page.contents_coalesce()
            bytestream = page.Contents.read_bytes()
        else:
            bytestream = page.read_bytes()

        # filter if there's OC blocks or placed forms, or we're already
        # in an optional content group
        do_filter = do_filter or b"/OC" in bytestream or b"Do" in bytestream

        # initialize empty stream and placed forms, then try to filter
        page_stream = None
        if do_filter:
            commands, placed_xobjs = self.filter_stream(page, current_layer_name)
            if len(self.current_state) != 1:
                raise Exception("Unbalanced Q/q operators")
            try:
                page_stream = pikepdf.unparse_content_stream(commands)
            except Exception as e:
                print(_("Failed writing stream to page with error type {}").format(type(e)))
                pass

            # get the dictionary of xobjects to process as well
            for name, info in placed_xobjs.items():
                if "/Subtype" in info["xobj"].keys() and info["xobj"].Subtype == "/Form":
                    self.initialize_state(info["state"])
                    self.filter_content(
                        info["xobj"], current_layer_name=info["current_layer_name"], do_filter=True
                    )

        elif not self.keep_non_oc:
            # if we're not filtering and not keeping non-optional content, obliterate the stream
            page_stream = b""

        # Remove the oc info from the page properties
        if self.delete_ocgs and "/Properties" in page.keys():
            for key, val in page.Properties.items():
                if "/Name" in val.keys() and val.Name not in self.keep_ocs:
                    del page.Properties[key]

        # finally, write the stream
        try:
            if is_page:
                page.Contents = self.out_pdf.make_stream(page_stream)
            else:
                # Probably a form xobject
                page.write(page_stream)
        except Exception as e:
            print(_("Failed writing stream to page with error type {}").format(type(e)))
            pass
