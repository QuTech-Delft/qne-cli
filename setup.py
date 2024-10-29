""" Quantum Network Explorer ADK

Copyright (c) 2024 QuTech

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""
from setuptools import setup, find_packages


def get_version_number(module):
    """Extract the version number from the source code.
    Returns:
        Str: the version number.
    """
    with open("src/{}/version.py".format(module), "r") as file_stream:
        line = file_stream.readline().split()
        version_number = line[2].replace("'", "")
    return version_number


def get_long_description():
    """Extract the long description from the README file"""

    with open("README.md", encoding="utf-8") as f:
        long_description = f.read()

    return long_description


setup(
    name="qne-adk",
    description="Application Development Kit to interact with the Quantum Network Explorer",
    long_description=get_long_description(),
    long_description_content_type="text/markdown",
    version=get_version_number("adk"),
    author="QuTech-Delft",
    author_email="support@quantum-network.com",
    url="https://github.com/QuTech-Delft/qne-adk",
    python_requires=">=3.8",
    package_dir={"": "src"},
    package_data={"": ["networks/*.json",
                       "schema/applications/*.json",
                       "schema/experiments/*.json",
                       "schema/networks/*.json"]},
    entry_points={
        "console_scripts": [
            "qne=adk.command_list:app",
        ]
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Environment :: Console",
        "Intended Audience :: Developers",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: MIT License",
        "Operating System :: MacOS",
        "Operating System :: Microsoft :: Windows",
        "Operating System :: POSIX :: Linux",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Topic :: Scientific/Engineering",
    ],
    license="MIT",
    packages=find_packages(where="src", exclude=["*tests*"]),
    install_requires=["typer[all]", "netqasm==0.13.3", "pydantic>=2.1.1", "pydantic-settings",
                      "tabulate", "jsonschema>=4.19.0", "referencing", "pyyaml", "typing-extensions",
                      "apistar", "typesystem==0.2.4", "pyjwt"],
    extras_require={
        "dev": ["pylint", "coverage>=4.5.1", "mypy", "pytest", "black", "isort", "types-tabulate", "types-PyYAML",
                "types-requests"],
        "rtd": [
            "sphinx<8",
            "sphinx_rtd_theme==1.3.0",
            "nbsphinx",
            "sphinx-automodapi",
            "recommonmark",
        ],
    },
)
