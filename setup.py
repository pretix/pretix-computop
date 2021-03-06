import os
from distutils.command.build import build

from django.core import management
from setuptools import find_packages, setup

from pretix_firstcash import __version__


try:
    with open(
        os.path.join(os.path.dirname(__file__), "README.rst"), encoding="utf-8"
    ) as f:
        long_description = f.read()
except Exception:
    long_description = ""


class CustomBuild(build):
    def run(self):
        management.call_command("compilemessages", verbosity=1)
        build.run(self)


cmdclass = {"build": CustomBuild}


setup(
    name="pretix-computop",
    version=__version__,
    description="Use Computop based payment providers",
    long_description=long_description,
    url="https://github.com/pretix/pretix-computop",
    author="Phin Wolkwitz",
    author_email="wolkwitz@rami.io",
    license="Apache",
    install_requires=["pycryptodome==3.14.*"],
    packages=find_packages(exclude=["tests", "tests.*"]),
    include_package_data=True,
    cmdclass=cmdclass,
    entry_points="""
[pretix.plugin]
pretix_computop=pretix_computop:PretixPluginMeta
pretix_firstcash=pretix_firstcash:PretixPluginMeta
""",
)
