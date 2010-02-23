# -*- coding: utf-8 -*-
# filter_utils.py

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


import re
import sys
import cStringIO
import os
import glob
import uuid
import string
import struct

_bit_sum_dict = {}

debug = -1 # for production
## debug = 1
## debug = 3  # Important debug messages
##debug = 5  # Lots of messages

quick_test = 50 # Higher the number for faster, e.g. 50
               # 0 for all tests
           
def dbg_print(text, level=5):
    """
    Print the text to std_out if "debug" in this module is >= level.
    i.e. If level is 0, then it will always be printed. The higher the
    level, the less likely it is to be printed.
    The ">" is inserted just to show which print statements have been converted
    to dbg_print.
    """
    if level <= debug:
        if text.startswith('\n'):
            prefix = '\n>'
            text = text.lstrip()
        else:
            prefix = '>'
        print prefix + text

def define_hex_conversions():
    global hex_to_dat
    hex_to_dat = {}
    for j in xrange(256):
        ch = chr(j)
        hex_ch = '%2.2X' % j
        hex_to_dat[hex_ch] = ch
        
def print_hex_conversions():
    for j in [0x47, 0x48, 0x49, 0x4A, 0x4B]:
        hex_ch = '%2.2X' % j
        dbg_print('**14820** hex_ch %s: %2.2X' % (
            hex_ch, ord(hex_to_dat[hex_ch])), 8)
define_hex_conversions()
##print_hex_conversions()

# Alternative executable
#     /Library/Frameworks/Python.framework/Versions/Current_2.6/bin/python
               
# Assume file structure:
#    /MyPackageName
#        /mypackagename
#            /docs
#            /tests
#
     
def abs_dir_of_file(abs_file_location):
    """Returns the absolute path of the package containing abs_file_location,
    usually found from __file__.
    """
    return os.path.dirname(os.path.realpath(abs_file_location))
                                 
##def abs_dir_package(abs_file_location): 
    ##"""Returns the absolute path of the package containing abs_file_location,
    ##usually found from __file__.
    ##"""
    ##return os.path.split(os.path.realpath(abs_file_location))[0]

##def abs_dir_tests(abs_file_location):
    ##"""Returns the absolute path of the tests in the package containing 
    ##abs_file_location, usually found from __file__.
    ##"""
    ##return os.path.join(os.path.split(abs_dir_package(abs_file_location))[0], 
                        ##'tests')

def all_files(pattern, search_path, path_sep=os.pathsep):
    """Given a search path, yield all files matching the pattern.
    From Python Cookbook, p. 92.
    """
    for path in search_path.split(path_sep):
        for match in glob.glob(os.path.join(path, pattern)):
            yield match

def bit_sum(chars):
    """Add the bits in all chars"""
    def _bit_sum_char(char):
        """Add the bits in a single char, if not already in the dictionary. """
        try:
            return _bit_sum_dict[ord(char)]
        except KeyError:
            byte_bit_sum = 0
            for shift in xrange(8):
                byte_bit_sum += (ord(char) >> shift) & 0x01 
            _bit_sum_dict[ord(char)] = byte_bit_sum
            return byte_bit_sum
    result = 0
    for char in chars:
        result += _bit_sum_char(char)
    return result

def config_obj_comma_fix(text):
    """ConfigObj puts strings with commas into a list, converting to integers
    where possible. Reconstruct the string with string types. Rejoin the list
    items with a comma, if present.
    """
    try:
        return ', '.join(str(x) for x in (text + []))
    except TypeError:   
        return text

def construct_filename(*args, **kwargs):
    filename = ''.join(args + (kwargs.get('extension'),))
    return os.path.join(kwargs.get('path', ''), filename)

def copy_attr(from_obj, to_obj, attr_name):
    to_obj.__dict__[attr_name] = from_obj.__dict__[attr_name]

def convert_config_list(values):
    """Apply convert_config_str for each item in the list.
    """
    conversions = []
    for val in values:
        conversions.append(convert_config_str(val))
    return conversions
    
def convert_config_str(value):
    """With string from config file, interpret it in order:
       1) as a number (integer, float or hex)
       2) as Boolean
       3) as space
       4) list
       5) dictionary
       6) else return original string.
    """
    try:
        value + ''  # Is this a string to be interpreted?
    except TypeError:
        # Is this a list of values to be converted?
        try:
            return convert_config_list(value + [])  # TypeError if not list
        except TypeError:
            # Not a string, or a list, so give up and don't try to convert
            return value
    value = value.strip()  # Remove surrounding white space
    try:
        if value.isdigit():
            return int(value)  # Try for integer
        else:
            return float(value)
    except ValueError:
        if value.startswith('0x'):
            try:
                return int(value, 16)  # Try for hex string
            except ValueError:
                pass   
        compare_value = value.lower()
        if compare_value in ['true', 't']:
            return True
        elif compare_value in ['false', 'f']:
            return False
        elif compare_value == 'none':
            return None
        elif compare_value == 'empty':
            return ''
        elif compare_value == 'space':
            return ' '
        elif value.startswith('[') and value.endswith(']'):
            # If paranoid, validate this with a regex for a Python list first
            try:
                alist = eval(value)
                try:
                    return convert_config_list(alist + []) 
                except TypeError:
                    return value
            except SyntaxError:
                # It's not really a list. Give up -- return original string
                return value  
        elif value.startswith('{') and value.endswith('}'):
            # If paranoid, validate value with a regex for a Python dict first
            try:
                adict = eval(value)
                adict.update({})  # Attribute error if not dict
                return adict
            except SyntaxError:
                # It's not really a dict. Give up -- return original string
                return value 
        else:
            return value  # Original string
        

##def convert_to_int(value):
    ##"""Return the integer value, if the input text is a hex string, or
       ##an integer, else return the original string."""
    ##try:
        ##return int(value)  # Check for integer
    ##except (ValueError, TypeError):
        ##if value.startswith('0x'):
            ##try:
                ##return int(value, 16)  # Check for hex string
            ##except (ValueError, TypeError):
                ##return value  # OK, it's just a string
        ##else:
            ##return value

def convert_to_2s_complement(str_val):
    """ Convert a data string into it 2s complement value
        E.g.
        0xF22C4158 is the hex string 0xF2 0x2C 0x41 0x58
        0xF2 0x2C 0x41 0x58 --> -231980712 (in 2s complement)
        
        NOTE: values must be strings
        NOTE: Please only give chars (1 byte), shorts (2 bytes) or
              longs (4 bytes). Anything else will currently return an error
    """
    try:
        str_val + ''
    except TypeError:
        raise TypeError, "String expected but got %s instead" % type(str_val)

    if len(str_val) == 1:
        converted_value = struct.unpack('>b', str_val)[0]
    elif len(str_val) == 2:
        converted_value = struct.unpack('>h', str_val)[0]
    elif len(str_val) == 4:
        converted_value = struct.unpack('>l', str_val)[0]
    else:
        print "Only chars (1 byte), shorts (2 bytes) and longs (4 bytes) " +\
              "are valid inputs. String of length %s given '%s'" % (
                  str(len(str_val)), str_val)
        return
    return converted_value

def get_word_interval_num_results(wps, hz):
    """
        Get the word interval and number of results per superframe, given the
        words per second and hertz
        
        WARNING: This function returns an int. If the user does not give
                 sensible values and a calculation is made that results in
                 non-zero values on the right hand side of the decimal point,
                 an inaccurate result will be given.
                 
                 EG: 
                 Inputs: WPS:256, HZ:3
                 Real Interval: 85.333333333333329, Real num results: 48.0
                 Function Output: (85, 48)       
          
    """
    if wps == 0 or hz == 0:
        msg = "One or more values are zero which is not allowed"
        raise ValueError, msg
    interval = float(wps) / float(hz)
    number_of_results = float(hz) * 16.0
    
    return (int(interval), int(number_of_results))

def convert_integers_to_hex(int_list, mode=4):
    """ Use this function for converting a list of integers into a hex
        representation in a format determined by mode.
        
        E.g. If input is [1, 2, 3]
        Mode        Format
        1           ['0x1', '0x2', '0x3']
        2           '0x010203'
        3           '\\x01\\x02\\x03'
        4           '01 02 03'
        
    """
    # Don't allow negative integers. Sorry but negative in hex values are
    # not valid e.g. you can't have 0x123-4
    for value in int_list:
        if value < 0:
            msg = 'negative integer found. Negative integers are not allowed'
            raise ValueError, msg
    
    # modexconvert (where x is a number) are lambda functions for doing
    # what needs to be done to the integer list
    # mode1convert converts into what's required by mode 1, mode2convert to
    # what's required by mode 2 and so on.
    mode1convert = lambda int_list: [hex(hex_val) for hex_val in int_list]
    mode3convert = lambda int_list: ''.join(
        [chr(hex_val) for hex_val in int_list])
    mode4convert = lambda int_list: data_to_hex_string(mode3convert(int_list))
    mode2convert = lambda int_list: '0x' + ''.join(
        mode4convert(int_list).split())
    
    # A dictionary mapping the modes to the lambda functions
    mode_funcs = {1:mode1convert,
                  2:mode2convert,
                  3:mode3convert,
                  4:mode4convert}
    
    # Using the user given mode, go execute the correct function
    return mode_funcs[mode](int_list)

def convert_to_zero_based_tuple(tup):
    """For each number in the tuple, return one less, converting 1-based
       counting to 0-based.
    """
    return tuple(x - 1 for x in tup)
    
def data_to_hex_string(data, limit=None, space=' '):
    """Return the hexadecimal representation of a string of bytes, so that
       it can be printed and compared with the display of a hex editor.
       
       e.g. 'ABC' --> '41 42 43'
    """
    return space.join([('%2.2X' % ord(char)) for char in data][:limit])

def data_type(data):
    """Return the type of data passed in.
    """
    try:
        data + []
        return 'list'
    except TypeError: # Not a list
        try:
            data + ''
            return 'string'
        except TypeError: # Not a string
            try:
                data * 1
                return 'number'
            except TypeError: # Not a number
                if data is None:
                    return 'none'
                else:
                    return 'unknown' 
                
def destruct_filename(filename):
    path, basename = os.path.split(filename)
    base, extension = os.path.splitext(basename)
    return path, base, extension

def get_values_from_name(filter_name):
    """Essential key values may be set after a ':' for the each essential key.
       e.g. foo:35:fred:${baz}
       This provides three key values to the filter foo: 35 (as an integer),
       'fred' (as a string) and baz as a variable to be substituted for.
    """
    parts = filter_name.split(':')
    # Parts list must have at least one part, if there is no ':'
    filt_name = parts[0]
    # Convert to integer, Boolean, etc if possible
    values = [convert_config_str(part) for part in parts[1:]]
    return filt_name, values

def hex_string_to_data(data, space=None):
    """Read string data as hexadecimal bytes, and return as data string.
       e.g '41 42 43' --> 'ABC'
       
       Note the use of the int() function, with a second parameter. 
       I hadn't realised that this was necessary for converting anything 
       apart from base 10 strings.
    """
    # Check that input data is made with spaces/etc in between hex chars
    bytes2 = data.split(space)  # NB default to None not ' '
    dbg_print('**14800** bytes2 =   "%s"' % ' '.join(ch for ch in bytes2), 8)
    if len(bytes2) == 1:  
        # No space found, so assume we have a continuous string of 0-F hex
        bytes2 = split_strings(data, 2)
##    result = ''.join(chr(int('0x%s' % ch, 16)) for ch in bytes2 if ch)
##    result = ''.join(chr(int('0x%2.2x' % ch, 16)) for ch in bytes2 if ch)
##    result = ''.join(chr(int(ch, 16)) for ch in bytes2 if ch)
    result = ''.join(hex_to_dat[ch] for ch in bytes2 if ch)
    result2 = []
    for ch in bytes2:
        result2.append(hex_to_dat[ch])
    result3 = ''.join(result2)
    results_ch = ' '.join([('%2.2X' % ord(ch)) for ch in result])
    dbg_print('**14810** data     = "%s"' % results_ch, 8)
    return result

def latest_defaults(keys):
    """Take a list with some repeated keys which have different default
    values. Return the only key with the latest value, in the position of the
    first occurrence of the key. e.g.
        keys_in = ['abc', 'def:0', 'fred', 'jane:ergo', 'def:3']
        keys_out = ['abc', 'def:3', 'fred', 'jane:ergo']
    """
    bare_keys = []
    key_values = {}
    for key in keys:
        bare_key = key.split(':')[0] 
        if ':' in key:
            # Later values will overwrite earlier ones
            key_values[bare_key] = key.split(':')[1]
        if bare_key not in bare_keys:
            # First position of bare_key will be maintained
            bare_keys.append(bare_key)
    keys_out = []
    for bare_key in bare_keys:
        if bare_key in key_values:
            keys_out.append('%s:%s' % (bare_key, key_values[bare_key]))
        else:
            keys_out.append(bare_key)
    return keys_out

def make_dict(*args, **kwargs):
    """Ease the dictionary making process by removing the need for quoting
       the keys.  \*args is for tuples coming from an existing dictionary,
       using the \*adict.items() form. \**kwargs forms keyword parameters into
       a dictionary.
       
    """
    adict = dict(args)
    adict.update(kwargs)
    return adict

def nibble_count(bit_length):
    """How many nibbles needed to show required numbers of bits?
    """
    return 1 + (bit_length - 1) // 4
    
def pad_string(text, length, pad_char=' '):
    """Pad input string to the length with pad_char. 
       If length < length(text), return the whole string.
    """
    return text + (pad_char * (length - len(text)))

def printable(text):
    """Return a string with all unprintable characters replaced with '?'
    """
    result = []
    for char in text:
        if ord(char) >= 32 and ord(char) <= 127:
            result.append(char)
        else:
            result.append('?')
    return ''.join(result)

def print_redirect(func, *args, **kwargs):
    """redirect(func, ...) --> (output string result, func's return value)
       (See p.257 of Python in a Nutshell)
       func must be a callable and may emit results to standard output.
       Capture those results as a string and return a pair: the print 
       output and func's return value.
    """
    save_out = sys.stdout
    sys.stdout = cStringIO.StringIO()
    try:
        ret_val = func(*args, **kwargs)
        return sys.stdout.getvalue(), ret_val
    finally:
        sys.stdout.close()
        sys.stdout = save_out

def pypes_for_dict_gen(file_dir):
    """Create generator to return all pypes in the pypes directory.
    """
##    print '**10530** Looking for *.pype files in %s' % file_dir
    for file_name in all_files('*.pype', file_dir):
        # Remove the path and the extension
        short_file_name = os.path.basename(file_name)[:-5]
##        print '**10550**', short_file_name, file_name
        yield short_file_name, file_name
        
def random_file_name(ext='.dat'):
    """Returns a unique random file name generated as a UUID string. This is
    statistically guaranteed to avoid a name clash.
    """
    return str(uuid.uuid4()) + ext

def remove_punctuation(string_in):
    """Removes all punctuation chars from string_in
    
    Punctuation removed:
    '!"#$%&\'()*+,-./:;<=>?@[\\]^_`{|}~'
    """
    allchars = string.maketrans('', '')
    keep = string.ascii_letters + string.digits + string.whitespace
    delchars = allchars.translate(allchars, keep)
    return string_in.translate(allchars, delchars)

def reverse_byte(byte):
##    for j in xrange(8):
##        result.append((byte & (1 << j)) << (7 - j))
    result = ((byte & 0x01) << 7) | \
             ((byte & 0x02) << 5) | \
             ((byte & 0x04) << 3) | \
             ((byte & 0x08) << 1) | \
             ((byte & 0x10) >> 1) | \
             ((byte & 0x20) >> 3) | \
             ((byte & 0x40) >> 5) | \
             ((byte & 0x80) >> 7)
    return result
        
##def set_first_ess_key_val(filter_class, essential_key_value, attr_dict, 
                          ##error_class):
    ##"""An essential key value can be set from config or route, but not
       ##both. Raise error even the two values are the same. <<<< TO-DO <<<<<
    ##"""
    ### TO-DO: tests for set_fekv_in_param_dict
    ##try:
        ##first_essential_key = filter_class.essential_keys[0]
    ##except IndexError:
        ##raise error_class, 'Filter class "%s" has no essential keys' % (
                                                        ##filter_class.__name__)
    ####if first_essential_key in attr_dict:
        ####if set_twice == 'ignore' and \
           ####attr_dict[first_essential_key] == essential_key_value:
            ##### Ignore resetting if it is to the same value
            ####return
        ####else:
            ####msg = 'Can\'t set the %s.%s parameter value more than once' % (
                  ####filter_class.__name__, first_essential_key)
            ####raise error_class, msg
    ##if first_essential_key not in attr_dict:
        ### Route may refer to the same filter more than once with an
        ### essential key suffix. Set it if it is the first time, or...
        ##attr_dict['first_essential_key'] = first_essential_key
        ##attr_dict[first_essential_key] = essential_key_value
    ##else:
        ### ...check that we're not trying to change the value.
        ##if attr_dict[first_essential_key] != essential_key_value:
            ##msg = 'Can\'t change the %s.%s parameter value from %s to %s' % (
                ##filter_class.__name__, first_essential_key,
                ##attr_dict[first_essential_key], essential_key_value)
            ##raise error_class, msg
            
def split_strings(data, split_size):
    """Return the input string as a list of strings, split into split_size
       pieces.  The last piece sent may be an incomplete split.
    """
    return [data[j:j + split_size] for j in xrange(0, len(data), split_size)]

def strip_number_suffix(txt):
    """Remove any trailing digits from a string and underscore.
    """
    for j in xrange(len(txt) - 1, -1, -1):
        if not txt[j].isdigit() and txt[j] != '_':
            alpha_at = j
            break
    else:
        alpha_at = -1
    return txt[:alpha_at + 1]
    
def strip_prefix(txt, separator):
    """Remove the text up to and including the separator, if there is one,
       or else return the original text.
    """
    try:
        return txt.split(separator)[1]
    except IndexError:  # No separator
        return txt
    except AttributeError: # Probably trying to split None
        return None
    
def strip_prefixes(txt, prefix_regex):
    re_prefix = re.compile(prefix_regex)
    try:
        return ''.join(re_prefix.split(txt))
    except TypeError:  # Not a string
        return txt
    
def unindent(lines):
    """Remove the same number of spaces from the front of each line, so that
    at least one line has no leading spaces. Return a list of the stripped
    lines. Ignore blank lines, even though they may have leading spaces.
    """
    if lines:
        min_spaces = min((len(x) - len(x.lstrip())) for x in lines if x.strip())
        return [line[min_spaces:] for line in lines]
    else:
        return []
   
    
bcd_msg = "Input values must be in in the BCD range 00 to 99 (A-F not supported)." 
BCD_lookUp = {chr(0):"00", chr(1):"01", chr(2):"02", chr(3):"03", chr(4):"04",
          chr(5):"05", chr(6):"06", chr(7):"07", chr(8):"08", chr(9):"09",
          chr(16):"10", chr(17):"11", chr(18):"12", chr(19):"13", chr(20):"14",
          chr(21):"15", chr(22):"16", chr(23):"17", chr(24):"18", chr(25):"19",
          chr(32):"20", chr(33):"21", chr(34):"22", chr(35):"23", chr(36):"24",
          chr(37):"25", chr(38):"26", chr(39):"27", chr(40):"28", chr(41):"29",
          chr(48):"30", chr(49):"31", chr(50):"32", chr(51):"33", chr(52):"34",
          chr(53):"35", chr(54):"36", chr(55):"37", chr(56):"38", chr(57):"39",
          chr(64):"40", chr(65):"41", chr(66):"42", chr(67):"43", chr(68):"44",
          chr(69):"45", chr(70):"46", chr(71):"47", chr(72):"48", chr(73):"49",
          chr(80):"50", chr(81):"51", chr(82):"52", chr(83):"53", chr(84):"54",
          chr(85):"55", chr(86):"56", chr(87):"57", chr(88):"58", chr(89):"59",
          chr(96):"60", chr(97):"61", chr(98):"62", chr(99):"63", chr(100):"64",
          chr(101):"65", chr(102):"66", chr(103):"67", chr(104):"68", chr(105):"69",
          chr(112):"70", chr(113):"71", chr(114):"72", chr(115):"73", chr(116):"74",
          chr(117):"75", chr(118):"76", chr(119):"77", chr(120):"78", chr(121):"79",
          chr(128):"80", chr(129):"81", chr(130):"82", chr(131):"83", chr(132):"84",
          chr(133):"85",  chr(134):"86", chr(135):"87", chr(136):"88", chr(137):"89",
          chr(144):"90",  chr(145):"91", chr(146):"92", chr(147):"93", chr(148):"94",
          chr(149):"95",  chr(150):"96", chr(151):"97", chr(152):"98", chr(153):"99",
          }

def bcd3(x,y,z,space=''):
    """
    e.g. bcd3('A','B','C',space=' ') -> '41 42 43' 
    """
    try:
        return BCD_lookUp[x]+space+BCD_lookUp[y]+space+BCD_lookUp[z]
    except KeyError, e:
        raise ValueError, bcd_msg + " Could not lookup '%s' ('%s')" % (
            str(e), hex(ord(e.args[0])))

def bcd2(x,y,space=''):
    """
    """
    try:
        return BCD_lookUp[x]+space+BCD_lookUp[y]
    except KeyError, e:
        raise ValueError, bcd_msg + " Could not lookup '%s' ('%s')" % (
            str(e), hex(ord(e.args[0])))
    
def bcd1(x):
    """
Single character bcd conversion.
    """
    try:
        return BCD_lookUp[x]
    except KeyError, e:
        raise ValueError, bcd_msg + " Could not lookup '%s' ('%s')" % (
            str(e), hex(ord(e.args[0])))
    
    
def bcd(values,space=''):
    """
    Convert input values (as a list) into a BCD string.
    Note: If number of values is 2 or 3 use bcd3 or bcd2 they work 2x faster.

Glen - 07/01/10 - Changed logic incase space is an empty string.
    """
    try:
        ret = ''
        for value in values[:-1]:
            ret += BCD_lookUp[value]+space
        return ret + BCD_lookUp[values[-1]]
    except KeyError, e:
        raise ValueError, bcd_msg + " Could not lookup '%s' ('%s')" % (
            str(e), hex(ord(e.args[0])))

# Glen - 05/01/10 - Requiring equivalents of standard library functions 
# converting network byte order to host byte order, and vice versa,
# htons, htonl, ntohs, ntohl were copied from:
# http://www.java2s.com/Tutorial/Python/0280__Buildin-Module/NetworkByteOrder.htm

def htons(num):
    """
Converts a short from network order (big-endian) to a string of length 2 in host order.

Equivalent of C OS library function of the same name.

Source: http://www.java2s.com/Tutorial/Python/0280__Buildin-Module/NetworkByteOrder.htm
    """
    return struct.pack('!H', num)

def htonl(num):
    """
Converts a long from network order (big-endian) to a string of length 4 in host order.    
    
Equivalent of C OS library function of the same name.

Source: http://www.java2s.com/Tutorial/Python/0280__Buildin-Module/NetworkByteOrder.htm
    """
    return struct.pack('!I', num)

def ntohs(data):
    """
Converts a string of length two from network order (big-endian) to a short in host order.
    
Equivalent of C OS library function of the same name.

Source: http://www.java2s.com/Tutorial/Python/0280__Buildin-Module/NetworkByteOrder.htm
    """
    return struct.unpack('!H', data)[0]

def ntohl(data):
    """
Converts a string of length four from network order (big-endian) to a long in host order.
    
Equivalent of C OS library function of the same name.

Source: http://www.java2s.com/Tutorial/Python/0280__Buildin-Module/NetworkByteOrder.htm
    """
    return struct.unpack('!I', data)[0]

a = 5
    
