import setuptools
from codecs import open
from setuptools import setup

setup(
    name='textfsm',
    maintainer_email='textfsm-dev@googlegroups.com',
    version='2.0',
    packages=setuptools.find_packages(),
    description='Python module for parsing semi-structured text into tables.',
    long_description=readme(),
    long_description_content_type='text/markdown',
    url='https://github.com/google/textfsm',
    license='Apache License 2.0',
) # removed some commented lines