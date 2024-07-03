from pathlib import Path

from setuptools import setup

this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text()

setup(
    name="te_schemas",
    version="2.1.16",
    description="Schemas supporting the Trends.Earth QGIS plugin.",
    long_description=long_description,
    url="https://github.com/ConservationInternational/trends.earth-schemas",
    author="Conservation International",
    author_email="trends.earth@conservation.org",
    license="GPL-2.0",
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "Intended Audience :: Science/Research",
        "Topic :: Scientific/Engineering :: GIS",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
    ],
    keywords="land degradation LDN SDG sustainable development goals",
    packages=["te_schemas"],
    package_dir={"te_schemas": "te_schemas"},
    package_data={"te_schemas": ["version.json"]},
    include_package_data=True,
    install_requires=[
        "defusedxml>=0.7.1",
        "marshmallow>=3.21.3",
        "marshmallow-dataclass[enum, union]==8.7.0",
    ],
    extras_require={
        "dev": ["check-manifest"],
        "test": ["coverage"],
    },
)
