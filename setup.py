#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Licence
#
# FilterPype is a process-flow pipes-and-filters Python framework.
# Copyright (c) 2009-2011 Flight Data Services
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

try:
    from setuptools import setup, find_packages
except ImportError:
    from ez_setup import use_setuptools
    use_setuptools()
    from setuptools import setup, find_packages
 
from filterpype import __version__ as VERSION

test_requirements = ['mock']

setup(
    # === Meta data ===
    
    # Required meta data
    name='FilterPype',
    version = VERSION,
    url='http://www.filterpype.org/',
    
    # Optional meta data   
    author='Flight Data Services',
    author_email='developers@flightdataservices.com',            
    description='FilterPype is a process-flow pipes-and-filters Python framework.',    
    long_description='''\
    FilterPype is being used for multi-level data analysis, but could be applied to
    many other areas where it is difficult to split up a system into small
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
    classifiers='',
    platforms='',
    license='MIT',

    packages = find_packages(exclude=['lextab.*', 'parsetab.*']),      
                
    #include_package_data = True, 

    package_data = {
        # Include the required files
        '': ['pypes/*.pype'],
    },

    test_suite = 'nose.collector',        
    tests_require = test_requirements, 
    setup_requires = ['nose>=1.0'],
    install_requires = ['setuptools>=0.6b1', 
                        'configobj', 
                        'ply>=3.3'] + test_requirements,
    zip_safe = False,        
    )
