import os
from setuptools import setup

_packages = ["ipypb"]

opts = dict(name="ipypb",
            description="Native Interactive Progress Bar",
            keywords = "progressbar",
            version = "0.1.0",
            license="MIT",
            author="Evgeny Frolov",
            platforms=["any"],
            packages=_packages)

if __name__ == '__main__':
    setup(**opts)
