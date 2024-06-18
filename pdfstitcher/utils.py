# PDFStitcher is a utility to work with PDF sewing patterns.
# Copyright (C) 2021 Charlotte Curtis
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import sys
import os
import pikepdf
from enum import IntEnum

from appdirs import user_config_dir
import yaml

# localization stuff
import gettext
from babel import Locale
from pathlib import Path

import importlib.metadata

__version__ = importlib.metadata.version("pdfstitcher")

VERSION_STRING = "v" + __version__

# Maximum size of a PDF document in Adobe (200 inches)
MAX_SIZE_PX = 14400

# Constant widget sizes - used for all the different panels
BORDER = 5
NUM_ENTRY_SIZE = (80, -1)
PATH_ENTRY_SIZE = (250, -1)

# language global variable
valid_langs = None

# URLs
WEB_HOME = "https://www.pdfstitcher.org"
DOCS_PAGE = WEB_HOME + "/docs/overview"
DOWNLOAD_PAGE = WEB_HOME + "/docs/download"
GIT_HOME = "https://github.com/cfcurtis/pdfstitcher"
PYPI_HOME = "https://pypi.org/pypi/pdfstitcher"
FLATHUB_HOME = "https://flathub.org/apps/details/com.github.cfcurtis.pdfstitcher"


class UNITS(IntEnum):
    INCHES = 0
    CENTIMETERS = 1
    POINTS = 2

    def __str__(self):
        """
        Returns the name of the units in the current language.
        """
        if self == UNITS.INCHES:
            return _("in")
        elif self == UNITS.CENTIMETERS:
            return _("cm")
        elif self == UNITS.POINTS:
            return _("pt")

    def units_to_pts(self, val: float, user_unit: float = 1):
        """
        Converts from current units to points.
        """
        if self == UNITS.INCHES:
            return val * 72 / user_unit
        elif self == UNITS.CENTIMETERS:
            return val * 72 / user_unit / 2.54
        elif self == UNITS.POINTS:
            return val / user_unit

    def pts_to_units(self, val: float, user_unit: float = 1):
        """
        Converts from points to current units.
        """
        if self == UNITS.INCHES:
            return user_unit * val / 72
        elif self == UNITS.CENTIMETERS:
            return user_unit * val / 72 * 2.54
        elif self == UNITS.POINTS:
            return user_unit * val


def unit_representer(dumper: yaml.Dumper, data: UNITS):
    return dumper.represent_scalar("!units", "%s" % data.name)


def unit_constructor(loader: yaml.Loader, node: yaml.Node):
    name = loader.construct_scalar(node)
    return UNITS[name]


yaml.add_representer(UNITS, unit_representer)
yaml.add_constructor("!units", unit_constructor)


class Config:
    """
    Singleton class to handle user preferences
    """

    general = {
        "units": UNITS.INCHES,
        "language": None,
        "check_updates": True,
        "open_dir": "",
        "save_dir": "",
        "margin": "0",
    }
    line_props = {
        "colour": {"enable": True, "value": (0, 0, 0), "fill": False},
        "thickness": {"enable": True, "value": "4", "units": UNITS.POINTS},
        "style": {"enable": True, "value": 0},
    }
    combo = {"general": general, "line_props": line_props}
    config_dir = Path(user_config_dir(appname="pdfstitcher", appauthor=False))
    config_file = "config.yml"

    @classmethod
    def load(cls):
        """
        Defines defaults, then loads configuration file to make any changes.
        """
        try:
            with open(cls.config_dir / cls.config_file, "r") as f:
                prefs = yaml.full_load(f)
        except OSError:
            # write the defaults for next time
            cls.save()
            prefs = {}

        try:
            # merge the defaults with the loaded prefs
            for key in prefs["general"].keys():
                cls.general[key] = prefs["general"][key]
            for key in prefs["line_props"].keys():
                cls.line_props[key] = prefs["line_props"][key]
        except KeyError:
            pass

    @classmethod
    def save(cls):
        """
        Save the current configuration for next time.
        """
        try:
            if not cls.config_dir.exists():
                cls.config_dir.mkdir(parents=True)
            with open(cls.config_dir / cls.config_file, "w") as f:
                yaml.dump(cls.combo, f)
        except OSError:
            print("Could not save configuration file.")


def resource_path(relative_path: str) -> Path:
    """
    Get absolute path to resources dir. Works for dev, PyInstaller, and Nuitka.
    """
    if hasattr(sys, "_MEIPASS"):
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = Path(sys._MEIPASS) / "resources"
    else:
        # Nuitka and PyPi place resources adjacent to the executable
        base_path = Path(__file__).parent.absolute() / "resources"

    # If we're running from source, the resources are in the parent directory
    if not base_path.exists():
        base_path = Path(__file__).parent.parent.absolute() / "resources"

    return base_path / relative_path


def get_valid_langs() -> list:
    """
    Get a list of valid languages for the UI.
    """
    valid = ["en"]
    try:
        valid += [f.name for f in os.scandir(resource_path("locale")) if f.is_dir()]
    except FileNotFoundError:
        # Something weird with resources, but don't crash
        pass

    return valid


def setup_locale(lang: str = None) -> None:
    """
    Sets the UI language, or falls back to the system default.
    """
    language_warning = None

    # Update the global valid_langs here to ensure it only happens once
    global valid_langs
    valid_langs = get_valid_langs()
    if lang is None:
        try:
            lang = os.getenv("LANG").split(".")[0]
        except Exception as e:
            language_warning = "Could not detect system language, defaulting to English"
            lang = "en"

    # First check if the language is defined as-is
    if lang in valid_langs:
        lang = lang
    # Then check just the language without country code
    elif lang[:2] in valid_langs:
        lang = lang[:2]
    elif lang[:2] == "sk":
        # fallback to Czech if Slovak is not available
        lang = "cs"
        # Google Translate to Slovak, this might be kind of awful
        language_warning = "Slovenský preklad nie je k dispozícii, predvolená je čeština"
    else:
        # check if there's a country code variant for the language
        for valid_lang in valid_langs:
            if lang[:2] in valid_lang:
                lang = valid_lang
                break

    try:
        translate = gettext.translation(
            "pdfstitcher", resource_path("locale"), languages=[lang], fallback=True
        )
        translate.install()

        Config.general["language"] = lang
        if not isinstance(translate, gettext.GNUTranslations) and "en" not in lang:
            language_warning = f"Could not find translation for language {Locale(*lang.split('_')).display_name}, defaulting to English"
            Config.general["language"] = "en"
    except Exception as e:
        language_warning = e
        Config.general["language"] = "en"

    return language_warning


def txt_to_float(txt: str) -> float:
    """
    Convert a string to a float, or return None if it can't be converted.
    Supports decimal and comma as decimal separator.
    """
    if txt is None or not txt.strip():
        return 0

    txt = txt.replace(",", ".")
    if any([c not in "0123456789.+-*/" for c in txt]):
        print(_("Invalid input") + " " + txt + " , " + _("only numeric values allowed"))
        return None

    try:
        txtnum = eval(txt)
    except ZeroDivisionError:
        print(_("Division by zero is not allowed"))
        return None
    except Exception as e:
        print(_("Invalid input") + " " + txt + " , " + _("only numeric values allowed"))
        return None

    return txtnum


def parse_page_range(ptext: str = "") -> list:
    """
    Parse out the requested pages.
    Allows for pages to be repeated and out of order.
    """
    page_range = []
    if ptext:
        for r in [p.split("-") for p in ptext.split(",")]:
            if len(r) == 1:
                page_range.append(int(r[0]))
            else:
                page_range += list(range(int(r[0]), int(r[-1]) + 1))

    else:
        print(_("Please specify a page range"))
        return None

    return page_range


def init_new_doc(pdf: pikepdf.Pdf) -> pikepdf.Pdf:
    """
    Initialize a new document and copy over the layer info (OCGs) if it exists.
    """
    new_doc = pikepdf.Pdf.new()

    local_root = new_doc.copy_foreign(pdf.Root)

    if "/OCProperties" in local_root:
        new_doc.Root.OCProperties = local_root.OCProperties

    if "/Metadata" in local_root:
        new_doc.Root.Metadata = local_root.Metadata

    with new_doc.open_metadata() as meta:
        # update the creator info
        meta["xmp:CreatorTool"] = "PDFStitcher " + VERSION_STRING

    return new_doc


def get_page_dims(
    page: pikepdf.Page, global_rotation: float = 0, page_uu: float = 1, output_uu: float = 1
) -> tuple:
    """
    Helper function to calculate the page dimensions
    Returns width, height in points as observed by the user
    (taking rotation and UserUnit into account)
    """

    if "/MediaBox" in page.keys():
        mbox = page.MediaBox
    else:
        mbox = page.BBox

    # The mediabox is typically specified as
    # [lower left x, lower left y, upper left x, upper left y],
    # but per PDF reference any two opposite corners can be defined
    page_width = float(abs(mbox[2] - mbox[0]))
    page_height = float(abs(mbox[3] - mbox[1]))

    if "/UserUnit" in page.keys():
        page_uu = float(page.UserUnit)

    # scale according to the page and target user units
    page_width *= page_uu / output_uu
    page_height *= page_uu / output_uu

    # global_rotation is defined by the document root, but
    # may be overridden on a specific page
    if "/Rotate" in page.keys():
        rotation = page.Rotate
    else:
        rotation = global_rotation

    # swap height and width if there is rotation
    if (rotation // 90) % 2 != 0:
        page_width, page_height = page_height, page_width

    return page_width, page_height


def print_media_box(media_box, user_unit: float = 1) -> None:
    """
    Display the media box in the requested units.
    Also checks to see if the size exceeds Adobe's max size.
    """
    width = abs(float(media_box[2]) - float(media_box[0]))
    height = abs(float(media_box[3]) - float(media_box[1]))
    if width > MAX_SIZE_PX or height > MAX_SIZE_PX:
        # check if it exceeds Adobe's 200 inch maximum size
        print(62 * "*")
        print(
            _("Warning! Output is larger than {} {}, may not open correctly.").format(
                round(Config.general["units"].pts_to_units(MAX_SIZE_PX, user_unit)),
                Config.general["units"],
            )
        )
        print(62 * "*")
    # just print it out for info
    print(
        _("Output size:")
        + " {:0.2f} x {:0.2f} {}".format(
            Config.general["units"].pts_to_units(width, user_unit),
            Config.general["units"].pts_to_units(height, user_unit),
            Config.general["units"],
        )
    )


def normalize_boxes(page: pikepdf.Page) -> None:
    """
    Normalizes the various pdf boxes on the page so they follow the assumed
    [lower x, lower y, upper x, upper y] format
    """

    for box in [key for key in page.keys() if "Box" in key]:
        if page[box][0] > page[box][2]:
            page[box][0], page[box][2] = page[box][2], page[box][0]
        if page[box][1] > page[box][3]:
            page[box][1], page[box][3] = page[box][3], page[box][1]

    # check if there are any xobjects with boxes that need to be normalized
    if "/Resources" in page.keys() and "/XObject" in page.Resources.keys():
        for key in page.Resources.XObject.keys():
            normalize_boxes(page.Resources.XObject[key])


def fix_utf16(string: str) -> str:
    """
    Helper function to put a band-aid on UTF-16 encoded strings.
    """
    new_string = string.replace("\x00", "")
    if new_string.startswith("ÿþ"):
        new_string = new_string[2:]
    return new_string


def add_name(ordered_names: list, name_object: pikepdf.Dictionary, depth: int = 0) -> None:
    """
    Add the name to the list of ordered names. Ignores duplicates.
    """
    if depth > 1:
        return
    for o in name_object:
        if "/Name" in o.keys():
            name = fix_utf16(str(o.Name))
            if name not in ordered_names:
                ordered_names.append(name)
        else:
            add_name(ordered_names, o, depth=depth + 1)


def get_layer_names(doc: pikepdf.Pdf) -> list:
    """
    Reads through the root to parse out the layers present in the file, excluding duplicates.
    Returns a list of layer names, or None if there are no layers
    """
    if "/OCProperties" in doc.Root.keys() and "/OCGs" in doc.Root.OCProperties.keys():
        ocp = doc.Root.OCProperties
    else:
        return []

    names = [str(oc.Name) for oc in ocp.OCGs]
    ordered_names = []
    if "/D" in ocp.keys() and "/Order" in ocp.D.keys():
        add_name(ordered_names, ocp.D.Order)
    for n in names:
        real_n = fix_utf16(n)
        if real_n not in ordered_names:
            ordered_names.append(real_n)
    return ordered_names


# helper functions to dump page contents to file for debugging
def write_page(fname: str, page: pikepdf.Page) -> None:
    with open(fname, "w") as f:
        commands = pikepdf.parse_content_stream(page)
        f.write(pikepdf.unparse_content_stream(commands).decode("pdfdoc"))
