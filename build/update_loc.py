#! /usr/bin/env python3

import sys
import argparse
from subprocess import run
from os import listdir
from pathlib import Path


locale_path = Path(__file__).parent.parent / "resources" / "locale"


def parse_args():
    parser = argparse.ArgumentParser(description="Extract, update, or compile translations.")
    parser.add_argument(
        "--extract",
        "-e",
        action="store_true",
    )
    parser.add_argument(
        "--update",
        "-u",
        action="store_true",
    )
    parser.add_argument(
        "--compile",
        "-c",
        action="store_true",
    )
    parser.add_argument(
        "--all",
        "-a",
        action="store_true",
    )
    return parser.parse_args()


def extract():
    print("**extract**")
    run(
        f'pybabel extract -F babel.cfg -o {locale_path / "pdfstitcher.pot" } --add-comments="translation_note" '
        + '--copyright-holder="Charlotte Curtis" --project=pdfstitcher .',
        shell=True,
    )


def update():
    print("**update**")
    locales = [lp for lp in listdir(locale_path) if (locale_path / lp).is_dir()]
    print(locales)

    for lang in locales:
        invoke_args = f' -D pdfstitcher -d {locale_path} -i {locale_path / "pdfstitcher.pot"} -l {lang}'
        if (locale_path / lang / "LC_MESSAGES" / "pdfstitcher.po").exists():
            cmd = "pybabel update" + invoke_args
        else:
            cmd = "pybabel init" + invoke_args
        run(cmd, shell=True)


def compile():
    print("**compile**")
    run(f"pybabel compile -D pdfstitcher -d {locale_path}", shell=True)


if __name__ == "__main__":
    args = parse_args()

    do_all = False
    if args.all or len(sys.argv) < 2:
        do_all = True

    if args.extract or do_all:
        extract()
    if args.update or do_all:
        update()
    if args.compile or do_all:
        compile()
