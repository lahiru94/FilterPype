# -*- coding: utf-8 -*-
# pipeline.py

# Licence
#
# FilterPype is a process-flow pipes-and-filters Python framework.
# Copyright (c) 2009 Folding Software Ltd and contributors
# www.foldingsoftware.com/filterpype, www.filterpype.org
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


#-----------------------------------------------------------------------
# TO-DO: Zero data cascading, so previous remainders are cleared in pump_data()
# TO-DO: Check environ
#
#
#-----------------------------------------------------------------------

# with statement is enabled by default in Python 2.6; needs next line in 2.5
from __future__ import with_statement
import sys
import re
from configobj import ConfigObj
import os

##import filterpype.lex_yacc5
import filterpype.lex_yacc4
import filterpype.data_filter as df
import filterpype.filter_utils as fut
## Circular import error if included: import filter_factory as ff
import filterpype.data_fltr_base as dfb

# Search for (>>> or ^^^), surrounded by spaces
spaces = r' *'
re_main_or_branch = re.compile(spaces + r'(>>>|\^\^\^)' + spaces)

class Pipeline(dfb.DataFilter):
    """A pipeline is a filter that has a filters dictionary which
       keys by name all the filters in the pipeline.
       
       The mechanism of how the filters work need not be known, for a higher
       level of functionality.
       
       The pipeline needs to know which factory to use to make its data filters.
       This would not normally change, so is passed in with the constructor.
       
       To make testing easier, we define an input binary file name, and 
       one or more output files.
       
    """
    config = 'not_set'  # To be overridden by subclass
    route = ''
    
    def __call__(self, data_in, clear_pipe=True):
        return self.pump_data(data_in, clear_pipe)
            
    def __init__(self, **kwargs):
        """ A pipeline has a number of reserved keywords which are used to
        modify the pipeline.
        
        - factory : Required. Maps the ftype strings to python classes.

        ROBDOC : is the following statement True?
        - ftype : Optional. Overwrites the __class__.ftype which is the 
          string representation of the pipeline class name. e.g. 'read_file'
        
        - pipeline : Optional. A link to the parent pipeline. If None, this
          pipeline is the top most pipeline in the hierarchy tree.
            
        - config : Optional. Overwrites the __class__.config which is the 
          pipeline configuration as a string in the following format:
                   [--main--]
                   ftype = demo
                   description = a_docstring
                   
                   [--route--]
                   sink
        
        - **kwargs : Optional. All other keyword arguments are assigned to 
          the DataFilter object dictionary as attributes. 
          
          DataFilterBase.__init__(**kwargs) performs self.__dict__.update(kwargs)

          These attributes are then available to the pipeline for use in
          functions zero_inputs() and update_filters() etc. as
          self.getf('filtername').attribute
          
          
                   
          """
        # factory, pipeline and config in kwargs
        # A pipeline must have a factory, whereas a filter may omit factory.
        if 'factory' not in kwargs:
            raise dfb.FilterAttributeError, 'Factory missing'
        if 'pipeline' not in kwargs:
            kwargs['pipeline'] = None
        
##        dfb.DataFilter.__init__(self, factory, **kwargs)
        ##if fut.debug > 1:  #pragma: nocover
            ##if self.refinery == self:
                ##level_label = 'REFINERY'
            ##else:
                ##level_label = 'pipeline'
            ##print '**5040** Initialising %s pipeline, %s (level=%s)' % (
                            ##self.__class__.__name__, self.name, level_label)
        self._name = None                    
        # Allow passed in config/route to override class attribute
        if 'config' in kwargs:
            self.__class__.config = kwargs['config'] 
            del(kwargs['config'])
##        # Clear out any previous settings of class attribute "keys"
##        self.__class__.keys = []
        self._config_keys = []

        # Need to record all filters made, in top level pipeline, so that the
        # order of filter updates will be correct. Note that _filter_dict
        # shouldn't be accessed directly, but rather through the get_filter()
        # function that will make a filter if it doesn't already exist.
        self._filter_dict = {}
        self.first_filter = None
        # last_filter is to be set if the packets are to be passed on 
        # to another filter/pipeline
        self.last_filter = None  
        self._next_filter = None  # Bad name ?? <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<
        self._shutting_down = False
        self._filter_dict_dict = {}
        self._ordered_filter_list = []
        self._python_code_lines = []  # For embedded Python

        self._read_config()
        # The class definition must be finished from parsing the config, before
        # the inherited __init__() can be called.
        self.dynamic = False  # Set True for live updates from embedded Python
        self._parse_config()
##        self.route_parser = lex_yacc5.RouteParser(debug=False)
##        print '**16230** In %s' % self
        self.route_parser = filterpype.lex_yacc4.RouteParser(debug=False)
##        print '**16250** new route_parser at %s' % (
##            hex(id(self.route_parser)))
        self._parse_route()
            

        dfb.DataFilter.__init__(self, **kwargs)
        ### self._can_be_refinery: True for pipelines, not filters. Must be set
        ### before the call to dfb.DataFilter.__init__()
        ##kwargs.update(dict(_can_be_refinery=True))  
        ## The name is set externally by the pipeline that includes it
        
        ### Filter can be made dynamic by 
        ###     (1) setting 'dynamic' as a key
        ###     (2)
        ###     (3)
        ##if self.dynamic:
            ##self.make_dynamic(True)
##            self.make_dynamic(False)

            
        if fut.debug > 100:  #pragma: nocover
            if self.refinery == self:
                level_label = 'REFINERY'
            else:
                level_label = 'pipeline'
            print '**15040** Initialising %s pipeline, %s (level=%s)' % (
                            self.__class__.__name__, self.name, level_label)

##        self._make_filters()

        ##if self.refinery == self:    
            ##self._recursive_set_values_and_connect()
        return
    
    def _check_ftype(self):
        """This needs to be called only for a filter, not a pipeline, where
        ftype is read from the config. So override base function.
        """
        pass

    def _close(self):
        """Send the pipeline _close() to the first filter in the pipeline.
        """
        self.first_filter._close()
    
    def _coded_update_filters(self):
        """Call update_filters() function if it has been defined within a
        pipeline.
        """
##        print '**10225** Before _coded_update_filters() for %s' % (self.name)
        self.update_filters()
        
    def _connect_filter_pair(self, from_filter_name, join, to_filter_name):
        """Connect two filters, given their names and the type of join. 
        """
        ##print '**10190** Connect (in %s) %s %s %s' % (
            ##self.name, from_filter_name.split(':')[0], 
            ##join, to_filter_name.split(':')[0])
        if to_filter_name == 'None':
            # End of branch/main. No connection necessary. In fact, the filter
            # may already be connected to some other filter, and we don't
            # want to overwrite it.
            return  
        else:
            to_filter = self.getf(to_filter_name)

        from_filter = self.getf(from_filter_name)

##        if from_filter_name.startswith('hidden_brancher_') and \
        if from_filter_name.startswith('hidden_branch') and \
           join == '^^^':
            from_filter.branch_filter = to_filter
        else:
            from_filter.next_filter = to_filter
            
    def _connect_filters(self):
        """Connect filters created by _make__filters(). 
        
        When data is sent to the pipeline, each packet is passed straight to
        the first_filter. In case the pipeline is connected further on to
        another filter or pipeline, we must make the next_filter of the
        pipeline point to the same filter as the next_filter of the final
        internal filter of the pipeline.
        """
        ##if fut.debug > 3:  #pragma: nocover
            ##print '**15130** _connect_filters() for %s (0x%X)' % (
                ##self.name, id(self))

        first_filter_name = re_main_or_branch.split(self.connections[0])[0]
        self.first_filter = self.getf(first_filter_name)
        assert self.first_filter, 'Pipeline is missing first_filter'

        for connection in self.connections:
            from_filter_name, join, to_filter_name = re_main_or_branch.split(
                                                                    connection)
            self._connect_filter_pair(from_filter_name, join, to_filter_name)
        # The final to_filter_name is None, so the last_filter is the
        # final from_filter_name.
        assert to_filter_name == 'None', 'to_filter_name is not None??'
        self.last_filter = self.getf(from_filter_name)
        
    # When an enclosing pipeline sets the next_filter property, to pass on
    # the data packets, there needs to be a side effect for a pipeline. 
    # The last_filter needs to have its next_filter set to the same filter.
    # This is done through a property.
    def _get_next_filter(self):
        return self._next_filter
    def _set_next_filter(self, nxt_filter):
        self._next_filter = nxt_filter
        if hasattr(self, 'last_filter') and self.last_filter:
            self.last_filter.next_filter = nxt_filter
    next_filter = property(_get_next_filter, _set_next_filter,
                    doc='Sets internal last_filter to have same next_filter')
        
    def _make_filter(self, param_dict):
        """Make the filter from the param dict
        """
        # Different factories will make different components from same config
        # Pass in pipeline as second argument, to give filters made a parent
        new_filter = self.factory.create_filter(param_dict, self)
        # self._filter_dict is used by getf() to get the filter
        ##print '**10120** Adding "%s" to pipeline "%s"' % (
            ##new_filter.name, self.name) 
        self._filter_dict[new_filter.name] = new_filter
        # Create a filter list, to be used later for recursive updates
        self.filter_list.append(new_filter)
##        self._ordered_filter_list.append(new_filter.name)
        return new_filter
        
    def _make_filters(self):
        """Create the filters filter_dict_list, to be connected up by
           _connect_filters().

           ##To allow external access to data, pass in an environment dictionary,
           ##which all the filters in the pipeline have read/write access to.

##           We have to add the environ_dict to the filter's attributes before
           the decorator is called to move to the first (yield).  This is
           because some results need to be initialised outside the while True
           loop.
        """
        ##if fut.debug > 3:  #pragma: nocover
            ##print '**5120** _make_filters() for %s (0x%X)' % (
                                                          ##self.name, id(self))
##        for param_dict in self._filter_dict_dict.itervalues():
        for filt_dict_name in self._ordered_filter_list:
            param_dict = self._filter_dict_dict[filt_dict_name]
            ## TO-DO: Check ftype -- can it ever not be a string?
            self._make_filter(param_dict)

    def _parse_config(self):
        """ ROBDOC : CJ added a vague description below, but could be sure...
        ##Parses the class config attribute?!
        """
        main_section_found = False
        ftype_in_config = False
        docstring = []
        config_obj = ConfigObj(self.config_only)
        ##if not config_obj:
            ##raise dfb.FilterError, 'Missing configuration'
            ### If input is a file, this will write out to the file, formatted
            ##lines = config_obj.write()
        self._filter_dict_dict = {}
        ##if self.__class__.keys:
            ##msg = 'Before parse_config, self.__class__.keys = %s'
            ##raise dfb.FilterAttributeError, msg % self.__class__.keys
        for section in config_obj.sections:
            if section == '--main--':
                main_section_found = True
                # Default values may be present or not
                keys_with_vals = []
                live_updates = []
                for name, value in config_obj[section].iteritems():
##                    print '**9810** [%s] %s = %s' % (section, name, value)
                    if name == 'ftype':
                        self.ftype = value
                        ftype_in_config = True
                    elif name.startswith('descr'):  # description
                        # Build up multiline docstring
                        # ConfigObj puts strings with commas into a list
                        docstring.append(fut.config_obj_comma_fix(value))  
                    elif name.startswith('key'):  # "key = ..." or "keys = ..."
                        key_list = value
                        try:
                            # Note: += doesn't raise the TypeError exception
                            keys_with_vals = keys_with_vals + key_list
                        except TypeError:
                            keys_with_vals = keys_with_vals + [key_list]
                    elif name == 'dynamic':
                        self.dynamic = fut.convert_config_str(value)
                    elif name.startswith('update_live'):  # e.g. update_live_27
                        update_list = value
                        try:
                            # Note: += doesn't raise the TypeError exception
                            live_updates = live_updates + update_list
                        except TypeError:
                            live_updates = live_updates + [update_list]
                    else:
                        msg = 'Unknown [--main--] parameter "%s" in config'
                        raise dfb.PipelineConfigError, msg % name
                # This is where the class attribute "keys" is defined, just
                # like the line "keys = [..]" in the filter definitions.
                ##print '**10025** Setting %s class attr keys from config=%s' % (
                    ##self.__class__.__name__, keys_with_vals)
                ##if self.ftype == 'read_and_align':
                    ##pass
##                self.__class__.keys = keys_with_vals
                self._config_keys = keys_with_vals
                self._live_updates = live_updates
                ##if self.__class__.keys:
                    ##self._extract_defaults_from_keys()  # Into self._keys()                            
            ##elif section == '--defaults--':
                ##print '**10300** Reached section --defaults--'
            else:
                if section not in self._ordered_filter_list:
                    self._ordered_filter_list.append(section)
                self._update_filter_dict(section, config_obj[section])
        if not main_section_found:
            msg = '[--main--] section missing from class %s' 
            raise dfb.PipelineConfigError, msg % self.__class__.__name__
        if not ftype_in_config:
            msg = 'ftype missing from [--main--] section in class %s'
            raise dfb.PipelineConfigError, msg % self.__class__.__name__ 
        # Append description to any docstring. Must have one or the other.
        if self.__doc__:
            docstring = [self.__doc__, '', ''] + docstring
        self.__doc__ = '\n'.join(docstring)
        if not self.__doc__:
            msg = '__doc__/description missing from [--main--] section ' + \
                  'in class %s'
            raise dfb.PipelineConfigError, msg % self.__class__.__name__ 
        
    def _parse_route(self):
##        print '**16240** pipeline route_parser at %s' % (
##            hex(id(self.route_parser)))
        parse_fn = self.route_parser.parse_route
        route_out, self.connections, fltr_names = parse_fn(self.route)
        if fut.debug > 300:  #pragma: nocover
            print_list = self.route_parser.pipeline_for_print(route_out)
            filter_name = self.name
            print '**13000** route for %s (class %s) =' % (
                filter_name, self.__class__.__name__)
            print '-' * 70
            print '\n'.join(print_list)
            print '-' * 70
        # If the filter doesn't exist, we have to make it before we can set
        # the essential key values, because we can't deduce the keys from 
        # the class.
##        print '**8045** _parse_route, filters found: %d' % len(fltr_names)
        for fltr_name in fltr_names:
            short_name, values = fut.get_values_from_name(fltr_name)
##            print '**8051** filter = %s, values = %s' % (short_name, values)
            # If there are no values, _key_values will be set to []
            # Do we need to update it? It may cancel previous values. TO-DO
            if short_name not in self._ordered_filter_list:
                self._ordered_filter_list.append(short_name)
            self._update_filter_dict(short_name, dict(_key_values=values))
        ##print '**10460** _ordered_filter_list for %s = %s' % (
            ##self.name, ' >>> '.join(self._ordered_filter_list))
                    
    def _prime(self):
        dfb.DataFilter._prime(self)
        
    def _code_line(self, line_num, indent, code):
        return 'line_%5.5d = |%s%s' % (line_num, ' ' * indent, code)
        
    def _python_function_start(self, line):
        fn_name = line.strip()[4:-1]
        ##print '**12315** function_name =', fn_name
        self.bare_fn_name = fn_name.split(':')[0]
        params = fn_name.split(':')[1:] + ['*args', '**kwargs']
        name_line = self._code_line(200, 0, '$comment$ ' + self.bare_fn_name)
        def_line = self._code_line(500, 0, 'def %s(%s):' % (
            self.bare_fn_name, '$comma$ '.join(params)))
        self.this_fn_lines = [name_line, def_line]
##        global_line = self._code_line(510, 4, 'global $%s$' % self.bare_fn_name)
##        self.this_fn_lines.append(global_line)
        pkt_line = self._code_line(
            520, 4, "packet = kwargs.get('packet'$comma$ None)")
        self.this_fn_lines.append(pkt_line)
        self.this_fn_global_params = set()
        self.in_python = True

    def _python_function_middle(self, line_num, line):
        found_params = set(dfb.re_caps_params.findall(line))
        self.this_fn_global_params = self.this_fn_global_params.union(
                                                                  found_params)
        self.all_global_params = self.all_global_params.union(found_params)
        # Note 4-space indent after "|" because we're in a function
        line2 = self._code_line(line_num, 4, line)
 ##       line = 'line_%5.5d = |    %s' % (line_no, line)
        # Config_obj strips comments
        return line2.replace('#', '$comment$').replace(',', '$comma$')        
    
    def _python_function_end(self):
        ##msg = '**12380** for %s, this_fn_global_params = %s'
        ##print msg % (self.bare_fn_name, self.this_fn_global_params)
        if self.this_fn_global_params:
##            str1 = '$%s$' % self.bare_fn_name
            params = '$comma$ '.join(sorted(self.this_fn_global_params))
##            self.this_fn_lines[1] = self.this_fn_lines[1].replace(str1, str2)
            self.this_fn_lines.insert(2, self._code_line(510, 4, 
                                                         'global ' + params))
        ##else:
            ##self.this_fn_lines.pop(1)  # Remove global line
        # Set the global_params to None, before the function defn starts
        # Initialise all the global params to '$$<unset>$$' rather than None,
        # so early tests find some value.
                
        ##init_code_lines = [self._code_line(0, 0, ('%s = None' % param)) 
                           ##for param in sorted(self.all_global_params)]

        self.this_fn_lines = \
            self.this_fn_lines[:1] + [
                ##self._code_line(300 + line_num, 0, ('%s = None' % param))
                self._code_line(300 + line_num, 0, 
                                ("%s = '%s'" % (param, dfb.k_unset)))
                for line_num, param 
                in enumerate(sorted(self.this_fn_global_params))
                ] + self.this_fn_lines[1:]
        ##print '**12390**', 60 * '\\'
        ##for line in self.this_fn_lines:
            ##print '**12390**', line.rstrip()
        ##print '**12390**', 60 * '/'
        self.config_lines3.extend(self.this_fn_lines)
        self.in_python = False

    def _read_config(self):
        """ Read pipeline configuration from three possible sources:
        
        (1) Fixed class variable config, not requiring an input parameter
        (2) External configuration file
        (3) Configuration in a multi-line text variable  ???????????????
        
        Here is an example configuration file, with the two special
        headings, [--main--] and [--route--]
        
        [--main--]
        ftype = foo
        description = TO-DO: docstring
        # a1, a2, b1, b2 are essential keys, while gfgf, jj, and uuu
        # are optional, with default values.
        keys = a1, a2, b1, b2, gfgf:34, jj:fred, uuu:none
                    
        [filter34]
        adasd = 45
        space = 96
        name = bill
        
        [--route--]
        temp_text_after1:${a1} >>>
        temp_text_before1:${b1} >>>
        reverse_string1 >>>
        temp_text_after2:${a2} >>>
        temp_text_before2:${b2} >>>
        reverse_string2                    
        """
        # config has been passed in as parameter, or set as class attribute
        config_lines = self.config.splitlines()
        if len(config_lines) == 1:
            # Then the config was a file name containing the actual config
            config_file = open(config_lines[0])
            try:
                config_lines = config_file.readlines()
            finally:
                config_file.close()
        ### Move config input left if whole file is indented
        ### TO-DO Put this into FilterUtils -- unindent_block()
        ##config_lines2 = []
        ##for line in config_lines:
####            print '**10624** "%s"' % line
            ##if not line.startswith(' ' * 4) and line.strip():
                ##break
            ##config_lines2.append(line[4:])
        ##else:
            ### All lines had 4 spaces at the start
            ##config_lines = config_lines2
        config_lines2 = fut.unindent(config_lines)
            
      ##      print '**10622** line %5.5d: %s' % (line_no, line)
        # Before stripping lines, check for python code filters. We have to 
        # prefix each line with "line_XXXXX =" to get it through config_obj.
        self.in_python = False
        self.config_lines3 = []
        self.all_global_params = set()
        for line_no, line in enumerate(config_lines2):
            if self.in_python:
                if line.startswith('['):
                    self._python_function_end()
                    self.config_lines3.append(line)  
                else:
                    line = self._python_function_middle(1000 + line_no, line)
                self.this_fn_lines.append(line)
            else:
                self.config_lines3.append(line)  
##            print '**10620**', line
            if line.startswith('[py_'):
                self._python_function_start(line)
        if self.in_python:    
            self._python_function_end()
##        print '**12400** config_lines3 =\n------------\n%s' % (
##            '\n'.join(self.config_lines3))       
        # Remove white space and blank lines
        config_lines4 = [line.strip() for line in self.config_lines3 
                         if line.strip()]
##        print '**10621** ----------------\nconfig_lines4 =\n', config_lines4
        # All pipeline configs must have a '[--route--]' section, as the final
        # section in the *.pype file. Read and split the file into two parts.
        try:
            route_heading_index = config_lines4.index('[--route--]')
        except ValueError:
            # TO-DO <<<< Put all these errors together in a list
            msg = '[--route--] heading is missing from config for class %s' 
            raise dfb.FilterRoutingError, msg % self.__class__.__name__
        self.config_only = config_lines4[:route_heading_index]
        self.route = '\n'.join(config_lines4[route_heading_index + 1:])
        if not self.route.strip():
            msg = '[--route--] section is empty for class %s'
            raise dfb.FilterRoutingError, msg % self.__class__.__name__

# --------------------------------------------------------------

                ##fn_name = line.strip()[4:-1]
                ##print '**12310** function_name =', fn_name
                ##bare_fn_name = fn_name.split(':')[0]
                ##params = fn_name.split(':')[1:] + ['*args', '**kwargs']
                ##def_line = 'line_00000 = |def %s(%s):' % (
                    ##bare_fn_name, '$comma$ '.join(params))
                ##config_lines3.append(def_line)
                ##print '**10625**', def_line
                ##global_line = 'line_00001 = |    global $%s$' % bare_fn_name
                ##config_lines3.append(global_line)
                ##print '**10625**', global_line
                ##pkt_line = "line_00002 = |    packet = kwargs.get('packet'$comma$ None)"
                ##config_lines3.append(pkt_line)
                ##print '**10625**', pkt_line
                ##global_params = set()
                ##in_python = True            ##config_lines3.append(line)    
            ##print '**10620**', line

                    ####if re_caps_params.findall(line):
                        ####print '**12370** findall =', re_caps_params.findall(line)
                    ##self.this_fn_global_params = self.this_fn_global_params.union(
                                        ##set(re_caps_params.findall(line)))
                    ### Note 4-space indent after "|" because we're in a function
                    ##line = 'line_%5.5d = |    %s' % (line_no, line)
                    ### Config_obj strips comments
                    ##line = line.replace('#', '$comment$'
                                        ##).replace(',', '$comma$')
                                        
# --------------------------------------------------------------

    def _update_filter_dict(self, filt_name, source_dict={}):
        """Update filter dict if it exists, or create a new one, referenced by
        name, which is also one of the dictionary's keys.
        """
        try:
            filt_dict = self._filter_dict_dict[filt_name]
        except KeyError:  
            # First reference to filter, so create dictionary
##            filt_dict = self._filter_dict_dict[filt_name] = dict(_name=filt_name)
            filt_dict = dict(_name=filt_name)
            self._filter_dict_dict[filt_name] = filt_dict
        for key, value in source_dict.iteritems():
            # Try to convert sensibly, rather than by formal configspec
            new_value = fut.convert_config_str(value)
            # We're building a dictionary, where the key values shouldn't
            # change. If a null value is being passed in where a significant
            # value is already set, we can ignore it, else raise an exception.
            if key in filt_dict and filt_dict[key]:
                if filt_dict[key] == new_value:
                    continue  # Nothing to do
                elif not new_value:
                    continue  # Avoid overwriting current value with [] or None
                else:  # Change value attempt
                    msg = 'Can\'t change %s value (from "%s" to "%s")'
                    raise dfb.FilterAttributeError, msg % (key, filt_dict[key],
                                                           new_value)
            else:            
                filt_dict[key] = new_value
                ##print '**12150** <%s>.filt_dict[%s] = %s' % (filt_name, 
                                                             ##key, new_value)
                
    def _update_route(self):
        self.update_route()

    def init_filter(self):
        """Initialise coroutine vaiables that are needed before we reach the
        (yield) statement. Override in subclasses.
        """
        pass
    
    def filter_data(self, packet):
        """This is the minimum functionality for a pipeline that does nothing.
        But some pipelines may want to override this, setting parameters
        before sending any data.
        """
        self.first_filter.send(packet)
            
    def get_filter(self, filter_name):
        """ TO-DO>>>> Return the filter from the _filter_dict, if it has
        already been made,
           
        else make the filter and then return it. This is necessary now because
        of allowing an empty config. Reference to a filter will create it.
        Test the name first for being in the format "some_name:23" where 23 is
        the value of the first key.
        """
        if not filter_name:
            raise df.FilterNameError
        # Throw away any _key_values after ':' 
        return self._filter_dict[filter_name.split(':')[0]]
    getf = get_filter
            
    def pump_data(self, data_in=None, zero_inputs=True): # << TO-DO Needs work
        ##, close_at_end=True):
        """Put the data into the pipeline by wrapping it in a Datapacket.
           Get the data out by temporarily sticking a Sink on the end,
           returning all the packets received.
           Remember to close the pipeline externally, if tidying up actions 
           need to be performed.
           
           
           If zero_inputs is True, reinitialise the variables before pumping 
           the new data in.  <<<<<<<zero_inputs<<<<<<<<< TO-DO <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<
        """
        pump_sink = df.Sink()
        self.last_filter.next_filter = pump_sink
        print '**10195** Connect (%s, pump_data) %s >>> %s' % (
            self.name, self.last_filter.name, pump_sink.name)
        try:
            data_in + []           # TO-DO: Better way to check the data type
        except TypeError:  # Not a list
            data_in = [data_in]
        for data in data_in:
            if data is None:
##                packet = None
                packet = dfb.DataPacket(None)  # Or ''??
            else:
                packet = dfb.DataPacket(str(data))
            if fut.debug > 1:  #pragma: nocover
                print '**3698**', 65 * '='
                if fut.debug > 2:  #pragma: nocover
                    show_data = '|'.join(fut.split_strings(str(data), 8))
                    print '**3705** data_in   = "%s"' % (
                        fut.data_to_hex_string(show_data[:80]))
            self.first_filter.send(packet)
        ##if close_at_end:
            ##self.first_filter.shut_down()
        # All data has arrived, so disconnect sink
        self.last_filter.next_filter = None
        # Store the full results packets in self.results in case they are 
        # needed, returning the packet.data as a list.
        self.results = pump_sink.results
        # TO-DO: Decide about which data type here -- strings or lists
##        return pump_sink.results[-1].data
        if len(self.results) == 1:
            return self.results[0].data
        else:
            return [pkt.data for pkt in self.results]
    
        ### Simple case: if there is only one item in the list, return its value
        ### <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<
        ##if False and len(pump_sink.results) == 1:
            ##if fut.debug > 1:  #pragma: nocover
                ##print '**3720** data_out = "%s"' % pump_sink.results[0].data
            ##return (pump_sink.results[0].data,
                    ##pump_sink.results)
        ##else:
            ### But there may be multiple results for even just one data input
            ##return ([pkt.data for pkt in pump_sink.results] ,
                    ##pump_sink.results)

    def update_filters(self):
        "Update filter parameter values after the creation of all the filters"
        pass

    def update_route(self):
        "Update pipeline route after the creation of all the filters"
        pass

    
@dfb.dynamic_params
class DynamicPipeline(Pipeline):
    """Pipeline that uses dynamic u/c variables.
    """
    

class PipelineForPypes(Pipeline):
    """For testing automatic pipeline creation
    
        BL - 28/8/09 - Added in a config to force it to have an ftype as a
        test was failing in FDS specific files due to it being missing
    """
    config='''
    [--main--]
    ftype=pipeline_for_pipes
    description=nothing
    
    [--route--]
    pass_through
    '''
    
class ExtractManyAttributes(Pipeline):
    """ Splits data into lines and extracts attributes based on a delimiter 
    parameter, the attributes are stored in the packet.
    """
    config = """
    [--main--]
    ftype = extract_many_attributes
    keys = attr_delim
    
    [--route--]
    split_lines >>>
    attribute_extractor:${attr_delim}
    """
        
class CopyFile(Pipeline):
    """Take in a file object via data stream, and write it to a named file.
    """
    
    config = '''
    [--main--]
    ftype = copy_file
    keys = dest_file_name, source_file_name:none
    # Callback removed -- environ:none
            
    [read_file]
    # Callback removed -- environ:none
    # Since environ is optional, the substitution will only happen if set
    ##environ = ${environ}
    source_file_name = ${source_file_name}
    
    [--route--]
    read_file >>>
    write_file:${dest_file_name}
    '''
    # TO-DO: Check the template system -- ${dest_file_name}  # <<<<<<<<<<<<<<<<<<<<<<<<<<<<<
    
    ##def close(self):
        ##self.getf('write_file').close_output_file()
        ##Pipeline.shut_down(self)
        
    def close_filter(self):
        self.getf('write_file').close_output_file()
                    
     
class Refinery(Pipeline):
    pass


class CheckEssentialKeys(Pipeline):
    """Check that parameters can be set in various ways.
    """
    
    config = '''
    [--main--]
    ftype = check_essential_keys
    description = Test class with two essential params and one optional param
    keys = foo, bar, baz_opt:16
    ##dynamic = True

    [--route--]
    batch:120
    '''


