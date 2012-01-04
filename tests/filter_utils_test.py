# -*- coding: utf-8 -*-
# filter_utils_test.py

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


import unittest
import time
import os
import mock

import filterpype.filter_utils as fut
import filterpype.data_fltr_base as dfb
import filterpype.data_filter as df

data_dir5 = os.path.join(fut.abs_dir_of_file(__file__), 
                         'test_data', 'tst_data5')

def setUp():
    pass
    
def tearDown():
    pass


class TestFilenameUtils(unittest.TestCase):
    
    def setUp(self):
        self.hold_debug_level = fut.debug
        fut.debug = 99
    
    def tearDown(self):
        pass
    
    def test_construct_filename(self):
        original_filename = '/one/two/basename.tsc'
        file_path, file_basename, file_ext = fut.destruct_filename(
                                             original_filename)
        tailnumber = '12345-A'
        
        new_filename = fut.construct_filename(tailnumber, '-', 
                                              file_basename, extension=file_ext,
                                              path=file_path)
        
        self.assertEquals(new_filename, '/one/two/12345-A-basename.tsc')

    def test_destruct_filename(self):
        filename = '/one/two/three/basename.ext'
        path, basename, extension = fut.destruct_filename(filename)
        self.assertEquals(path, '/one/two/three')
        self.assertEquals(basename, 'basename')
        self.assertEquals(extension, '.ext')
        
    
class TestFilterUtils(unittest.TestCase):
    
    def setUp(self):
        self.hold_debug_level = fut.debug
        fut.debug = 99
        
    def tearDown(self):
        pass
    
    def test_all_files(self):
        # Make three files to test against
        # Two that match and one that doesn't
        file_names = ['temp_file_one-tmp.tsc99', 
                      'temp_file_two-123tmp.tsc99', 
                      'temp_file_no_pattern.tsc99']
        for file_name in file_names:
            full_name = os.path.join(data_dir5, file_name)
            open(full_name, 'w').close()
        
        # Use generator to make a list
        pattern = '*tmp.tsc99'
        search_path = data_dir5
        file_found_list = list(fut.all_files(pattern, search_path))

        # Test to make sure there are only the two expected items in the list
        self.assertEquals(len(file_found_list), 2)
        
        # Remove testing files
        for file_name in file_names:
            full_name = os.path.join(data_dir5, file_name)
            os.remove(full_name)
        
        
    def test_bit_sum_one_char(self):
        self.assertEquals(fut.bit_sum(chr(0x00)), 0)
        self.assertEquals(fut.bit_sum(chr(0x03)), 2)
        self.assertEquals(fut.bit_sum(chr(0x11)), 2)
        self.assertEquals(fut.bit_sum(chr(0xFF)), 8)
        self.assertEquals(fut.bit_sum(chr(0xA5)), 4)
        # Test same char twice to force use of dictionary
        self.assertEquals(fut.bit_sum(chr(0xA5)), 4)
        self.assertEquals(fut.bit_sum('A'), 2) 
        self.assertEquals(fut.bit_sum('A'), 2) 
        self.assertEquals(fut.bit_sum('z'), 5) 
    
    def test_bit_sum_many_chars(self):
        self.assertEquals(fut.bit_sum('ABC'), 7) 
        self.assertEquals(fut.bit_sum('Hello, World'), 46) 
        self.assertEquals(fut.bit_sum('0123456789'), 35) 
        
    def test_config_obj_comma_fix(self):
        self.assertEquals(fut.config_obj_comma_fix('hello'), 'hello')
        self.assertEquals(fut.config_obj_comma_fix(['a','b','c']), 'a, b, c')
        self.assertEquals(fut.config_obj_comma_fix(['x = a + sum(3', 4, 'f4)']),
                                                   'x = a + sum(3, 4, f4)')

    def test_convert_boolean(self):
        self.assertEquals(fut.convert_config_str('True'), True)
        self.assertEquals(fut.convert_config_str('false'), False)
        self.assertEquals(fut.convert_config_str('T'), True)
        self.assertEquals(fut.convert_config_str(True), True)
    
    def t1est_convert_str_returns_on_value_error(self):
        # Does not work yet
        input_string = '{}'
        input_string.startswith = mock.Mock()
        input_string.endswith = input_string.startswith
        input_string.startswith.return_value = True
        self.assertEquals(fut.convert_config_str(input_string), input_string)        
        eval = eval_holder

    def test_convert_config(self):
        self.assertEquals(fut.convert_config_str('1234'), 1234)
        self.assertEquals(fut.convert_config_str(3456), 3456)
        self.assertEquals(fut.convert_config_str('hello'), 'hello')
        self.assertEquals(fut.convert_config_str('0x0'), 0)
        self.assertEquals(fut.convert_config_str('0x20'), 32)
        self.assertEquals(fut.convert_config_str('0xhello'), '0xhello')
        
    def test_convert_dict(self):
        self.assertEquals(fut.convert_config_str('{}'), {})
        self.assertEquals(fut.convert_config_str('{1:1, 2:2, 3:3}'), 
                                                  {1:1, 2:2, 3:3})
        self.assertEquals(fut.convert_config_str("{'q':'q', 'w':'w'}"), 
                                                  dict(q='q', w='w'))
        self.assertEquals(fut.convert_config_str('{$$//$$}'), '{$$//$$}')
        
    def test_convert_empty(self):
        self.assertEquals(fut.convert_config_str('empty'), '')
        self.assertEquals(fut.convert_config_str('Empty'), '')
        self.assertEquals(fut.convert_config_str(''), '')

    def test_convert_iterables(self):
        self.assertEquals(fut.convert_config_str('[]'), [])
        self.assertEquals(fut.convert_config_str('{}'), {})
        
    def test_convert_none(self):
        self.assertEquals(fut.convert_config_str(None), None)
        self.assertEquals(fut.convert_config_str('None'), None)
        self.assertEquals(fut.convert_config_str('none'), None)
        self.assertEquals(fut.convert_config_str('non'), 'non')

    def test_convert_list_as_list(self):
        self.assertEquals(fut.convert_config_str([]), [])
        self.assertEquals(fut.convert_config_str([1, 2, 3]), [1, 2, 3])
        self.assertEquals(fut.convert_config_str(['4', '5', '6']), [4, 5, 6])
        self.assertEquals(fut.convert_config_str(
            ['q', 'w', 'e']), ['q', 'w', 'e'])
        
    def test_convert_list_as_string(self):
        self.assertEquals(fut.convert_config_str('[]'), [])
        self.assertEquals(fut.convert_config_str('[1, 2, 3]'), [1, 2, 3])
        self.assertEquals(fut.convert_config_str("['4', '5', '6']"), [4, 5, 6])
        self.assertEquals(fut.convert_config_str("['q', 'w', 'e']"), 
                                                  ['q', 'w', 'e'])
        self.assertEquals(fut.convert_config_str(
            "['hello', '0x20', 'false', '[]']"), ['hello', 32, False, []])
        self.assertEquals(fut.convert_config_str('[$$//$$]'), '[$$//$$]')
        
    def test_convert_space(self):
        # Actual spaces are stripped out
        self.assertEquals(fut.convert_config_str(' '), '')
        self.assertEquals(fut.convert_config_str('space'), ' ')
        self.assertEquals(fut.convert_config_str('Space'), ' ')

    def test_convert_hex_to_int(self):
        self.assertEquals(fut.convert_config_str('0x2000'), 8192)
        self.assertEquals(fut.convert_config_str(0x2000), 8192)
        self.assertEquals(fut.convert_config_str('A'), 'A')
        self.assertEquals(fut.convert_config_str('0xA'), 10)
        self.assertEquals(fut.convert_config_str('0xabc'), 0xABC)
        
    def test_data_to_hex_string(self):
        self.assertEquals(fut.data_to_hex_string('ABC'), '41 42 43')
        self.assertEquals(fut.data_to_hex_string('hello world'), 
                          '68 65 6C 6C 6F 20 77 6F 72 6C 64')
        self.assertEquals(fut.data_to_hex_string(''), '')
        self.assertEquals(fut.data_to_hex_string('ABC', space='-'), '41-42-43')
        self.assertEquals(fut.data_to_hex_string('ABC', space=''), '414243')
        
    def test_data_type(self):
        self.assertEquals(fut.data_type('abc'), 'string')
        self.assertEquals(fut.data_type(2), 'number')
        self.assertEquals(fut.data_type(''), 'string')
        self.assertEquals(fut.data_type(-2.5), 'number')
        self.assertEquals(fut.data_type(None), 'none')
        self.assertEquals(fut.data_type([1,2,3]), 'list')
        self.assertEquals(fut.data_type({}), 'unknown')
        
    def test_get_values_from_name(self):
        get_vals = fut.get_values_from_name
        self.assertEquals(get_vals('abc:234'), ('abc', [234]))
        self.assertEquals(get_vals('abc:def'), ('abc', ['def']))
        self.assertEquals(get_vals('abc'), ('abc', []))
        self.assertEquals(get_vals(':567'), ('', [567]))
        self.assertEquals(get_vals('abc:true'), ('abc', [True]))
        self.assertEquals(get_vals('abc:1.25'), ('abc', [1.25]))
        self.assertEquals(get_vals('foo:35:fred:${baz}'), 
                          ('foo', [35, 'fred', '${baz}']))
    
    def test_hex_string_to_data(self):
        self.assertEquals(fut.hex_string_to_data('41 42 43'), 'ABC')
        self.assertEquals(fut.hex_string_to_data('41-42-43', '-'), 'ABC')
        self.assertEquals(fut.hex_string_to_data('414243'), 'ABC')
        self.assertEquals(fut.hex_string_to_data('68 65 6C 6C 6F 20 77 6F 72 6C 64'),
                                            'hello world')
        self.assertEquals(fut.hex_string_to_data(''), '')
        # Trailing space caused problem, because of using .split(' ') instead
        # of .split(None). See Python in Nutshell, 2nd ed p.190
        self.assertEquals(fut.hex_string_to_data('41 42 43 '), 'ABC')
        
    def test_latest_defaults(self):
        keys_in = ['123', 'fred', 'jane', 'def:3']
        keys_out = ['123', 'fred', 'jane', 'def:3']
        self.assertEquals(fut.latest_defaults(keys_in), keys_out)
        keys_in = ['abc', 'def:0', 'fred', 'jane:ergo', 'def:3']
        keys_out = ['abc', 'def:3', 'fred', 'jane:ergo']
        self.assertEquals(fut.latest_defaults(keys_in), keys_out)
        keys_in = []
        keys_out = []
        self.assertEquals(fut.latest_defaults(keys_in), keys_out)
        keys_in = ['123', 'fred', 'jane', 'def:3', 'jane:445']
        keys_out = ['123', 'fred', 'jane:445', 'def:3']
        self.assertEquals(fut.latest_defaults(keys_in), keys_out)

    def test_make_dict(self):
        d1 = {'a': 1, 'b': 2}
        d2 = {'c': 3, 'd': 4}
        d3 = d1.copy()
        d3.update(d2)
        self.assertEquals(fut.make_dict(*d1.items()), d1)
        self.assertEquals(fut.make_dict(c=3, d=4), d2)
        d4 = fut.make_dict(*d1.items())
        d4.update(d2)
        self.assertEquals(d4, d3)
        
    def test_pad_string(self):
        self.assertEquals(fut.pad_string('abc', 5), 'abc  ')
        self.assertEquals(fut.pad_string('abc', 1), 'abc')
        self.assertEquals(fut.pad_string('', 3), '   ')
        self.assertEquals(fut.pad_string('def', 4, 'x'), 'defx')  
    
    def test_print_redirect(self):
        def print_something(text):
            print text
            return len(text)
        self.assertEquals(fut.print_redirect(print_something, 'hello world'), 
                          ('hello world\n', 11))
        
    def test_remove_punctuation(self):
        lotsa_punc = '!"#$%&\'()*+,2-./:;7<= >pu?@[\\]^n_c`\t\n{Fou|nd}~z'
        print "lots of punctuation:", lotsa_punc
        punc_removed = fut.remove_punctuation(lotsa_punc)
        self.assertEqual(punc_removed, 
                         '27 punc\t\nFoundz')
        print "punctuation removed:", punc_removed
        
    def test_reverse_byte(self):
        self.assertEquals(fut.reverse_byte(0), 0)
        self.assertEquals(fut.reverse_byte(0xFF), 0xFF)
        self.assertEquals(fut.reverse_byte(0x11), 0x88)
        self.assertEquals(fut.reverse_byte(0x12), 0x48)
        self.assertEquals(fut.reverse_byte(0xFE), 0x7F)
        
    def test_split_strings(self):
        self.assertEquals(fut.split_strings('ABCD', 2), ['AB', 'CD'])
        self.assertEquals(fut.split_strings('ABCDE', 2), ['AB', 'CD', 'E'])
        self.assertEquals(fut.split_strings('', 2), [])
        self.assertEquals(fut.split_strings('ABCDEF', 5), ['ABCDE', 'F'])
        self.assertRaises(ValueError, fut.split_strings, 'ABCDEF', 0)

    def test_strip_number_suffix(self):
        self.assertEquals(fut.strip_number_suffix('abc123'), 'abc')
        self.assertEquals(fut.strip_number_suffix('12345'), '')
        self.assertEquals(fut.strip_number_suffix('9'), '')
        self.assertEquals(fut.strip_number_suffix('hello'), 'hello')
        self.assertEquals(fut.strip_number_suffix('12AB34'), '12AB')
        self.assertEquals(fut.strip_number_suffix(''), '')
        self.assertEquals(fut.strip_number_suffix('hello_'), 'hello')
        self.assertEquals(fut.strip_number_suffix('abc_123'), 'abc')
        self.assertEquals(fut.strip_number_suffix('12AB_34'), '12AB')
        self.assertEquals(fut.strip_number_suffix('_'), '')
    
    def test_strip_prefix(self):
        self.assertEquals(fut.strip_prefix('001~xx', '~'), 'xx')
        self.assertEquals(fut.strip_prefix('001~', '~'), '')
        self.assertEquals(fut.strip_prefix('~xx', '~'), 'xx')
        self.assertEquals(fut.strip_prefix('xx', '~'), 'xx')
        self.assertEquals(fut.strip_prefix('001-xx', '-'), 'xx')
        
    def test_strip_prefixes(self):
        regex = r'\d\d\d\d~'
        self.assertEquals(fut.strip_prefixes('1234~xx', regex), 'xx')
        self.assertEquals(fut.strip_prefixes('123~xx', regex), '123~xx')
        self.assertEquals(fut.strip_prefixes('123~xx (5678~yy) 9876~zz', 
                                             regex), '123~xx (yy) zz')
        self.assertEquals(fut.strip_prefixes('1234~2345~', regex), '')
        self.assertEquals(fut.strip_prefixes('qwert0000~yui', regex), 
                          'qwertyui')
        self.assertEquals(fut.strip_prefixes(None, regex), None)
        self.assertEquals(fut.strip_prefixes(123, regex), 123)
        
        
    ##def test_abs_dir_of_file(self):
        ##self.assertEquals(os.path.split(fut.abs_dir_of_file(__file__))[0],
                          ##os.path.split(fut.abs_dir_package())[0])
        
    def test_temp_file_name(self):
        fname1 = fut.random_file_name()
        print '**8200** temp_file_name1 = "%s"' % fname1
        self.assertTrue(fname1.endswith('.dat'))
        self.assertEquals(len(fname1), 40)
        # No two names should ever be the same
        fname2 = fut.random_file_name()
        print '**8200** temp_file_name2 = "%s"' % fname2
        self.assertNotEquals(fname1, fname2)

    def test_unindent(self):
        lines1 = ['   qwe',
                  '  etryry',
                  '',
                  '     xxx',
                  ]
        self.assertEquals(fut.unindent(lines1),  
                          [' qwe', 'etryry', '', '   xxx'])
        self.assertEquals(fut.unindent([]), [])
        lines2 = ['a', 'b', 'c']
        self.assertEquals(fut.unindent(lines2), lines2)
   

class TestConversions(unittest.TestCase):
    def test_convert_to_2s_complement_char(self):
        """ test_convert_to_2s_complement_char
            
        """
        char_1 = '\xFF'
        char_2 = '\x01'
        
        result1 = fut.convert_to_2s_complement(char_1)
        result2 = fut.convert_to_2s_complement(char_2)
        self.assertEquals(result1, -1)
        self.assertEquals(result2, 1)
        
    def test_convert_to_2s_complement_short(self):
        """ test_convert_to_2s_complement_short
            
        """
        short_1 = '\xFF\xFF'
        short_2 = '\x00\x01'
        
        result1 = fut.convert_to_2s_complement(short_1)
        result2 = fut.convert_to_2s_complement(short_2)
        self.assertEquals(result1, -1)
        self.assertEquals(result2, 1)
        
    def test_convert_to_2s_complement_long(self):
        """ test_convert_to_2s_complement_long
            
        """
        long_1 = '\xFF\xFF\xFF\xFF'
        long_2 = '\x00\x00\x00\x01'
        
        result1 = fut.convert_to_2s_complement(long_1)
        result2 = fut.convert_to_2s_complement(long_2)
        self.assertEquals(result1, -1)
        self.assertEquals(result2, 1)
        
    def test_convert_to_2s_complement_raises(self):
        """ test_convert_to_2s_complement_raises
            
        """
        non_str = 8
        self.assertRaises(TypeError, fut.convert_to_2s_complement, non_str)

    def test_convert_to_2s_complement_6_bytes(self):
        """ test_convert_to_2s_complement_6_bytes
            
            This should return none as we don't want to deal with things that
            are not 1, 2 or 4 bytes long (the functionality does not yet exist)
            
        """
        long_str = '\x12\x12\x12\x12\x12\x12'
        result = fut.convert_to_2s_complement(long_str)
        self.assertEquals(result, None)
    
    def test_convert_integers_to_hex(self):
        """ test_convert_integers_to_hex
            
            Convert a list of integers into hex values
        """
        integer_list = [1, 2, 3, 4, 5]
        with_negative_list = [1, -1, -2]
        
        exp_mode1_res = ['0x1', '0x2', '0x3', '0x4', '0x5']
        exp_mode2_res = '0x0102030405'
        exp_mode3_res = '\x01\x02\x03\x04\x05'
        exp_mode4_res = '01 02 03 04 05'

        result1 = fut.convert_integers_to_hex(integer_list, 1)
        result2 = fut.convert_integers_to_hex(integer_list, 2)
        result3 = fut.convert_integers_to_hex(integer_list, 3)
        result4 = fut.convert_integers_to_hex(integer_list, 4)

        self.assertEquals(result1, exp_mode1_res)
        self.assertEquals(result2, exp_mode2_res)
        self.assertEquals(result3, exp_mode3_res)
        self.assertEquals(result4, exp_mode4_res)
        self.assertRaises(ValueError, fut.convert_integers_to_hex,
                          with_negative_list, 1)

    def test_get_word_interval_num_results(self):
        """ test_get_word_interval_num_results
            
            Make sure that the correct word interval and number of results are
            returned
        """
        wps1 = 256
        hz1 = 4
        wps2 = 64
        hz2 = 0.25
        wps3 = 512
        hz3 = 2
        wps4 = 128
        hz4 = 0.125
        wps5 = 0
        hz5 = 0
        
        expected_word_interval1 = 64
        expected_number_of_results1 = 64
        expected_word_interval2 = 256
        expected_number_of_results2 = 4
        expected_word_interval3 = 256
        expected_number_of_results3 = 32
        expected_word_interval4 = 1024
        expected_number_of_results4 = 2
        
        res_word_interval1, res_num_results1 = fut.get_word_interval_num_results(
            wps1, hz1)
        res_word_interval2, res_num_results2 = fut.get_word_interval_num_results(
            wps2, hz2)
        res_word_interval3, res_num_results3 = fut.get_word_interval_num_results(
            wps3, hz3)
        res_word_interval4, res_num_results4 = fut.get_word_interval_num_results(
            wps4, hz4)
        self.assertRaises(ValueError, fut.get_word_interval_num_results, wps5,
                          hz5)
        
        self.assertEquals(res_num_results1, expected_number_of_results1)
        self.assertEquals(res_word_interval1, expected_word_interval1)
        self.assertEquals(res_num_results2, expected_number_of_results2)
        self.assertEquals(res_word_interval2, expected_word_interval2)
        self.assertEquals(res_num_results3, expected_number_of_results3)
        self.assertEquals(res_word_interval3, expected_word_interval3)
        self.assertEquals(res_num_results4, expected_number_of_results4)
        self.assertEquals(res_word_interval4, expected_word_interval4)
        

        
def spike1():
    # Test the speed of byte reverTestMultiPartParameterJoiningsal
    # Result : Calculate takes 5* as long as dictionary lookup
    start = time.time()
    a = 0x88
    b = {1:3, 2:55}
    for j in xrange(5 * 10 ** 6):
        a = fut.reverse_byte(a)
##        a = b[1]
    print 'After %0.2f secs, a = 0x%X' % (time.time() - start, a)
        
if __name__ == '__main__':  #pragma: nocover
    TestFilterUtils('test_latest_defaults').run()
    #TestFilterUtils('test_config_obj_comma_fix').run()
    #TestFilterUtils('test_convert_list_as_list').run()
    #TestConversions('test_convert_to_2s_complement_char').run()
    #TestConversions('test_convert_to_2s_complement_short').run()
    #TestConversions('test_convert_to_2s_complement_long').run()
    TestFilterUtils('test_unindent').run()
    ##TestFilterUtils('test_convert_str_returns_on_value_error').run()
##    TestConversions('test_convert_start_end_bytes_from_docs').run()
    print '\n**1940** Finished'
