#!/usr/bin/env python
from setuptools import setup
from pdfstitcher.version import __version__

# compile translation messages
from pdfstitcher.update_loc import compile
compile()

setup(
    package_data={'': ['locale/*/*/*.mo', 'locale/*/*/*.po']},
    version = __version__
)