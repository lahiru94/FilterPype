# -*- coding: utf-8 -*-
# data_fltr_base_test.py

# Licence
#
# FilterPype is a process-flow pipes-and-filters Python framework.
# Copyright (c) 2009 Flight Data Services
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


import unittest
import hashlib
##from configobj import ConfigObj
import sys
import math
import timeit
import os
import shutil

import filterpype.data_fltr_base as dfb
import filterpype.data_filter as df
import filterpype.filter_utils as fut
import filterpype.filter_factory as ff
import filterpype.pipeline as ppln

k_run_long_tests = True

data_dir5 = os.path.join(fut.abs_dir_of_file(__file__), 
                         'test_data', 'tst_data5')

# Sample data 1 is in a media type with values:
# file header length = 11
# block size = 104 bytes
# including a 24-byte header

sample_data1 = '''\
file_header\
=====block_header01=====\
$13_567_9AB_DEF_\
ABC_EFG_IJK_MNP_\
XXX_XXX_XXX_XXX_\
0000000011111111\
$23_567_9AB_DEF_\
=====block_header02=====\
ABC_EFG_IJK_MNP_\
XXX_XXX_XXX_XXX_\
0000000022222222\
$33_567_9AB_DEF_\
ABC_EFG_IJK_MNP_\
=====block_header03=====\
XXX_XXX_XXX_XXX_\
0000000033333333\
$43_567_9AB_DEF_\
ABC_EFG_IJK_MNP_\
XXX_XXX_XXX_XXX_\
'''

class TestDataFilter(unittest.TestCase):

    def setUp(self):
        self.factory = ff.DemoFilterFactory()
        self.sink = df.Sink()
        self.file_name1 = os.path.join(data_dir5, 'short.dat')
        f1 = open(self.file_name1, 'wb')
        try:
            f1.write('one two three four five six')
        finally:
            f1.close()
        self.config = '''
        [--main--]
        ftype = demo
        description = TO-DO: docstring

        [--route--]
        sink
        '''

    def tearDown(self):
        pass

    def test_bad_attribute(self):
        self.assertRaises(dfb.FilterAttributeError, df.PassThrough, bad_attr=99)
        
    ##def test_make_sink(self):
        ##self.sink2 = df.Sink()
        ##assert 55 == 66
        
    def test_get_refinery(self):
        ppln1 = ppln.Pipeline(factory=self.factory, config=self.config)
        print '**6600** ppln1 =', ppln1
        ppln2 = ppln.Pipeline(factory=self.factory, config=self.config)
        print '**6600** ppln2 =', ppln2
        ppln3 = ppln.Pipeline(factory=self.factory, config=self.config)
        print '**6600** ppln3 =', ppln3
        ppln3.pipeline = ppln2
        ppln2.pipeline = ppln1
        self.assertEquals(ppln3.refinery, ppln1)

    def test_missing_attribute(self):
        #Batch requires size attribute
        print '**16204** test_missing_attribute'
        self.assertRaises(dfb.FilterAttributeError, df.Batch)

    def test_missing_attribute2(self):
        #Batch requires size attribute
        self.assertRaises(dfb.FilterAttributeError, df.Batch)
        factory = ff.DemoFilterFactory()
        self.assertRaises(dfb.FilterAttributeError, df.Batch, factory=factory)
                    
    def test_missing_filter_data_not_overridden(self):
        class Pointless(dfb.DataFilter):
            ftype = 'pointless'
        pointless = Pointless()
        packet1 = dfb.DataPacket(data='abcdef')
        # filter_data() is not overridden
        self.assertRaises(dfb.FilterError, pointless.send, packet1)

    def test_reprime_filter(self):
        pass_through = df.PassThrough()
        pass_through.next_filter = self.sink
        packet1 = dfb.DataPacket(data='abcdef')
        # Sending the packet primes the filter
        pass_through.send(packet1)
        # Can't prime the coroutine twice
        self.assertRaises(dfb.FilterError, pass_through._prime)
        
    def test_all_keys(self):
        
        class DerivedClass1(df.PassThrough):
            keys = ['abc', 'defg:0']
    
        class DerivedClass2(DerivedClass1):
            pass
    
        class DerivedClass3(DerivedClass2):
            keys = ['fred', 'jane', 'defg:3']

        class DerivedClass4(DerivedClass3):
            keys = ['bill', 'defg:49']
            
        b = df.PassThrough()
        d1 = DerivedClass1(abc=99)
        d2 = DerivedClass2(abc=99)
        d3 = DerivedClass3(abc=99, fred=1, jane=2)
        d4 = DerivedClass4(abc=99, fred=1, jane=2, bill=34)
        self.assertEquals(b.keys, [])
        self.assertEquals(b._all_keys(), [])
        self.assertEquals(d1.keys, ['abc', 'defg:0'])
        self.assertEquals(d1._all_keys(), ['abc', 'defg:0'])
        self.assertEquals(d2.keys, ['abc', 'defg:0'])
        self.assertEquals(d2._all_keys(), ['abc', 'defg:0'])
        self.assertEquals(d3.keys, ['fred', 'jane', 'defg:3'])
        self.assertEquals(d3._all_keys(), ['abc', 'defg:3', 'fred', 'jane'])
        self.assertEquals(d3.defg, 3)
        self.assertEquals(d4.keys, ['bill', 'defg:49'])
        self.assertEquals(d4._all_keys(), 
                          ['abc', 'defg:49', 'fred', 'jane', 'bill'])
        self.assertEquals(d4.defg, 49)
    
    
class TestDataPacket(unittest.TestCase):

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_make_packet(self):
        packet1 = dfb.DataPacket()
        self.assertEquals(packet1.data, '')
        packet2 = dfb.DataPacket(data='fred')
        self.assertEquals(packet2.data, 'fred')
        packet3 = dfb.DataPacket('jane', speed=35)
        self.assertEquals(packet3.data, 'jane')
        self.assertEquals(packet3.speed, 35)
        self.assertEquals(packet3.message, None)

    def test_clone_packet(self):
        packet4 = dfb.DataPacket('jim', roll=75)
        packet5 = packet4.clone()
        self.assertEquals(packet5.data, 'jim')
        self.assertEquals(packet5.roll, 75)
        packet6 = packet4.clone(data='nancy')
        self.assertEquals(packet6.data, 'nancy')
        # Check that the dictionary has been copied, not just the pointer,
        # by checking the address of the keys() function.
        self.assertNotEquals(getattr(packet4.__dict__, 'keys'),
                             getattr(packet5.__dict__, 'keys'))

    def test_clone_packet_with_params(self):
        packet7 = dfb.DataPacket('bill', roll=27)
        self.assertEquals(packet7.data, 'bill')
        self.assertEquals(packet7.roll, 27)
        packet8 = packet7.clone(data='baz', some_func='foo')
        self.assertEquals(packet8.data, 'baz')
        # Check that the dictionary has been copied, not just the pointer,
        # by checking the id
        self.assertNotEquals(id(packet7), id(packet8))
        
    def test_clear_data(self):
        packet9 = dfb.DataPacket('bill', roll=27)
        packet9.clear_data()
        self.assertEquals(packet9.data, '')
        self.assertEquals(packet9.roll, 27)
        
    def test_data_length(self):
        packet10 = dfb.DataPacket('jane')
        self.assertEquals(packet10.data_length, 4)
        packet11 = dfb.DataPacket([1,2,3])
        self.assertEquals(packet11.data_length, 0)
        
        
##class DemoDynamic(dfb.DataFilterDynamic):
    
    ##ftype = 'demo_dynamic'
    
    ##def __init__(self, **kwargs):
        ##dfb.DataFilterDynamic.__init__(self, **kwargs)
        ##self.first_name = 'john'
            

class TestDataFilterDynamic(unittest.TestCase):

    def setUp(self):
        self.factory = ff.DemoFilterFactory()
        self.sink = df.Sink()

    def tearDown(self):
        pass
    
    def test_dynamic_access1(self):
        # MixInClass seems not to work with new-style classes
        return 
        base_filter = dfb.DataFilter(ftype='dynamic_test')
        base_filter.static_param = 113
        self.assertEquals(base_filter.static_param, 113)
        
        MixInClass = dfb.mix_in_copy(dfb.DataFilter, dfb.DynamicMixIn)
        
        dyn_filter = DemoDynamic()
        dyn_filter.static_param = 152
        self.assertEquals(dyn_filter.static_param, 152)
        dyn_filter.dynamic_param = '%LENGTH'
        self.assertEquals(dyn_filter.dynamic_param, 'fred')
        
        # [  ] Add all the external modules with the same name
        
        # [  ] dyn_filter.first_name
        
        # [  ] Next actions:
        
        # [  ] Convert tests which use dynamic variables to derive from 
        # [  ] DataFilterDynamic
        
        
        # [  ] Put ATTRIBUTE into Python embedded environment
        
        # [  ] Check value comes back if %ATTRIBUTE is used.
        
        # [  ] Make pipeline; check retrieve parent value if emb pipeline not
        # there or doesn't have value.
        
        # [  ] Bitshift -- dynamic
        # [  ] ReversedBitshift doesn't need to be dynamic
        # [  ] Check carry is working in Bitshift
        
        # [  ] Return same embed module each time -- 
        
    def test_dynamic_access_no_decorator(self):
        class SomeFilterNoDecorator(object):
            pass
        
        no_dec = SomeFilterNoDecorator()
        no_dec.name = 'no_decorator'
        no_dec.zero = 0
        no_dec.dynamic_value = '%RADIO_ALT'
        no_dec.alist = [1, 2, 3]
        self.assertEquals(no_dec.__class__.__name__, 'SomeFilterNoDecorator')
        self.assertEquals(no_dec.name, 'no_decorator')
        self.assertEquals(no_dec.zero, 0)
        self.assertEquals(no_dec.dynamic_value, '%RADIO_ALT')
        self.assertEquals(no_dec.alist, [1, 2, 3])
        
    def test_dynamic_access_with_decorator(self):
        
        @dfb.dynamic_params
        class SomeFilterWithDecorator(object):
            pass
        
        no_dec = SomeFilterWithDecorator()
        no_dec.name = 'with_decorator'
        no_dec.zero = 0
        no_dec.dynamic_value = '%RADIO_ALT'
        no_dec.alist = [1, 2, 3]
        self.assertEquals(no_dec.name, 'with_decorator')
        self.assertEquals(no_dec.zero, 0)
        self.assertEquals(no_dec.dynamic_value, dfb.k_unset)
        self.assertEquals(no_dec.alist, [1, 2, 3])
                
        
class TestHiddenBranchRoute(unittest.TestCase):
    
    def setUp(self):
        self.hidden_branch_filter = dfb.HiddenBranchRoute()
        self.sink_main = df.Sink()
        self.hidden_branch_filter.next_filter = self.sink_main
        self.sink_branch = df.Sink()
        self.hidden_branch_filter.branch_filter = self.sink_branch
    
    def tearDown(self):
        pass
    
    def test_closing_main_and_branch(self):
        return # test_closing_main_and_branch   TO-DO
        self.hidden_branch_filter.send(dfb.DataPacket('hello', 
                                                      fork_dest='main'))
        self.hidden_branch_filter.shut_down()
        self.sink_main.send(dfb.DataPacket('world'))
##        assert 55 == 77
    

class TestMessageBottle(unittest.TestCase):

    def setUp(self):
        self.destination = None

    def tearDown(self):
        pass

    def test_make_bottle(self):
        bottle2 = dfb.MessageBottle(self.destination, message='hello')
        self.assertEquals(bottle2.message, 'hello')

    def test_make_bottle_with_data(self):
        # Data not allowed in a message. Use "values" instead.
        self.assertRaises(dfb.MessageError, dfb.MessageBottle, self.destination,
                          'reset', data='fred')
        
    def test_no_message(self):
        self.assertRaises(dfb.MessageError, dfb.MessageBottle, 
                          self.destination, '')
              
    def test_send_reset_msg(self):
#        bottle1 = dfb.MessageBottle('reset_seq_num:0')  <<<<<<<<<<<<<<
        bottle1 = dfb.MessageBottle(self.destination, 'reset_seq_num')

                
class TestPriorityQueue(unittest.TestCase):
    
    def setUp(self):
        self.priority_queue = dfb.PriorityQueue()
    
    def tearDown(self):
        pass
    
    def test_add_items_standard_order(self):
        data = [('a', 1), ('b', 2), ('c', 3)]
        for item, prio in data:
            self.priority_queue.push(item)
        self.assertEquals(self.priority_queue.pop(), data[0][0])
        self.assertEquals(self.priority_queue.pop(), data[1][0])
        self.assertEquals(self.priority_queue.pop(), data[2][0])
        self.assertEquals(self.priority_queue.queue_size(), 0)
        for item, prio in data:
            self.priority_queue.push(item, prio)
        self.assertEquals(self.priority_queue.pop(), data[0][0])
        self.assertEquals(self.priority_queue.pop(), data[1][0])
        self.assertEquals(self.priority_queue.pop(), data[2][0])
        self.assertEquals(self.priority_queue.queue_size(), 0)

    def test_add_items_reverse_order(self):
        data = [('d', 6), ('e', 5), ('f', -1)]
        for item, prio in data:
            self.priority_queue.push(item)
        self.assertEquals(self.priority_queue.pop(), data[0][0])
        self.assertEquals(self.priority_queue.pop(), data[1][0])
        self.assertEquals(self.priority_queue.pop(), data[2][0])
        self.assertEquals(self.priority_queue.queue_size(), 0)
        for item, prio in data:
            self.priority_queue.push(item, prio)
        self.assertEquals(self.priority_queue.pop(), data[2][0])
        self.assertEquals(self.priority_queue.pop(), data[1][0])
        self.assertEquals(self.priority_queue.pop(), data[0][0])
        self.assertEquals(self.priority_queue.queue_size(), 0)
        
    def test_queue_functions(self):
        data = [('d', 6), ('e', 5), ('f', -1)]
        for item, prio in data:
            self.priority_queue.push(item)
        self.assertEquals(self.priority_queue.pop(), data[0][0])
        self.assertEquals(self.priority_queue.pop(), data[1][0])
        self.assertEquals(self.priority_queue.pop(), data[2][0])
        self.priority_queue.clear()
        self.assertEquals(self.priority_queue.queue_size(), 0)
        
    def test_sorted_all_items(self):
        data = [('d', 6), ('e', 5), ('f', -1)]
        for item, prio in data:
            self.priority_queue.push(item, prio)
        self.assertEquals([x[2] for x in self.priority_queue.sorted_items()],
                          ['f', 'e', 'd'])
        self.priority_queue.clear()
        data = [('r', 60), ('t', 4), ('s', 4)]
        for item, prio in data:
            self.priority_queue.push(item, prio)
        # 't' will have been pushed fractionally before 's' so has sort prio.
        self.assertEquals([x[2] for x in self.priority_queue.sorted_items()],
                          ['t', 's', 'r'])
    
if __name__ == '__main__':  #pragma: nocover
##        TestBatch('test_batch_no_headers').run()
        #TestPipelines('test_filter11').run()
##    runner = unittest.TextTestRunner()
##    runner.run(TestPipelines('test_filter13'))
    ##++runner.run(TestPipelines('test_filter_sums'))
##$$    runner.run(TestPipelines('test_filter11'))

##    TestBranchRoute('test_branch_route').run()
##    TestDataFilter('test_missing_attribute').run()
##    TestRenameFile('test_rename_to_already_exists').run()
    TestDataFilterDynamic('test_dynamic_access_with_decorator').run()
##    TestDataFilter('test_missing_attribute').run()
    print '\n**1910** Finished'



