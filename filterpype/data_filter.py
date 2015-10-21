# -*- coding: utf-8 -*-

# TO-DO: ReadLine filter -- forwards and backwards
# TO-DO: Check that ftype class attribute matches the obj made

import sys
import hashlib
import bz2
import os
import time
import re
import new
# configobj used by WriteConfigObjFile
import configobj

import filterpype.filter_utils as fut
import filterpype.data_fltr_base as dfb
import filterpype.embed as embed

re_python_key_sub = re.compile(r'\${\b([a-z][a-z0-9_]*)\b}')


class AttributeChangeDetection(dfb.DataFilter):
    """
Examines a list of attributes for change in value. Sets the
packet_change_flag attribute to True upon change of any of the attributes,
otherwise flag stays False. AttributeError raised if packet has not got
all attributes. Change of initial value.
    """
    ftype = "attribute_change_detection"
    keys = ["attributes",
            "packet_change_flag:attribute_changed",
            "compare_initial_value:True"]

    def filter_data(self, packet):
        for attribute in self.attributes:
            packet_value = getattr(packet, attribute)
            try:
                filter_value = getattr(self, attribute)
            except AttributeError:
                # Filter attribute not set, storing initial value for
                # change detection. Do not compare this value.
                setattr(self, attribute, packet_value)
                continue

            if filter_value != packet_value:
                setattr(packet, self.packet_change_flag, True)
                if not self.compare_initial_value:
                    setattr(self, attribute, packet_value)
                break
        else:
            # For loop completed without finding a changed attribute
            # value.
            setattr(packet, self.packet_change_flag, False)
        self.send_on(packet)

    
class InitialValueChangeDetection(dfb.DataFilter):
    """Takes in a dict of attribute_name:value and """
    ftype = "initial_value_change_detection"
    keys = ["attribute_map",
            "packet_change_flag:attribute_changed"]
    
    def filter_data(self, packet):
        for attribute_name, attribute_value in self.attribute_map.items():
            try:
                packet_value = getattr(packet, attribute_name)
            except AttributeError, err:
                setattr(packet, self.packet_change_flag, True)
                break
            if packet_value != attribute_value:
                setattr(packet, self.packet_change_flag, True)
                break
        else:
            setattr(packet, self.packet_change_flag, False)
        self.send_on(packet)


class AttributeExtractor(dfb.DataFilter):
    """ Extract attributes from text strings using a delimiter to determine the
    split between key (on the left) and value (on the right).
    Key has all punctuation removed and spaces replaced with underscores and is
    assigned to the packet dictionary.

    Sample input: '  someone's Gender : is maiL'
    Packet output: packet.someones_gender = 'is maiL'

    Beware: do not override reserved attributes within the packet (such
    as 'data')

    """
    ftype = 'attribute_extractor'
    keys = ['delimiter:none']

    def init_filter(self):
        # if delimiter is None, then whitespace is used

        delim_map = {'equ' : '=',   # equals
                     'col' : ':',   # colon
                     'spa' : ' ',   # space
                     'tab' : '\t'   # tab
                     }
        try:
            self.delim = delim_map[self.delimiter[:3]]
        except (KeyError, TypeError):
            # KeyError if delimiter not recognised in list
            # TypeError if delimiter is None
            # delimiter provided will be used
            self.delim = self.delimiter
        print "**7890** AttributeExtractor delmiter:", self.delim


    def filter_data(self, packet):
        data = packet.data
        key_value = [item.strip() for item in data.split(self.delim)]
        key = 0
        key_value[key] = fut.remove_punctuation(key_value[key])
        key_value[key] = key_value[key].replace(' ', '_').lower()
        # split the data given and populate a dictionary with key value pairs
        try:
            attributes_dict = dict([key_value])
        except ValueError:
            # probably too many values to split, only works on a single
            # (key, value) pair.
            # This might be caused by the incorrect delimiter being set
            # e.g. 'some key = some value' with no delimiter will become:
            #      ['some', 'key', '=', 'some', 'value'] which is invalid
            if len(key_value) == 1:
                # only one value provided (no delimiter found)
                return
            else:
                raise
        ### update the filter's dictionary with the extracted attribute
        ##self.__dict__.update(attributes_dict)
        # update the packet's dictionary with the extracted attribute
        packet.__dict__.update(attributes_dict)
        self.send_on(packet)


        ### split by line, split on = and make a dict.
        ##params = dict([line.split('=') for line in file_header_expected_start.splitlines()])
        ### expected output:
        #### {'DFDR': 'MQAR2', 'TAILNUM': 'OH-AFI', 'VERSION': 'v04044' ...}
        ### append dict to self
        ##self.__dict__.update(params)

class BranchUntilValue(dfb.DataFilter):
    ftype = 'branch_until_value'
    keys = ['value']
    
    def init_filter(self):
        self.__value_seen = False
        self.__stored_data = ''
    
    def filter_data(self, packet):
        if self.__value_seen:
            self.send_on(packet)
            return
        self.__stored_data += packet.data
        try:
            index_of_value = self.__stored_data.index(self.value)
        except ValueError:
            return
        self.__value_seen = True
        branch_data = self.__stored_data[:index_of_value]
        if branch_data:
            self.send_on(packet.clone(data=branch_data), 'branch')
        main_data = self.__stored_data[index_of_value:]
        if main_data:
            self.send_on(packet.clone(data=main_data), 'main')
        

class Batch(dfb.DataFilter):
    """Input is a series of strings of any length, with header removed.
    Split up data into blocks.

    There are two general cases to cope with:
    a) the input string is larger than the block size
    b) the input string is smaller.

    To avoid having two different approaches, we use an inputs list
    as a buffer:
    1) Repeatedly put the packet data into inputs until chars_in >= size
    2) Join inputs to be one string.
    3) Split string into blocks, leaving a remainder.
    4) Send on each block.
    5) Put remainder back as the only item in inputs.
    
    Wrong:
    An added feature is that we can set an initial_branch_size that sends the
    first N bytes off to a branch. This enables us to strip off junk at the
    beginning of a block of data, by sending it to a branch where it goes to
    waste. Alternatively, it can resynchronise frames of data, by pointing the
    branch and the main to the same filter following in the pipeline.

    ##We can set more than one batch size, using the size parameter for a list 
    """
    ftype = 'batch'
    keys = ['size', 'fork_dest:main']

    def _init_input(self, data=''):
        """Reset the inputs list to nothing, or whatever was left over from
        the previous batching operation.
        Create an empty dfb.DataPacket object initially for self._last_packet.
        """
        self.inputs = [data]
        self.input_char_count = len(data)
        self.block_index = 0
        
        
    def before_filter_data(self, packet):
        """Clone the incoming packet and store within self._last_packet for
        flush_buffer()."""
        self._last_packet = packet.clone()

    def filter_data(self, packet):
        """Split the data, allowing size and fork_dest to be changed each loop.
        We need to check batch size each loop, in case it has been changed
        to a silly value, e.g. 0, which will just carry on sending the same 
        data ad infinitum.
        """
        self.inputs.append(packet.data)
        self.input_char_count += packet.data_length
        if self.input_char_count < int(self.size):
            return  # Not enough input data to make up even one batch block

        all_inputs = ''.join(self.inputs)
        while True:
            if int(self.size) <= 0:
                msg = 'Bad batch size, = %d, should be >= 1'
                raise dfb.FilterAttributeError, msg % self.size
            block = all_inputs[self.block_index:self.block_index + self.size]
            if len(block) == self.size:
                self.block_index += self.size  # Point to next data to go
                # N.B. After sending this packet, size and dest may change
                ##if self.name == 'batch_before':
                    ##print
                # restricted block output as it fills debug with binary output!
                # ONLY enable during debugging, otherwise this is REALLY slow
                #msg = '**13420** %s (%d) is sending data block[:40] "%s" to %s'
                #fut.dbg_print(msg % (self.name, self.size, 
                                     #fut.data_to_hex_string(block[:40]), 
                                     #self.fork_dest), 8)
                self.send_on(packet.clone(data=block), self.fork_dest)
            else:  # Ran out of data -- remember remainder for next input
                self._init_input(block)
                break 

    def flush_buffer(self):
        remainder = ''.join(self.inputs)
        if remainder:  # Avoid sending a final empty data packet
            self.send_on(self._last_packet.clone(remainder), self.fork_dest)

    def init_filter(self):
        self._init_input()
        # self._last_packet is a copy of the last packet to enter the filter.
        # This is required to persist attributes when flush_buffer() sends on
        # the remaining batched data in a new packet.
        self._last_packet = dfb.DataPacket()

    def validate_params(self):
        """Zero batch size gives ValueError: 
               range() step argument must not be zero 
        """
        try:
            self.size + 0
            if self.size <= 0:
                raise dfb.FilterAttributeError, 'Bad batch size, = %d' % (
                    self.size)
        except TypeError:
            if self.size and \
               self.size != dfb.k_unset and \
               not dfb.re_caps_params_with_percent.match(self.size):
                msg = 'Non-integer batch size, = "%s"'
                raise dfb.FilterAttributeError, msg % self.size


class BranchClone(dfb.DataFilter):
    """Clones (duplicates) the packet, sending one copy to main, one to
    branch. BranchClone filter should be followed by a HiddenBranchRoute
    filter, i.e. "(" in the route.
    """
    ftype = 'branch_clone'

    def filter_data(self, packet):
        # N.B. Branch always goes first!
        self.send_on(packet.clone(), 'branch') 
        self.send_on(packet, 'main')


class BranchDynamic(dfb.DataFilter):
    """Sends along the main and/or branch depending on two variables within the
    embedded environment. If the variables have not been set, this filter will
    die loudly raising an AttributeError.
    """
    ftype = 'branch_dynamic'
    
    keys = ['main_variable:MAIN', 'branch_variable:BRANCH']
    
    def filter_data(self, packet):
        
        emb = embed.pype
        # Comparing directly against True because uninstantiated variables 
        # within the embedded environment evaluate as "<<$unset$>>.
        ##print "BranchDynamic: %s = %s, %s = %s" % (self.main_variable, getattr(emb, self.main_variable),
                                                   ##self.branch_variable, getattr(emb, self.branch_variable))
        if getattr(emb, self.main_variable) is True:
            self.send_on(packet)
        if getattr(emb, self.branch_variable) is True:
            self.send_on(packet, 'branch')


class BranchFirstPart(dfb.DataFilter):
    """Send the first part of the packet.data to the branch, and the rest to
    main. This differs from DistillHeader because the amount to send is read
    from the packet, and to keep things simple, must be >= packet data length.
    """
    ftype = 'branch_first_part'

    def filter_data(self, packet):
        if packet.branch_up_to > 0 and packet.data:
            self.send_on(packet.clone(packet.data[:packet.branch_up_to]), 
                         'branch')
            packet.data = packet.data[packet.branch_up_to:]
        self.send_on(packet, 'main')


class BranchIf(dfb.DataFilter):
    """Decide on branching, dependent of the name of an attribute
    'branch_key', found either in the filter or the packet. Optional key is
    'branch_on_packet', with default of True. If branch_on_packet is False,
    then use filter instead of packet. If the attribute is not present, a
    KeyError will be raised. BranchIf should be followed by HiddenBranchRoute
    filter, i.e. "(" in route.
    """
    ftype = 'branch_if'
    keys = ['branch_key', 'comparison:equals', 'compare_value:true',
            'branch_on_packet:true']

    def filter_data(self, packet):
        if self.branch_on_packet:
            lhs_value = getattr(packet, self.branch_key)
        else:
            lhs_value = getattr(self, self.branch_key)

        if self.comparison == 'equals':
            result = lhs_value == self.compare_value
        elif self.comparison == 'less_than':
            result = lhs_value < self.compare_value
        elif self.comparison == 'greater_than':
            result = lhs_value > self.compare_value
        elif self.comparison == 'not_equals':
            result = lhs_value != self.compare_value
        else:
            raise FilterLogicError, 'Unknown comparison "%s"' % (
                comparison)
        if result:
            self.send_on(packet, 'branch')
        else:
            self.send_on(packet, 'main')


class BranchOnceTriggered(dfb.DataFilter):
    """
Sends packet down the branch forever after the first case where watch_attribute 
does not equal watch_value.
    """
    ftype = "branch_once_triggered"
    keys = ["watch_attribute", "watch_value:true"]
    
    def init_filter(self):
        self._send_to_branch = False
    
    def filter_data(self, packet):
        if self._send_to_branch:
            self.send_on(packet, "branch")
            return
        
        if getattr(packet, self.watch_attribute) == self.watch_value:
            self._send_to_branch = True
            self.send_on(packet, "branch")
        else:
            self.send_on(packet, "main")


class BranchParam(dfb.DataFilter):
    """Send parameter results to the branch. Optionally send only some of
    the list items.

    ROBDOC : sorry, what does this do? Filter a list using slice / dice? CJ
    """
    ftype = 'branch_param'
    keys = ['param_name', 'start:0', 'stop_before:9999', 'step:1']


    def filter_data(self, packet):
        results = getattr(packet, self.param_name
                          )[self.start:self.stop_before:self.step]
        results_packet = dfb.DataPacket(results, param_name=self.param_name)
        self.send_on(results_packet, 'branch')
        self.send_on(packet)
    


class BranchRef(dfb.DataFilter):
    """Send the packet object to both branch and main. This is without cloning
    it, i.e. this is not a copy but a reference to the same object! Any
    changes made by the branch will affect the packet it refers to.
    BranchRef filter should be followed by a HiddenBranchRoute filter, i.e.
    "(" in the route.
    """
    ftype = 'branch_ref'

    def filter_data(self, packet):
        # N.B. Branch always goes first!
        self.send_on(packet, 'branch') 
        self.send_on(packet, 'main')


class BreakPoint(dfb.DataFilter):
    """ Debugging in a pipeline that has no convienently placed filters can
        be difficult so this is a filter purely for being able to insert a
        break point in
    """
    
    ftype = 'break_point'
    dynamic = True
    
    def filter_data(self, packet):
        place_break_point_here = None
        self.send_on(packet)
        
class BZipCompress(dfb.DataFilter):
    """Take the input stream and compress it using bzip2 compression object.
       Use level 9 for large files (this is the default).
    """
    ftype = 'bzip_compress'

    def filter_data(self, packet):
        packet.data = self.compressor.compress(packet.data)
        self.send_on(packet)

    def flush_buffer(self):
        """Flush compression buffer before closing"""
        self.send_on(dfb.DataPacket(self.compressor.flush()))

    def zero_inputs(self):
        self.compressor = bz2.BZ2Compressor()


class BZipDecompress(dfb.DataFilter):
    """Take the input stream and decompresses it using bzip2.
    """
    ftype = 'bzip_decompress'

    def filter_data(self, packet):
        decompr_data = self.decompressor.decompress(packet.data)
        self.send_on(packet.clone(data=decompr_data))

    def zero_inputs(self):
        self.decompressor = bz2.BZ2Decompressor()


class CalcSlope(dfb.DataFilter):
    """Calculate the rate of change of a parameter, over five consecutive
    values, given a list of packets, from which we can get

        [h0, h1, h2, h3, h4]

    We use the formula:
        mean_slope_for_h2 = (h4 - h0 + h3 - h1) / 6.0

    The packet arriving should contain references to the five packets we need
    to differentiate. They are still continuing in the main pipeline. If there
    are not precisely five packets, then pass on the grouping packet for
    other calculating methods.

    """
    ftype = 'calc_slope'
    keys = ['calc_source_name', 'calc_name_suffix:slope']

    def filter_data(self, grouping_packet):
        vals = [getattr(pkt, self.calc_source_name) 
                for pkt in grouping_packet.data]
        # If there are not precisely five values, we can't calculate the slope
        # according to this formula. Allow fewer numbers to pass, because this
        # may happen at the beginning and the end of the data.
        if len(vals) == 5:
            slope_calc = (vals[4] - vals[0] + vals[3] - vals[1]) / 6.0  
            setattr(grouping_packet.data[2], self.calc_param_name, slope_calc)
        elif len(vals) > 5:
            raise dfb.DataError, 'More than five values to calculate slope'
        self.send_on(grouping_packet)

    def init_filter(self):
        self.calc_param_name = '%s_%s' % (self.calc_source_name, 
                                          self.calc_name_suffix)


class Calculate(dfb.DataFilter):
    """ Simple calculator for two numbers
    """
    ftype = 'calculate'
    keys = ['lhs_value', 'operator:add', 'rhs_value', 'param_result']

    def filter_data(self, packet):
        if hasattr(packet, self.param_result):
            msg = 'Packet attribute "%s" already has values and can\'t be reset'
            raise dfb.FilterAttributeError, msg % self.param_result

        # This is a proof of concept idea.
        # This will hpoefully, look in the packet for parameter names matching
        # the lhs and rhs input name. If found then it will take the values from
        # the packet attributes named.
        try:
            self.lhs_value + ''
            if hasattr(packet, self.lhs_value):
                self.lhs_value = getattr(packet, self.lhs_value)
        except TypeError:
            pass

        try:
            self.rhs_value + ''
            if hasattr(packet, self.rhs_value):
                self.rhs_value = getattr(packet, self.rhs_value)
        except TypeError:
            pass
        # --- end proof of concept


        try:
            self.lhs_value + 1
            self.rhs_value + 1
        except TypeError:
            msg = 'One or more attributes "%s %s" are not a number'
            raise dfb.FilterAttributeError, msg % (
                self.lhs_value, self.rhs_value)

        setattr(packet, self.param_result, self._do_calc(packet.data))
        self.send_on(packet)

    def _do_calc(self, packet):
        if self.operator == 'add':
            result = self.lhs_value + self.rhs_value
        elif self.operator == 'subtract':
            result = self.lhs_value - self.rhs_value
        elif self.operator == 'multiply':
            result = self.lhs_value * self.rhs_value
        elif self.operator == 'divide':
            # Make sure the user is not trying to divide by zero
            try:
                result = float(self.lhs_value) / float(self.rhs_value)
            except ZeroDivisionError:
                raise dfb.FilterLogicError, 'Cannot divide by zero %s, %s' % (
                    str(self.lhs_value), str(self.rhs_value))
        return result


class CallbackOnAttribute(dfb.DataFilter):
    """ Watches packets for a specified watch attribute and calls the provided
    callback method with the attribute value as a parameter, 

    e.g. If watch_attr = 'holy' and no environ provided, the following callback
    will be made if a packet arrives with the 'holy' attribute with the 
    value 'grail'

    self.callback('found:holy', holy='grail')

    num_watch_pkts is the number of packets which can pass through the filter
    until it will stop watching for the attribute. If the attribute has
    not been found by this point, it will return a callback:

    self.callback('not_found:holy')

    allowed_inconsistencies:
    self.callback('inconsistency_value_exceeded:holy')
    
    If num_watch_pkts is None (default) it will watch forever and only return a
    not_found callback when closing the filter.

    count_to_confirm is the number of identical values of the watched attribute
    required to pass through the filter before it will return a callback.

    watch_for_change will make a callback only when the attribute changes it's
    value from the previous (including the first assignment of the value in
    the first packet).

    include_in_environ allows you to provide a list of additional packet
    attributes to include in the environ used in the callback. (watch_attr is
    always included where available)

    if the parameter is not found by the time the pipeline closes down, the 
    response is made "not_found:<watch_attr>"
    
    if the value of watch_attr is None, it is ignored (passed through).
    
    changes the refinery send() method's return value to 'found', 'not_found'
    or 'inconsistant'
    
    print_when_callback allows you to aid your debugging by printing to stdout
    when a callback is made
    """
    ftype = 'callback_on_attribute'
    keys = ['watch_attr', 'callback', 'environ:none', 'count_to_confirm:1', 
            'num_watch_pkts:none', 'allowed_inconsistencies:0',
            'watch_for_change:false', 'include_in_environ:[]',
            'close_when_found:false', 'print_when_callback:false']

    def _populate_environ(self, packet):
        # add required keys to the environment where they are available
        for attr_name in self.include_in_environ:
            try:
                self.environ[attr_name] = getattr(packet, attr_name)
                self.environ['pipeline'] = self.pipeline.name
            except AttributeError:
                # don't add it if it doesn't exist in the packet
                pass

    def filter_data(self, packet):
        """Used by open_message_bottle too - but as message bottles get sent
        on automatically, we don't want to send it if there is a message in
        the packet. (TO-DO discuss) <-- there should be a tidier way of doing
        this!
        
        TO-DO: Split the getattr and functionality within try except into
        seperate private function, then send_on can be handled outside of that
        function.
        """
        if self.callback is None:
            # allow None, but print error message`0
            print "'%s' filter cannot perform callback as it is set to None" % self.name
            return
        
        if self.attribute_found and self.watch_for_change is False:
            if not packet.message: self.send_on(packet)
            return

        if self.num_watch_pkts is not None:
            # only watch for num_watch_pkts
            self.pkt_count += 1
            if self.pkt_count > self.num_watch_pkts:
                # stop watching
                if not packet.message: self.send_on(packet)
                return
        try:
            value = getattr(packet, self.watch_attr)
            # count values found until confirm number is met
            # number of times we have seen the current value 
            if value is None:
                # we're not monitoring for None values
                if not packet.message: self.send_on(packet)
                return
            self.value_dict[value] = self.value_dict.get(value, 0) + 1
            ##self.value_dict[value] = current_value_count
            if self.watch_for_change is True:
                if value != self.prev_value:
                    # we've found a new value
                    self._populate_environ(packet)
                    #self.environ[self.watch_attr] = value
                    self.attribute_found = True
                    self.prev_value = value
                    self.callback('found:' + self.watch_attr, **self.environ)
                    if self.print_when_callback:
                        print "found '%s': %s" % (self.watch_attr, value)
                    if not packet.message: self.send_on(packet)
                    # If the pipeline does not need to do anything else, let it
                    # shutdown after the attribute is found
                    if self.close_when_found and self.pipeline:
                        self.refinery.return_value = 'found'
                        self.pipeline.shut_down()
                    return
                else:
                    # values are the same, we're not interested
                    if not packet.message: self.send_on(packet)
                    return


            if len(self.value_dict) - 1 > self.allowed_inconsistencies:
                if self.inconsistent_callback_made:
                    return
                # We have had too many inconsistent values
                self._populate_environ(packet)
                self.environ['values_found'] = self.value_dict.keys()
                self.callback('inconsistency_value_exceeded:' + self.watch_attr,
                              **self.environ)
                self.inconsistent_callback_made = True
                self.value_dict = {value:1}
                if self.close_when_found and self.pipeline:
                    self.refinery.return_value = 'inconsistant'
                    self.pipeline.shut_down()
                    return

            # if we have seen the current value for the number of times required
            # by count_to_confirm, we have found the attribute
            if self.value_dict[value] >= self.count_to_confirm:
                # we've found the attribute
                self.attribute_found = True
                ##self.environ[self.watch_attr] = value
                self._populate_environ(packet)
                self.callback('found:' + self.watch_attr, **self.environ)
                # If the pipeline does not need to do anything else, let it
                # shutdown after the attribute is found
                if self.close_when_found and self.pipeline:
                    self.pipeline.shut_down()
        except AttributeError:
            ### Moved below...
            ##if self.pkt_count == self.num_watch_pkts\
                ##and not self.attribute_found:
                ### we've not found the packet
                ##self.callback('not_found:' + self.watch_attr, **self.environ)
            # We need to set value to something, after an AttributeError,
            # to avoid "UnboundLocalError: local variable 'value' 
            #           referenced before assignment"
            value = None
            pass
        # We want to say that the attribute was not found regardless of whether
        # we get the above AttributeError on the final watched packet or not...
        # If self.num_watch_pkts has not been set, it will evaluate 
        # as False ( 0 == None )
        if self.pkt_count == self.num_watch_pkts\
           and not self.attribute_found:
            # we've not found the packet
            self._populate_environ(packet)
            self.callback('not_found:' + self.watch_attr, **self.environ)

        if not packet.message: self.send_on(packet)

    def init_filter(self):
        # include the watch attribute in the environment
        self.include_in_environ.append(self.watch_attr)
        # pipeline is not shutting down quickly enough after making
        # the inconsistent callback.
        self.inconsistent_callback_made = False
        self.attribute_found = False
        self.pkt_count = 0
        self.value_dict = {}
        self.prev_value = None
        # ensure environ is a dictionary if it hasn't been provided
        if self.environ is None:
            self.environ = {}
        try:
            self.environ.keys()
        except AttributeError:
            raise TypeError('Environ must be a dictionary\nFound: %s : %s' % (
                type(self.environ), self.environ ) )

    def open_message_bottle(self, msg_bottle):
        """
        This must do something very similar to the filter_data class, but
        not send_on the message bottle - as this is arranged for us in the 
        DataFilter base class.

        Work around for the above is to only send on in filter_data when
        there is a message attached to the packet.

        Currently it will open all messages from the msg_bottle. this may or 
        may not be a good idea, but it does allow for items to be clocked up
        on the "not" found count. <-- however, it is also worth noting that
        if the message destination wasn't set and it defaulted to this ftype,
        it may get more messages than intended.

        will count_to_confirm etc. etc. work? are they sharing resources with filter_data counts?

        """
        self.filter_data(msg_bottle)

    def close_filter(self):
        """ Make a not_found callback if the attribute was not found and
        num_watch_pkts is set to None (which watches forever) and we haven't
        made an inconsistent call
        """
        if not self.attribute_found and self.num_watch_pkts == None \
           and self.refinery.return_value != 'inconsistant':
            self.callback('not_found:' + self.watch_attr, **self.environ)
            self.refinery.return_value = 'not_found'


class CallbackOnMultipleAttributes(dfb.DataFilter):
    """Simplified version of data_filter's CallbackOnAttribute which will make
a callback based on multiple attributes. watch_attrs is comma separated, though
is parsed as a list by FilterPype. Will only make the callback once when all
attributes have been found."""
    ftype = 'callback_on_multiple_attributes'
    keys = ['watch_attrs', 'callback', 'environ']
    
    def init_filter(self):
        self.found_attrs = {}
        self.callback_made = False
    
    def _make_callback(self, found_attrs):
        self.environ.update(found_attrs)
        self.callback('found:%s' % '_and_'.join([attr for attr in self.watch_attrs if found_attrs.has_key(attr)]), **self.environ)
        self.callback_made = True
    
    def filter_data(self, packet):
        if self.callback_made:
            self.send_on(packet)
            return
        
        for attr_name in self.watch_attrs:
            if hasattr(packet, attr_name):
                self.found_attrs[attr_name] = getattr(packet, attr_name)
        
        if all([self.found_attrs.has_key(a) for a in self.watch_attrs]):
            self._make_callback(self.found_attrs)
        
        self.send_on(packet)
        
    def close_filter(self):
        if self.callback_made:
            return
        # May be partial match.
        if self.found_attrs:
            self._make_callback(self.found_attrs)
        else:
            self.callback('not_found:%s' % '_and_'.join(self.watch_attrs))


class CentrifugeOne(dfb.DataFilter):  # TO-DO
    """Extract the data from each packet into an extract dictionary. 
    A centrifuge map is a dictionary in the form

        key_attribute_name = tuple_with_extraction_parameters
        e.g.               = (word_no, high_bit_no, low_bit_no)
        superframe_number = (3, 8, 1)

    Note that all numbering systems from the analysts point of view
    are 1-based, so have to be converted to 0-based before use.

    """
    ftype = 'centrifuge_one'
    keys = ['centrifuge_map']

    def filter_data(self, packet):
        dest_filter = self.pipeline.getf(self.dest_tag_packet)
        dest_filter.tag = packet.tag
        self.send_on(packet)


class Combine(dfb.DataFilter):
    """Combine a list of fields or constants into one target field.
    Source field names will use the value of the field, which is prefixed
    either with 'f.' for filter attribute, or 'p.' for packet attribute.

        source_field_names = f.header_prefix, p.seq_num, XXXX

    produces

        ===+++ 27 XXXX

    If the source field name is not prefixed with f. or p., it will be 
    treated as a constant. Target field name always starts with f. or p.

    """
    ftype = 'combine'
    keys = ['source_field_names', 'target_field_name']

    def filter_data(self, packet):
        summary = []
        for source in self.source_field_names:
            if source.startswith('f.'):
                add_this = self.__dict__[source[2:]]
                try:
                    add_this + ''
                    summary.append(add_this)
                except TypeError:
                    summary.append(str(self.__dict__[source[2:]]))
            elif source.startswith('p.'):
                add_this = packet.__dict__[source[2:]]
                try:
                    add_this + ''
                    summary.append(add_this)
                except TypeError:
                    summary.append(str(packet.__dict__[source[2:]]))
            else:
                # Treat the field name as a literal string
                summary.append(source)
        summary_str = ''.join(summary)
        if self.target_field_name.startswith('f.'):
            self.__dict__[self.target_field_name[2:]] = summary_str
        elif self.target_field_name.startswith('p.'):
            packet.__dict__[self.target_field_name[2:]] = summary_str
        else:
            msg = 'Bad target field "%s". Must start ' + \
                'with \'f.\' or \'p.\''
            raise FilterAttributeError, msg % self.target_field_name
        self.send_on(packet)


class ConcatPath(dfb.DataFilter):
    """
    Concatinate path
    """
    ftype = 'concat_path'
    keys = ['input_path', 'end_part', 'variable_name']

    def filter_data(self, packet):
        emb = embed.pype
        
        new_path = self.input_path + self.end_part
        setattr(emb, self.variable_name, new_path)
        self.send_on(packet)


class ConvertBytesToInt(dfb.DataFilter):
    """ Convert a string of hex values (e.g. 'x01x02x03') into a integer
        representation of the given string.

        NOTE: Using exscape characters in rst is not allowed so the hex values
              below AND above would normally be escaped

        E.g. 'x00' --> 0
             or
             'x00x81' --> 129
    """

    ftype = 'convert_bytes_to_int'
    keys = ['param_names']

    def filter_data(self, packet):
        self.packet = packet
        try:
            self.param_names + []
        except TypeError, err:
            self._process_data(self.param_names)
        else:
            for param_name in self.param_names:
                self._process_data(param_name)

        self.send_on(self.packet)


    def _process_data(self, param_name):
        if not hasattr(self.packet, param_name):
            msg = 'Packet attribute "%s" is not defined'
            raise dfb.FilterAttributeError, msg % param_name
        value_to_convert = getattr(self.packet, param_name)
        converted_value = int('0x' + fut.data_to_hex_string(
            value_to_convert, None, ''), 16)
        setattr(self.packet, param_name, converted_value)


class ConvertFilenameToPath(dfb.DataFilter):
    """ Join a file path to a file name to give a full file name
    """
    ftype = 'convert_filename_to_path'
    keys = ['input_file_name:none', 'in_attr', 'out_attr']

    def filter_data(self, packet):
        if not self.input_file_name:
            self.input_file_name = '.'
        source_file_name = getattr(packet, 'source_file_name',
                                   self.input_file_name)
        if not hasattr(packet, self.in_attr):
            msg = 'Packet attribute "%s" is not defined'
            raise dfb.FilterAttributeError, msg % self.in_attr

        filename = getattr(packet, self.in_attr)
        full_path = os.path.join(
            os.path.dirname(source_file_name), filename)
        setattr(packet, self.out_attr, full_path)
        self.send_on(packet)


class CollectData(dfb.DataFilter):
    """Record data from each passing packet, until a maximum collection
    size is reached. Then send to the branch a packet with data of all the
    values in a list.
    """
    ftype = 'collect_data'
    keys = ['collection_size:5']

    def filter_data(self, packet): 
        self.data_collection.append(packet.data)
        if len(self.data_collection) >= self.collection_size:
            self.send_on(packet.clone(data=self.data_collection), 'branch')
            self.zero_inputs()
        self.send_on(packet)

    def zero_inputs(self):
        self.data_collection = []


class CountBytes(dfb.DataFilter):
    """Count the number of bytes passing a filter. Unlike SeqPacket and
    CountLoops, nothing is written to the packet, just to the filter.
    Count packets as well, but not in a custom field.
    """
    ftype = 'count_bytes'
    keys = ['count_bytes_field_name:counted_bytes']
    

    def filter_data(self, packet):  
        cbfn = self.count_bytes_field_name
        setattr(self, cbfn, getattr(self, cbfn) + packet.data_length)
        self.counted_packets += 1
        if self.counted_packets <= 50 or self.counted_packets % 10 == 0:
            msg = '**14840** Received another %d bytes (total %d bytes ' + \
                  'in %d packets)'
            fut.dbg_print(msg % (packet.data_length,
                getattr(self, cbfn), self.counted_packets), 3)
        self.send_on(packet)

    def zero_inputs(self):
        setattr(self, self.count_bytes_field_name, 0)
        self.counted_packets = 0


class CountLoops(dfb.DataFilter):
    """Give each packet a number that starts at 1 and increments for each
    pass. This is used for counting loops

    Contrast this with CountPackets that records in the filter the number of
    packets going past.

    Also contrast this with SeqPacket that gives the packet an ID number.
    The next number is taken from the filter, and the packet number is not
    overwritten if it already exists.
    """

    ftype = 'count_loops'
    keys = ['count_loops_field_name:loop_num']

    def filter_data(self, packet):
        clfn = self.count_loops_field_name
        try:
            packet.__dict__[clfn] = packet.__dict__[clfn] + 1
        except KeyError:
            packet.__dict__[clfn] = 1
        self.send_on(packet)


class CountPackets(dfb.DataFilter):
    """Count the number of packets passing a filter. Unlike SeqPacket and
    CountLoops, nothing is written to the packet, just to the filter.
    """    
    ftype = 'count_packets'
    keys = ['count_packets_field_name:counted_packets',
            'include_message_bottles:false']

    def filter_data(self, packet): 
        cpfn = self.count_packets_field_name
        self.__dict__[cpfn] = self.__dict__[cpfn] + 1
        fut.dbg_print('**14830** packets = %d' % getattr(self, cpfn), 3)
        self.send_on(packet)

    def zero_inputs(self):
        self.__dict__[self.count_packets_field_name] = 0


class DataLength(dfb.DataFilter):
    """Calculates the length of data that has passed through the filter.

    When closing the filter, it sends a message bottle to the msg_destin
    which defaults to the ftype of callback_on_attribute.

    not_data must be a single chr value data_length(0 to 256)

    single_use means that the message bottle it sends will be used by the first
    msg_destin found (i.e. defaults means the first callback_on_attribute it 
    comes across)
    """
    ftype = 'data_length'
    keys = ['not_data:0x00', 'msg_destin:callback_on_attribute',
            'single_use:true']

    def filter_data(self, packet):
        # strip off the stuff that isn't classed as data
        # TO-DO: if this is slow, try to improve with a comparison of a packet 
        # lengths worth of no_data:
        ##assert len(not_data) == 1
        ##if not_data * packet.data_length == packet.data:
            ##self.send_on(packet)
            ##return
        # requires packet.data to be a string
        data_only = packet.data.rstrip(self.not_data)
        if data_only:
            self.data_last_seen = self.bytes_seen + len(data_only)
        self.bytes_seen += packet.data_length
        self.send_on(packet)

    def init_filter(self):
        self.bytes_seen = 0
        self.data_last_seen = 0
        # ensure not_data is in string format
        self.not_data = chr(self.not_data)

    def close_filter(self):
        # put the parameter into a new last packet
        #self.send_on(dfb.DataPacket(total_data_length=self.data_last_seen))
        self.send_on(dfb.MessageBottle(
            destination=self.msg_destin,
            message='total_data_length',  
            # not used in callback_on_attribute
            total_data_length=self.data_last_seen,
            bytes_seen=self.bytes_seen))


        """

        As lots of processes rely on having data available, lets change this
        to a messagebottle which is opened by CallbackOnAttribute


        # if we shutdown a pipeline early - using p.shut_down() - does it run
        close_filter first or not? i.e. will we get an incorrect file size
        returned to the callback method if we're shutdown early?
        """


class DataBuffer(dfb.DataFilter):
    ftype = 'data_buffer'
    keys = []
    
    def __init__(self, *args, **kwargs):
        '''
        '''
        super(DataBuffer, self).__init__(*args, **kwargs)
        self._chunks = []
    
    @property
    def _buffer_size(self):
        '''
        Get the total size of the data in the buffer.
        
        :returns: Total size of buffer data.
        :rtype: int
        '''
        return sum(len(d) for d in self._chunks)
    
    def _chunk_index(self, data_index):
        '''
        Translates a single data index into both self._chunks index and within chunk index.
        
        :type data_index: int
        :rtype: int or None, int or None
        '''
        if data_index <= 0:
            return 0, 0
        
        chunk_size = 0
        for chunk_index, chunk in enumerate(self._chunks):
            chunk_size += len(chunk)
            if data_index == chunk_size:
                return chunk_index + 1, 0
            elif chunk_size > data_index:
                return chunk_index, data_index - (chunk_size - len(chunk))
        else:
            return None, None
    
    def _add_data(self, data):
        self._chunks.append(data)
    
    def _get_data(self, data_index=None):
        '''
        Get data from the start of the buffer, concatenating if required.
        
        :type data_index: int or None
        :rtype: str
        '''
        if data_index is None:
            return ''.join(self._chunks)
        
        chunk_index, split_index = self._chunk_index(data_index)
        
        if chunk_index is None:
            return ''.join(self._chunks)
        
        matching_chunks = self._chunks[:chunk_index]
        
        if not split_index:
            return ''.join(matching_chunks)
        
        split_chunk = self._chunks[chunk_index]
        return ''.join(matching_chunks + [split_chunk[:split_index]])
    
    def _truncate_data(self, data_index):
        '''
        Truncate data from the start of the buffer.
        
        :type data_index: int
        :rtype: None
        '''
        chunk_index, split_index = self._chunk_index(data_index)
        
        if chunk_index is None:
            self._chunks = []
            return
        
        if not split_index:
            self._chunks = self._chunks[chunk_index:]
            return
        
        split_chunk = self._chunks[chunk_index]
        self._chunks = [split_chunk[split_index:]] + self._chunks[chunk_index + 1:]
    


class DedupeData(dfb.DataFilter):
    """Takes a list of data as an input, and outputs the set of different
    values. This can be used to ensure that a parameter read multiple times
    has the same value.
    """
    ftype = 'dedupe_data'
    keys = ['start:0']  # Allow for discarding first few values in list

    def filter_data(self, packet):  
        try:
            # Record value before deduping, if the param_name is there
            setattr(packet, packet.param_name, packet.data)
        except AttributeError:
            pass
        packet.data = list(set(packet.data[self.start:]))
        self.send_on(packet)


##class DistillHeader(dfb.DataFilterDynamic):
# We need to be able to have filters that are static, unless particularly
# required to be dynamic in one instance.
class DistillHeader(dfb.DataFilter):
    """Strip header off, and send header_size bytes to the branch. If
    distill_mode is "once" then the header will be removed only once, from the
    first packet, while if distill_mode is "repeated", it will removed from
    each packet that is received.
    """
    ftype = 'distill_header'
    # header_size in bytes; distill_mode 'once' or 'repeated'
    keys = ['header_size', 'distill_mode:repeated', 'keep_header_key:none'] 

    def filter_data(self, packet):
        if self.headers_done:
            # Just send data stream straight through
            self.send_on(packet, 'main')
            return
        # We need enough inputs to make up a header
        self.inputs.append(packet.data)
        self.input_char_count += packet.data_length

        if self.distill_mode == 'once':
            if self.input_char_count < self.header_size:
                return

        # We should now have enough chars for header output
        all_inputs = ''.join(self.inputs)
        self.inputs = []
        self.input_char_count = 0
        fut.dbg_print("**2342** Distill header size: %s %s" % (
            self.header_size, type(self.header_size)))
        header = all_inputs[:self.header_size]
        self.remainder = all_inputs[self.header_size:]
        self.send_on(packet.clone(data=header), 'branch')
        if self.distill_mode == 'once':
            # Only one header to be sent
            self.headers_done = True
        if self.remainder:
            packet_out = packet.clone(data=self.remainder)
            if 'keep_header_key' in self.filter_attrs:
                setattr(packet_out, self.keep_header_key, header)
            self.send_on(packet_out, 'main')
            self.remainder = None

    def zero_inputs(self):
        self.inputs = []
        self.input_char_count = 0
        self.headers_done = False
        self.remainder = None


class EmbedPython(dfb.DataFilter):
    """EmbedPython TO-DO
    """
    # Note change from naming convention to allow filter names to start
    # just with "python_" or "py_"
    ftype = 'py'  
    ##keys = ['arg1:none', 'arg2:none'] ROBDOC : It would be nice to be able 
    ##to pass in any key you like to the python environment

    def subst_keys(self, line):
        """Replace keys from the enclosing pipeline where they are of the
        format "${fred}"

        ROBDOC: Will only work on strings / primitive data types (not objects)
        """
        #    re_python_key_sub = re.compile(r'\${\b([a-z][a-z0-9_]*)\b}')
        keys = re_python_key_sub.findall(line)
        line_out = line
        for key in keys:
            value = getattr(self.pipeline, key)
            ##self.value_list[key] = value
            try:
                value + ''
                value = "'%s'" % value
            except TypeError:
                pass
            line_out = line_out.replace('${%s}' % key, '%s' % value)
        return line_out

    def _import_code(self, code, module_name='singleton_pype', 
                     add_to_sys_modules=False):
        if not self.module_loc._emb_module:
            self.module_loc._emb_module = new.module(module_name)
            embed.modules[module_name] = self.module_loc._emb_module
            if add_to_sys_modules:
                sys.modules[module_name] = self.module_loc._emb_module
 
        self.python_module = self.module_loc._emb_module  # TO-DO
        exec code in self.module_loc._emb_module.__dict__   

        # ===============================================================
        # We need to talk about what is happening here and what you are
        # trying to do.
        return # <<<< _import_code  TO-DO
        # ROBDOC: Please do not remove functionality like this without
        # talking to us first or making it extremely obvious what
        # has occurred as other systems will rely on these features.
        # ===============================================================
        
        # Add all refinery keys (optional and required) to embedded module
        # stored as CAPITAL versions of the input lowercase keys.
        refinery = self._get_refinery()
        for key in refinery._keys:
            # add key from refinery to KEY in embedded python module
            setattr(self.module_loc._emb_module, key.upper(),
                    refinery.__dict__[key])

    def _remake_python_code(self):
        # Replace comments and remove leading "|" if it is a Python line
        if True and False:
            for (key, value) in sorted(self.__dict__.iteritems()):
                if key.startswith('line_') and not value.startswith('| '):
                    print '**12410** %s=%s' % (
                        key[6:], value.replace('$comment$', '#'
                                               ).replace('$comma$', ','))
        python_lines = [
            line.replace('$comment$', '#').replace('$comma$', ',') for line in 
            (fut.config_obj_comma_fix(value[1:] + '') for (key, value) in 
             sorted(self.__dict__.iteritems()) if key.startswith('line_'))
        ]
        python_lines2 = [self.subst_keys(line) for line in python_lines]
        self.python_code = '\n'.join(python_lines2)
        if python_lines2:
            self.function_name = python_lines2[0][2:]  # e.g. "# fn_name"
            # Populate a list of code lines for debugging output
            self.module_loc._python_code_lines.extend(python_lines2)
        else:
            self.function_name = None

    def _validate(self):
        """For this filter only, we want to turn off validation by overriding
        the base class _validate() function, because we've no idea what
        variables will be set in the code to be evaluated.
        """
        pass

    def filter_data(self, packet):
        if self.function_name:
            getattr(self.python_module, self.function_name)(packet=packet)
        if packet.fork_dest:
            fork_dest = packet.fork_dest
        else:
            fork_dest = 'main'
        self.send_on(packet, fork_dest)

    def init_filter(self):
        self._remake_python_code()
        # Don't pass the module_loc.name, so that all modules use the 
        # default name: "pype" or "singleton_pype"    ##"one_pype_module"
        self._import_code(self.python_code)


class FormatParam(dfb.DataFilter):
    """Format results received in a list, to be passed on as a string.
    param_name may be an attribute of the results packet.
    """
    ftype = 'format_param'
    keys = ['format']


    def filter_data(self, packet):
        results = packet.data
        packet.data = self.join_char.join(self.results_gen(results))
        self.send_on(packet)

    def _hex_gen(self, results):
        return (('0x%X' % res) for res in results)

    def _int_gen(self, results):
        return (('%d' % res) for res in results)

    def _str_gen(self, results):
        return ((chr(res or ord('?'))) for res in results)

    def init_filter(self):
        if self.format == 'hex':
            self.join_char = ' '
            self.results_gen = self._hex_gen
        elif self.format == 'int':
            self.join_char = ' '
            self.results_gen = self._int_gen
        if self.format == 'str':
            self.join_char = ''
            self.results_gen = self._str_gen


class GetBytes(dfb.DataFilter):
    """ Get the raw data value for the target byte range. 

        Mandatory keys are:
        start_byte (int)
        bytes_to_get (int)
        param_name (string) Uppercase please

        NOTE: All counting is base 0 for developers.
        Data extracted is sent to branch;

    """

    ftype = 'get_bytes'
    keys = ['start_byte', 'bytes_to_get', 'param_name']

    def filter_data(self, packet):

        if hasattr(packet, self.param_name):
            msg = 'Packet attribute "%s" already has values and can\'t be reset'
            raise dfb.FilterAttributeError, msg % self.param_name
        setattr(packet, self.param_name, self._get_data_value(packet.data))
        self.send_on(packet)

    def _get_data_value(self, data):
        data_value = data[self.start_byte:(
            self.start_byte + self.bytes_to_get)]
        return data_value


class HashSHA256(dfb.DataFilter):
    """Takes the input stream and computes a hash using the sha-256 algorithm.
    """  
    ftype = 'hash_sha256'

    def filter_data(self, packet):
        self.hasher.update(packet.data)
        self.send_on(packet)

    def zero_inputs(self):   # TO-DO versus dynamic init
        self.hasher = hashlib.sha256()


class HeaderAsAttribute(dfb.DataFilter):
    """In cases where the header is required for further processing later in
    pipeline, this filter assigns the header_attribute to the packet, while the
    packet's data will no longer contain the header.
    
    The send_on_if_only_header key defines whether this filter should send_on
    packets if there is not enough data to split into both header and remaining
    data.
    """
    ftype = "header_as_attribute"
    keys = ["header_size",
            "header_attribute:header_data",
            "send_on_if_only_header:false"]
    
    def filter_data(self, packet):
        # If we are not sending on packets if there is not enough data for both
        # the header_attribute and new data.
        if not self.send_on_if_only_header and packet.data_length <= self.header_size:
            # Do not send_on.
            return
        # Set the self.header_attribute of the packet with self.header_size
        # amount of data.
        setattr(packet,
                self.header_attribute,
                packet.data[:self.header_size])
        # Set the packet's data to be the remaining data after the header.
        packet.data = packet.data[self.header_size:]
        self.send_on(packet)


class Join(dfb.DataFilter):
    """Store the data items that are strings, until receiving something where
    the data is not a string, typically None. Then join the strings together, 
    using space as the default join string.
    """
    ftype = 'join'
    keys = ['join_str:space']  

    def filter_data(self, packet):
        try:
            packet.data + ''  # Test for a string
            self.parts.append(packet.data)
        except TypeError:
            # Not a string, so send on joined string
            packet_out = dfb.DataPacket(self.join_str.join(self.parts))
            self.zero_inputs()
            self.send_on(packet_out)   

    def flush_buffer(self):
        if self.parts:
            # Send on any unjoined data before closing
            final_packet = dfb.DataPacket(self.join_str.join(self.parts))
            self.send_on(final_packet)

    def zero_inputs(self):
        self.parts = []


class PassNonZero(dfb.DataFilter):
    """Check that the first n bytes of data for being non-zero (i.e. not 0x00
    or 0xFF). If the first n bytes are 00/FF and all the same, don't pass on
    the data. 

    If the length of the data packet is less than check_byte_count, then the
    packet should pass, because the check has failed, even if the data is
    00/FF.
    """

    ftype = 'pass_non_zero'
    keys = ['check_byte_count:32', "attribute:data"]

    def filter_data(self, packet):
        self.check00 = self.check_byte_count * chr(0x00)
        self.checkFF = self.check_byte_count * chr(0xFF)
        data = getattr(packet, self.attribute)
        if not data.startswith(self.check00) and \
           not data.startswith(self.checkFF):
            self.send_on(packet)

    #def init_filter(self):
        ###self.check00 = unicode(self.check_byte_count * chr(0x00), 'ISO-8859-1')
        ###self.checkFF = unicode(self.check_byte_count * chr(0xFF), 'ISO-8859-1')
        #self.check00 = self.check_byte_count * chr(0x00)
        #self.checkFF = self.check_byte_count * chr(0xFF)

class PassThrough(dfb.DataFilter):
    """A pass through filter just forwards all packets to the next filter. 
       There are various uses for a null node, such as being able to redirect 
       pipeline flow while the pipeline is active. Alternatively, it may be 
       used for simulating multiway branching, with a syntax built around 
       binary branching.
    """
    ftype = 'pass_through'

    def filter_data(self, packet):
        self.send_on(packet)


class Peek(dfb.DataFilter):
    """Look ahead some bytes into the next data packet. Record the bytes found
    in the packet, if bytes are found, or an end of file marker <<<TO-DO<<< if
    the data has finished.
    """
    ftype = 'peek'
    keys = ['peek_ahead']

    def close_filter(self):
        # Send on the last packet, if reached end of file.
        self.packet_in.peek = ''
        self.send_on(self.packet_in)

    def filter_data(self, packet):
        self.packet_in = packet
        peeked_bytes = self.packet_in.data[:self.peek_ahead]
        if self.prev_packet:
            self.prev_packet.peek = peeked_bytes
            self.send_on(self.prev_packet)
        self.prev_packet = self.packet_in

    def zero_inputs(self):
        self.prev_packet = None
        self.packet_in = None


class PrintParam(dfb.DataFilter):
    """Format results received in a list, to be passed on as a string.
    param_name may be an attribute of the results packet.
    """
    ftype = 'print_param'
    keys = ['label:empty']

    def filter_data(self, packet):
        try:
            print_str = fut.printable(packet.data + '')
            print_str = '%s' % packet.data
        except TypeError:
            print_str = '%s' % packet.data
        print '%s: %s.%s = %s' % (self.label, self.pipeline_name, 
                                  packet.param_name, print_str)
        self.send_on(packet)

    def init_filter(self):
        try:
            self.pipeline_name = self.pipeline.name
        except AttributeError:
            self.pipeline_name = 'no_pipeline'
            

class ReadBatch(dfb.DataFilter):
    """Chop file up into string blocks to pass inside packets into pipeline.

    We need a file object to read from. This can be provided directly or
    indirectly, with either the open file object or the file name being
    sent to ReadBatch.

    This can also be done by setting the source_file_name as a fixed
    parameter for the filter, but this stops more than one file being read and
    doesn't fit so well with the idea of data filters.

    The file object passed in (or opened) signalled for closing in three ways:
    1) The file has been consumed by reading, so the next read() returns a
    block of zero length.
    2) The refinery is shutting down (checked on each read() loop). Whether or
    not the reading is finished, the file should be closed.

    NOTE: This should not be used in the middle of a pipeline as it creates
          a brand new packet and does NOT pass on the packet that it was
          originally supplied with. In other words, use this at the start of
          a pipeline or in an external wrapper pipeline.
          
    :param max_reads: Number of batches to read.
    :type  max_reads: int
    """  
    ftype = 'read_batch'
    keys = ['batch_size:0x2000', 'max_reads:0', 
            'initial_skip:0', 'read_every:1', 'binary_mode:true', 
            'source_file_name:none', 
            'file_size:none',
            'print_progress:false']

    def _ensure_file_closed(self):
        """Check that the file has been closed, or close it.
        """
        if hasattr(self, 'file1'):
            if self.file1 and not self.file1.closed:
                self.file1.close()
        else:
            self.file1 = None

    def _get_file_obj(self, full_file_name_or_obj):
        # TO-DO: Create exception if full_file_name_or_obj is not a string or
        # is not a file object
        if not full_file_name_or_obj:
            # Sent file name overrides fixed file name, but if not present, 
            # look for optional_key source_file_name.
            if not self.source_file_name:
                raise dfb.DataError, 'File object or name is missing'
            else:
                self.full_file_name = self.source_file_name                
        else:
            try:
                full_file_name_or_obj + ''  # Test for a string
                self.full_file_name = full_file_name_or_obj
            except TypeError:
                # Not a string -- must already be a file object
                self.full_file_name = full_file_name_or_obj.name
                return full_file_name_or_obj     
        if self.binary_mode:
            mode = 'rb'
        else:
            mode = 'r'
        return open(self.full_file_name, mode)


    def _calculate_progress(self, bytes_read='unknown'):
        """ Stores the current progress (percent of data read) within the
            packet attribute 'packet.read_percent'.
            
        If no bytes_read provided or file_size has been set to -1 then -1 is
        returned.
        """
        # TO-DO  I think this extends the ReadBatch filter too much. We could
        # handle file_size in a separate filter, or at least a descendant.
        if bytes_read == 'unknown' or self.file_size == -1:
            return -1
        
        if self.file_size is None:
            try:
                self.file_size = os.path.getsize(self.file1.name)
                if self.file_size == 0L:
                    # getsize on raw usb can return 0L on Unix
                    raise OSError
            except OSError:
                # some special file objects can have a file_size attribute
                try:
                    self.file_size = self.file1.file_size
                except AttributeError:
                    # cannot get file size for raw usb devices
                    raise dfb.FilterAttributeError(\
                        "file_size could not be obtained. Required as a filter "+
                        "attribute. If not, os.path.getsize('%s') is queried." \
                        % self.file1.name)
        #try:
        progress = int(bytes_read * 100.0 / self.file_size)
        #except ZeroDivisionError, err:
            #print "**4322** Progress cannot be estimated as file_size is '%s'. %s" % (self.file_size, err)
        # TO-DO: Take this out:
        if self.print_progress:
            try:
                if progress != self.prev_progress:
                    self.prev_progress = progress
                    print "%02d" % progress
            except AttributeError:
                self.prev_progress = 0
        
        return progress


    ##def _report_progress(self, bytes_read='unknown'):
        ##"""Use the callback, if one is available, to report how much of the
        ##file has been read. This can be passed in explicitly
        ##"""
        ##if not self.environ:
            ##return
####        print '**8055** environ =', self.environ    
####           hasattr(self, 'file_size') and \

        ##if hasattr(self, 'results_callback') and \
            ##hasattr(self, 'environ') and self.environ != '${environ}':

            ####file_size = self.environ['file_size']
            ##if bytes_read == 'unknown':
                ##percent = -1
####                self.environ['read_percent'] = -1
            ##else:
                ##if self.file_size is None:
                    ### try to get the file size from the environ
                    ##try:
                        ##self.file_size = self.environ['file_size']
                    ##except KeyError:
                        ### environ doesn't have the file size in it
                        ### try to get it from the file object
                        ##try:
                            ##self.file_size = os.path.getsize(self.file1.name)
                        ##except OSError:
                            ### cannot get file size for raw usb devices
                            ##raise dfb.FilterAttributeError(\
##"file_size could not be obtained. Required in 'environ' or as a "+
##"filter attribute. If both fail, os.path.getsize('%s') is queried." \
##% self.file1.name)

                ##percent = int(bytes_read * 100.0 / self.file_size)
            ##if percent != self.percent_read:
                ##self.environ['bytes_read'] = bytes_read
                ##self.environ['read_percent'] = percent
                ####print '**8060** %d of %d bytes_read, = %d%% progress' % (
                    ####bytes_read, file_size, percent)

####            msg = '**8040** read_progress results_callback, environ = "%s"'
####            print msg % self.environ             
                ##self.results_callback('read_progress', **self.environ)
                ##self.percent_read = percent

    def close_filter(self):
##        if self.refinery:
##        self.refinery.shutting_down = True
        self.shut_down()
        self._ensure_file_closed()

    def filter_data(self, packet):
        # Having this (yield) here makes this conform to filter.   TO-DO         
        # This is now used to take in the file name, to enable processing
        # a list of files without recreating filter each file.

        if self.shutting_down:  # TO-DO
            return
        full_file_name_or_obj = packet.data
        self._ensure_file_closed()
        self.file1 = self._get_file_obj(full_file_name_or_obj)
        self.char_count = 0

        self.file_counter += 1
        # Skip initial unread data
        for block_no in xrange(self.initial_skip):
            block = self.file1.read(self.batch_size)
            if len(block) == 0:
                break
        read_count = 0
        while not self.shutting_down:  # TO-DO
            if self.refinery.shutting_down:
                self.shutting_down = True
                # Use "continue" rather than "break", to get to "else"
                continue  
            block = self.file1.read(self.batch_size)

            if len(block) > 0:
                self.char_count += len(block)
                percent = self._calculate_progress(self.char_count)
                packet = dfb.DataPacket(
                    block, source_file_name=self.full_file_name,
                    read_percent=percent,
                    read_bytes=self.char_count
                )
                self.send_on(packet)
                ##self._report_progress(self.char_count)
            else:
                # File has run out, so we loop, closing first, to avoid
                # leaving while waiting for a (yield).
                self._ensure_file_closed()
                break
            read_count += 1
            if self.max_reads and read_count >= self.max_reads:
                # Enough of the file has been read, so close and move
                # on to the next file.
                self._ensure_file_closed()
                break
        else:
            # We haven't broken out of the loop, so close normally.
            self._ensure_file_closed()

    def zero_inputs(self):  # TO-DO change to open_filter?
        self.file_counter = 0
        self._ensure_file_closed()
## Once a pipeline has been shut down, it can't be reopened.
##        self.shutting_down = False  # TO-DO  self.refinery.shutting_down = False
        ##self.percent_read = None
        ##self.file_size = None

    def init_filter(self):
        pass


class ReadBytes(dfb.DataFilter):
    """ Simple ReadFile filter to read files using bytes

        Notes about keys:

        source_file_name - the source file to read from
        start_byte - the starting byte. Must be positive integer.
        size - number of bytes to read.
               zero : read nothing
               positive int : read this number of bytes
               negative int : read all of file (covention is to use -1)
        block_size - size in bytes to read at a time.
        whence - where to seek from:
                 0 - Start of file
                 1 - End of file

    """
    ftype = 'read_bytes'
    keys = ['source_file_name', 'start_byte:0', 'size:-1', 'block_size:2048',
            'whence:0', 'ack:false']

    def filter_data(self, packet):
        packet.FINAL = False
        file_desc = open(self.source_file_name, 'rb')
        total_file_size = os.path.getsize(self.source_file_name)
        counter = 0

        # Seek to start position in the file
        if self.whence == 1:
            seek_whence = 2
        else:
            seek_whence = 0
        # Setting the start byte to the end if the user has specified a starting
        # point beyond the end of the file is not useful in itself but will
        # help to avoid errors being raised.
        if self.start_byte > total_file_size:
            self.start_byte = total_file_size
        try:
            file_desc.seek(self.start_byte, seek_whence)
        except:
            # Seeking is unsupported, read from current location.
            pass

        # Set up size to read
        if self.size < 0:
            # Read from the starting position of the file to the end
            # It's a negative so turn it to positive!
            size = total_file_size - file_desc.tell()
        elif self.size > (total_file_size - file_desc.tell()):
            size = total_file_size - self.start_byte
        else:
            # Read the size asked for
            size = self.size
        
        # This is used in the calculation of the read progress.
        self.file_size = size

        if self.block_size > size:
            self.block_size = size

        # Read the file in chunks
        to_read = size
        self.previous_progress = -1
        while to_read > 0:
        #while counter < size:
            # Clone the packet so we don't just send on a reference to the
            # one passed in
            pkt_snd = packet.clone()
            progress = self._calculate_progress(bytes_read=counter)
            if progress > self.previous_progress:
                pkt_snd.read_percent = progress
            self.previous_progress = progress
            # Check to see if the amount left to read is smaller than the next
            # block_size, otherwise it may read too much!
            #if self.block_size > size - counter:
                #self.block_size = size - counter
            if self.block_size > to_read:
                self.block_size = to_read
            pkt_snd.data = file_desc.read(self.block_size)
            counter += self.block_size
            # Send on new packet
            self.send_on(pkt_snd)
            to_read -= self.block_size
        file_desc.close()
        # Send a 'FINAL' packet for things that may want to watch and see
        # when a read has been finished.
        # Only send once so the pipeline stops recieving packets properly
        if self.final and self.ack:
            ##self.ack = False
            self.final = False
            pkt_fin = packet.clone()
            pkt_fin.data = ''
            pkt_fin.FINAL = True
            self.send_on(pkt_fin)
            
            
    def _calculate_progress(self, bytes_read='unknown'):
        """ Stores the current progress (percent of data read) within the
            packet attribute 'packet.read_percent'.
            
        If no bytes_read provided or file_size has been set to -1 then -1 is
        returned.
        """
        # TO-DO  I think this extends the ReadBatch filter too much. We could
        # handle file_size in a separate filter, or at least a descendant.
        if bytes_read == 'unknown' or self.file_size == -1:
            return -1
        
        if self.file_size is None:
            try:
                self.file_size = os.path.getsize(self.file1.name)
                if self.file_size == 0L:
                    # getsize on raw usb can return 0L on Unix
                    raise OSError
            except OSError:
                # some special file objects can have a file_size attribute
                try:
                    self.file_size = self.file1.file_size
                except AttributeError:
                    # cannot get file size for raw usb devices
                    raise dfb.FilterAttributeError(
                        "file_size could not be obtained. Required as a filter "
                        "attribute. If not, os.path.getsize('%s') is queried."
                        % self.file1.name)
        progress = int(float(bytes_read) / float(self.file_size) * 100.0)
        
        return progress

    def init_filter(self):
        self.final = True

class ReadLines(dfb.DataFilter):
    """Read lines of a text file, in normal or reversed order.
       For a first implementation, this requires the whole file being in 
       memory, but this could be optimised.
    """
    ftype = 'read_lines'
    keys = ['direction:forwards', 'initial_skip:0', 
            'read_every:1', 'max_lines:0']

    def close_filter(self):
##        if self.refinery:
        self.refinery.shutting_down = True
        self.file1.close()

    def filter_data(self, packet):
        self.source_file_name = (yield)
        self.char_count = 0
        self.file1 = open(self.source_file_name, 'rb')
        self.file_counter += 1
        # Skip initial unread data
        for line_no in xrange(self.initial_skip):
            line = self.file1.readline()
            if not line:  # Not even '\n' for blank line
                return
        line_count = 0
        while True:
##            if self.refinery and self.refinery.shutting_down:
            if self.refinery.shutting_down:
                break
            line = self.file1.readline()
            if line:
                packet = DataPacket(
                    line.rstrip(), 
                    source_file_name=self.source_file_name)
                self.send_on(packet)
                self.char_count += len(line)
            else:
                # End of data, file all read, so close and move to next
                self.file1.close()
                break
            line_count += 1
            if self.max_lines and line_count >= self.line_reads:
                break
##        if self.refinery and self.refinery.shutting_down:
        if self.refinery.shutting_down:
            return  # ??? TO-DO check this for ReadLines

    def zero_inputs(self):
        self.file_counter = 0


class RenameFile(dfb.DataFilter):
    """Rename file, with from/to names passed in as packet data.
    """
    ftype = 'rename_file'

    def filter_data(self, packet):
        try:
            from_name = packet.from_filename
            to_name = packet.to_filename
            if from_name == to_name:
                raise dfb.DataError, 'Source and Destination filenames match'
            if os.path.exists(to_name):
                self.log_results.append(
                    'Destination file %s overwritten' % to_name)
            try:
                os.rename(from_name, to_name)        
                self.log_results.append(
                    'Success: %s renamed to %s' % (from_name, to_name))
            except OSError:
                self.log_results.append(
                    'From-file not found: %s' % from_name)
        except ValueError:
            self.log_results.append(
                'Only one file name given: %s' % packet.data)
        packet.log_results = self.log_results 
        self.send_on(packet)

        # TO-DO Rename many files at once?

    def zero_inputs(self):
        self.log_results = []


class SwapTwoBytes(dfb.DataFilter):
    """ Reverse a string (in packet.data) that is of at least 2 characters long.
        The result will be stored back into packet.data.
    """
    ftype = 'swap_two_bytes'

    def filter_data(self, packet):
        hanging_char = None
        try:
            packet.data + ''
        except TypeError:
            raise TypeError, 'Cannot swap on a non-string'

        # Check to see if packet.data is divisible by two.
        if (packet.data_length % 2) != 0:
            print "Found uneven data in packet. Cropping"
            hanging_char = packet.data[-1]
            packet.data = packet.data[:-1]
        packet.data = ''.join(
            (str_byte[1] + str_byte[0]) for str_byte in (
                packet.data[count:count + 2] for count in xrange(
                    0,packet.data_length,2))
        )
        # If we took a character off of the end (due to the string not
        # being even) put it back on (??? should it be put back on?)
        if hanging_char:
            packet.data += hanging_char
        self.send_on(packet)


class ReverseString(dfb.DataFilter):
    """ Reverse a string (in packet.data) that is of at least 2 characters long.
        The result will be stored back into packet.data.
    """
    ftype = 'reverse_string'

    def filter_data(self, packet):
        try:
            packet.data + ''
        except TypeError:
            raise TypeError, 'Cannot swap on a non-string'

        packet.data = packet.data[::-1]
        self.send_on(packet)


class R111esetBranch(dfb.DataFilter):
    """Reset to zero an attribute in the next filter.
    """
    ftype = 'r111eset_branch'
    keys = ['branch_filter_field_name']

    def filter_data(self, packet):
        # Reset the target, which is the branch from HiddenBranchRoute
        self.next_filter.branch_filter.__dict__[
            self.branch_filter_field_name] = 0
        self.send_on(packet)

    def validate_params(self):
        """Check that we have reset followed by a branch, in order to have
        somewhere to send the reset to.
        """
##        if self.next_filter.__class__ != HiddenBranchRoute:
        if not isinstance(self.next_filter, dfb.HiddenBranchRoute):
            msg = 'Reset must be followed by a branch, not "%s"'
            raise dfb.FilterAttributeError, msg % (
                self.next_filter.__class__.__name__)


class SendMessage(dfb.DataFilter):
    """Send a message in a bottle to a downline filter. The message bottle
    will pass along the pipeline until it gets to a filter where the name
    matches. Then the parameter will be set to the new value.
    """
    ftype = 'send_message'
##    keys = ['target_filter_name', 'message', 'values:[]', 'single_use:true']  # TO-DO
    keys = ['message', 'values:[]']  # TO-DO

    def filter_data(self, packet):
        msg_bottle = dfb.MessageBottle(self.message, value=self.values)
        # N.B. Branch always goes first!
        self.send_on(msg_bottle, 'branch') 
        self.send_on(packet, 'main')


class Reset(dfb.DataFilter):
    """Send a message bottle to a downstream filter, to reset one of the
    parameters. The message bottle will pass along the pipeline until it gets
    to a filter where the name matches. Then the parameter will be set to the
    new value.

    The 'value' key can be either a proper value (such as 3 or 'hello') or
    the name of a packet attribute where the value will be retrieved. The 
    packet attribute takes precedence over the Filter key.
    """
    ftype = 'reset'
    keys = ['target_filter_name', 'param_name', 'value:none'] 

    def filter_data(self, packet):
        message = 'reset'

        # This is a proof of concept idea.
        # This will look in the packet for parameter names matching
        # the value. If found then it will take the value from
        # the packet attribute named.
        #try:
            #self.value + ''
            #if hasattr(packet, self.value):
                #self.value = getattr(packet, self.value)
        #except TypeError:
            ## Don't do anything (it's not failing silently as it's
            ## not really failing)
            #pass
        # --- end proof of concept

        # If there is no value given, look for an attribute param_name of the
        # data packet.
        if self.value is None:
            new_value = getattr(packet, self.param_name)
        else:
            try:
                self.value + ''
                if hasattr(packet, self.value):
                    self.value = getattr(packet, self.value)
            except TypeError:
                # Don't do anything (it's not failing silently as it's
                # not really failing)
                pass
            new_value = self.value

        msg_bottle = dfb.MessageBottle(self.target_filter_name, message,
                                       param_name=self.param_name,
                                       new_value=new_value)
        self.send_on(msg_bottle) 
        self.send_on(packet)   


class SeqPacket(dfb.DataFilter):
    """Give each data packet a sequential number (e.g. as an ID), starting
    from 0 or whatever reset_counter_to is set to. To allow for looping, the
    seq_packet_field_name will not be overwritten. If you need to add another
    numberer, use a different field. 

    Message bottle packets don't have to be handled, because they are not sent
    to filter_data().
    """  
    ftype = 'seq_packet'
    keys = ['seq_packet_field_name:seq_num', 'field_width:6']

    def filter_data(self, packet):  
        ##print '**10360** packet in to SeqPacket', packet
        ##if packet.message: 
            ##setattr(packet, self.seq_packet_field_name, -1)
            ##if packet.message == 'reset':
                ##try:
                    ##self.reset_counter(packet.values[0])
                ##except IndexError:
                    ##self.reset_counter()
                ##if packet.single_use:
                    ### It's been used, so don't send it on
                    ##return
        ##else:  # This is a data packet

        spfn = self.seq_packet_field_name
        # Packets are initialised with seq_num = -1
        if not hasattr(packet, spfn) or getattr(packet, spfn) < 0:
            fut.copy_attr(self, packet, spfn)
            self.__dict__[spfn] += 1

        # The packet is sent on (a) if it's a normal data packet
        #                       (b) if message isn't the expected one
        #                       (c) if it is to be used more than once
        self.send_on(packet)

    def init_filter(self):
        self.zero_inputs()

    def reset_counter(self, reset_to=0):
        self.__dict__[self.seq_packet_field_name] = reset_to

    def zero_inputs(self):
        self.reset_counter()


class Sink(dfb.DataFilter):
    """Store the output of the previous filter in a results list. Check the
    latest addition to the list with results[-1].

    Set max_results to limit the number of results stored in the list. If
    there are more than max_results, the oldest gets popped off the top of the
    list. If max_results is 0, then there is no limit, and all results are
    stored. The default limit is 20.

    Set the sink's capture_msgs=True in order to capture MessageBottles in
    addition to DataPackets.
    """
    ftype = 'sink'
    keys = ['max_results:30', 'capture_msgs:false']

    def _get_all_data(self):
        """Return a list of the data from the packets in results. If you want
        a continuous stream with no inter-packet markers, use
        ''.join(sink.all_data) in the calling function.
        """
        return [packet.data for packet in self.results]
    all_data = property(_get_all_data, doc='List of sink packet data')


    def _save_data(self, packet):
        self.results.append(packet)
        if self.max_results and len(self.results) > self.max_results:
            self.results.pop(0)

    def filter_data(self, packet):
        self._save_data(packet)
        self.send_on(packet)

    def init_filter(self):
        self.zero_inputs()

    def open_message_bottle(self, packet):
        # do nothing with the message
        #pass
        # Doing nothing here results in no message bottles being captured
        if self.capture_msgs:
            self._save_data(packet)

    def send_on(self, packet, fork_dest='main'): # TO-DO discuss
        if packet.message and self.capture_msgs and fork_dest is 'main':
            self._save_data(packet)
        dfb.DataFilter.send_on(self, packet, fork_dest)

    def zero_inputs(self):
        self.results = []


class Sleep(dfb.DataFilter):
    """ Simply sleeps for the specified time and sends on incoming packets.
    Intended for debugging purposes, watching printed output to understand
    the flow of a pipeline."""
    ftype = 'sleep'
    keys = ['time:1']
    
    def filter_data(self, packet):
        time.sleep(self.time)
        self.send_on(packet)


class SplitWords(dfb.DataFilter):
    """Split the data into chunks, looking for some character string to split
    on. Uses white space as the default.       
    """
    ftype = 'split_words'
    keys = ['split_on_str:None']

    def filter_data(self, packet):
        words = packet.data.split(self.split_on_str)
        for word in words:
            # Creating a new DataPacket instead of calling
            # packet.clone because it is possible that the data will be an
            # empty string. If clone is called with data as an empty string,
            # the previous packet's data will be cloned.
            self.send_on(dfb.DataPacket(data=word))


class SplitLines(dfb.DataFilter):
    """Split the data provided into lines.
    Only sends on lines which have data within them. It will include any
    whitespace on the line.
    """
    ftype = 'split_lines'
    keys = [] ##'split_on_str:None'

    def filter_data(self, packet):
        lines = packet.data.splitlines()
        for d, line in enumerate(lines):
            # only send on lines which have data
            # otherwise, clone data will assign the original packet's data
            if line.strip():
                #print "line %d: %s" % (d, line)
                self.send_on(packet.clone(data=line))


class TagPacket(dfb.DataFilter):
    """Apply a tag to each packet, from a tag_field_name. 

    This tag value is updated by a send_tag filter setting the tag property.??
    """
    ftype = 'tag_packet'                       # TO-DO  Tag~packet test needed
    keys = ['tag_field_name', 'tag_field_value']
##    keys = ['tag_field_names']

    ##def _get_tag(self):
####        return self.__dict__[self.tag_field_name]
        ##return getattr(self, self.tag_field_name)
    ##def _set_tag(self, value):
####        self.__dict__[self.tag_field_name] = value
        ##setattr(self, self.tag_field_name, value)
    ##tag = property(_get_tag, _set_tag, doc='Tag the tag_packet filter')    

    def filter_data(self, packet):
##        fut.copy_attr(self, packet, self.tag_field_name)
##        for field_name in self.tag_field_names:
        setattr(packet, self.tag_field_name, self.tag_field_value)
        self.send_on(packet)

    def zero_inputs(self):
        self.tag = ''


class TankFeed(dfb.DataFilter):
    """Take a (yield)ed packet and send it to a tank_queue, but not through
       the (yield), to avoid ValueError: "generator already executing"
       ROBDOC: This does not explain the main purpose of this filter.
    """
    ftype = 'tank_feed'

    def filter_data(self, packet):
        self.destination_tank.push(packet)

    def zero_inputs(self):
        """To avoid the locking up of the coroutine links by circular calls,
        we push packets on to a tank queue instead of sending them. But the
        destination is taken from the same pipeline structure.
        """
        if self.next_filter:
            # We can never use next_filter, particular for close(), or we get
            # a "generator already executing" ValueError. Therefore disable it.
            # Remember the next_filter before disabling it, in case zero_inputs
            # is called more than once.
            self._next_filter = self.next_filter
            self.next_filter = None
        else:
            raise FilterRoutingError, 'tank_feed must have a next_filter'
        if self._next_filter.ftype == 'tank_queue':
            self.destination_tank = self._next_filter
        else:
            raise FilterRoutingError, 'tank_feed must be followed by tank_queue'


class TankQueue(dfb.DataFilter):
    """Store the input packets in a priority queue, waiting until tap_open
    before sending on the packets.

    This description is in bits, and reads like it: pretty incomprfwehensbleuhg



    This decoupling is needed to allow coroutines to loop.

    All packets should have been numbered by a previous filter, to ensure
    that the earlier packets are processed first, in particular, that
    looping packets are processed before new ones.
    If the packets haven't been numbered before, they are given sequence
    number zero 

    <<<<<<<<<<<<<<<<<<< TankQueue <<<<<<<<<<<<<TO-DO<<<<<<<<<<<

    If the factorial hasn’t recursed down to 1, it branches to tank_feed, to
    calculate one less factorial. tank_feed put the new values back into the
    tank_queue, by pushing directly on to the tank_queue’s priority queue.
    The tank_queue gives the packets a sequential number to use in the
    priority queue, to ensure that all the recursive calculations on one
    packet are finished before the next packet is processed.

    The packet coming into the tank_queue by the normal (yield) is pushed on
    to the queue. Then a while-True loop takes all the packets out of the
    queue for processing, which means that it completes the entire recursion
    before going back for the next (yield).

    Fill the tank with up to tank_size packets. When next packet arrives, the
    first one in is sent on.

    When tank_size is changed, either the excess packets are sent on, or the
    front end is filled out with None.

    ##The normal send_now() behaviour is to queue all the packets until the
    ##current filter_data() function has been completed. This doesn't work for
    ##recursive use of the tank, because the packets must keep recursing round.
    ##Therefore we have a send_now key which can be set to True when needed.
    """        
    ftype = 'tank_queue'
    keys = ['tank_size:0', 'priority_field_name:seq_num']

    def __str__(self):
        return '%s (%s): size = %s, len(queue) = %s, spare = %s' % (
            self.name, hex(id(self)), self.tank_size, 
            len(self._priority_queue.queue), self.spare_capacity)

    def _get_all_data(self):
        """Return the concatenated data from the packets in the tank's
        priority queue. The packet is the third item in the queue tuple.
        """
        return [pkt.data for pkt in self.sorted_packets]
    all_data = property(_get_all_data, 
                        doc='Tank packet data, sorted and concatenated')

    def _get_sorted_packets(self):
        """Return the sorted packets from the priority queue. This can't be
        done just by looking at the list, because this is managed in heap
        order by the heapq module.
        """
        return [queue_tuple[2]
                for queue_tuple in self._priority_queue.sorted_items()
                if queue_tuple[2]]  # <<< Skip over None packets? TO-DO discuss
    sorted_packets = property(_get_sorted_packets,
                              doc='All data in tank packet, sorted ' + \
                              'in priority order')

    def _get_spare_capacity(self):
        """Return the number of packets/Nones that could be held in the tank
        queue before it goes over its size limit.
        """
        ##try:
            ##if self._tank_size < 0:
                ##return sys.maxint
            ##return self._tank_size - self._priority_queue.queue_size()
        ##except AttributeError:
            ##return sys.maxint
        if self._tank_size < 0:
            return sys.maxint
        try:
            return self._tank_size - self._priority_queue.queue_size()
        except AttributeError:  # _priority_queue not yet made
            return 0
        except TypeError: # the _tank_size refers to a variable that has not been initialised
            return 0
    spare_capacity = property(_get_spare_capacity,
                              doc='Count of packets needed to match tank_size')   
    
    
    @property
    def tank_size(self):
        return self._get_tank_size()
    
    @tank_size.setter
    def tank_size(self, value):
        self._set_tank_size(value)
    
    def _get_tank_size(self):
        try:
            return self._tank_size
        except AttributeError:
            return -2  # No packets leave, like -1
        
    def _set_tank_size(self, new_size):
        self._tank_size = new_size
        while self.spare_capacity < 0:
            # Send on excess packets, because tank_size has been reduced
            packet_out = self.pop()
            if packet_out:
                self.send_on(packet_out)
        # If self._tank_size < 0, spare_capacity is infinite (sys.maxint). No
        # more packets to be sent on. Can't do infinite padding with None.
        if self.spare_capacity < sys.maxint:      
            while self.spare_capacity > 0:
                self.push(None)  # Pad front with None
    tank_size = property(_get_tank_size, _set_tank_size,
                         doc='Adjust the tank size to change the number ' + \
                         'of packets held.')    

    def _search_tank(self):
        """
        Abstract method for implementation specific searching
        """
        pass

    def filter_data(self, packet):
        self.push(packet)
        # Restore target size by sending on the oldest packet
        while self.spare_capacity < 0:
            packet_out = self.pop()
            if packet_out:
                ##print '**12040** packet popped: %s' % packet_out.data
                self.send_on(packet_out)
        # search the tank if any new data has been added
        self._search_tank()

        # We're now ready to do any calculation, so tell the branch
        # <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<TankQueue<<<<<<<<<<<<<TO-DO<<<<<<<<<<<<<<<<<<<
        # How to send a message??
        ##msg_bottle = MessageBottle('calc_slope', 
                                    ##packets=self._priority_queue.queue)
        ##self.send_on(msg_bottle, 'branch')

    def flush_buffer(self):
        # Force sending on of any outstanding packets but setting size to 0 
        self.tank_size = 0

    def init_filter(self):
        self._priority_queue = dfb.PriorityQueue()
        self.packets_held = 0
        try:
            self._tank_size + 0
            hold_tank_size = self._tank_size
        except AttributeError:
            self._tank_size = -1  # Default is to have the queue unlimited size
            # tank_size will have been set in the kwargs. This needs to be read and
            # removed so that the property works as it should.
            try:
                hold_tank_size = self.__dict__['tank_size']
                #del(self.__dict__['tank_size'])
            except KeyError:
                try:
                    hold_tank_size = self._defaults['tank_size']
                except KeyError:
                    raise FilterAttributeError, 'tank_size is not set'
        if 'tank_size' in self.__dict__:
            del(self.__dict__['tank_size'])
        # Allow the tank_size property to pad tank with None, if tank_size > 0
        self.tank_size = hold_tank_size

    def pop(self):
        try:
            packet = self._priority_queue.pop()
            # Check that the packet isn't just a None spacer
            if packet:
                self.packets_held -= 1
            return packet
        except IndexError:  # No more packets in the queue
            return None
        except AttributeError:  # No priority queue yet
            return None

    def push(self, packet):
        """Each packet into the priority queue should be numbered, but if not
        numbered, we need to set priority to 0. In this case, the priority
        ordering will be on the time.time() set at time of push. Or should not
        being numbered raise an exception??   TO-DO

        PriorityQueue now gives a sequential number, rather than 0, so this
        is the default sorting mechanism.

        Packets are pushed with a given priority, whereas None is pushed with
        a special negative priority, to ensure it comes at the front.
        """
        if packet:
            priority = packet.__dict__.get(self.priority_field_name, None)
            self._priority_queue.push(packet, priority)
            self.packets_held += 1
        else:
            self._priority_queue.push_none()

    def zero_inputs(self):
        self._priority_queue.clear()


class TankBranch(TankQueue):
    """TankQueue that sends references to its packets held to the branch every
    time a packet is received. This enables the branch to process a sliding
    window, wihtout duplicating any data.
    """
    ftype = 'tank_branch'

    def before_filter_data(self, packet):
        pass

    def after_filter_data(self, packet):
        # Send to the branch a list of current packets queued in the tank
        self.send_on(dfb.DataPacket(self.sorted_packets), 'branch')

    def before_send_on(self, packet, fork_dest):
        """Allow proper processing of data being flushed down main.  Avoid
        catching the packet lists, which are normally sent down the branch.
        """
        if fork_dest == 'main' and self.refinery.shutting_down:
            self.send_on(dfb.DataPacket(self.sorted_packets), 'branch')


class Transmit(dfb.DataFilter):   # TO-DO  Test needed
    """Reset to zero an attribute in the next filter, to a value dependent on
    the current packet.
    """
    ftype = 'transmit'
    keys = ['target_filter_field_name', 'source_packet_field_name:0']

    def filter_data(self, packet):
        if self.next_filter:
            # Get the field value, or use the name as a constant
            spfn = self.source_packet_field_name
            reset_value = packet.__dict__.get(spfn, spfn)
            self.next_filter.__dict__[self.target_filter_field_name
                                      ] = reset_value
        self.send_on(packet)


class UseDataToTag(dfb.DataFilter):    # TO-DO  Test needed
    """Send tag property of incoming packet data to a tag_packet filter, by
    setting its <tag_field_name> attribute.
    """
    keys = ['dest_tag_packet']

    def filter_data(self, packet):
        dest_filter = self.pipeline.getf(self.dest_tag_packet)
        dest_filter.tag = packet.tag
        self.send_on(packet)


class Waste(dfb.DataFilter):
    """A waste filter just throws away all the packets it sees. This is used
    when combining results from branches and the main stream is not wanted.
    """ 
    ftype = 'waste'

    def filter_data(self, packet):
        pass


class Wrap(dfb.DataFilter):
    """Wrap packet data with a prefix and/or suffix. This can be used for
    inserting periodic strings (e.g. creating a regular file header within a
    stream of data) or padding missing data.
    """
    ftype = 'wrap'
    # wrap_mode 'once' or 'repeated'
    keys = ['data_prefix:empty', 'data_suffix:empty', 'wrap_mode:repeated'] 

    def filter_data(self, packet):
        # Without unicode() we get error 
        # 'ascii' codec can't decode byte 0xff in position 0
        # because data has been converted to unicode on reading.
        ##packet.data = ''.join([unicode(self.data_prefix, 'ISO-8859-1'), 
                                ##packet.data, 
                                ##unicode(self.data_suffix, 'ISO-8859-1')])
        packet.data = ''.join([self.data_prefix, packet.data, self.data_suffix])
        self.send_on(packet)


class SetAttributesToData(dfb.DataFilter):
    """ Creates delimited data from attribute lists.

    Changes a list of attributes (columns) and joins them into a list of
    rows. Each row is joint together, delimited by the seperator (default ','
    comma) . All the rows are then joint with the end of line 'eol' seperator
    and put into the packet.data.

    Where write_field_headers is True, attribute names are used for field
    headers at the start of the data.

    It will accept attribute lists of different lengths. When a list runs out
    of entries, it is padded with ' ' (space char) values at the end.

    output_format will apply a formatting to each and every value.
    str : applies string representation of value (default)
    int : applies integer base 16 to value (requires int / str of an int)
    hex : applies hexidecimal to value (requires integers)
    bin : applies binary to value (requires integers)
    oct : applies octal to value (requires integers)

    method_name is the name of a method to call on an object if the attribute
    list contains objects rather than literal values. Method name shall not
    require any arguments. If it does then it'll fail as it's supposed to be
    for simple getter style methods, not complicated things.



    * TO-DO: Replace str with a safe_string conversion so that ascii chars such
    as "delete" etc are not written to file!
    """

    ftype = 'set_attributes_to_data'
    keys = ['attribute_list:[]', 'write_field_headers:True', 
            'separator:,', 'eol:ret', 'line_numbers:False',
            'output_format:str', 'method_name:none','object_attr:none',
            'default_value:']

    def _set_up_headers(self):
        # Allow the first line of the file to have the attribute names as
        # field headers
        if not self.headers_written and self.write_field_headers:
            self.headers_written = True
            if self.line_numbers:
                new_attr_list = ['line']
                new_attr_list.extend(self.attribute_list)
                ##rows = [new_attr_list]
                rows = new_attr_list
            else:
                rows = self.attribute_list
                ##rows = [self.attribute_list]
        else:
            rows = []
        return rows

    def _check_values_in_lists(self, packet):
        prev_length = None
        for attribute in self.attribute_list:
            try:
                attr_val = getattr(packet, attribute)
                # If the user has provided a method name then we're dealing
                # with an object and need to go get the values via the method
                #if self.method_name:
                if self.object_attr:
                    #method = getattr(attr_val, self.method_name)
                    #value = method(packet.data)
                    value = getattr(attr_val, self.object_attr)
                else:
                    # Otherwise, treat it like a literal value
                    value = attr_val                    
            except AttributeError:
                raise AttributeError, "There is no such attribute:" + attribute
            try:
                value.append('')
                value.pop()
            except AttributeError:
                # attribute_list is not a list so make it one
                value = [value]
                #if self.method_name:
                if self.object_attr:
                    #setattr(attr_val, self.method_name, value)
                    setattr(attr_val, object_attr, value)
                else:
                    setattr(packet,attribute,value)

            # I see not why this filter cares about writing nor that the attributes
            # it has been told to deal with should be the same length.
            # - a tired CJ Sunday at 3minutes past midnight
            ##if prev_length is None:
                ##prev_length = len(value)
            ##if prev_length != len(value):
                ##msg = 'This filter requires all attributes for ' +\
                    ##'writing to have an equal number of items.'
                ##raise dfb.DataError, msg
                ##print "**3213** Attribute list has %s items which is different the previous of %s items." % (len(value), prev_length)
            ##prev_length = len(value)
            # store the length of the longest attribute values
            self.attribute_lengths.append(len(value))
            ##if len(value) > self.max_attr_length:
                ##self.max_attr_length = len(value)

        return packet, prev_length

    def _convert(self, value):
        if value is None:
            return self.default_value
        try:
            return self.convert(value)
        except TypeError:
            # could not convert, use string representation
            return str(value)

    ##def _lambda_replacement(self, *row):
        ##return [str(elem) or self.default_value for elem in row]

    def _transposed(self, lists):
        # http://code.activestate.com/recipes/410687/

        # Notes :
        # self._convert(elem) (with try / except) takes 56 CPU seconds
        # self.convert (with str operation only) takes 17 CPU seconds
        if not lists: return []
        return map(lambda *row: [self._convert(elem) or self.default_value for elem in row], *lists)
        ##return map(lambda row: [self._convert(elem) or defval for elem in row], lists)
        ##return map(self._lambda_replacement, *lists)

    def filter_data(self, packet):
        """        
        Purpose is to transpose lists of attribute lists into CSV data.
        Doing this by creating new lists of the lists is rather slow (lots of
        list generation with .append etc).

# http://code.activestate.com/recipes/410687/
#def transposed(lists):
        #if not lists: return []
        #return map(lambda *row: list(row), *lists)

def transposed2(lists, defval=0):
        if not lists: return []
        return map(lambda *row: [elem or defval for elem in row], *lists)

        """

        try:
            self.attribute_list.append('')
            self.attribute_list.pop()
        except AttributeError:
            # attribute_list is not a list so make it one
            self.attribute_list = [self.attribute_list]
        if len(self.attribute_list) == 1:
            self.separator = ''

        if self.attribute_list:
            header_row = self._set_up_headers()

            (packet, attr_length) = self._check_values_in_lists(packet)
            attr_val = [getattr(packet, attr) for attr in self.attribute_list]
            #if self.method_name:
            if self.object_attr:
                #methods = [getattr(param_obj, 
                #                self.method_name) for param_obj in attr_val]
                #cols = [method(packet.data) for method in methods]
                cols = [getattr(val, self.object_attr) for val in attr_val]
            else:
                cols = attr_val

            if self.line_numbers:
                cols.insert(0, xrange(1, len(cols[0])+1 ) )
                ##row_list.append('%d' % (line_num + 1))  ## was %02d
            rows = self._transposed(cols)
            rows.insert(0, header_row)

            lots_of_lists_way = '''
            ##for line_num in xrange(attr_length):
            ##for line_num in xrange(self.max_attr_length):
            for line_num in xrange(max(self.attribute_lengths)):
                # this is very good code, but every column must have an entry in each row
                ##row_list = [str(col[line_num]) for col in cols]
                # this code will pad columns which are shorter than others with None values

                row_list = []
                if self.line_numbers:
                    row_list.append('%d' % (line_num + 1))  ## was %02d
                for col in cols:
                    try:
                    ##if len(col) > line_num:
                    ##if self.attribute_lengths[line_num] > line_num:
                        # there is data for this line in this column
                        try:
                            row_list.append( self.convert( col[line_num] ) )
                        except TypeError:
                            # could not convert, use string representation
                            row_list.append( str( col[line_num] ) )
                    ##else:
                    except IndexError:
                        # append a space char for no data
                        row_list.append('')
                # add the new line (row) to the rows list
                rows.append(row_list)
                '''

            joined_rows = [self.separator.join(row) for row in rows]
            prepend = self.eol #+ '====,' * 951 + self.eol  # TEMP: REMOVE THIS after debugging!!!!
            # If this is the first packet, we do not want to prepend the data 
            # with an end of line character
            if self.first_packet:
                prepend = ''
                self.first_packet = False
            packet.data = prepend + self.eol.join(joined_rows)

        self.send_on(packet)

    def init_filter(self):
        self.attribute_lengths = []
        self.first_packet = True
        self.count = 0
        self.headers_written = False
        self.max_attr_length = 0
        #try:
            #self.attribute_list.append('')
            #self.attribute_list.pop()
        #except AttributeError:
            ## attribute_list is not a list so make it one
            #self.attribute_list = [self.attribute_list]
        #if len(self.attribute_list) == 1:
            #self.separator = ''
        if self.eol == 'ret':
            self.eol = os.linesep
        self.convert = str # currently the default
        if self.output_format.startswith('str'):
            self.convert = str
        elif self.output_format.startswith('int'):
            self.convert = int
        elif self.output_format.startswith('hex'):
            self.convert = hex
        elif self.output_format.startswith('bin'):
            self.convert = bin
        elif self.output_format.startswith('oct'):
            self.convert = oct
        else:
            raise dfb.FilterAttributeError(
                'unrecognised output format "%s"' % self.output_format)


class WriteConfigObjFile(dfb.DataFilter):
    """Creates a ConfigObj object and adds new sections to it from incoming
packet's data. Only accepts packet.data as a dictionary in the following format:

{ config_obj_section_name (str) : config_obj_section (dict)* }
    """
    ftype = "write_config_obj_file"
    keys = ["dest_file_name",
            "dest_file_suffix",
            "write_config:True"]
    
    def init_filter(self):
        self._config_obj = configobj.ConfigObj()
        
    def before_filter_data(self, packet):
        # Raise an exception if packet.data is not in the correct format.
        try:
            packet.data.items()
        except AttributeError:
            raise AttributeError, "Incoming packet.data needs to be a \
dictionary for %s. packet.data evaluated as: %s." %  (self.__class__.__name__,
                                                      packet.data)
        # Ensure each value in the dict is also a dict for configobj.
        try:
            for value in packet.data.values():
                value.items()
        except AttributeError:
            raise AttributeError, "All values of incoming packet.data need \
#to be dictionaries for %s" % self.__class__.__name__
    
    def filter_data(self, packet):
        # Add every key value pair as a new section in config obj.
        for key, value in packet.data.items():
            self._config_obj[key] = value
        self.send_on(packet)
    
    def flush_buffer(self):
        """When the pipeline is shutting down, write out self._config_obj if
        write_config is True."""
        if self.write_config:
            out_filename = self.dest_file_name + '.' + self.dest_file_suffix
            with open(out_filename, 'wb') as out_file_obj:
                self._config_obj.write(out_file_obj)


class WriteFile(dfb.DataFilter):
    """Write data from all packets to an external file.

    Write the data to the file, opening the file if necessary first.
    File opening is left to this point, to allow the changing of the
    output file until after the initialisation of the generator.

    So how do we know when the file has finished and needs closing? The input
    to read_batch could be many files, all to be written to one output
    file. We can't use a timeout, so closing needs to be done explicitly, or
    via the closure of the pipeline.

    By providing a message bottle with the message 'change_write_suffix'
    and the packet attribute 'packet.file_name_suffix'
    the current file will be closed and a new one will
    be opened with the suffix appended to it.
    
    compress : currenly only 'bzip' is enabled (true / bzip resolves to bzip2)
    """
    ftype = 'write_file'
    keys = ['dest_file_name', 'append:False', 'binary_mode:true', 
            'do_write_file:True', 'compress:none']

    def _ensure_file_closed(self):
        """Check that the file has been closed, or close it.
        """
        if hasattr(self, 'out_file'):
            if self.out_file and not self.out_file.closed:
                # if compression, flush any remaining data
                if self.compress:
                    # NB: Assumes all compressor types have a flush method
                    self.out_file.write(self.compressor.flush())
                    # Set compressor to None to make sure the object goes away,
                    # otherwise we can end up with a memory leak
                    if getattr(self, 'compressor'):
                        self.compressor = None
                self.out_file.close()
        else:
            self.out_file = None

    def _get_dest_file_name(self):
        if not hasattr(self, 'write_suffix'):
            file_name = self.dest_file_name
        else:
            file_name = os.extsep.join([self.dest_file_name, self.write_suffix])
        if self.compress in ('bzip', 'bzip2', True):
            return file_name + '.bz2'
        else:
            return file_name
    
    def init_filter(self):
        self.enabled = True
        if self.dest_file_name is None:
            print "'%s' not writing any data as dest_file_name is None" % self.name
            #return
            self.enabled = False


    def _write_data(self, data):

        if self.do_write_file:
            # TO-DO: Write a nice little test to ensure this works (GK)
            
            # this feature will allow us to have lots of different write_file
            # filters in a pipeline (very useful for testing etc) but also
            # have the ability only write out data to the write_file filters
            # that we need to. To do so, set dest_file_name to None (as a
            # default key in the pipeline) to disable the writing to that file.
            
            # do this in init_filter()
            #if self.dest_file_name is None:
                #print "'%s' not writing any data as dest_file_name is None" % self.name
                ##return
                #self.enabled = False

            if not self.enabled:
                return
                
            try:
                if self.compress:
                    self.out_file.write(self.compressor.compress(data))
                else:
                    self.out_file.write(data)
            except AttributeError:
                if self.binary_mode:
                    mode2 = 'b'
                else:
                    mode2 = ''
                
                if self.append:
                    self.out_file = open(self._get_dest_file_name(), 'a' + mode2)
                else:
                    self.out_file = open(self._get_dest_file_name(), 'w' + mode2)
                ##print '**10900** Writing to file: ...%s' % (
                    ##self._get_dest_file_name()[-55:])

                if self.compress in ('bzip', 'bzip2', True):
                    try:
                        self.compressor = bz2.BZ2Compressor()
                    except MemoryError, err:
                        msg = "Memory Error in WriteFile filter: %" % err
                        raise MemoryError, msg
                        
                elif self.compress:
                    raise dfb.FilterAttributeError, "Compression '%s' not supported" % self.compress
                
                if self.compress:
                    self.out_file.write(self.compressor.compress(data))
                else:
                    print "Writing to new file: %s" % os.path.basename(self.out_file.name)
                    self.out_file.write(data)
                
                ##self.out_file.write(data)

    def close_filter(self):
        self._ensure_file_closed()

    def close_output_file(self):
        self._ensure_file_closed()

    def before_filter_data(self, packet):
        try:
            self.out_file.isatty
        except AttributeError:
            return
        if self.out_file.name != self._get_dest_file_name():
            self._ensure_file_closed()
            self.out_file = None

    def filter_data(self, packet):
        self._write_data(packet.data)
        self.send_on(packet)

    def zero_inputs(self):
        self._ensure_file_closed()

    def open_message_bottle(self, packet):
        if packet.message == 'change_write_suffix':
            self._ensure_file_closed()
            self.out_file = None
            self.write_suffix = packet.file_name_suffix
        elif packet.message == 'change_dest_file_name':
            self._ensure_file_closed()
            self.out_file = None
            self.dest_file_name = packet.dest_file_name
        else:
            dfb.DataFilter.open_message_bottle(self, packet)

##+++++TO-DO:+++++  yield 'pass data back??'  <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<
