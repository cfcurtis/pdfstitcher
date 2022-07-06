#!/usr/bin/env python
from setuptools import setup
from setuptools.command.install import install
from setuptools.command.develop import develop
from babel.messages.frontend import compile_catalog


def run_compile(cmdclass):
    # Shamelessly copied from https://stackoverflow.com/a/41120180
    compiler = compile_catalog(cmdclass.distribution)
    compiler.directory = "pdfstitcher/locale"
    compiler.domain = ["pdfstitcher"]
    compiler.run()


class InstallWithCompile(install):
    def run(self):
        run_compile(self)
        super().run()


class DevelopWithCompile(develop):
    def run(self):
        run_compile(self)
        super().run()


setup(cmdclass={"install": InstallWithCompile, "develop": DevelopWithCompile})
