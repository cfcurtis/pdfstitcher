# PDFStitcher is a utility to work with PDF sewing patterns.
# Copyright (C) 2021 Charlotte Curtis
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import argparse
from pdfstitcher import utils
from pdfstitcher.processing.mainproc import MainProcess
from pdfstitcher.utils import Config


def add_tile_args(parser: argparse.ArgumentParser) -> None:
    """
    Add the tile arguments to the parser.
    """
    t_parser = parser.add_argument_group(
        _("Tile Options"),
        _(
            "Options for tiling pages. "
            "If no grid layout is specified, pages will be copied without tiling."
        ),
    )

    m_group = t_parser.add_mutually_exclusive_group(required=False)
    m_group.add_argument(
        "-r",
        "--rows",
        type=int,
        help=_("Number of rows in tiled grid."),
        default=None,
    )
    m_group.add_argument(
        "-c",
        "--columns",
        type=int,
        help=_("Number of columns in tiled grid."),
        default=None,
    )

    t_parser.add_argument(
        "-u",
        "--units",
        choices=[_("in"), _("cm")],
        default=_("in"),
        help=_("Units for margin and trim values."),
    )
    t_parser.add_argument(
        "-m",
        "--margin",
        type=float,
        help=_("Margin size in selected units."),
        default=0,
    )
    t_parser.add_argument(
        "-t",
        "--trim",
        default="0,0,0,0",
        help=_("Amount to trim from edges in selected units")
        + " "
        + _("given as left,right,top,bottom (e.g. 0.5,0,0.5,0 would trim 0.5 from left and top)"),
    )
    t_parser.add_argument(
        "-R",
        "--rotate",
        type=int,
        default=0,
        choices=[0, 90, 180, 270],
        help=_("Rotate pages"),
    )
    t_parser.add_argument(
        "--col-major",
        type=bool,
        default=False,
        help=_("Fill columns before rows (default is rows first)"),
    )
    t_parser.add_argument(
        "--right-to-left",
        type=bool,
        default=False,
        help=_("Fill columns right to left (default is left to right)"),
    )
    t_parser.add_argument(
        "--bottom-to-top",
        type=bool,
        default=False,
        help=_("Fill rows bottom to top (default is top to bottom)"),
    )
    t_parser.add_argument(
        "--target-height",
        type=float,
        help=_("Height of output document in selected units.") + " "
        # translation_note: This message only appears in the CLI when the user
        # specifies a target size for the output document.
        + _("Caution: results in scaling of pages"),
        default=None,
    )
    t_parser.add_argument(
        "--target-width",
        type=float,
        help=_("Width of output document in selected units.")
        + " "
        + _("Caution: results in scaling of pages"),
        default=None,
    )
    t_parser.add_argument(
        "--trimbox-to-mediabox",
        action="store_true",
        help=_("Override trimbox with mediabox"),
        default=False,
    )
    t_parser.add_argument(
        "--actually-trim",
        action="store_true",
        help=_("Actually trim the pages (default is overlap)"),
        default=False,
    )


def add_layer_args(parser: argparse.ArgumentParser) -> None:
    """
    Add the layer arguments to the parser.
    """
    l_parser = parser.add_argument_group(
        _("Layer Options"),
        _("Options for handling layers in the document."),
    )
    l_parser.add_argument(
        "-k",
        "--keep",
        type=str,
        # translation_note: These are CLI arguments, punctuation must be preserved
        help=_("List of layer names to keep, separated by semicolons (e.g. 'Layer1;Layer2')"),
        default=[],
    )
    l_parser.add_argument(
        "--keep-non-oc",
        type=bool,
        help=_("Keep non-optional (background) content."),
        default=True,
    )
    l_parser.add_argument(
        "--hide-layers",
        action="store_true",
        help=_("Hide layers. If set, layer visibility is set to Off instead of removing content."),
    )


def parse_arguments() -> argparse.Namespace:
    """
    Helper function to parse command line arguments.
    """
    parser = argparse.ArgumentParser(
        _("PDF Stitcher"),
        description=_("Stitch PDF pages together, add margins, remove layers, and more."),
    )

    # Required arguments
    parser.add_argument(
        "input",
        help=_("Input filename (pdf)"),
    )
    parser.add_argument(
        "output",
        nargs="?",
        help=_("Output filename (pdf)"),
        default=None,
    )

    parser.add_argument(
        "-p",
        "--pages",
        help=_(
            "Pages to Process. May be range or list (e.g. 1-5 or 1,3,5-7, etc). "
            "Default: entire document. Use 0 values to add blank pages."
        ),
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help=_("Print verbose output"),
        default=False,
    )

    add_tile_args(parser)
    add_layer_args(parser)

    args, unknown = parser.parse_known_args()
    if unknown:
        print(_("Ignoring unknown arguments:"))
        [print(u) for u in unknown]

    # validate the trim values
    trim = [utils.txt_to_float(t) for t in args.trim.split(",")]
    if len(trim) == 1:
        args.trim = [trim[0], trim[0], trim[0], trim[0]]
    elif len(trim) == 2:
        args.trim = [trim[0], trim[0], trim[1], trim[1]]
    elif len(trim) == 4:
        args.trim = trim
    else:
        print(_("Invalid trim value specified, ignoring"))
        args.trim = [0, 0, 0, 0]

    return args


def pretty_print(params: dict, name: str) -> None:
    """
    Pretty print the parameters with the given name.
    """
    print(name)
    for key, value in params.items():
        print(f"\t{key}: {value}")


def main():
    """
    Configure and run the app.
    """
    Config.load()
    language_warning = utils.setup_locale(Config.general["language"])

    if language_warning:
        print(language_warning)

    args = parse_arguments()
    Config.general["units"] = utils.UNITS.INCHES if args.units == _("in") else utils.UNITS.CM
    main_process = MainProcess(doc=args.input)

    if args.output is None:
        if args.verbose:
            print(_("No output file specified, showing input document info and exiting."))

        # Show info about the file and exit
        doc_info = main_process.doc_info
        doc_info["first_page_dims"] = (
            str([Config.general["units"].pts_to_units(d) for d in doc_info["first_page_dims"]])
            + " "
            + str(Config.general["units"])
        )
        pretty_print(doc_info, args.input)
        return

    # Set the page range
    main_process.page_range = args.pages

    # Set the page tiler parameters
    tile_params = {
        "cols": args.columns,
        "rows": args.rows,
        "col_major": args.col_major,
        "right_to_left": args.right_to_left,
        "bottom_to_top": args.bottom_to_top,
        "rotation": args.rotate,
        "margin": args.margin,
        "trim": args.trim,
        "override_trim": args.trimbox_to_mediabox,
        "actually_trim": args.actually_trim,
        "target_height": args.target_height,
        "target_width": args.target_width,
    }

    # Set the layer filter parameters
    layer_params = {
        "keep_ocs": args.keep.split(";") if args.keep else [],
        "keep_non_oc": args.keep_non_oc,
        "delete_ocgs": not args.hide_layers,
        "line_props": None,  # Haven't figured out how to specify in CLI yet
    }
    if any(layer_params.values()):
        main_process.toggle("LayerFilter", True)
        main_process.set_params("LayerFilter", layer_params)

        # make sure the layers actually exist
        for layer in layer_params["keep_ocs"]:
            if layer not in main_process.doc_info["layers"]:
                print(_("Layer") + " " + layer + " " + _("not found in the document. Ignoring."))

        if args.verbose:
            pretty_print(layer_params, _("Layer Options"))

    if args.columns is None and args.rows is None:
        main_process.toggle("PageTiler", False)
        filter_params = {"margin": args.margin}
        main_process.set_params("PageFilter", filter_params)
        if args.verbose:
            pretty_print(filter_params, _("Options"))
    else:
        main_process.toggle("PageTiler", True)
        main_process.set_params("PageTiler", tile_params)
        if args.verbose:
            pretty_print(tile_params, _("Tile Options"))

    success = main_process.run()

    if success:
        main_process.out_doc.save(args.output)
        print(_("Successfully written to") + " " + args.output)


if __name__ == "__main__":
    main()
