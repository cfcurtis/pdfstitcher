#  PDFStitcher is a utility to work with PDF sewing patterns.
#  Copyright (C) 2021 Charlotte Curtis
# 
#  This program is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
# 
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
# 
#  You should have received a copy of the GNU General Public License
#  along with this program.  If not, see <https://www.gnu.org/licenses/>.

# Initial list copied from https://gitlab.freedesktop.org/poppler/poppler/-/blob/master/test/pdf-operators.c
# Each operator has a tuple defining whether it is used to show stuff on the page, modify the state, 
# or begin/end a block. The second element of the tuple indicates what type of content is affected.
ops = {
    'b': ('show','graphics'), # Close, fill, and stroke path using nonzero winding number rule
    'B': ('show','graphics'), # Fill and stroke path using nonzero winding number rule
    'b*': ('show','graphics'), # Close, fill, and stroke path using even-odd rule
    'B*': ('show','graphics'), # Fill and stroke path using even-odd rule
    'BDC': ('begin','markedcontent'), # (PDF 1.2) Begin marked-content sequence with property list
    'BI': ('begin','image'), # Begin inline image object
    'BMC': ('begin','markedcontent'), # (PDF 1.2) Begin marked-content sequence
    'BT': ('begin','text'), # Begin text object
    'BX': ('begin','compatibility'), # (PDF 1.1) Begin compatibility section
    'c': ('show','graphics'), # Append curved segment to path (three control points)
    'cm': ('state','all'), # Concatenate matrix to current transformation matrix
    'CS': ('state','graphics'), # (PDF 1.1) Set color space for stroking operations
    'cs': ('state','graphics'), # (PDF 1.1) Set color space for nonstroking operations
    'd': ('state','graphics'), # Set line dash pattern
    'd0': ('state','text'), # Set glyph width in Type 3 font
    'd1': ('state','text'), # Set glyph width and bounding box in Type 3 font
    'Do': ('show','all'), # Invoke named XObject
    'DP': ('point','markedcontent'), # (PDF 1.2) Define marked-content point with property list
    'EI': ('end','image'), # End inline image object
    'EMC': ('end','markedcontent'), # (PDF 1.2) End marked-content sequence
    'ET': ('end','text'), # End text object
    'EX': ('end','compatibility'), # (PDF 1.1) End compatibility section
    'f': ('show','graphics'), # Fill path using nonzero winding number rule
    'F': ('show','graphics'), # Fill path using nonzero winding number rule (obsolete)
    'f*': ('show','graphics'), # Fill path using even-odd rule
    'G': ('state','graphics'), # Set gray level for stroking operations
    'g': ('state','graphics'), # Set gray level for nonstroking operations
    'gs': ('state','graphics'), # (PDF 1.2) Set parameters from graphics state parameter dictionary
    'h': ('show','graphics'), # Close subpath
    'i': ('state','graphics'), # Set flatness tolerance
    'ID': ('point','image'), # Begin inline image data
    'j': ('state','graphics'), # Set line join style
    'J': ('state','graphics'), # Set line cap style
    'K': ('state','graphics'), # Set CMYK color for stroking operations
    'k': ('state','all'), # Set CMYK color for nonstroking operations
    'l': ('show','graphics'), # Append straight line segment to path
    'm': ('show','graphics'), # Begin new subpath
    'M': ('state','graphics'), # Set miter limit
    'MP': ('point','markedcontent'), # (PDF 1.2) Define marked-content point
    'n': ('show','graphics'), # End path without filling or stroking
    'q': ('state','all'), # Save graphics state
    'Q': ('state','all'), # Restore graphics state
    're': ('show','graphics'), # Append rectangle to path
    'RG': ('state','graphics'), # Set RGB color for stroking operations
    'rg': ('state','all'), # Set RGB color for nonstroking operations
    'ri': ('state','graphics'), # Set color rendering intent
    's': ('show','graphics'), # Close and stroke path
    'S': ('show','graphics'), # Stroke path
    'SC': ('state','graphics'), # (PDF 1.1) Set color for stroking operations
    'sc': ('state','all'), # (PDF 1.1) Set color for nonstroking operations
    'SCN': ('state','graphics'), # (PDF 1.2) Set color for stroking operations (ICCBased and special color spaces)
    'scn': ('state','all'), # (PDF 1.2) Set color for nonstroking operations (ICCBased and special color spaces)
    'sh': ('show','graphics'), # (PDF 1.3) Paint area defined by shading pattern
    'T*': ('state','text'), # Move to start of next text line
    'Tc': ('state','text'), # Set character spacing
    'Td': ('state','text'), # Move text position
    'TD': ('state','text'), # Move text position and set leading
    'Tf': ('state','text'), # Set text font and size
    'Tj': ('show','text'), # Show text
    'TJ': ('show','text'), # Show text, allowing individual glyph positioning
    'TL': ('state','text'), # Set text leading
    'Tm': ('state','text'), # Set text matrix and text line matrix
    'Tr': ('state','text'), # Set text rendering mode
    'Ts': ('state','text'), # Set text rise
    'Tw': ('state','text'), # Set word spacing
    'Tz': ('state','text'), # Set horizontal text scaling
    'v': ('show','graphics'), # Append curved segment to path (initial point replicated)
    'w': ('state','graphics'), # Set line width
    'W': ('show','all'), # Set clipping path using nonzero winding number rule
    'W*': ('show','all'), # Set clipping path using even-odd rule
    'y': ('show','graphics'), # Append curved segment to path (final point replicated)
    "'": ('show','text'), # Move to next line and show text
    '"': ('show','text')  # Set word and character spacing, move to next line, and show text
}