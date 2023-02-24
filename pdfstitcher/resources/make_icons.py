#! /usr/bin/env python3

import os
import sys
import shutil
import argparse
import subprocess

from os.path import dirname, abspath, join

ICONS_PATH = dirname(abspath(__file__))
input_file = join(ICONS_PATH, "stitcher-icon.svg")
sp_args = dict(shell=True, cwd=ICONS_PATH, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)


def parse_arguments():
    parser = argparse.ArgumentParser(
        description="Create PDFStitcher icons for Windows and macOS. Requires Inkscape <https://inkscape.org/> and ImageMagick <https://imagemagick.org/>.",
    )
    parser.add_argument(
        "--inkscape",
        "-i",
        help="Alternative path to the Inkscape binary. Will be determined automatically if not set.",
    )
    parser.add_argument(
        "--magick",
        "-m",
        help="Alternative path to the ImageMagick binary. Will be determined automatically if not set.",
    )
    parser.add_argument(
        "--nowindows",
        "-nw",
        help="Skip creating icons for Windows.",
        action="store_false",
        dest="windows",
    )
    parser.add_argument(
        "--nomacos",
        "-nm",
        help="Skip creating icons for macOS.",
        action="store_false",
        dest="macos",
    )
    return parser.parse_args()


def get_inkscape_command(args):
    if args.inkscape is not None:
        inkscape = args.inkscape
    else:
        inkscape = shutil.which("inkscape")
        if sys.platform.startswith("win32"):
            if inkscape is None:
                inkscape = r"C:\Program Files\Inkscape\bin\inkscape.exe"

    if not os.path.exists(inkscape):
        print("Inkscape binary not found.", file=sys.stderr)
        sys.exit()

    return inkscape


def get_convert_command(args):
    if args.magick is not None:
        binary = args.magick
    else:
        if sys.platform.startswith("win32"):
            binary = shutil.which("magick")
        else:
            # on Linux (Ubuntu 20.04), the convert command is only available directly
            # not sure what applies to macOS
            binary = shutil.which("convert")

    if not os.path.exists(binary):
        print("ImageMagick binary not found.", file=sys.stderr)
        sys.exit()

    if sys.platform.startswith("win32"):
        command = binary + " convert"
    else:
        command = binary

    return command


def generate_icons_windows(convert_cmd):
    output = join(ICONS_PATH, "stitcher-icon.ico")
    command = f"{convert_cmd} -background none {input_file} -define icon:auto-resize {output}"
    print(command)
    subprocess.run(command, **sp_args)


def generate_icons_macos(inkscape_cmd):
    # create the different sized PNGs for mac

    out_directory = join(ICONS_PATH, "stitcher-icon.iconset")
    prefix = join(out_directory, "icon")

    # complete set of icons defined at https://developer.apple.com/library/archive/documentation/GraphicsAnimation/Conceptual/HighResolutionOSX/Optimizing/Optimizing.html
    sizes = (16, 32, 128, 256, 512)

    for i, size in enumerate(sizes):
        if i % 2 == 0:
            output = f"{prefix}_{sizes[i]}x{sizes[i]}.png"
        else:
            output = f"{prefix}_{sizes[i-1]}x{sizes[i-1]}@2x.png"
        icon_command = f"{inkscape_cmd} -o {output} -w {size} -h {size} {input_file}"
        print(icon_command)
        subprocess.run(icon_command, **sp_args)

    if sys.platform.startswith("darwin"):
        # if on macOS, bundle the icon set
        iconutil_cmd = shutil.which("iconutil")
        bundle_command = f"{iconutil_cmd} -c icns {out_directory}"
        print(bundle_command)
        subprocess.run(bundle_command, **sp_args)


def main():
    args = parse_arguments()

    if args.windows:
        convert_cmd = get_convert_command(args)
        generate_icons_windows(convert_cmd)

    if args.macos:
        inkscape_cmd = get_inkscape_command(args)
        generate_icons_macos(inkscape_cmd)


if __name__ == "__main__":
    main()
