# -*- coding: utf-8 -*-
"""setup.py."""


import setuptools


def read_file(fname):
    """Read file and return the its content."""
    with open(fname, "r") as f:
        return f.read()


def get_attr(fname, attr):
    """Read file and return specific "attribute" content."""
    lines = read_file(fname)
    for line in lines.splitlines():
        if line.startswith(attr):
            delim = '"' if '"' in line else "'"
            return line.split(delim)[1]
    raise RuntimeError("Unable to find string.")


ver_file = "src/__version__.py"
init_file = "src/__init__.py"
name = "magicformulabr"

setuptools.setup(
    name=name,
    version=get_attr(ver_file, "__version__"),
    description=get_attr(init_file, "__description__"),
    author=get_attr(init_file, "__author__"),
    url=get_attr(init_file, "__url__"),
    license=get_attr(init_file, "__license__"),
    long_description=read_file("README.md"),
    long_description_content_type="text/markdown",
    install_requires=read_file("requirements.txt").splitlines(),
    packages=setuptools.find_packages(
        exclude=(["tests", "*.tests", "*.tests.*", "tests.*"])
    ),
    include_package_data=True,
    classifiers=[
        "License :: OSI Approved :: MIT License",
        "Environment :: Console",
        "Topic :: Software Development",
        "Topic :: Terminals",
        "Topic :: Utilities",
        "Programming Language :: Python :: 3",
        "Intended Audience :: Developers",
        "Intended Audience :: System Administrators",
        "Operating System :: OS Independent",
    ],
    # flake8: noqa: E231
    entry_points={
        "console_scripts": [
            "magicformulabr=src.magicformulabr:main",
        ],
    },
)

# vim: ts=4
