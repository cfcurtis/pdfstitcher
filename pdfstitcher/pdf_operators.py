# PDFStitcher is a utility to work with PDF sewing patterns.
# Copyright (C) 2021 Charlotte Curtis
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

# Initial list copied from https://gitlab.freedesktop.org/poppler/poppler/-/blob/master/test/pdf-operators.c
# Each operator has a tuple defining whether it is used to show stuff on the page, modify the state,
# or begin/end a block. The second element of the tuple indicates what type of content is affected.
ops = {
    "b": ("show", "stroke"),  # Close, fill, and stroke path using nonzero winding number rule
    "B": ("show", "stroke"),  # Fill and stroke path using nonzero winding number rule
    "b*": ("show", "stroke"),  # Close, fill, and stroke path using even-odd rule
    "B*": ("show", "stroke"),  # Fill and stroke path using even-odd rule
    "BDC": ("begin", "markedcontent"),  # (PDF 1.2) Begin marked-content sequence with property list
    "BI": ("begin", "image"),  # Begin inline image object
    "BMC": ("begin", "markedcontent"),  # (PDF 1.2) Begin marked-content sequence
    "BT": ("begin", "text"),  # Begin text object
    "BX": ("begin", "compatibility"),  # (PDF 1.1) Begin compatibility section
    "c": ("show", "stroke"),  # Append curved segment to path (three control points)
    "cm": ("state", "all"),  # Concatenate matrix to current transformation matrix
    "CS": ("state", "stroke"),  # (PDF 1.1) Set color space for stroking operations
    "cs": ("state", "nonstroke"),  # (PDF 1.1) Set color space for nonstroking operations
    "d": ("state", "stroke"),  # Set line dash pattern
    "d0": ("state", "text"),  # Set glyph width in Type 3 font
    "d1": ("state", "text"),  # Set glyph width and bounding box in Type 3 font
    "Do": ("show", "all"),  # Invoke named XObject
    "DP": ("point", "markedcontent"),  # (PDF 1.2) Define marked-content point with property list
    "EI": ("end", "image"),  # End inline image object
    "EMC": ("end", "markedcontent"),  # (PDF 1.2) End marked-content sequence
    "ET": ("end", "text"),  # End text object
    "EX": ("end", "compatibility"),  # (PDF 1.1) End compatibility section
    "f": ("show", "nonstroke"),  # Fill path using nonzero winding number rule
    "F": ("show", "nonstroke"),  # Fill path using nonzero winding number rule (obsolete)
    "f*": ("show", "nonstroke"),  # Fill path using even-odd rule
    "G": ("state", "stroke"),  # Set gray level for stroking operations
    "g": ("state", "nonstroke"),  # Set gray level for nonstroking operations
    "gs": ("state", "all"),  # (PDF 1.2) Set parameters from graphics state parameter dictionary
    "h": ("show", "stroke"),  # Close subpath
    "i": ("state", "nonstroke"),  # Set flatness tolerance
    "ID": ("point", "image"),  # Begin inline image data
    "j": ("state", "stroke"),  # Set line join style
    "J": ("state", "stroke"),  # Set line cap style
    "K": ("state", "stroke"),  # Set CMYK color for stroking operations
    "k": ("state", "all"),  # Set CMYK color for nonstroking operations
    "l": ("show", "stroke"),  # Append straight line segment to path
    "m": ("show", "stroke"),  # Begin new subpath
    "M": ("state", "stroke"),  # Set miter limit
    "MP": ("point", "markedcontent"),  # (PDF 1.2) Define marked-content point
    "n": ("show", "stroke"),  # End path without filling or stroking
    "q": ("state", "all"),  # Save graphics state
    "Q": ("state", "all"),  # Restore graphics state
    "re": ("show", "stroke"),  # Append rectangle to path
    "RG": ("state", "stroke"),  # Set RGB color for stroking operations
    "rg": ("state", "all"),  # Set RGB color for nonstroking operations
    "ri": ("state", "all"),  # Set color rendering intent
    "s": ("show", "stroke"),  # Close and stroke path
    "S": ("show", "stroke"),  # Stroke path
    "SC": ("state", "stroke"),  # (PDF 1.1) Set color for stroking operations
    "sc": ("state", "nonstroke"),  # (PDF 1.1) Set color for nonstroking operations
    "SCN": (
        "state",
        "stroke",
    ),  # (PDF 1.2) Set color for stroking operations (ICCBased and special color spaces)
    "scn": (
        "state",
        "nonstroke",
    ),  # (PDF 1.2) Set color for nonstroking operations (ICCBased and special color spaces)
    "sh": ("show", "nonstroke"),  # (PDF 1.3) Paint area defined by shading pattern
    "T*": ("state", "text"),  # Move to start of next text line
    "Tc": ("state", "text"),  # Set character spacing
    "Td": ("state", "text"),  # Move text position
    "TD": ("state", "text"),  # Move text position and set leading
    "Tf": ("state", "text"),  # Set text font and size
    "Tj": ("show", "text"),  # Show text
    "TJ": ("show", "text"),  # Show text, allowing individual glyph positioning
    "TL": ("state", "text"),  # Set text leading
    "Tm": ("state", "text"),  # Set text matrix and text line matrix
    "Tr": ("state", "text"),  # Set text rendering mode
    "Ts": ("state", "text"),  # Set text rise
    "Tw": ("state", "text"),  # Set word spacing
    "Tz": ("state", "text"),  # Set horizontal text scaling
    "v": ("show", "stroke"),  # Append curved segment to path (initial point replicated)
    "w": ("state", "stroke"),  # Set line width
    "W": ("show", "all"),  # Set clipping path using nonzero winding number rule
    "W*": ("show", "all"),  # Set clipping path using even-odd rule
    "y": ("show", "stroke"),  # Append curved segment to path (final point replicated)
    "'": ("show", "text"),  # Move to next line and show text
    '"': ("show", "text"),  # Set word and character spacing, move to next line, and show text
}

line_style_arr = [[[], 0], [[6, 3], 0], [[1], 0]]  # solid  # dashed  # dotted


def rgb_to_cmyk(rgb):
    if rgb == [0, 0, 0]:
        # black
        return [0, 0, 0, 1]

    c = 1 - rgb[0]
    m = 1 - rgb[1]
    y = 1 - rgb[2]

    # extract out k [0, 1]
    min_cmy = min(c, m, y)
    c = (c - min_cmy) / (1 - min_cmy)
    m = (m - min_cmy) / (1 - min_cmy)
    y = (y - min_cmy) / (1 - min_cmy)
    k = min_cmy

    return [c, m, y, k]
