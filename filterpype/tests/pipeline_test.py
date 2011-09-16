# -*- coding: utf-8 -*-
# pipeline_test.py

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

 
import StringIO
import os
import sys
import unittest 
import time
import configobj
import mock

import filterpype.data_fltr_base as dfb
import filterpype.data_filter as df
import filterpype.pipeline as ppln
import filterpype.ppln_demo as ppln_demo
import filterpype.filter_factory as ff
import filterpype.filter_utils as fut
import filterpype.profiler_fp as prof

data_dir3 = os.path.join(fut.abs_dir_of_file(__file__), 
                         'test_data', 'tst_data3')
##data_dir4 = 'test_data4'
data_dir5 = os.path.join(fut.abs_dir_of_file(__file__), 
                         'test_data', 'tst_data5')

k_run_long_tests = True

def dir_fn3(fname):
    return os.path.join(data_dir3, fname)

def dir_fn4(fname):
    return os.path.join(data_dir4, fname)

file_in_name1 = dir_fn3('file_data1.dat')
file_out_name1 = dir_fn3('file_data1.out')
file_in_name2 = dir_fn3('file_data2.dat')
file_out_name2 = dir_fn3('file_data2.out')

file_in_name5 = dir_fn3('file_data5.dat')
file_out_name5 = dir_fn3('file_data5.out')


data_files = {
    file_in_name1: 'abcdef',
    file_in_name2: '123456',
}

def make_data_files():
    for name, data in data_files.iteritems():
        f1 = open(name, 'wb')
        try:
            f1.write(data)
        finally:
            f1.close()

def setUp():
    make_data_files()
    
def tearDown():
    pass

class CheckKeySubstitutions(ppln.Pipeline):
    """Check that key substitutions ${pipeline_key} are successful."""
    
    config = '''
    [--main--]
    ftype = check_key_substitutions
    keys = integer:213, string_sub:process
    
    [test_key_substitutions]
    ftype = key_substitutions
    first_key = ${integer}
    second_key = do_not_${string_sub}_this
    
    [--route--]
    test_key_substitutions'''

    
class JustSink(ppln.Pipeline):
    """Simple class for testing closing context manager.
    """

    config = '''
    [--main--]
    ftype = testing
    description = TO-DO: docstring
        
    [--route--]
    sink1 >>>
    sink2
    '''

    ##def __init__(self, factory=None, **kwargs):
        ##ppln.Pipeline.__init__(self, factory, **kwargs)
        ##if self:
            ##pass
                
    def filter_data(self, packet):
        raise dfb.PipelineError, \
              'To check what happens with closer context manager'
                
                
class JustSinkBadFilter(ppln.Pipeline):
    # This now passes because the filters are made automatically.
    ##config = """
##[sink1]

##[sink2]

##[pipeline]
##route = '''
##sink1 
##sink3
##'''
##"""
    
    config = '''
    [--route--]
    sink1 >>>
    sink3 
    '''
    
class JustSinkDuplicateFilter1(ppln.Pipeline):

    config = '''
    # These two lines raise a configobj.DuplicateError
    [sink1]
    [sink1]
    
    [--route--]
    sink1
    '''
    
class CheckEssentialKeys3(ppln.Pipeline):
    """Wrapper class for CheckEssentialKeys. For that class
            keys = foo, bar, baz_opt:16
    """
    
    config = '''
    [--main--]
    ftype = check_some_keys
    description = TO-DO: docstring

    [--route--]
    check_essential_keys:456:bill >>>
    sink:20
    '''
    
class CheckDocString1(ppln.Pipeline):
    # No docstring

    config = '''
    [--main--]
    ftype = check_docstring1
    description = Testing check for docstring

    [--route--]
    pass_through
    '''

class CheckDocString2(ppln.Pipeline):
    """Class with no description but a somewhat longer docstring"""

    config = '''
    [--main--]
    ftype = check_docstring2

    [--route--]
    pass_through
    '''

class CheckDocString3(ppln.Pipeline):
    # Class with neither description nor __doc__

    config = '''
    [--main--]
    ftype = check_docstring3

    [--route--]
    pass_through
    '''

    
    
class CheckEssentialKeys3Missing(ppln.Pipeline):
    """Wrapper class for CheckEssentialKeys. For this class
            keys = foo, bar, baz_opt:16
    but "bar" is not given a value.
    """
    
    config = '''
    [--main--]
    ftype = check_some_keys_missing
    description = TO-DO: docstring

    [--route--]
    check_essential_keys:456 >>>
    sink:20
    '''
    
class TestExtractManyAttributesSplitWords(unittest.TestCase):
    def setUp(self):
        self.factory = ff.DemoFilterFactory()
        
    def test_extract_many_attributes_split_words(self):
        data_in = """
        TIME CHIP SERIAL IS: 5ABF3. OTHER VALUE IS: 312. SOME TRAILING TEXT
        """
        extractor = ppln.ExtractManyAttributesSplitWords(\
            factory=self.factory, split_on_str=". ", attr_delim='col')
        extractor_filter = extractor.getf('attribute_extractor')
        sink = df.Sink()
        extractor_filter.next_filter = sink
        extractor.send(dfb.DataPacket(data_in))
        #TEST PACKET NOT FILTER
        self.assertEqual(sink.results[0].time_chip_serial_is, '5ABF3')
        self.assertEqual(sink.results[1].other_value_is, '312')
    
class TestExtractManyAttributes(unittest.TestCase):
    """
    """
    
    def setUp(self):
        self.factory = ff.DemoFilterFactory()
        
    def test_extract_many_attributes(self):
        data_in = """
        person's name=Postman pat
        age=500000
        
        gender=mail
        
        
        hair col0ur=balding
        """
        
        extractor = ppln.ExtractManyAttributes(factory=self.factory,
                                               attr_delim='equals')
        extractor_filter = extractor.getf('attribute_extractor')
        sink = df.Sink()
        extractor_filter.next_filter = sink
        extractor.send(dfb.DataPacket(data_in))
        #TEST PACKET NOT FILTER
        self.assertEqual(sink.results[0].persons_name, 'Postman pat')
        self.assertEqual(sink.results[1].age, '500000')
        self.assertEqual(sink.results[2].gender, 'mail')
        self.assertEqual(sink.results[3].hair_col0ur, 'balding')
    
class TestEssentialKeys(unittest.TestCase):

    def setUp(self):
        self.factory = ff.DemoFilterFactory()
    
    def tearDown(self):
        pass
    
    def test_essential_keys(self):
        check1a = ppln.CheckEssentialKeys(factory=self.factory, 
                                          foo=123, bar='asdf', dynamic=True)
        return
        self.assertEquals(check1a.foo, 123)
        self.assertEquals(check1a.bar, 'asdf')
        self.assertEquals(check1a.baz_opt, 16)

    def test_essential_keys3(self):
        check3 = CheckEssentialKeys3(factory=self.factory)
        check1 = check3.getf('check_essential_keys')
        self.assertEquals(check1.foo, 456)
        self.assertEquals(check1.bar, 'bill')
        self.assertEquals(check1.baz_opt, 16)

    def test_essential_keys3missing(self):
        # "bar" is not given a value in the route.
        self.assertRaises(dfb.FilterAttributeError, CheckEssentialKeys3Missing,
                          factory=self.factory)

    def test_no_route_heading(self):
        config = '''
        [--main--]
        keys = e1, e2, p1:10, p2:20, p3:foo
        '''
        self.assertRaises(dfb.FilterRoutingError, ppln.Pipeline,
                          factory=self.factory, config=config)

    def test_no_route_section(self):
        config = '''
        [--main--]
        keys = e1, e2, p1:10, p2:20, p3:foo
        [--route--]
        '''
        self.assertRaises(dfb.FilterRoutingError, ppln.Pipeline,
                          factory=self.factory, config=config)
        config2 = '''
        [--main--]
        keys = e1, e2, p1:10, p2:20, p3:foo
        
        '''
        self.assertRaises(dfb.FilterRoutingError, ppln.Pipeline,
                          factory=self.factory, config=config2)

        
class TestCopyFile(unittest.TestCase):
    # Read binary file in and write it out. Source is either the file name or
    # an already opened file object.

    def setUp(self):
        self.factory = ff.DemoFilterFactory()
        self.file_name2 = os.path.join(data_dir5, 'short2.dat')
        self.file_name_out = os.path.join(data_dir5, 'short2.out')
        f2 = open(self.file_name2, 'wb')
        try:
            f2.write('one two three four five six')
        finally:
            f2.close()
        # Empty target file
        f3 = open(self.file_name_out, 'wb')
        f3.close()
        
    def tearDown(self):
        pass
    
    def test_copy_file_obj1(self):
        copy_file_ppln = ppln.CopyFile(
            factory=self.factory, dest_file_name=self.file_name_out)
        file_obj = open(self.file_name2, 'rb')
        self.assertEquals(os.path.getsize(self.file_name_out), 0)
        copy_file_ppln.send(dfb.DataPacket(file_obj))
        copy_file_ppln.shut_down()
        self.assertEquals(os.path.getsize(self.file_name_out), 27)
        self.assertEquals(os.path.getsize(self.file_name_out),
                          os.path.getsize(self.file_name2))
        print "**3213** sizes are equal"
 
    def test_copy_file_from_name(self):
        copy_file_ppln = ppln.CopyFile(
            factory=self.factory, source_file_name=self.file_name2,
            dest_file_name=self.file_name_out)
        self.assertEquals(os.path.getsize(self.file_name_out), 0)
        copy_file_ppln.send(dfb.DataPacket(None))
        copy_file_ppln.shut_down()
        self.assertEquals(os.path.getsize(self.file_name_out), 27)

class TestCopyFileCompression(unittest.TestCase):
    """ Tests for the CopyFileCompression Pipeline
    """
    
    def setUp(self):
        self.factory = ff.DemoFilterFactory()
        self.file_name = os.path.join(data_dir5, 'short_tst3.dat')
        self.file_name_out = os.path.join(data_dir5, 'short_tst3.dat.bz2')
        self.file_contents = 'one two three four five six'
        f2 = open(self.file_name, 'wb')
        try:
            f2.write(self.file_contents)
        finally:
            f2.close()
        # Empty target file
        #f3 = open(self.file_name_out, 'wb')
        #f3.close()
    
    def tearDown(self):
        pass

    def test_copy_file_obj1(self):
        if os.path.exists(self.file_name_out):
            os.remove(self.file_name_out)
        copy_file_comp_ppln = ppln.CopyFileCompression(
            factory=self.factory, dest_file_name=self.file_name,
            callback=mock.Mock())
        file_obj = open(self.file_name, 'rb')
        copy_file_comp_ppln.send(dfb.DataPacket(file_obj))
        copy_file_comp_ppln.shut_down()

        # Uncompress file and check its size and content
        import bz2
        decomp = bz2.BZ2Decompressor()
        out_file_fd = open(self.file_name_out, 'r')
        new_file_data = bz2.decompress(out_file_fd.read())
        out_file_fd.close()
        
        self.assertEquals(len(new_file_data), 27)
        self.assertEquals(len(new_file_data), os.path.getsize(self.file_name))
        self.assertEquals(new_file_data, self.file_contents)
        print "**1835** sizes are equal"
    
    def test_pipeline_for_memory_leaks(self):
        self.assertEquals(self.function_for_tst_pipeline_for_memory_leaks(), 3)

    def function_for_tst_pipeline_for_memory_leaks(self):
        """ Function to help with test_pipeline_for_memory_leaks.
        
            This is not a test all on its own
        """
        file_name = os.path.join(data_dir5, 'short_tst4.dat')
        test_file_fd = open(file_name, 'w')
        
        test_file_fd.write(1000*'A')
        test_file_fd.close()

        
        for x in xrange(3000):
            copy_file_comp_ppln = ppln.CopyFileCompression(
                factory=self.factory, dest_file_name=self.file_name,
                callback=mock.Mock())

            if os.path.exists(self.file_name_out):
                os.remove(self.file_name_out)
            file_obj = open(self.file_name, 'rb')
            
            copy_file_comp_ppln.send(dfb.DataPacket(file_obj))
            copy_file_comp_ppln.flush_buffer()
            copy_file_comp_ppln.shut_down()

        if os.path.exists(os.path.join(data_dir5, 'short_tst4.dat')):
            os.remove(os.path.join(data_dir5, 'short_tst4.dat'))
        copy_file_comp_ppln.shut_down()
        
        return 3

class TestDocString(unittest.TestCase):
    # Test for the existence of either __doc__ or description.
    # Raise exception if neither.

    def setUp(self):
        self.factory = ff.DemoFilterFactory()

    def tearDown(self):
        pass
    
    def test_docstring1(self):
        docstring1 = CheckDocString1(factory=self.factory)
        self.assertEquals(len(docstring1.__doc__), 27)

    def test_docstring2(self):
        docstring2 = CheckDocString2(factory=self.factory)
        self.assertEquals(len(docstring2.__doc__), 59)

    def test_docstring3(self):
        self.assertRaises(dfb.PipelineConfigError, CheckDocString3, 
                          factory=self.factory)


class TestDynamicParams(unittest.TestCase):

    def setUp(self):
        self.factory = ff.DemoFilterFactory()
        
        self.config1 = '''\
        [--main--]
        ftype = demo_dynamic_pipeline1 
        description = Pipeline to test dynamic parameter setting
        keys = foo, bar:27
        # dynamic can be defined here along with the Pipelines constructor.
        dynamic = True
        
        [py_set_param]
        print '**16125** Setting SPEED to 170'
        SPEED = 170
        
        [--route--]
        py_set_param >>>
        pass_through
        '''

    def tearDown(self):
        pass
    
    def test_static_pipeline(self):
        pipeline21 = ppln.Pipeline(factory=self.factory, config=self.config1,
                                   foo='jim', dynamic=False)
        self.assertEquals(pipeline21.foo, 'jim')
        self.assertEquals(pipeline21.bar, 27)
        pipeline21.bar = 456
        self.assertEquals(pipeline21.bar, 456)
        
    def test_dynamic_pipeline1(self):
        # Set dynamic=True in the kwargs passed in
        pipeline22 = ppln.DynamicPipeline(factory=self.factory, 
                                          config=self.config1,
                                          foo='jim')
        self.assertEquals(pipeline22.foo, 'jim')
        self.assertEquals(pipeline22.bar, 27)
        pipeline22.bar = '%SPEED'
        # All u/c params should default to dfb.k_unset before packet 
        # is sent through
        self.assertEquals(pipeline22.bar, dfb.k_unset) 
        # Send packet to activate py_set_param
        packet = dfb.DataPacket('hello')
        pipeline22.send(packet)
        self.assertEquals(pipeline22.bar, 170)

    def test_dynamic_pipeline2(self):
        # Set dynamic=True by calling make_dynamic()
        pipeline23 = ppln.DynamicPipeline(factory=self.factory, 
                                          config=self.config1,
                                          foo='joe')
        self.assertEquals(pipeline23.foo, 'joe')
        self.assertEquals(pipeline23.bar, 27)
        pipeline23.bar = '%SPEED'
        # All u/c params should default to dfb.k_unset before packet 
        # is sent through
        self.assertEquals(pipeline23.bar, dfb.k_unset)
        # Send packet to activate py_set_param
        packet = dfb.DataPacket('goodbye')
        pipeline23.send(packet)
        self.assertEquals(pipeline23.bar, 170)
        ### Stop the pipeline being dynamic
        ##pipeline23.make_dynamic(False)
        ##self.assertEquals(pipeline23.bar, '%SPEED')

    def test_dynamic_pipeline3(self):
        # Set dynamic=True as a key in the pipeline config
        config2 = '''\
        [--main--]
        ftype = demo_dynamic_pipeline2
        description = Pipeline with dynamic set in main section
        keys = foo, bar:31
        dynamic = true
        
        [py_set_param]
        print '**16130** Setting RADALT to 2000'
        RADALT = 2000

        [--route--]
        py_set_param >>>
        pass_through
        '''
        pipeline24 = ppln.DynamicPipeline(factory=self.factory, config=config2,
                                          foo='jane')
        self.assertEquals(pipeline24.foo, 'jane')
        self.assertEquals(pipeline24.bar, 31)
        pipeline24.bar = '%RADALT'
        # All u/c params should default to k_unset before packet is sent through
        self.assertEquals(pipeline24.bar, dfb.k_unset)
        # Send packet to activate py_set_param
        packet = dfb.DataPacket('goodbye')
        pipeline24.send(packet)
        self.assertEquals(pipeline24.bar, 2000)
        
    def test_dynamic_filter_in_static_pipeline1(self):
        # Batch is set to be dynamic in config
        config3 = '''\
        [--main--]
        ftype = demo_static_pipeline3
        description = Static pipeline with reversible dynamic filter
        keys = foo, bar:43
        
        [py_set_param]
        print '**16130** Setting BATCH_SIZE to 256'
        BATCH_SIZE = 256
        
        [batch]
        dynamic = true
        size = %BATCH_SIZE

        [--route--]
        py_set_param >>>
        batch
        '''
        pipeline25 = ppln.Pipeline(factory=self.factory, config=config3,
                                   foo='jim')
        self.assertEquals(pipeline25.foo, 'jim')
        self.assertEquals(pipeline25.bar, 43)
        batch_filter = pipeline25.getf('batch')
        # Dynamic value not yet set
        self.assertEquals(batch_filter.size, dfb.k_unset)
        # Send packet to activate py_set_param
        packet = dfb.DataPacket('hi')
        pipeline25.send(packet)
        self.assertEquals(batch_filter.size, 256)
        # Can't do this using metaclass approach
        ### Stop the pipeline being dynamic
        ##batch_filter.make_dynamic(False)
        ##self.assertEquals(batch_filter.size, '%BATCH_SIZE')
        
    def test_dynamic_filter_in_static_pipeline3(self):
        # Batch is set to be reversibly dynamic in config
        config3 = '''\
        [--main--]
        ftype = demo_static_pipeline3
        description = Static pipeline with reversible dynamic filter
        keys = foo, bar:43
        #dynamic = true
        
        [py_set_param]
        print '**16130** Setting BATCH_SIZE to 256'
        BATCH_SIZE_SOMETHING = 256
        BATCH_SIZE_OTHER = 128
        
        
        [distill_something]
        ftype = distill_header
        dynamic = true
        
        [distill_other]
        ftype = distill_header
        dynamic = true


        [--route--]
        py_set_param >>>
        distill_something:%BATCH_SIZE_SOMETHING >>>
            (pass_through)
        distill_other:%BATCH_SIZE_OTHER >>>
            (pass_through)
        sink
        '''
        pipeline25 = ppln.Pipeline(factory=self.factory, config=config3,
                                   foo='jim')
        self.assertEquals(pipeline25.foo, 'jim')
        self.assertEquals(pipeline25.bar, 43)
        something_filter = pipeline25.getf('distill_something')
        other_filter = pipeline25.getf('distill_other')
        # Dynamic value not yet set
        self.assertEquals(something_filter.header_size, dfb.k_unset)
        # Send packet to activate py_set_param
        packet = dfb.DataPacket('hi')
        pipeline25.send(packet)
        self.assertEquals(something_filter.header_size, 256)
        self.assertEquals(other_filter.header_size, 128)
        ### Stop the pipeline being dynamic
        # Can't do this bit any more, using the metaclass approach
        ##batch_filter.make_dynamic(False)
        ##self.assertEquals(something_filter.header_size, \
                          ##'%BATCH_SIZE_SOMETHING')
        ##self.assertEquals(other_filter.header_size, '%BATCH_SIZE_OTHER')
        
        
    def test_dynamic_filter_in_static_pipeline2(self):
        # Batch is set to be dynamic in config, using metaclass.
        # Possibly not so useful, since it is not reversible.
        config4 = '''\
        [--main--]
        ftype = demo_static_pipeline4
        description = Static pipeline with metaclass dynamic filter
        keys = foo, bar:55
        
        [py_set_param]
        print '**16140** Setting BATCH_SIZE to 2048'
        BATCH_SIZE = 2048
        
        [batch]
        dynamic = meta
        size = %BATCH_SIZE

        [--route--]
        py_set_param >>>
        batch
        '''
        pipeline26 = ppln.Pipeline(factory=self.factory, config=config4,
                                   foo='cyrus')
        self.assertEquals(pipeline26.foo, 'cyrus')
        self.assertEquals(pipeline26.bar, 55)
        batch_filter = pipeline26.getf('batch')
        # Dynamic value not yet set
        self.assertEquals(batch_filter.size, dfb.k_unset)
        # Send packet to activate py_set_param
        packet = dfb.DataPacket('lo')
        pipeline26.send(packet)
        self.assertEquals(batch_filter.size, 2048)
    
        
class TestEssentialAndOptionalKeys(unittest.TestCase):

    def setUp(self):
        self.factory = ff.DemoFilterFactory()
    
    def tearDown(self):
        pass
    
    ##def _access_missing_optional(self, pipelin):
        ##pipelin.foo
    
    def test_essential_and_optional_keys(self):
        config = '''
        [--main--]
        ftype = demo 
        description = TO-DO: docstring
        keys1 = a1:joe, b2, c3, d4
        keys2 = w:10, x:0xFF, y:12.5, z:false, ghj:asdf, foo:none, baz:none
        
        [--route--]
        pass_through
        '''
        pipeline5 = ppln.Pipeline(factory=self.factory, config=config,
                                  baz='jim', b2='bill', c3=789, d4='jane')
        self.assertEquals(pipeline5.a1, 'joe')
        self.assertEquals(pipeline5.b2, 'bill')
        self.assertEquals(pipeline5.c3, 789)
        self.assertEquals(pipeline5.d4, 'jane')
        self.assertEquals(pipeline5.w, 10)
        self.assertEquals(pipeline5.x, 255)
        self.assertEquals(pipeline5.y, 12.5)
        self.assertEquals(pipeline5.z, False)
        self.assertEquals(pipeline5.ghj, 'asdf')
        

class TestFilterTypeSetting(unittest.TestCase):

    def setUp(self):
        self.factory = ff.DemoFilterFactory()
    
    def tearDown(self):
        pass
    
    def test_type_set_in_config_overrides_name_interp(self):
        config = '''
        [--main--]
        ftype = testing
        description = TO-DO: docstring
        
        [batch_which_isnt_a_batch]
        ftype = sink
        
        [--route--]
        batch_which_isnt_a_batch
        '''
        pipeline32 = ppln.Pipeline(factory=self.factory, config=config)
        self.assertEquals(pipeline32.first_filter.ftype, 'sink')
        
        
class TestParameterSetting(unittest.TestCase):

    def setUp(self):
        self.factory = ff.DemoFilterFactory()
    
    def tearDown(self):
        pass
    
    def test_count_packet(self):
##        return # <<<<<<<<<<<<<<<<<<<<<<<<<<<<<  subframe_number ?? TO-DO
        config = '''
        [--main--]
        ftype = testing
        description = TO-DO: docstring
        
        [--route--]
        seq_packet:subframe_number >>>
        sink
        '''
        pipeline3 = ppln.Pipeline(factory=self.factory, config=config)
        id_giver = pipeline3.getf('seq_packet')
        self.assertEquals(id_giver.subframe_number, 0)
    
    def test_set_param_in_config(self):
        config = '''
        [--main--]
        ftype = testing
        description = TO-DO: docstring
        
        [batch]
        size = 10

        [--route--]
        batch >>>
        sink
        '''
        pipeline1 = ppln.Pipeline(factory=self.factory, config=config)
        self.assertEquals(pipeline1.getf('batch').size, 10)
    
    def test_set_param_in_route_with_config(self):
        config = '''
        [--main--]
        ftype = testing
        description = TO-DO: docstring
    
        [batch]

        [--route--]
        batch:22 >>>
        sink
        '''
        pipeline1 = ppln.Pipeline(factory=self.factory, config=config)
        self.assertEquals(pipeline1.getf('batch').size, 22)
    
    def test_set_param_in_route_no_config(self):
        config = '''
        [--main--]
        ftype = testing
        description = TO-DO: docstring
    
        [--route--]
        batch:33 >>>
        sink
        '''
        pipeline1 = ppln.Pipeline(factory=self.factory, config=config)
        self.assertEquals(pipeline1.getf('batch').size, 33)
    
    def test_set_param_in_route_and_config_same(self):
        # Previously setting a parameter in both config and route was an
        # error, but there are situations when it may be necessary. We have to
        # allow the same value because e.g. one "batch:40" filter may be
        # parsed twice, as a from and a to filter. It doesn't really matter,
        # as long as the values are the same.
        config = '''
        [--main--]
        ftype = testing
        description = TO-DO: docstring

        [batch]
        size = 44

        [--route--]
        batch:44 >>>
        sink
        '''
        pipeline1 = ppln.Pipeline(factory=self.factory, config=config)
        self.assertEquals(pipeline1.getf('batch').size, 44)

    def test_set_param_in_route_and_config_different(self):
        config = '''
        [--main--]
        ftype = testing
        description = TO-DO: docstring
    
        [batch]
        size = 46

        [--route--]
        batch:48 >>>
        sink
        '''
        self.assertRaises(dfb.FilterAttributeError, ppln.Pipeline,
                          factory=self.factory, config=config)
    
    def test_set_param_in_route_twice_same(self):

        config = '''
        [--main--]
        ftype = testing
        description = TO-DO: docstring

        [--route--]
        distill_header:100 >>>
            (batch:55)
        sink >>>
        batch:55
        '''
        pipeline1 = ppln.Pipeline(factory=self.factory, config=config)
        self.assertEquals(pipeline1.getf('batch').size, 55)

    def test_set_param_in_route_once_with_extra_key_1(self):
        # "batch" occurs twice in the route, but only once with a value.
        # The once with a value should be taken, in which ever order they come. 

        config = '''
        [--main--]
        ftype = testing
        description = TO-DO: docstring

        [--route--]
        distill_header:100 >>>
            (batch)
        sink >>>
        batch:66
        '''
        pipeline1 = ppln.Pipeline(factory=self.factory, config=config)
        self.assertEquals(pipeline1.getf('batch').size, 66)

    def test_set_param_in_route_once_with_extra_key_2(self):
        # "batch" occurs twice in the route, but only once with a value.
        # The once with a value should be taken, in which ever order they come. 

        config = '''
        [--main--]
        ftype = testing
        description = TO-DO: docstring

        [--route--]
        distill_header:100 >>>
            (batch:77)
        sink >>>
        batch
        '''
        pipeline1 = ppln.Pipeline(factory=self.factory, config=config)
        self.assertEquals(pipeline1.getf('batch').size, 77)

    def test_set_param_in_route_twice_different(self):
        config = '''
        [--main--]
        ftype = testing
        description = TO-DO: docstring

        [--route--]
        distill_header:100 >>>
            (batch:88)
        sink >>>
        batch:99
        '''
        self.assertRaises(dfb.FilterAttributeError, ppln.Pipeline,
                          factory=self.factory, config=config)
    
    ##def test_set_param_in_route_twice_different_one_zero(self):
        ### Zero is a null value, so we allow overwriting with a different value
        ##config = '''
        ##[--main--]
        ##ftype = testing

        ##[--route--]
        ##distill_header:100 
            ##(batch:123)
        ##sink 
        ##batch:0
        ##'''
        ##pipeline1 = ppln.Pipeline(factory=self.factory, config=config)
        ##self.assertEquals(pipeline1.getf('batch').size, 124)


class TestPipeline(unittest.TestCase):
    
    config = '''
    [--main--]
    ftype = testing
    description = TO-DO: docstring
    
    [--route--]
    reverse_string >>>
    sink >>>
    pass_through1 >>>
    pass_through2 >>>
    pass_through3
    '''
    
    def setUp(self):
        self.factory = ff.DemoFilterFactory()
        # We can't make the pipeline until the parameters have been read.
    
    def tearDown(self):
        pass
    
    def test_substitute_keys_1(self):
        ppln = CheckKeySubstitutions(factory=self.factory)
        test_filter = ppln.getf('test_key_substitutions')
        self.assertEqual(test_filter.first_key, 213)
        self.assertEqual(test_filter.second_key, 'do_not_process_this')
    
    def test_substitute_keys_2(self):
        ppln = CheckKeySubstitutions(factory=self.factory,
                                     integer='string_instead',
                                     string_sub=3131)
        test_filter = ppln.getf('test_key_substitutions')
        self.assertEqual(test_filter.first_key, 'string_instead')
        self.assertEqual(test_filter.second_key, 'do_not_3131_this')
    
    def test_closing_context_manager(self):
        just_sink = JustSink(factory=self.factory)
        self.assertEquals(just_sink(44), '44')  # Data types <<<<<<<TO-DO<<<<<<<<<<<<<<<<
        
    def test_duplicate_filter(self):
        config = [line.strip() 
                  for line in JustSinkDuplicateFilter1.config.splitlines()]
        config2 = config[:config.index('[--route--]')]
        for line in config2:
            print '**6680** "%s"' % line
        self.assertRaises(configobj.DuplicateError, configobj.ConfigObj, 
                          config2)
        
    def test_shutting_down(self):
        just_sink = JustSink(factory=self.factory)
        just_sink(55)
        self.assertFalse(just_sink.shutting_down)
        just_sink.shut_down()
        self.assertTrue(just_sink.shutting_down)
        
    def test_raise_filter_error(self):
        just_sink1 = JustSink(factory=self.factory)
        packet1 = dfb.DataPacket('hhh12345')
        # FilterProcessingException now raised instead of FilterError due to
        # alleviating the StopIteration issue as described within
        # ProblemsWeHaveEncountered (trac).
        ##self.assertRaises(dfb.PipelineError, just_sink1.send, packet1)
        self.assertRaises(dfb.FilterProcessingException,
                          just_sink1.send,
                          packet1)
        ### No error in sending because pipeline is not set
        ##just_sink1.send(packet1)

        just_sink2 = JustSink(factory=self.factory)
        packet2 = dfb.DataPacket('abc12345')
        just_sink2.pipeline = just_sink1
        # dfb.FilterProcessingException.
        ##self.assertRaises(dfb.PipelineError, just_sink2.send, packet2)
        self.assertRaises(dfb.FilterProcessingException,
                          just_sink2.send,
                          packet2)

        just_sink3 = JustSink(factory=self.factory)
        just_sink3.pipeline = just_sink2
        just_sink3.pipeline.shut_down()
        packet3 = dfb.DataPacket('545454')
        self.assertRaises(StopIteration, just_sink2.send, packet2)
        
                
    def test_raising_filter_error(self):
        just_sink = JustSink(factory=self.factory)
        just_sink(55)
        
    ##def test_creation(self):
        ##print '**10400** Testing creation of pipeline'
        ##pipe1 = ppln.Pipeline(factory=self.factory)
####        filt1 = dfb.DataFilter()
####        align_supf4 = dfb.DataFilterBase()
        ##self.assertEquals(pipe1, pipe1)
        
class TestTankQueue(unittest.TestCase):
    
    config_normal = '''
    [--main--]
    ftype = testing_tank_queue_normal
    
    [--route--]
    tank_queue:5 >>>
    sink
    '''
    
    config_keys = '''
    [--main--]
    ftype = testing_tank_queue_tank_size_key
    keys = size
    
    [--route--]
    tank_queue:${size} >>>
    sink
    '''
    
    config_expand_reduce = '''
    [--main--]
    ftype = testing_tank_queue_reduce_expand
    
    [--route--]
    tank_queue:5 >>>
    sink
    '''
    def setUp(self):
        self.factory = ff.DemoFilterFactory()
        self.packet1 = dfb.DataPacket(height=1)
        self.packet2 = dfb.DataPacket(height=2)
        self.packet3 = dfb.DataPacket(height=3)
        self.packet4 = dfb.DataPacket(height=4)
        self.packet5 = dfb.DataPacket(height=5)
        self.packet6 = dfb.DataPacket(height=9)
        
    def test_pipeline_wrapped_tank_queue(self):
        pipeline = ppln.Pipeline(factory=self.factory, config=self.config_normal)
        tank_queue = pipeline.getf('tank_queue')
        sink = pipeline.getf('sink')
        self.assertEqual(tank_queue.tank_size, 5)
        pipeline.send(self.packet1, self.packet2, self.packet3, self.packet4,
                      self.packet5)
        self.assertEqual(len(sink.results), 0)
        pipeline.send(self.packet6)
        self.assertEqual(len(sink.results), 1) # sink now has a single packet
        self.assertEqual(sink.results[0], self.packet1) # first in is first out
        
    def test_pipeline_with_keys(self):
        pipeline = ppln.Pipeline(factory=self.factory, config=self.config_keys,
                                 size=2)
        tank_queue = pipeline.getf('tank_queue')
        sink = pipeline.getf('sink')
        self.assertEqual(tank_queue.tank_size, 2)
        pipeline.send(self.packet1, self.packet2, self.packet3, self.packet4,
                      self.packet5)
        self.assertEqual(len(sink.results), 3)
        pipeline.send(self.packet6)
        self.assertEqual(len(sink.results), 4) # sink now has 4 packets
        # test that the packets came out in the correct order...
        self.assertEqual(sink.results[0], self.packet1)
        self.assertEqual(sink.results[1], self.packet2)
        self.assertEqual(sink.results[2], self.packet3)
        self.assertEqual(sink.results[3], self.packet4)
        
    def test_pipeline_reduce_expand(self):
        pipeline = ppln.Pipeline(factory=self.factory, 
                                 config=self.config_expand_reduce)
        tank_queue = pipeline.getf('tank_queue')
        sink = pipeline.getf('sink')
        self.assertEqual(tank_queue.tank_size, 5)
        pipeline.send(self.packet1, self.packet2, self.packet3)
        self.assertEqual(len(sink.results), 0)
        # reduce!
        tank_queue.tank_size = 0
        # ensure the packets are flushed from the tank queue
        self.assertEqual(len(sink.results), 3)
        pipeline.send(self.packet4)
        # ensure that the tank_queue does not store anything when it's size is 0
        self.assertEqual(len(sink.results), 4)
        # expand!
        tank_queue.tank_size = 10
        self.assertEqual(tank_queue.spare_capacity, 0)
        pipeline.send(self.packet5, self.packet6)
        self.assertEqual(len(sink.results), 4)
    
        
class TestTankAndSlope(unittest.TestCase):
    
    config = '''
    [--main--]
    ftype = testing_calc_slope
    description = Differentiate packet attribute over five points
        
    [--route--]
    tank_branch:5 >>>
        (calc_slope:height)
    sink
    '''
    
    def setUp(self):
        self.factory = ff.DemoFilterFactory()
        self.pipeline1 = ppln.Pipeline(factory=self.factory, config=self.config)
        self.packet1 = dfb.DataPacket(height=1)
        self.packet2 = dfb.DataPacket(height=2)
        self.packet3 = dfb.DataPacket(height=3)
        self.packet4 = dfb.DataPacket(height=4)
        self.packet5 = dfb.DataPacket(height=5)
        self.packet6 = dfb.DataPacket(height=9)
    
    def tearDown(self):
        pass

    def test_height_slope(self):
        tank = self.pipeline1.getf('tank_branch')
        sink = self.pipeline1.getf('sink')
        
        self.pipeline1.send(self.packet1)
        self.assertEquals(tank.spare_capacity, 4)
        self.assertEquals(len(sink.results), 0)
        
        self.pipeline1.send(self.packet2)
        self.pipeline1.send(self.packet3)
        self.pipeline1.send(self.packet4)
        self.assertFalse(hasattr(self.packet3, 'height_slope'))
        self.pipeline1.send(self.packet5)
        # We now have five packets in the pipeline, so calculation can be done
        self.assertEquals(self.packet3.height_slope, 1.0)
        self.assertFalse(hasattr(self.packet4, 'height_slope'))
        self.pipeline1.send(self.packet6)
        self.assertEquals(self.packet4.height_slope, 1.5)
        # Change tank size to 0 to flush contents
        tank.tank_size = 0
        self.assertEquals(len(sink.results), 6)
        self.assertEquals(sink.results[3].height_slope, 1.5)
        
        
##        last_packet = .results[-1].data
##        self.assertEquals(last_packet.height, 1)
##        assert 6 == 8
        
        
class TestUpdateLive(unittest.TestCase):
    
    config = '''
    [--main--]
    ftype = testing_update_live
    description = Reading live data from Python module
    keys = foo, bar, baz:20
    update_live = foo:FOO, bar:BAR_17, baz:BAZ
        
    [--route--]
    
    sink
    '''
    
    def setUp(self):
        self.factory = ff.DemoFilterFactory()
        self.pipeline3 = ppln.Pipeline(factory=self.factory, 
                                       config=self.config,
                                       foo=0, bar=45)
        self.packet1 = dfb.DataPacket(height=1)
        self.packet2 = dfb.DataPacket(height=2)
    
    def tearDown(self):
        pass

    def test_update_live(self):
        print '**12610** %s' % (self.pipeline3._live_updates)
        updates = self.pipeline3._live_updates
        
        update_dict = dict([update.split(':') for update in updates]) 
        import pprint
        pprint.pprint(update_dict)

        
if __name__ == '__main__':  #pragma: nocover
##
#    TestParameterSetting('test_count_packet').run()
#    TestEssentialKeys('test_essential_keys3').run()
##    TestEssentialAndOptionalKeys('test_essential_and_optional_keys').run()
##    TestParameterSetting('test_set_param_in_route_with_config').run()
##    TestFilterTypeSetting('test_type_set_in_config_overrides_name_interp').run()
#    TestDynamicParams('test_static_pipeline').run()
#    TestParameterSetting('test_count_packet').run()
    ##TestTankAndSlope('test_height_slope').run()
##    TestExtractManyAttributes('test_extract_many_attributes').run()

    ##TestEssentialKeys('test_essential_keys').run()
    
    ##TestTankQueue('test_pipeline_wrapped_tank_queue').run()
##    TestEssentialKeys('test_essential_keys').run()
    TestDynamicParams('test_dynamic_pipeline1').run()
##    TestDynamicParams('test_dynamic_filter_in_static_pipeline1').run()
    print '\n**6205** Finished.'

    
