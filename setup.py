"""
openff-recharge
An automated framework for generating optimized partial charges for molecules.
"""
import sys
from setuptools import setup, find_namespace_packages
import versioneer

short_description = __doc__.split("\n")

# from https://github.com/pytest-dev/pytest-runner#conditional-requirement
needs_pytest = {"pytest", "test", "ptr"}.intersection(sys.argv)
pytest_runner = ["pytest-runner"] if needs_pytest else []

try:
    with open("README.md", "r") as handle:
        long_description = handle.read()
except IOError:
    long_description = "\n".join(short_description[2:])


setup(
    # Self-descriptive entries which should always be present
    name="openff-recharge",
    author="Simon Boothroyd",
    author_email="simon.boothroyd@colorado.edu",
    description=short_description[0],
    long_description=long_description,
    long_description_content_type="text/markdown",
    version=versioneer.get_version(),
    cmdclass=versioneer.get_cmdclass(),
    license="MIT",
    # Which Python importable modules should be included when your package is installed
    # Handled automatically by setuptools. Use 'exclude' to prevent some specific
    # subpackage(s) from being added, if needed
    packages=find_namespace_packages(include=["openff.*"]),
    # Optional include package data to ship with your package
    # Customize MANIFEST.in if the general case does not suit your needs
    # Comment out this line to prevent the files from being packaged with your software
    include_package_data=True,
    # Allows `setup.py test` to work correctly with pytest
    setup_requires=[] + pytest_runner,
    # Required packages, pulls from pip if needed; do not use for Conda deployment
    install_requires=[
        # Core dependencies
        "click",
        "numpy",
        "pydantic",
        # ESP generation
        "jinja2",
        # ESP storage
        "sqlalchemy",
        # Python <3.8 compatibility
        "typing-extensions",
    ],
    # Set up the main CLI entry points
    entry_points={
        "console_scripts": [
            "openff-recharge=openff.recharge.cli:cli",
        ],
    },
    # Python version restrictions
    python_requires=">=3.6",
)
