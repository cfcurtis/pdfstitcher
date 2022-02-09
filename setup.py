#!/usr/bin/env python
from setuptools import setup
from setuptools.command.install import install

# From https://milkr.io/kfei/5-common-patterns-to-version-your-Python-package/5
version = {}
with open("pdfstitcher/version.py") as fp:
    exec(fp.read(), version)

# Shamelessly copied from https://stackoverflow.com/a/41120180
class InstallWithCompile(install):
    def run(self):
        from babel.messages.frontend import compile_catalog
        compiler = compile_catalog(self.distribution)
        option_dict = self.distribution.get_option_dict('compile_catalog')
        compiler.domain = [option_dict['domain'][1]]
        compiler.directory = option_dict['directory'][1]
        compiler.run()
        super().run()

setup(
    cmdclass={
        'install': InstallWithCompile,
    },
    package_data={'': ['locale/*/*/*.mo', 'locale/*/*/*.po']},
    version = version['__version__']
)