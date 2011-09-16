# -*- coding: utf-8 -*-
# data_fltr_demo_test.py

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


import unittest
import sys
import os
import math

import filterpype.data_fltr_base as dfb
import filterpype.data_filter as df
import filterpype.data_fltr_demo as dfd
import filterpype.filter_utils as fut
import filterpype.pipeline as ppln

k_run_long_tests = True
data_dir5 = os.path.join(fut.abs_dir_of_file(__file__), 
                         'test_data', 'tst_data5')

class TestAddNumbers(unittest.TestCase):
    
    def setUp(self):
        self.add_numbers = dfd.AddNumbers()
        # Ready to check output
        self.sink = df.Sink()
        # Connect filters
        self.add_numbers.next_filter = self.sink
    
    def tearDown(self):
        pass
    
    def test_add_number_list(self):
        packet = dfb.DataPacket(data=[1, 2, 3])
        self.add_numbers.send(packet)  
        # Check last (and only) item in sink results
        self.assertEquals(self.sink.results[-1].psum, 6)
        self.add_numbers.send(dfb.DataPacket(data=[-1, -2.5, 4]))  
        self.assertEquals(self.sink.results[-1].psum, 0.5)
        self.add_numbers.send(dfb.DataPacket(data=[]))  
        self.assertEquals(self.sink.results[-1].psum, 0)

    def test_add_number_string(self):
        packet = dfb.DataPacket(data='1, 2, 3')
        self.add_numbers.send(packet)  
        # Check last (and only) item in sink results
        self.assertEquals(self.sink.results[-1].psum, 6)
        self.add_numbers.send(dfb.DataPacket(data='-1, -2.5, 4'))  
        self.assertEquals(self.sink.results[-1].psum, 0.5)
        self.add_numbers.send(dfb.DataPacket(data=''))  
        self.assertEquals(self.sink.results[-1].psum, 0)

    def test_add_non_number_list(self):
        # TO-DO: This test gives a StopIteration error ??
        return  # <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<
        packet = dfb.DataPacket(data=[1, 2, '3'])
        self.assertRaises(TypeError, self.add_numbers.send, packet)  
        # Check last (and only) item in sink results
        packet = dfb.DataPacket(data=[2, 22, []])
        self.assertRaises(TypeError, self.add_numbers.send, packet)
        
class TestByteValueCounter(unittest.TestCase):
    
    def setUp(self):
        self.bvc = dfd.ByteValueCounter()
        
    def tearDown(self):
        pass
        
    def test_byte_values(self):
        packet = dfb.DataPacket(data='abracadabra')
        self.bvc.send(packet)
        self.assertEquals(self.bvc.byte_value_dict,
                          {97: 5, 98: 2, 99: 1, 100: 1, 114: 2})
        
        
class TestCapitalise(unittest.TestCase):
    
    def setUp(self):
        self.caps = dfd.Capitalise()
        # Ready to check output
        self.sink = df.Sink()
        # Connect filters
        self.caps.next_filter = self.sink
    
    def tearDown(self):
        pass
    
    def test_capitalise(self):
        packet1 = dfb.DataPacket('hello world')
        self.caps.send(packet1)
        self.assertEquals(self.sink.results[-1].data, 'Hello world')
        packet2 = dfb.DataPacket('oneword')
        self.caps.send(packet2)
        self.assertEquals(self.sink.results[-1].data, 'Oneword')
        packet3 = dfb.DataPacket('')
        self.caps.send(packet3)
        self.assertEquals(self.sink.results[-1].data, '')


class TestDataFilterDemo2(unittest.TestCase):

    def setUp(self):
        self.sink = df.Sink()
        self.file_name1 = os.path.join(data_dir5, 'short.dat')
        f1 = open(self.file_name1, 'wb')
        try:
            f1.write('one two three four five six')
        finally:
            f1.close()

    def tearDown(self):
        pass

    def test_multiply_if_int(self):
        self.assertRaises(dfb.FilterAttributeError, dfd.MultiplyIfInteger)
        mult_if_int = dfd.MultiplyIfInteger(multiply_by=2)
        mult_if_int.next_filter = self.sink
        mult_if_int.send(dfb.DataPacket('3'))
        self.assertEquals(self.sink.results[-1].data, '6')
        mult_if_int.send(dfb.DataPacket(-2))
        self.assertEquals(self.sink.results[-1].data, '-4')
        mult_if_int.send(dfb.DataPacket('bill'))
        self.assertEquals(self.sink.results[-1].data, 'bill')
        mult_if_int.shut_down()


class TestDataFilter1(unittest.TestCase):

    def setUp(self):
        self.source_data = ['123456', '69439876', '', '1010789X']

    def tearDown(self):
        pass

    def test_filter1(self):
        import filterpype.filter_factory as ff
        factory = ff.DemoFilterFactory()

        config = '''
        [--main--]
        ftype = demo
        description = TO-DO: docstring
        
        [--route--]
        batch:3 >>>
        reverse_string >>>
        sink
        '''

        pipeline1 = ppln.Pipeline(factory=factory, config=config)
        # Manual connection for now
        pgf = pipeline1.get_filter
        pipeline1.first_filter = pgf('batch')
##        pgf('batch').next_filter = pgf('reverse_string')
##        pgf('reverse_string').next_filter = pgf('sink')

        for string in self.source_data:
            pipeline1.send(dfb.DataPacket(string))
        print '**1700** about to close'
        pipeline1.shut_down()
        for part in pgf('sink').results:
            print '**2482**  ', part.data
##        print pgf('sink'].all_data
        self.assertEquals(pgf('sink').results[-8].data, '321')
        self.assertEquals(pgf('sink').results[-7].data, '654')
        self.assertEquals(pgf('sink').results[-6].data, '496')
        self.assertEquals(pgf('sink').results[-5].data, '893')
        self.assertEquals(pgf('sink').results[-4].data, '167')
        self.assertEquals(pgf('sink').results[-3].data, '010')
        self.assertEquals(pgf('sink').results[-2].data, '987')
        self.assertEquals(pgf('sink').results[-1].data, 'X')


class TestDataFilterDemo(unittest.TestCase):

    def setUp(self):
        self.sink = df.Sink()
        self.file_name1 = os.path.join(data_dir5, 'short.dat')
        f1 = open(self.file_name1, 'wb')
        try:
            f1.write('one two three four five six')
        finally:
            f1.close()

    def tearDown(self):
        pass

    ##def test_append_string(self):
        ##append_string = dfd.AppendString(extra_data='===')
        ##append_string.next_filter = self.sink
        ##packet = dfb.DataPacket(data='abcdef')
        ##append_string.send(packet)
        ##self.assertEquals(self.sink.results[-1].data, 'abcdef===')

    def test_reverse_string(self):
        reverse_string = dfd.ReverseString()
        reverse_string.next_filter = self.sink
        reverse_string.send(dfb.DataPacket('abcdef'))
        self.assertEquals(self.sink.results[-1].data, 'fedcba')
        reverse_string.send(dfb.DataPacket(''))
        self.assertEquals(self.sink.results[-1].data, '')
        reverse_string.send(dfb.DataPacket('aaaa\naa'))
        self.assertEquals(self.sink.results[-1].data, 'aa\naaaa')

    def test_square_if_number(self):
        square_if_number = dfd.SquareIfNumber()
        square_if_number.next_filter = self.sink
        square_if_number.send(dfb.DataPacket('3'))
        self.assertEquals(self.sink.results[-1].data, 9)
        square_if_number.send(dfb.DataPacket(-2))
        self.assertEquals(self.sink.results[-1].data, 4)
        square_if_number.send(dfb.DataPacket(2.5))
        self.assertEquals(self.sink.results[-1].data, 6.25)
        square_if_number.send(dfb.DataPacket('bill'))
        self.assertEquals(self.sink.results[-1].data, 'bill')
        square_if_number.shut_down()

    def test_sum_bits(self):
        sum_bits = dfd.SumBits()
        packet1 = dfb.DataPacket(data=fut.hex_string_to_data('12 34 56'))
##        sum_bits._gen.send(packet1)
        sum_bits.send(packet1)
        self.assertEquals(sum_bits.bit_sum, 9)
        self.assertEquals(sum_bits.byte_count, 3)
        
        sum_bits2 = dfd.SumBits()
        packet2 = dfb.DataPacket(data=fut.hex_string_to_data('AB C0'))
##        sum_bits2._gen.send(packet2)
        sum_bits2.send(packet2)
        packet3 = dfb.DataPacket(data=fut.hex_string_to_data('0D EF'))
##        sum_bits2._gen.send(packet3)
        sum_bits2.send(packet3)
        self.assertEquals(sum_bits2.bit_sum, 17)
        self.assertEquals(sum_bits2.byte_count, 4)

    def test_sum_bytes(self):
        sum_bytes = dfd.SumBytes()
        packet1 = dfb.DataPacket(data=fut.hex_string_to_data('12 23 34'))
        sum_bytes.send(packet1)
        self.assertEquals(sum_bytes.byte_sum, 0x69)
        
        sum_bytes2 = dfd.SumBytes()
        packet2 = dfb.DataPacket(data=fut.hex_string_to_data('11 22'))
        sum_bytes2.send(packet2)
        packet3 = dfb.DataPacket(data=fut.hex_string_to_data('33 22'))
        sum_bytes2.send(packet3)
        self.assertEquals(sum_bytes2.byte_sum, 0x88)

    def test_sum_nibbles(self):
        sum_nibbles = dfd.SumNibbles()
        packet1 = dfb.DataPacket(data=fut.hex_string_to_data('12 34 56'))
        sum_nibbles.send(packet1)
        self.assertEquals(sum_nibbles.nibble_sum, 21)
        
        sum_nibbles2 = dfd.SumNibbles()
        packet2 = dfb.DataPacket(data=fut.hex_string_to_data('AB C0'))
        sum_nibbles2.send(packet2)
        packet3 = dfb.DataPacket(data=fut.hex_string_to_data('0D EF'))
        sum_nibbles2.send(packet3)
        self.assertEquals(sum_nibbles2.nibble_sum, 75)
        nd = sum_nibbles2.nibble_dict
        self.assertEquals(nd[0xA], 1)
        packet4 = dfb.DataPacket(data=fut.hex_string_to_data('EE EE'))
        sum_nibbles2.send(packet4)
        self.assertEquals(nd[0xE], 5)  

    def test_switch_bits(self):
        switch_bits = dfd.SwitchBits(bit_switch_mask=0x01)
        switch_bits.next_filter = self.sink
        packet1 = dfb.DataPacket(data=fut.hex_string_to_data('AB CD EF'))
        switch_bits.send(packet1)
        self.assertEquals(self.sink.results[-1].data,
                                    fut.hex_string_to_data('AA CC EE'))
        packet2 = dfb.DataPacket(data=fut.hex_string_to_data('12 34 56'))
        switch_bits.send(packet2)
        self.assertEquals(self.sink.results[-1].data,
                                    fut.hex_string_to_data('13 35 57'))


class TestPrintData(unittest.TestCase):
    
    def setUp(self):
        self.prt_data = dfd.PrintData()
        
    def tearDown(self):
        pass
    
    def test_print_data(self):
        packet1 = dfb.DataPacket(data=fut.hex_string_to_data('AB CD EF'))
        # To test print we need to redirect stdout
        result = fut.print_redirect(self.prt_data.send, packet1)
        self.assertEquals(result[0].splitlines()[0], 'Data   1:  AB CD EF')
        

class TestShowProgress(unittest.TestCase):
    
    def setUp(self):
        self.hold_debug = fut.debug
        fut.debug = 900  # Temporarily turn off debugging
        self.show_progress1 = dfd.ShowProgress(packet_progress_freq=1)
        self.show_progress5 = dfd.ShowProgress(packet_progress_freq=5)
        self.show_progress9 = dfd.ShowProgress(packet_progress_freq=1,
                                               progress_line_length=3)
        
    def tearDown(self):
        fut.debug = self.hold_debug
    
    def _print_dots(self, show_progress, *args):
        for arg in args:
            show_progress.send(dfb.DataPacket(data=arg))
    
    def test_print_data1(self):
        result = fut.print_redirect(self._print_dots, self.show_progress1,
                                    1, 2, 3, 'fgfg', 5)
        self.assertEquals(result[0], '.' * 5)
        
    def test_print_data5(self):
        result1 = fut.print_redirect(self._print_dots, self.show_progress5,
                                    1, 2, 3, '4')
        self.assertEquals(result1[0], '')
        result2 = fut.print_redirect(self._print_dots, self.show_progress5,
                                    'yui', 6, 7)
        self.assertEquals(result2[0], '.')
        
    def test_print_multi_line(self):
        result = fut.print_redirect(self._print_dots, self.show_progress9,
                                    1, 2, 3, 4, 5, 6, 7, 8)
        self.assertEquals(result[0], '... 3\n... 6\n..')
        
if __name__ == '__main__':  #pragma: nocover
    runner = unittest.TextTestRunner()
##    runner.run(TestAddNumbers('test_add_non_number_list'))
##    TestFactorial('test_factorial').run()
##    TestPrintData('test_print_data').run()
##    TestShowProgress('test_print_data1').run()
    TestDataFilter1('test_filter1').run()
##    TestDataFilterDemo2('test_multiply_if_int').run()
##    TestDataFilterDemo('test_sum_bits').run()
    print '\n**1920** Finished'

