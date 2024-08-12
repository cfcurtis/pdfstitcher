#! /usr/bin/env python3

import sys
import argparse
from subprocess import run
from os import listdir
from pathlib import Path

# can't use importlib in github build pipeline, so read the toml directly
import tomli

root_dir = Path(__file__).parent.parent

with open(root_dir / "pyproject.toml", mode="rb") as f:
    toml_file = tomli.load(f)

pdfstitcher_version = toml_file["project"]["version"]

locale_path = root_dir / "resources" / "locale"


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
        "pybabel extract "
        f'-F {locale_path / "babel.cfg"} '
        f'-o {locale_path / "pdfstitcher.pot" } '
        "--project=pdfstitcher . "
        '--add-comments="translation_note" '
        "-w 100 "
        '--copyright-holder="Charlotte Curtis" '
        "--msgid-bugs-address=ccurtis@mtroyal.ca "
        f"--version={pdfstitcher_version} ",
        shell=True,
    )


def update():
    print("**update**")
    locales = [lp for lp in listdir(locale_path) if (locale_path / lp).is_dir()]
    print(locales)

    for lang in locales:
        invoke_args = (
            f' -D pdfstitcher -d {locale_path} -i {locale_path / "pdfstitcher.pot"} -l {lang}'
        )
        if (locale_path / lang / "LC_MESSAGES" / "pdfstitcher.po").exists():
            cmd = "pybabel update" + invoke_args
        else:
            cmd = "pybabel init" + invoke_args
        run(cmd, shell=True)


def compile():
    print("**compile**")
    run(f"pybabel compile --use-fuzzy -D pdfstitcher -d {locale_path}", shell=True)


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
