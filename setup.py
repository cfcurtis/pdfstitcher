#!/usr/bin/env python
from setuptools import setup
from setuptools.command.install import install
from babel.messages.frontend import compile_catalog

# Shamelessly copied from https://stackoverflow.com/a/41120180
class InstallWithCompile(install):
    def run(self):
        compiler = compile_catalog(self.distribution)
        option_dict = self.distribution.get_option_dict('compile_catalog')
        compiler.directory = option_dict['directory'][1]
        compiler.domain = [option_dict['domain'][1]]
        compiler.run()
        super().run()

setup(
    cmdclass={
        "install": InstallWithCompile
    }
)