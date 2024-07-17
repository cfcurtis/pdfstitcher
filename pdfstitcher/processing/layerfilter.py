# PDFStitcher is a utility to work with PDF sewing patterns.
# Copyright (C) 2021 Charlotte Curtis
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import pikepdf
import pdfstitcher.processing.pdf_operators as pdf_ops
import pdfstitcher.utils as utils
from pdfstitcher.processing.procbase import ProcessingBase
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
    "K": pdf_ops.rgb_to_cmyk([0, 0, 0]),
    "k": pdf_ops.rgb_to_cmyk([0, 0, 0]),
    "RG": [0, 0, 0],
    "rg": [0, 0, 0],
    "d": pdf_ops.line_style_arr[0],
}

# ------------------------------
# Helper functions
# ------------------------------


def is_transparency_group(obj: pikepdf.Object) -> bool:
    """
    Returns true if the object is a transparency group.
    """
    if "/Group" in obj.keys() and obj.Group.S == "/Transparency":
        return True
    return False


# ------------------------------
# Main class
# ------------------------------


class LayerFilter(ProcessingBase):
    """
    Class to filter layers and modify line properties.
    """

    def __init__(self, *args, **kw) -> None:
        super().__init__(*args, **kw)

    def _filter_ocg_order(self, ocg_list=None):
        """
        Recursively filters the ocg list to only include those in the keep_ocs list.
        """

        if ocg_list is None:
            ocg_list = self.out_doc.Root.OCProperties.D.Order

        if ocg_list._type_name == "array":
            to_delete = []
            for i, item in enumerate(ocg_list):
                if self._filter_ocg_order(item):
                    to_delete.append(i)

            # delete the items in reverse order so we don't mess up the indices
            for i in reversed(to_delete):
                del ocg_list[i]

            return len(ocg_list) == 0

        elif ocg_list._type_name == "dictionary":
            if "/Type" in ocg_list.keys():
                if ocg_list.Type == pikepdf.Name.OCG and ocg_list.Name not in self.p["keep_ocs"]:
                    # found the OCG entry, delete it if it's not in our keep array
                    return True

        return False

    def _update_ocs(self) -> None:
        """
        Updates the OCProperties dictionary to only include the layers we want.
        """
        # If the list was 'all', modify so it includes all the layers
        if self.p["keep_ocs"] == "all":
            self.p["keep_ocs"] = utils.get_layer_names(self.in_doc)
            return

        if self.p["keep_ocs"] == "no_ocgs":
            # no OCGs in document, and hopefully nobody names a layer this
            return

        # edit the OCG listing in the root
        On = [
            oc for oc in self.out_doc.Root.OCProperties.OCGs if str(oc.Name) in self.p["keep_ocs"]
        ]
        Off = [
            oc
            for oc in self.out_doc.Root.OCProperties.OCGs
            if str(oc.Name) not in self.p["keep_ocs"]
        ]

        # Delete requires parsing
        if self.p["delete_ocgs"]:
            self.out_doc.Root.OCProperties.OCGs = On
            self.out_doc.Root.OCProperties.D.ON = On
            self._filter_ocg_order()
        else:
            # just switch them off
            self.out_doc.Root.OCProperties.D.ON = On
            self.out_doc.Root.OCProperties.D.OFF = Off

        # by default, unlock all layers
        self.out_doc.Root.OCProperties.D.Locked = []

    def _convert_layer_props(self) -> None:
        """
        convert the line properties from the GUI to what the PDF needs
        """
        self.pdf_line_props = {}

        for layer, lp in self.p["line_props"].items():
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
                clp["K"] = [Decimal(k) for k in pdf_ops.rgb_to_cmyk(lp["rgb"])]
                clp["RG"] = [Decimal(rg) for rg in lp["rgb"]]
                # Modify the nonstroking colour if fill_colour is checked
                if "fill_colour" in lp and lp["fill_colour"]:
                    clp["k"] = clp["K"]
                    clp["rg"] = clp["RG"]

            self.pdf_line_props[layer] = clp

    def _adjust_user_unit(self, new_uu: float) -> None:
        """
        Updates the width and dash pattern to match the user unit.
        """
        # Don't do anything if it's already the same
        if self.user_unit == new_uu:
            return

        scale = self.user_unit / new_uu

        for layer, lp in self.pdf_line_props.items():
            if "w" in lp.keys():
                self.pdf_line_props[layer]["w"][0] *= scale

            if "d" in lp.keys():
                self.pdf_line_props[layer]["d"][0] = [d * scale for d in lp["d"][0]]

        self.user_unit = new_uu

    def _override_state(self, commands: list, line_props: dict, transparency: bool = False):
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

    def _initialize_state(self, state=DEFAULT_STATE) -> None:
        """
        Initializes the list of relevant states.
        """
        del self.current_state
        self.current_state = [copy.copy(state)]

    def _push_state(self) -> None:
        """
        Create a copy of the current state and add to the list.
        """
        self.current_state.append(copy.copy(self.current_state[-1]))

    def _pop_state(self) -> None:
        """
        Pop the last state off the list.
        """
        self.current_state.pop()

    def _reset_to_previous_state(self, commands: list) -> None:
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

    def _get_oc_list(self, xobj: pikepdf.Object) -> list:
        """
        Returns the list of OC names for the given XObject.
        """
        if "/OC" in xobj.keys() and "/Name" in xobj.OC.keys():
            return [str(xobj.OC.Name)]

        if "/Type" in xobj.keys() and xobj.Type == "/OCMD":
            return [str(ocg.Name) for ocg in xobj.OCGs]

    def _get_priority_oc(self, oc_list: list) -> str:
        """
        In cases where there are multiple OCGs, return the first one with line
        property mods. Otherwise, return the first keeper, then empty.
        """
        f_list = [oc for oc in oc_list if oc in self.p["keep_ocs"]]
        if len(f_list) > 0:
            for oc in f_list:
                if oc in self.p["line_props"].keys():
                    return oc
            return f_list[0]
        else:
            return ""

    def _get_valid_obs(self, page: pikepdf.Object) -> tuple:
        """
        Loops through the XOBjects on the given page or form XOBject.
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
            oc_names = self._get_oc_list(xobj)
            if oc_names is None:
                other_obs[key] = xobj
            elif any(name in self.p["keep_ocs"] for name in oc_names):
                oc_obs[key] = xobj

        return oc_obs, other_obs

    def _filter_stream(self, ob: pikepdf.Object, current_layer_name: str = "") -> tuple:
        """
        Does the actual filtering of the stream (page or form). If we're "in" a layer (for placed forms), current_layer_name is set.
        Returns a tuple containing the list of new commands and a dictionary of placed forms.
        """
        op = ""
        commands = []
        placed_forms = {}
        oc_obs, other_obs = self._get_valid_obs(ob)
        # if the current object (page or form) is defined with transparency,
        # things go wonky when we try to override the fill colour, so don't
        transparency = is_transparency_group(ob)

        # initialize copying with keep_non_oc
        keeping = self.p["keep_non_oc"] or current_layer_name in self.p["keep_ocs"]
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
                self._pop_state()
                continue

            if op == "Do":
                # check if the object to be placed is defined as optional content,
                # and if so, is it content we want to keep
                ob_name = str(operands[0])
                if ob_name in oc_obs:
                    placed_forms[ob_name] = {
                        "state": copy.copy(self.current_state[-1]),
                        "xobj": oc_obs[ob_name],
                        "current_layer_name": self._get_priority_oc(
                            self._get_oc_list(oc_obs[ob_name])
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
                    self._override_state(
                        commands, self.pdf_line_props[current_layer_name], transparency
                    )
                elif op in self.pdf_line_props[current_layer_name]:
                    # and check if the current operator is one we need to modify
                    operands = self.pdf_line_props[current_layer_name][op]
                elif op in ("G", "g") and "RG" in self.pdf_line_props[current_layer_name]:
                    # G/g sets the colourspace to greyscale, so override it if colour selected
                    operands = self.pdf_line_props[current_layer_name]["RG"]
                    operator = pikepdf.Operator("RG") if op.isupper() else pikepdf.Operator("rg")

            if keeping or op in STATE_OPS or op == "Do":
                # if we're keeping this command, write it out
                commands.append((operands, operator))

                # and update the state
                if op in self.current_state[-1].keys():
                    self.current_state[-1][op] = operands

                # check for q/Q
                if op == "q":
                    self._push_state()
                elif op == "Q":
                    self._pop_state()

            if op == "BDC" or op == "BMC":
                # add to the marked content list and indicate whether it's an OC block
                if len(operands) > 1 and str(operands[0]) == "/OC":
                    # we're entering a new layer (optional content group)
                    oc_label = str(operands[1])
                    if page_props is not None and oc_label in page_props.keys():
                        ocg = page_props[oc_label]
                        current_layer_name = str(ocg.Name)
                        keeping = current_layer_name in self.p["keep_ocs"]

                    mc_list.append(True)
                else:
                    # not an OC block, but still need to add to the marked content list
                    mc_list.append(False)

            if op == "EMC":
                # pop the marked content list
                is_oc_end = mc_list.pop()
                if is_oc_end:
                    # end of a BDC/EMC block, reset the state
                    self._reset_to_previous_state(commands)
                    keeping = self.p["keep_non_oc"]
                    current_layer_name = ""

        return commands, placed_forms

    def _process_content(
        self,
        content: pikepdf.Object,
        current_layer_name: str = "",
        do_filter: bool = False,
    ) -> None:
        """
        Entry point for filtering content, usually starting with a page.
        Recursively filters any placed forms.

        The "do_filter" parameter flips to true if the page has OC blocks or placed forms, but also needs to be set as true if we're already inside an OC block.
        """
        # First check the id of the object and don't re-filter if we've seen it before
        obid = content.unparse()
        if obid in self.processed_objects:
            return
        else:
            self.processed_objects.add(obid)

        # Adjust the user unit if necessary (page specific!)
        if "/UserUnit" in content.keys() and self.pdf_line_props:
            self._adjust_user_unit(content.UserUnit)

        # the page is either an actual page, or a form xobject
        is_page = isinstance(content, pikepdf.Page)

        if is_page:
            # collapse any arrays of content streams into a single stream
            content.contents_coalesce()
            bytestream = content.Contents.read_bytes()
        else:
            bytestream = content.read_bytes()

        # filter if there's OC blocks or placed forms, or we're already
        # inside an optional content group.
        do_filter = do_filter or b"/OC" in bytestream or b"Do" in bytestream

        # if we're filtering, recursively process the stream and any placed forms
        if do_filter:
            commands, placed_xobjs = self._filter_stream(content, current_layer_name)
            if len(self.current_state) != 1:
                raise Exception("Unbalanced Q/q operators")
            try:
                page_stream = pikepdf.unparse_content_stream(commands)
            except Exception as e:
                print("Failed writing stream to page with error type {}").format(type(e))
                pass

            # get the dictionary of xobjects to process as well
            for _, info in placed_xobjs.items():
                if "/Subtype" in info["xobj"].keys() and info["xobj"].Subtype == "/Form":
                    self._initialize_state(info["state"])
                    self._process_content(
                        info["xobj"], current_layer_name=info["current_layer_name"], do_filter=True
                    )
        elif not self.p["keep_non_oc"]:
            # if we're not filtering and not keeping non-optional content, obliterate the stream
            page_stream = b""
        else:
            # if we're not filtering but we are keeping non-optional content, just copy the stream
            page_stream = bytestream

        # Remove the oc info from the page properties if requested
        if self.p["delete_ocgs"] and "/Properties" in content.keys():
            for key, val in content.Properties.items():
                if "/Name" in val.keys() and val.Name not in self.p["keep_ocs"]:
                    del content.Properties[key]

        # finally, write the stream
        try:
            if is_page:
                content.Contents = self.out_doc.make_stream(page_stream)
            else:
                # Probably a form xobject
                content.write(page_stream)
        except Exception as e:
            print("Failed writing stream to page with error type {}").format(type(e))
            pass

    def run(self, progress_win=None) -> bool:
        """
        Process the layers. Progress window is optional, but a good idea as this can take a while.
        """
        # initialize the state-tracking stuff
        self.processed_objects = set()
        self.pdf_line_props = {}
        self.current_state = []
        self.user_unit = 1

        # check if the user requested no modifications
        if self.p["keep_non_oc"] and self.p["keep_ocs"] == "all" and len(self.p["line_props"]) == 0:
            # nothing to do, just return the input document
            self.out_doc = self.in_doc
            progress_win and progress_win.Update(1)
            return True

        # check if the user requested no layers
        if len(self.p["keep_ocs"]) == 0 and self.p["keep_non_oc"] == False:
            print(_("No layers selected, generated PDF would be blank."))
            progress_win and progress_win.Update(1)
            return False

        # Open a new copy of the input. We could just open one instance,
        # but this allows for repeated runs without reloading the file.
        self.out_doc = pikepdf.Pdf.open(self.in_doc.filename)
        unique_pages = list(set([p for p in self.page_range if p > 0]))
        n_page = len(unique_pages)

        # initialize the progress window
        progress_win and progress_win.SetRange(n_page)  # don't run if the callback is None

        # We don't need to parse the streams if we're just hiding OCGs
        parse_streams = self.p["delete_ocgs"] or not self.p["keep_non_oc"]
        # update_ocs modifies the keep_ocs list if it was previously 'all'!
        self._update_ocs()

        # check if we're modifying line properties. If so, convert to PDF format.
        # This also requires parsing streams.
        if self.p["line_props"]:
            self._convert_layer_props()
            parse_streams = True

        if parse_streams:
            for p in unique_pages:
                # reset the graphics state before each page, then filter
                self._initialize_state()

                if self.p["keep_ocs"] == "no_ocgs":
                    self._process_content(
                        self.out_doc.pages[p - 1], current_layer_name="no_ocgs", do_filter=True
                    )
                else:
                    self._process_content(self.out_doc.pages[p - 1])

                # update the progress bar for each page, then check if user cancelled
                progress_win and progress_win.Update(unique_pages.index(p))
                if progress_win and progress_win.WasCancelled():
                    return False

        # done, update progress and strip out unused stuff
        progress_win and progress_win.Update(n_page)
        self.out_doc.remove_unreferenced_resources()
        return True
