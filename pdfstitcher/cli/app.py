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


def parse_arguments() -> argparse.Namespace:
    """
    Helper function to parse command line arguments.
    """
    parser = argparse.ArgumentParser(
        description=_("Tile PDF pages into one document."),
        epilog=_("Note: If both rows and columns are specified, rows are ignored.")
        + " "
        + _("To insert a blank page, include a zero in the page list."),
    )

    # Required arguments
    parser.add_argument(
        "input",
        help=_("Input filename (pdf)"),
    )
    parser.add_argument(
        "output",
        help=_("Output filename (pdf)"),
    )
    group = parser.add_argument_group(
        _("Grid layout"), _("Number of Columns") + " " + _("OR Number of Rows")
    )
    m_group = group.add_mutually_exclusive_group(required=False)
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

    parser.add_argument(
        "-p",
        "--pages",
        help=_(
            "Pages to tile. May be range or list (e.g. 1-5 or 1,3,5-7, etc). Default: entire document."
        ),
    )
    parser.add_argument(
        "-u",
        "--units",
        choices=[_("in"), _("cm")],
        default=_("in"),
        help=_("Units for margin and trim values."),
    )
    parser.add_argument(
        "-m",
        "--margin",
        type=float,
        help=_("Margin size in selected units."),
        default=0,
    )
    parser.add_argument(
        "-t",
        "--trim",
        default="0,0,0,0",
        help=_("Amount to trim from edges in selected units")
        + " "
        + _("given as left,right,top,bottom (e.g. 0.5,0,0.5,0 would trim 0.5 from left and top)"),
    )
    parser.add_argument(
        "-R",
        "--rotate",
        type=int,
        default=0,
        choices=[0, 90, 180, 270],
        help=_("Rotate pages"),
    )
    parser.add_argument(
        "--col-major",
        type=bool,
        default=False,
        help=_("Fill columns before rows (default is rows first)"),
    )
    parser.add_argument(
        "--right-to-left",
        type=bool,
        default=False,
        help=_("Fill columns right to left (default is left to right)"),
    )
    parser.add_argument(
        "--bottom-to-top",
        type=bool,
        default=False,
        help=_("Fill rows bottom to top (default is top to bottom)"),
    )
    parser.add_argument(
        "--target-height",
        type=float,
        help=_("Height of output document in selected units.")
        + " "
        + _("Caution: results in scaling of pages"),
        default=None,
    )
    parser.add_argument(
        "--target-width",
        type=float,
        help=_("Width of output document in selected units.")
        + " "
        + _("Caution: results in scaling of pages"),
        default=None,
    )
    parser.add_argument(
        "--trimbox-to-mediabox",
        action="store_true",
        help=_("Override trimbox with mediabox"),
        default=False,
    )
    parser.add_argument(
        "--actually-trim",
        action="store_true",
        help=_("Actually trim the pages (default is overlap)"),
        default=False,
    )

    args = parser.parse_args()

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
    print(name, _("Parameters:"))
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
    main_process = MainProcess(doc=args.input)

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
    }

    if args.columns is None and args.rows is None:
        if len(main_process.page_range) > 1:
            print(
                _(
                    "Warning: No grid layout specified, will copy pages and save document without tiling."
                )
            )
        main_process.toggle("PageTiler", False)
        filter_params = {"margin": args.margin}
        main_process.set_params("PageFilter", filter_params)
        pretty_print(filter_params, "PageFilter")
    else:
        main_process.toggle("PageTiler", True)
        main_process.set_params("PageTiler", tile_params)
        pretty_print(tile_params, "PageTiler")

    # Layer filter not yet implemented
    success = main_process.run()

    if success:
        main_process.out_doc.save(args.output)
        print(_("Successfully written to") + " " + args.output)


if __name__ == "__main__":
    main()
