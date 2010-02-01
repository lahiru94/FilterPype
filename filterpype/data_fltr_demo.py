# -*- coding: utf-8 -*-
# data_fltr_demo.py

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


import sys

import filterpype.data_filter as df
import filterpype.filter_utils as fut
import filterpype.data_fltr_base as dfb


class AddNumbers(dfb.DataFilter):
    """Adds the numbers in the input list, passing on the result in the
    packet. We're expecting either a Python list of numbers, or a comma-
    separated string to be read as a list.
    """
    ftype = 'add_numbers'

    def filter_data(self, packet):
        try:
            packet.data + []
            number_list = packet.data
        except TypeError:
            # Try splitting a string instead
            # This first version failed in tests with emtpy string
            ##number_list = [float(x) for x in packet.data.split(',')]
            number_list = [float(x) for x in packet.data.split(',')
                           if len(x) > 0]
        # Store the results in the packet dictionary, to leave
        # the original data in tact.
        packet.psum = sum(number_list)
        self.send_on(packet)

        
class ByteValueCounter(dfb.DataFilter):
    """Count how many of each byte value have passed through the filter.
    """
    ftype = 'byte_value_counter'
    
    def filter_data(self, packet):
        bvd = self.byte_value_dict
        for char in packet.data:
            try:
                bvd[ord(char)] += 1
            except KeyError:
                # First time we've found this char
                bvd[ord(char)] = 1
        self.send_on(packet)

    def zero_inputs(self):
        self.byte_value_dict = {}


class Capitalise(dfb.DataFilter):
    """Capitalise the first character of the packet's data.
    """
    ftype = 'capitalise'
                
    def filter_data(self, packet):
        packet.data = packet.data.capitalize()
        self.send_on(packet)

        
class FactorialCalc(dfb.DataFilter):
    """Experiment to see if we can loop recursively with filters.
       We can't: ValueError: generator already executing.
       Aha! We have a solution.
       Packets in will have attributes:

           'x'  -- the number to get the factorial of.
           'pending'  -- intermediate calculation
           'x_factorial'
           
       Until calculation is finished, packet will be sent via the branch
       to the tank_queue that feeds this filter.  <<<< rewrite TO-DO <<<<
       
       Follow FactorialCalc by BranchIf:recurse
    """
    ftype = 'factorial_calc'

    def filter_data(self, packet):
        assert packet.x > 0, 'Can\'t calc factorial of negative number'
        try:
            seq_num = packet.seq_num
        except AttributeError:
            seq_num = 0
        print '**6415** FactorialCalc, packet.seq_num=%d, x=%d' % (
            seq_num, packet.x)

        if packet.x == 1:
            try:
                packet.x_factorial = packet.pending
            except KeyError:  # First time being called
                packet.x_factorial = 1
            packet.recurse = False
            ##                    self.send_on(packet, fork_dest='main')
            print '**6440** Result = %d' % packet.x_factorial
        else:
            try:
                packet.pending *= packet.x
            except AttributeError:  # First time being called
                packet.pending = packet.x
            packet.x -= 1
            packet.recurse = True
            ##                    self.send_on(packet, fork_dest='branch')
        self.send_on(packet)


class MultiplyIfInteger(dfb.DataFilter):
    """If an input is an integer, or a string integer, return a multiple of 
       the number as a string, else return the original string, in a packet.
    """

    ftype = 'multiply_if_integer'
    keys = ['multiply_by']
               
    def filter_data(self, packet):
        # EAFP better than LBYL
        try:
            packet.data = str(int(packet.data) * self.multiply_by)
        except ValueError:
            pass
        self.send_on(packet)

                
class PrintData(dfb.DataFilter):
    """Print first part of data block in hex.
    """

    ftype = 'print_data'
    keys = ['print_limit:100']

    def filter_data(self, packet):
        self.counter += 1
        print 'Data %3d:  %s' % (
            self.counter, 
            fut.data_to_hex_string(packet.data[:self.print_limit]))
        self.send_on(packet)

    def zero_inputs(self):
        self.counter = 0

                
class ReverseString(dfb.DataFilter):
    """Filter to return a reversed string for each yielded packet"""
    ftype = 'reverse_string'
    
    def filter_data(self, packet):
        packet.data = packet.data[::-1]
        self.send_on(packet)

                
class ShowProgress(dfb.DataFilter):
    """Print char to screen to show progress
    """
    ftype = 'show_progress'
    # A dot every how many packets
    keys = ['packet_progress_freq', 'progress_char:.', 
            'progress_line_length:50']

    def _print_packet_count(self):
        sys.stdout.write(' %d\n' % self.packet_counter)
        
    def close_filter(self):
        """At the end of the pipeline, print an extra new line before any
        final output from the calling program.
        """
        self._print_packet_count()
                
    def filter_data(self, packet):
        self.packet_counter += 1
        if self.packet_counter % self.packet_progress_freq == 0:
            sys.stdout.write(self.progress_char)
            self.print_counter += 1
            # Move to the next output line
            if self.progress_line_length and \
               self.print_counter % self.progress_line_length == 0:
                self._print_packet_count()
        self.send_on(packet)

    def zero_inputs(self): 
        self.packet_counter = 0
        self.print_counter = 0
        

class SquareIfNumber(dfb.DataFilter):
    """If a string input is an number, return the square of the number, as a
    number, else leave packet alone.
    """
    ftype = 'square_if_number'
                
    def filter_data(self, packet):
        # EAFP better than LBYL
        try:
            packet.data = float(packet.data) * float(packet.data)
        except ValueError:
            pass
        self.send_on(packet)

                
class SumBits(dfb.DataFilter):
    """However much the bits are shuffled or padded with zeros, their sum
    should not change.
    """
    ftype = 'sum_bits'
         
    def filter_data(self, packet):
        self.bit_sum += fut.bit_sum(packet.data)
        self.byte_count += packet.data_length
        self.send_on(packet)

    def zero_inputs(self):
        self.byte_count = 0
        self.bit_sum = 0

                
class SumBytes(dfb.DataFilter):
    """However much the bytes are shuffled, their sum should not change.
    """
    ftype = 'sum_bytes'
    
    def filter_data(self, packet):
        for char in packet.data:
            byte = ord(char)
            self.byte_sum += byte
            self.byte_count += 1
            self.byte_dict[byte] += 1
        self.send_on(packet)

    def zero_inputs(self):
        self.byte_count = 0
        self.byte_sum = 0
        self.byte_dict = dict((n, 0) for n in xrange(0x100))

                
class SumNibbles(dfb.DataFilter):
    """However much the nibbles are shuffled or padded with zeros, their sum
    should not change.
    """
    ftype = 'sum_nibbles'

    def filter_data(self, packet):
        for char in packet.data:
            nibbles = (ord(char) >> 4, ord(char) & 0xF)
            self.nibble_sum += sum(nibbles)
            self.byte_count += 1
            for nibble in nibbles:
                self.nibble_dict[nibble] += 1
        self.send_on(packet)

    def zero_inputs(self):
        self.byte_count = 0
        self.nibble_sum = 0
        self.nibble_dict = dict((n, 0) for n in xrange(16))
        
                
class SwitchBits(dfb.DataFilter):
    """Filter to return data with some bits switched"""

    ftype = 'switch_bits'
    keys = ['bit_switch_mask']
    
    def filter_data(self, packet):
        new_data = []
        for char in packet.data:
            # xor one bit
            new_data.append(chr(ord(char) ^ self.bit_switch_mask))
        packet.data = ''.join(new_data)
        self.send_on(packet)
        
        
class TempTextAfter(dfb.DataFilter):
    """Put string after the data.
    """
    ftype = 'temp_text_after'
    keys = ['text_after']
                
    def filter_data(self, packet):
        packet.data = packet.data + self.text_after
        self.send_on(packet)

    
class TempTextBefore(dfb.DataFilter):
    """Put string in front of the data.
    """    
    ftype = 'temp_text_before'
    keys = ['text_before']
 
    def filter_data(self, packet):
        packet.data = self.text_before + packet.data
        self.send_on(packet)

                
class TempSpace(dfb.DataFilter):
    """Insert a space between each character in the data.
    """
    ftype = 'temp_space'
                
    def filter_data(self, packet):
        packet.data = ' '.join(char for char in packet.data)
        self.send_on(packet)
                

