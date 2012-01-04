# -*- coding: utf-8 -*-
# ppln_demo.py

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


import sys
import re
##from configobj import ConfigObj
import os
import pprint as pp

import filterpype.data_filter as df
import filterpype.filter_utils as fut
import filterpype.data_fltr_base as dfb
import filterpype.pipeline as ppln


##class CopyFile(ppln.Pipeline):
    ##"""Copy a file. Pass in values for keywords file_from_name, file_to_name.
    ##"""
    
    ##config = '''
    ##[--main--]
    ##ftype = copy_file
    
    ##[--keys--]          
    ##essential = file_from_name, file_to_name
    
    ##[read_batch]
    ##size = 1000  # or 10

    ##[--route--]
    ##read_batch:1000 
    ##write_file
    ##'''
        
    ##def update_filters(self):
        ##self.getf('read_batch').source_file_name = self.file_from_name
        ##self.getf('write_file').dest_file_name = self.file_to_name
        
        
class Factorial(ppln.Pipeline):
    """Recursion to calculate factorials.
    """
    config = '''
    [--main--]
    ftype = factorial
    description = Recursive filter to show looping, while calculating factorials
    
    # Check print_connections
    [--route--]
    tank_queue:0:true >>>
    factorial_calc >>>
    branch_if:recurse >>>
        (tank_feed >>> tank_queue)
    sink
    '''
    
 
#=================================================================

class InnerBar(ppln.Pipeline):
    """Test inner pipeline class
    """
    config = '''
    [--main--]
    ftype = inner_bar
    keys = temperature, speed
    
    [py_print_vars]
    x = 3
    y = x + 4
    # NB Using %s for string formatting, not %d
    print '**14400** Inside py_print_vars'
    print '**14410** packet.data = "%s"' % packet.data
    print '**14450** temperature = %s' % ${temperature}
    print '**14460** speed = %s' % ${speed}
    print '**14480** SPEED = %s' % '%SPEED'
    
    ##[py_set_vars]
    ##SPEED = 73
    
    [--route--]
    ##py_set_vars >>>
    py_print_vars
    '''
        
    
class SmallPipeBaz(ppln.Pipeline):
    """Test inner small baz pipeline
    """
    config = '''
    [--main--]
    ftype = small_pipe_baz
    key = temperature, speed
    
    [py_pointless]
    TEMPERATURE = 1200
    SPEED = 90

    [--route--]
    # ${temperature} will substitute once at the beginning
    # %TEMPERATURE will substitute values each time
    # inner_bar:${temperature}
    
    inner_bar:%TEMPERATURE:%SPEED
    '''
    
class Freda(object):
    speed = 50
    
class Jane(Freda):
    def __getattribute__(self, attr_name):
        return 'fred'
    
class Alison(object):
    def _hidden__getattribute__(self, attr_name):
        superclass = Alison.__bases__[0]
        value = superclass.__getattribute__(self, attr_name)
        try:
            if value.startswith('%'):
                return 'fred'
            else:
                return value
        except AttributeError:
            return value
         
#=================================================================
        

class VariableBatchPipeline(ppln.Pipeline):

    config = '''\
    [--main--]
    ftype = embedded_batch_sizing
    description = Pipeline should batch alternately
    
    [batch]
    dynamic = true
    size = %BATCH_SIZE
    
    [py_init]
    if BATCH_SIZE == '$$<unset>$$':
        BATCH_MODE = 'size'
        BATCH_SIZE = 2
    
    [py_batch_sizer]
    print '**12550** BATCH_SIZE = %s, PREV_BATCH_MODE = %s' % (
        BATCH_SIZE, PREV_BATCH_MODE)
    
    if BATCH_MODE == 'size':
        BATCH_SIZE = int(packet.data) 
        BATCH_MODE = 'data'
    else:
        BATCH_MODE = 'size'
        BATCH_SIZE = 2
        
    print '**12560** BATCH_SIZE = %s, PREV_BATCH_MODE = %s' % (
        BATCH_SIZE, PREV_BATCH_MODE)
    if PREV_BATCH_MODE == 'data':
        BATCH_SIZE == 2
        PREV_BATCH_MODE = 'size'
    else:  # PREV_BATCH_MODE == 'size'
        BATCH_SIZE = int(packet.data) 
        PREV_BATCH_MODE = 'data'
    print '**12570** BATCH_SIZE = %s, PREV_BATCH_MODE = %s' % (
        BATCH_SIZE, PREV_BATCH_MODE)
    
    
    [--route--]
    py_init >>>
    batch >>>
    py_batch_sizer >>>
    sink
    '''
    
    
class SimpleLoop(ppln.Pipeline):
    """Simple loop to print counter.
    """
    
    config = '''
    [--main--]
    ftype = simple_loop
    description = TO-DO: docstring
    
    [--route--]
    tank_queue 
    '''

class ReverseChars(ppln.Pipeline):
    """Takes string input and returns a reversed string.
    """
    
    config = '''
    [--main--]
    ftype = reverse_chars
    description = TO-DO: docstring
    
    [--route--]
    reverse_string >>>
    sink
    '''
        
    
class SquareNumber(ppln.Pipeline):
    """Test simple function to square numbers in a pipeline.
    """
    
    config = '''
    [--main--]
    ftype = square_number
    description = TO-DO: docstring

    [--route--]
    square_if_number >>>
    sink
    '''

    
class TempMultipleAB(ppln.Pipeline):
    """Spike for putting data into multiple pipes.
    """
    
    config = '''
    [--main--]
    ftype = temp_multiple_ab
    description = TO-DO: docstring
    keys1 = a1, a2, b1, b2
    keys2 = w:1, x:2, y:3, z:4

    [--route--]
    temp_text_after1:${a1} >>>
    temp_text_before1:${b1} >>>
    reverse_string1 >>>
    temp_text_after2:${a2} >>>
    temp_text_before2:${b2} >>>
    reverse_string2
    '''
    
    ##def update_filters(self):
        ##self.getf('temp_text_after1').text_after = self.a1
        ##self.getf('temp_text_after2').text_after = self.a2
        ##self.getf('temp_text_before1').text_before = self.b1
        ##self.getf('temp_text_before2').text_before = self.b2
    
    
class TempMultipleSpace(ppln.Pipeline):
    
    config = '''
    [--main--]
    ftype = temp_multiple_space
    description = TO-DO: docstring
    keys = a1, a2, b1, b2
    
    [--route--]
    temp_multiple_ab >>>
    temp_space
    '''
                
    def update_filters(self):
        self.getf('temp_multiple_ab').a1 = self.a1
        self.getf('temp_multiple_ab').a2 = self.a2
        self.getf('temp_multiple_ab').b1 = self.b1
        self.getf('temp_multiple_ab').b2 = self.b2
        

class WordsInCaps(ppln.Pipeline):
    """Take each word in the data and capitalise.
    """
    
    config = '''
    [--main--]
    ftype = words_in_caps
    description = TO-DO: docstring
    key = join_words_with:~
    
    [--route--]
    split_words >>>
    capitalise >>>
    join:${join_words_with}
    '''
    
    ##def __init__(self, factory, config=None, **kwargs):
        ##ppln.Pipeline.__init__(self, factory, config, **kwargs)
  
