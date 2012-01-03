#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Licence
#
# FilterPype is a process-flow pipes-and-filters Python framework.
# Copyright (c) 2009-2011 Flight Data Services Ltd
# http://www.filterpype.org
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

import re

try:
    from setuptools import setup, find_packages
except ImportError:
    from distribute_setup import use_setuptools
    use_setuptools()
    from setuptools import setup, find_packages

def parse_requirements(file_name):
    """
    Extract all dependency names from requirements.txt.
    """
    requirements = []
    for line in open(file_name, 'r').read().split('\n'):
        if re.match(r'(\s*#)|(\s*$)', line):
            continue
        if re.match(r'\s*-e\s+', line):
            # TODO support version numbers
            requirements.append(re.sub(r'\s*-e\s+.*#egg=(.*)$', r'\1', line))
        elif re.match(r'\s*-f\s+', line):
            pass
        else:
            requirements.append(line)

    requirements.reverse()
    return requirements

def parse_dependency_links(file_name):
    """
    Extract all URLs for packages not found on PyPI.
    """
    dependency_links = []
    for line in open(file_name, 'r').read().split('\n'):
        if re.match(r'\s*-[ef]\s+', line):
            dependency_links.append(re.sub(r'\s*-[ef]\s+', '', line))

    dependency_links.reverse()
    return dependency_links
 
from filterpype import __version__ as VERSION

setup(
    # === Meta data ===
    
    # Required meta data
    name='FilterPype',
    version = VERSION,
    url='http://www.filterpype.org/',
    
    # Optional meta data   
    author='Flight Data Services Ltd',
    author_email='developers@flightdataservices.com',            
    description='FilterPype is a process-flow pipes-and-filters Python framework.',    
    long_description='''\
    FilterPype is being used for multi-level data analysis, but could be applied 
    to many other areas where it is difficult to split up a system into small
    independent parts

    Some of its features:

     - Advanced algorithms broken down into simple data filter coroutines
     - Pipelines constructed from filters in the new FilterPype mini-language
     - Domain experts assemble pipelines with no Python knowledge required
     - Sub-pipelines and filters linked by automatic pipeline construction
     - All standard operations available: branching, joining and looping
     - Recursive coroutine pipes allowing calculation of e.g. factorials
     - Using it is like writing a synchronous multi-threaded program
    ''',    
    download_url='http://www.filterpype.org/',
    platforms='',
    license='MIT',

    packages = find_packages(exclude=['lextab.*', 'parsetab.*']),                      
    include_package_data = True, 

    # Parse the 'requirements.txt' file to determine the dependencies.
    install_requires = parse_requirements('requirements.txt'), 
    dependency_links = parse_dependency_links('requirements.txt'),
    setup_requires = ['nose>=1.0'],
    test_suite = 'nose.collector',
    
    zip_safe = False,  
    classifiers = [
        "Development Status :: 5 - Production/Stable",  	
        "Environment :: Console",
        "Intended Audience :: Developers",
        "Intended Audience :: Science/Research",
        "License :: Other/Proprietary License",
        "Programming Language :: Python :: 2.7",
        "Operating System :: OS Independent",
        "Topic :: Software Development :: Libraries :: Application Frameworks",
        "Topic :: Software Development :: Libraries :: Python Modules",
    	],                  
    )
