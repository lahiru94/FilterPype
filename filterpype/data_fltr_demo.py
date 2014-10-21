# -*- coding: utf-8 -*-

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

class KeySubstitutions(dfb.DataFilter):
    """Only exists to test pipeline key substitution."""
    ftype = "key_substitution"
    keys = ['first_key', 'second_key:value']

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
                

