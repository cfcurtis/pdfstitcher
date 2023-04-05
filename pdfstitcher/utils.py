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
import locale
from babel import Locale
from pathlib import Path

import importlib.metadata

__version__ = importlib.metadata.version("pdfstitcher")

VERSION_STRING = "v" + __version__

# Maximum size of a PDF document in Adobe (200 inches)
MAX_SIZE_PX = 14400

# Constant widget sizes - used for all the different panels
BORDER = 5
NUM_ENTRY_SIZE = (40, -1)
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

    def units_to_px(self, val):
        """
        Converts from current units to pixels.
        """
        if self == UNITS.INCHES:
            return val * 72
        elif self == UNITS.CENTIMETERS:
            return val * 72 / 2.54
        elif self == UNITS.POINTS:
            return val

    def px_to_units(self, val):
        """
        Converts from pixels to current units.
        """
        if self == UNITS.INCHES:
            return val / 72
        elif self == UNITS.CENTIMETERS:
            return val / 72 * 2.54
        elif self == UNITS.POINTS:
            return val


def unit_representer(dumper, data):
    return dumper.represent_scalar("!units", "%s" % data.name)


def unit_constructor(loader, node):
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


def resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller"""
    if hasattr(sys, "_MEIPASS"):
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    else:
        base_path = str(Path(__file__).parent.absolute())

    return os.path.join(base_path, relative_path)


def get_valid_langs():
    """
    Get a list of valid languages for the UI.
    """
    langs = ["en"]
    for lang in os.listdir(resource_path("locale")):
        if lang != "pdfstitcher.pot":
            langs.append(lang)
    return langs


def setup_locale(lang: str = None) -> None:
    """
    Sets the UI language, or falls back to the system default.
    """
    language_warning = None

    # Update the global valid_langs here to ensure it only happens once
    global valid_langs
    valid_langs = get_valid_langs()
    if lang is None:
        lc = locale.getdefaultlocale()

        try:
            if lc[0] is None:
                lc = os.getenv("LANG")[:4]
            else:
                lang = lc[0]
        except:
            try:
                # try the Apple way
                from Foundation import NSUserDefaults

                defaults = NSUserDefaults.standardUserDefaults()
                globalDomain = defaults.persistentDomainForName_("NSGlobalDomain")
                languages = globalDomain.objectForKey_("AppleLanguages")

                # just take the first one
                lang = languages[0]
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


def txt_to_float(txt):
    """
    Convert a string to a float, or return None if it can't be converted.
    Supports decimal and comma as decimal separator.
    """
    if txt is None or not txt.strip():
        return 0

    try:
        txtnum = float(txt.replace(",", "."))
    except ValueError:
        print(_("Invalid input") + txt + " , " + _("only numeric values allowed"))
        return None

    return txtnum


def parse_page_range(ptext=""):
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


def init_new_doc(pdf):
    """
    Initialize a new document and copy over the layer info (OCGs) if it exists.
    """
    new_doc = pikepdf.Pdf.new()

    local_root = new_doc.copy_foreign(pdf.Root)

    if "/OCProperties" in local_root:
        new_doc.Root.OCProperties = local_root.OCProperties

    if "/Metadata" in local_root:
        for k in pdf.Root.Metadata.keys():
            new_doc.Root.Metadata = local_root.Metadata

    with new_doc.open_metadata() as meta:
        # update the creator info
        meta["xmp:CreatorTool"] = "PDFStitcher " + VERSION_STRING

    return new_doc


def get_page_dims(page, global_rotation=0):
    """
    Helper function to calculate the page dimensions
    Returns width, height as observed by the user
    (taking rotation into account)
    """
    # The mediabox is typically specified as
    # [lower left x, lower left y, upper left x, upper left y],
    # but per PDF reference any two opposite corners can be defined
    mbox = page.MediaBox
    page_width = float(abs(mbox[2] - mbox[0]))
    page_height = float(abs(mbox[3] - mbox[1]))

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


def print_media_box(media_box, user_unit=1):
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
                round(Config.general["units"].px_to_units(MAX_SIZE_PX)),
                Config.general["units"],
            )
        )
        print(62 * "*")
    # just print it out for info
    print(
        _("Output size:")
        + " {:0.2f} x {:0.2f} {}".format(
            user_unit * Config.general["units"].px_to_units(width),
            user_unit * Config.general["units"].px_to_units(height),
            Config.general["units"],
        )
    )


def normalize_boxes(page):
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
