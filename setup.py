#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Licence
#
# FilterPype is a process-flow pipes-and-filters Python framework.
# Copyright (c) 2009-2012 Flight Data Services Ltd
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

# http://cburgmer.posterous.com/pip-requirementstxt-and-setuppy
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
    name='FilterPype',
    version = VERSION,
    url='http://www.filterpype.org/',
    author='Flight Data Services Ltd',
    author_email='developers@flightdataservices.com',            
    description='FilterPype is a process-flow pipes-and-filters Python framework.',
    long_description = open('README').read() + open('CHANGES').read(),
    download_url='http://www.filterpype.org/',
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
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 2.5",                
        "Programming Language :: Python :: 2.6",        
        "Programming Language :: Python :: 2.7",
        "Operating System :: OS Independent",
        "Topic :: Scientific/Engineering :: Information Analysis",
        "Topic :: Software Development :: Libraries :: Application Frameworks",
        "Topic :: Software Development :: Libraries :: Python Modules",
    	],                  
    )
