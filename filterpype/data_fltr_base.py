# -*- coding: utf-8 -*-
# data_fltr_base.py

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


# TO-DO: ReadLine filter -- forwards and backwards
# TO-DO: Remove _data_type from DataPacket, and decide by guessing. ??

# with statement is enabled by default in Python 2.6; needs next line in 2.5
# TO-DO: Conditional on Python 2.5 ??

# ---------------------------------------------------------------------
# NOTE: All data entering should be in unicode (language is important):
#       iso-8859-1
# ---------------------------------------------------------------------

from __future__ import with_statement
import heapq
import time
import new
from contextlib import contextmanager 
import re

import filterpype.filter_utils as fut
import filterpype.embed as embed

# Match to word boundary
re_caps_params = re.compile(r'\b[A-Z][A-Z0-9_]+\b')
# Match param only if entire string
re_caps_params_with_percent = re.compile(r'^%[A-Z][A-Z0-9_]+$')

k_unset = '$$<unset>$$'


class ControllerError(Exception):
    pass

class DataError(Exception):
    pass

class FilterError(Exception):
    pass
    
class FilterAttributeError(FilterError):
    pass

class FilterFactoryError(FilterError):
    pass

class FilterLogicError(FilterError):
    pass

class FilterNameError(FilterError):
    pass

class FilterRoutingError(FilterError):
    pass

class MessageError(Exception):
    pass

class PipelineConfigError(FilterError):
    pass

class PipelineError(FilterError):
    pass

class PipelineRecursionError(FilterError):
    pass

class ResponseError(FilterError):
    pass

class SerialNumberInvalidError(DataError):
    pass

class SerialNumbersInconsistentError(DataError):
    pass

class TankOverflowException(FilterError):
    pass


@contextmanager
def closer(afilter):
    # See http://docs.python.org/whatsnew/2.5.html#pep-343-the-with-statement
    try:
        afilter.zero_inputs()
        yield afilter
    except GeneratorExit:
        # close() has been called, so here we can flush any pending output
##$$$$$$$$$$$$$$$$$$$$        afilter.shut_down()
##        afilter.flushing = True
##        print '**13345** flushing = True, for filter %s' % afilter.name
        afilter.flush_buffer()   # For overridden functionality
        afilter.flushing = False
        afilter.closing = True
        afilter.close_filter()   # For overridden functionality
        # Close the downstream filter, and exit
        afilter._close_filter_next()
    # DataError: ??  TO-DO
    except FilterError:
        # Bad/insufficient data should raise an exception unless the
        # refinery is in the process of shutting down, when we don't mind.
        if afilter.refinery.shutting_down:
            pass
        else:
            raise
        
        
class DataFilterBase(object):
    """This is the Filter part of the Pipes and Filters design pattern, using
    Python co-routines to push the data from one filter to the next.

    Each processing step is encapsulated in a filter component. Pipes are the
    means by which data is passed from one filter to the next, implemented by
    Unix pipes or FIFO queues. However, using co-routines in Python means
    that, in simple cases, there is no longer a need for the pipe to buffer
    data between filters. Each filter will just wait until more data arrives
    in its yield inbox.

    Note that "filter" is a Python reserved word, so use "data_filter" or some
    other variation instead.
       
    The DataFilter has the factory that made it passed in, so if there are
    missing settings in the validation, it can try to get them from its
    factory.
       
    Filters are named with a verb for the transformation, rather than a noun,
    where possible. So we say CountLoops rather than LoopCounter, ReadFileBatch
    rather than FileReader, and Peek rather than Peeker. Then we can talk
    about the ReadFileBatch DataFilter.
       
    """

    # Keys are optional if they have a default value, else compulsory,
    #     e.g. ['name1', 'name2:def_val']   
    # Here, name1 is compulsory, but name2 is optional
    # Read-only class attributes
    
    # A filter has a number of essential/optional attributes or keys
    keys = []  # To be used as a read-only class attribute. Copied into
               # self._keys object attribute, to avoid confusion.
    callbacks = ['results_callback']
##    standard_keys = ['_can_be_refinery', '_class', 'factory', 'ftype', 
    standard_keys = ['_class', '_key_values', '_name', 'factory', 'ftype', 
                     'pipeline', 'dynamic', 'update_live'] + callbacks
    
    ##def __init__(self, factory=None, pipeline=None, **kwargs):
        ##self.factory = factory
        ##self.pipeline = pipeline
        
    def _get_parent_value(self, attr_name):
        """Recurse up to the refinery, looking for the value for attr_name
        """
        # Note that we can't use hasattr to test for pipeline attribute,
        # 
        #     if hasattr(self, 'pipeline') and self.pipeline:
        #
        # because this gives a recursive error. (hasattr uses AttributeError)
        # 
        #     Exception RuntimeError: 'maximum recursion depth exceeded 
        #     while calling a Python object' in 
        #     <type 'exceptions.AttributeError'> ignored
        #
        # If we don't test self.pipeline before use, this also raises
        # AttributeError, causing recursive call to __getattr__. 
        # We have to test the dictionary directly.
        # Avoid unintentionally recursing up the hierarchy for internal
        # attributes that start with '_'.
        if 'pipeline' in self.__dict__ and self.pipeline and \
           not attr_name.startswith('_'):
            return getattr(self.pipeline, attr_name)
        elif 'pipeline' in self.__dict__:
            # Added description similar to base AttributeError
            raise AttributeError, "'%s' object has no attribute '%s'" % (
                self.pipeline.__repr__(), attr_name)
        else:
            # no parent pipeline exists, so raise attribute error without
            # printing the pipeline __repr__ (which causes a recursive 
            # AttributeError much like the description above).
            
            # By using self.name we can avoid recursive AttributeErrors
            # _get_name first checks the _name attribute (which we've set to
            # None before now), then tries to get the ftype (which it doesn't
            # know yet) and falls back on the class name (which works).
            raise AttributeError, "'%s' pipeline has no attribute '%s'" % (
                self.name, attr_name)

    ##def __getattr__(self, attr_name):
        ##"""Called whenever attribute access fails. Let's see if the attribute
        ##exists in a parent pipeline, if any.
        ##"""
        ##return self._get_parent_value(attr_name)


    def __init__(self, **kwargs):
        # factory and pipeline now in kwargs; they may be None
        # ROBDOC: I can understand why there might not be a pipeline but not
        #         why there wouldn't be a factory
        # Ans: A filter doesn't need a factory, because it isn't making other
        # filter. A pipeline must have a factory to know how to make filters.
        if 'factory' not in kwargs:
            kwargs['factory'] = None
        if 'pipeline' not in kwargs:
            kwargs['pipeline'] = None
            
        # self.name MUST be set before we do any checks on Attributes (as below)
        # as it is required by the __getattr__ function when printing description
        # around the AttributeError!
        # Set _name to default value before updating __dict__
        self._name = None
        
        try:
            self._config_keys
##            print '**10510** self._config_keys =', self._config_keys
        except AttributeError:
            # Copy the keys from class attribute hierarchy
            self._config_keys = self.__class__._all_keys()
##wwwwwww            self._config_keys = self.__class__.keys
            ##print '**12130** <%s>._config_keys = %s' % (
                ##self.name, self._config_keys)
            ##try:  
                ##self._config_keys = self.__class__.keys
            ##except AttributeError:
                ##self._config_keys = []
                
        ### If the filter is being made by a pipeline, then its parent pipeline 
        ### object will be passed in in kwargs.
        ##self.pipeline = None
        # Knowledge of the top level pipeline (or refinery) is required to 
        # be able to check various global parameters, particularly the 
        # shutting_down flag.
        # Each filter is its own refinery until it is placed in a pipeline.
        # This will be set in the first call on the refinery property.
##        self._refinery = None
        self._shutting_down = False
##        self._can_be_refinery = False # True for pipelines, not filters
        # Filters will be linked up later by the pipeline
        self.next_filter = None
        
        # TO-DO: Surely callbacks in a pipeline hierarchy should be in the
        # pipeline.py Pipeline base class rather than here?
        
        # When passing results back up a pipeline hierarchy, use a callback
        for callback in self.callbacks:
            self.__dict__[callback] = None
        # A pipeline has a list of filters. Needs to be here for _recurse().
        self.filter_list = []
        self._key_values = []
        ### MOVED ABOVE
        ### Set _name to default value before updating __dict__
        ##self._name = None
        # Dictionary must be updated before making coroutine
        self.__dict__.update(kwargs)
##        self._set_key_values()
        # Check we have the right keys in the filter dictionary
        self.filter_attrs = kwargs
        # For testing: if the name is missing, set it to the name of the class
##        if not hasattr(self, 'name'):
        ##if 'name' not in self.__dict__:
            ##self.name = self.__class__.__name__.lower()
            
            ##jjjjjjjjjjjjjjj
        self._primed = False
        self._corout = None
        self.flushing = False  # Starting to flush_buffer() on close
        self.closing = False # Starting to close() after flushing buffer
#>>>>>        self._set_key_values()
        self._defaults = {}  # To be overridden by extract from keys 
                             # with defaults
        self._main_packet_queue = []
        self._branch_packet_queue = []
        self._emb_module = None  # For any direct Python filters # TO-DO 
        ##self._module_loc = None
        self._refinery = None
        ##self._need_dynamic_update = None
##        self._live_update_params = ['XYZ', 'BATCH_SIZE']
##        self._live_update_params = ['BATCH_SIZE']
        self._live_update_params = []
        #  Any filter/pipeline without a parent pipeline must recurse
        if not self.pipeline:   
            self._recursive_set_values_and_connect()

        return
    
    
        ### Make the rest callable in _recursive_set_values_and_connect
        ### The top level (refinery) pipeline  
        ###$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$
        ##self._recursive_set_values_and_connect()
        ###$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$
        ##self._extract_defaults_from_keys()                               
        ### Set the key values only after defaults have been extracted from
        ### optional keys, to avoid setting an attribute name to something like
        ### "size:0x2000" rather than "size".
        ##self._set_key_values()
        
        ### Set the default values before the init_filter() in case the init
        ### uses something that requires a default value to have been set.        
        ###<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<
####        self.init_filter()
        ###<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<
####        print '**9870** Before __init__-->_set_defaults()'
        ##self._set_defaults()
        ##### Optionally validate the input parameters before initialisation        ##self.validate_params()
        ### Optionally initialise the coroutine, for instance, to set up 
        ### calculated parameters
        ##self.init_filter()
        ### Validation can be performed now, unless this filter is part of a
        ### pipeline. The pipeline may be doing a _filter_update() that is
        ### needed before validation.
####        if not self.refinery and not self.pipeline:
####        self._check_ftype_on_init(**kwargs)
        ##if self.refinery == self:
            ##self._validate()
                
    ##def _all_keys(cls):
        ##return sorted(list(cls._all_keys_as_set()))
    ##_all_keys = classmethod(_all_keys)

    ##def _all_keys_as_set(cls):
        ### Recurse up the class hierarchy, collecting keys from class
        ### attributes on the way. We use a set, to avoid key duplication. This
        ### may happen unintentionally, or if no key attributes are declared for
        ### a class. Thus keys may be redeclared in sub classes.
        ##set_of_keys = set(cls.keys)
        ##for _class in cls.__bases__:
            ##if _class != object:
                ##set_of_keys = set_of_keys.union(_class._all_keys_as_set())
        ##return set_of_keys
    ##_all_keys_as_set = classmethod(_all_keys_as_set)

    def _all_keys(cls):
        # Recurse up the class hierarchy, collecting keys from class
        # attributes on the way. We may not use a set to avoid key
        # duplication, because set() automatically sorts items. Keys may be
        # not redeclared in sub classes.
        try:
            # Collect keys from this class only, not a superclass
            these_keys = cls.__dict__['keys']
        except KeyError:
            these_keys = []
            
        for _class in cls.__bases__:
            if _class != object:
                these_keys = _class._all_keys() + these_keys
        # If defaults have been overridden, choose the latest value in the
        # original position in the list
        return fut.latest_defaults(these_keys)
    _all_keys = classmethod(_all_keys)

    def _check_ftype(self):
        """We have to check filter type on initialisation of a filter, but not
        a pipeline, because ftype is set only after the config has been read.
        Therefore Pipeline disables this.
        """
        # Check that the ftype class variable is lower case and matches the
        # ftype in kwargs if there is one there.
        try:
            if self.ftype != self.ftype.lower():
                raise FilterAttributeError, 'ftype "%s" must be lower case' % (
                    self.ftype)
        except AttributeError:
            raise FilterAttributeError, 'ftype is missing from class %s' % (
                self.__class__.__name__)
            
        ##try:
            ### How can this happen? self.__dict__ is updated directly from kwargs
            ##if kwargs['ftype'] != self.ftype:
                ##msg = 'Filter type requested was "%s", but "%s" was made'
                ##raise FilterAttributeError, msg % (kwargs['ftype'], self.ftype)
        ##except KeyError:
            ##pass  
                    
    def _close(self):
        """Call the coroutine close() to raise the GeneratorExit exception.
        """
        if self._corout:
            self._corout.close()
            
    def _close_filter_next(self):
        """Close the next (main) filter if there is one. 
        HiddenBranchRoute will ensure that branches are called as well.
        """
        if self.next_filter:
            self.next_filter._close()  
            
    def _coded_update_filters(self):
        # This does something only in Pipeline class.
        pass
    
    def _connect_filters(self):
        # This does something only in Pipeline class.
        pass
    
    def _coroutine(self):
        raise FilterError, 'coroutine() not overridden'
    
    def _temp_get_defaults(self):
        return self._really_defaults
    def _temp_set_defaults(self, value):
        self._really_defaults = value
    _defaults = property(_temp_get_defaults, _temp_set_defaults)
    

    def _extract_defaults_from_keys(self):
        """Optional keys can be set as a list, or a list with default values
        embedded, separated by a colon. Extract these if present. Some
        optional keys may not have a default, e.g. a default for
        'source_file_name' in read_file wouldn't make sense, but it is a
        possible key, in case the file name is set there rather than sending
        it to the filter.
        
        e.g 'foo:45', 'bar', 'baz:space'
        """
        ##if self.ftype == 'read_and_align':
            ##pass
        # Copy original list to allow resetting and appending
##        keys_possibly_with_vals = self.__class__.keys[:]
        keys_possibly_with_vals = self._config_keys[:]
        all_keys_no_vals = []
        keys_that_have_vals = []
        vals = []
        for key_maybe_val in keys_possibly_with_vals:
            key = key_maybe_val.split(':')[0]   
            all_keys_no_vals.append(key)
            if ':' in key_maybe_val:
                keys_that_have_vals.append(key)
                val = fut.convert_config_str(key_maybe_val.split(':')[1])
                vals.append(val)
        self._keys = all_keys_no_vals
        if keys_that_have_vals:
            # At least one key had a val
            self._defaults = dict(zip(keys_that_have_vals, vals))
##            print '**12140** <%s>._defaults = %s' % (self.name, self._defaults)
        else:
            self._defaults = {}
            
    def _get_emb_module(self):
        return self.module_loc._emb_module
    def _set_emb_module(self, value):
        self.module_loc._emb_module = value
    # Do we need emb_module and module_loc both as properties? TO-DO
    emb_module = property(_get_emb_module, _set_emb_module, 
                          doc='Embedded Python module')   

    ##def _get_module(self):
        ##"""Module to be found in module_loc.
        ##"""
        ##return self.module_loc._emb_module
    ##module = property(_get_module, doc='Embedded Python module')
    
    def _get_module_loc(self):
        """Return the location of the embedded Python module, which is placed
        in the pipeline, but not in the parent pipeline's pipeline.
        Set on the first access, but shouldn't need to change.
        """
        ##if not self._module_loc:
            ##if self.pipeline:
                ##self._module_loc = self.pipeline  # Or -- could be refinery?
            ##else:
                ##self._module_loc = self
        return self.refinery
    module_loc = property(_get_module_loc, 
                          doc='Location of embedded Python module')

    def _get_name(self):
        """Return some sort of meaningful name in all cases.
        """
        if self._name: ##this is set early on
            return self._name
        elif 'ftype' in self.__dict__:
            return self.ftype
        else:
            return self.__class__.__name__.lower()
    def _set_name(self, value):
        self._name = value
    name = property(_get_name, _set_name, doc='Name for filter/pipeline')

    ##def _get_need_dynamic_update(self):
        ##"""At the start, we can work out whether we need to check for live
        ##data or not.
        ##"""
        ##if self._need_dynamic_update is None:
            ##self._need_dynamic_update = \
                ##len(self._key_values) > 0 and \
                ##self.ftype != 'py' and \
                ##self.module_loc and self.module_loc != self
            ####if self._need_dynamic_update:
                ##### Make empty embedded Python module
                ####pass
        ##return self._need_dynamic_update
    ##need_dynamic_update = property(_get_need_dynamic_update,
                 ##doc='Do we check embedded Python on receipt of each packet?')

    ##def _get_module_loc(self):
        ##"""Return the location of the embedded Python module, which is placed
        ##in the pipeline, but not in the parent pipeline's pipeline.
        ##Set on the first access, but shouldn't need to change.
        ##"""
        ##if not self._module_loc:
            ##if self.pipeline:
                ##self._module_loc = self.pipeline  # Or -- could be refinery?
            ##else:
                ##self._module_loc = self
        ##return self._module_loc
    ##module_loc = property(_get_module_loc, 
                          ##doc='Location of embedded Python module')
    
    def _get_refinery(self):   #<<<<<<<TEST-TO-DO<<<<<<<<<<<<
        """Recurse up through the pipelines until you reach a pipeline which
        has no parent pipeline. Thus the refinery is the whole system, as much
        as one pipeline knows about it. It acts as a place to access global
        attributes, in particular "shutting_down".    
        
        This is also the location of the embedded Python module.
        """
        if not self._refinery:            
            if self.pipeline:
                self._refinery = self.pipeline._get_refinery()
            else: # We've at the top of a pipeline, or a lone filter
                self._refinery = self
        return self._refinery
    refinery = property(_get_refinery, doc='Top-level pipeline')   
    
    def _get_shutting_down(self):
        """
        """
        return self.refinery._shutting_down 
    shutting_down = property(_get_shutting_down, 
                             doc='Is refinery shutting down (read-only)') 
    
    def _hidden__getattribute__(self, attr_name):
        """Make a filter/pipeline dynamic by setting __getattribute__ to
        point to this function. The superclass allows us to get the attribute
        without recursion, thus being able to return alternative values.
        """
        superclass = DataFilterBase.__bases__[0]
        value = superclass.__getattribute__(self, attr_name)
        try:
            value + ''  # Test for being a string, to give TypeError if not.
                        # Avoid raising AttributeError to pass it. If so,
                        # exception from getattr would mistakenly return value.
            if re_caps_params_with_percent.match(value): 
                return getattr(embed.pype, value[1:], k_unset)
            else:
                return value
        except TypeError:
            return value
        
    def make_dynamic(self, is_dynamic=True):
        if is_dynamic:
            print '**16090** Making "%s" filter/pipeline dynamic' % (
                self.name)
            # Hold default value =
            #     <slot wrapper '__getattribute__' of 'object' objects>
            self._hold__getattribute__ = self.__class__.__getattribute__
            self.__class__.__getattribute__ = self._hidden__getattribute__
            ##self._hold__getattribute__ = self.__getattribute__
            ##self.__getattribute__ = self._hidden__getattribute__
        else:
            print '**16090** Resetting "%s" filter/pipeline to static' % (
                self.name)
            self.__class__.__getattribute__ = self._hold__getattribute__
            ##self.__getattribute__ = self._hold__getattribute__
                    
    def _make_filters(self):
        # This does something only in Pipeline class.
        pass
    
    def _prime(self):
        """Prime the filter by calling next() on the coroutine, to get it
           ready to receive the first packet of data. This is called 
           just-in-time to allow filter attributes to be prepared.
           
           We call it just in time, as an alternative to the @start_filter 
           decorator approach, because that calls next() within the
           constructor, which may be too soon if some of the filter attributes
           need to be changed by the enclosing pipeline first.
        """
        if self._primed:
            raise FilterError, 'You can\'t prime an already primed filter'
        # We now have everything ready to construct the coroutine
        self._corout = self._coroutine()
        # Immediately move on to the first (yield) of the coroutine, where
        # it will wait for a data packet to arrive.
        if self._corout:
            self._corout.next()
        self._primed = True
        
    def _do_recursive_call(self, func_names):
        """This is where the functions are called in turn, at one particular
        level in the recursion. We could pass in general **kwargs, but haven't
        found a use case for it yet.
        
        ROBDOC: It may be useful to metion what 'the functions' are
        (e.g. 'init_filters')
        """
        ##try:
        for func_name in func_names:
            # Use getattr() rather than __dict__ to ensure that inherited
            # methods are found. getattr() returns an unbound function, so
            # needs self as first argument.
            ##getattr(self.__class__, func_name)(self)
            try:
                func = getattr(self.__class__, func_name)
            except AttributeError, err:
                print '**10110** Function "%s" not found, "%s"' % (func_name, err)
                raise
            # execute the function
            func(self)
        
    def _recurse(self, func_names, preorder=True, level=0):
        """Call the func_names for this object, and then recurse for each
        child filter. This will recurse down until it reaches filters with no
        children. If preorder is False, then recursion will be done in
        postorder. This is needed for linking up pipelines, where children
        must be done first.
        """
        if level > 50:
            raise PipelineRecursionError, 'level has reached %d' % level
        self.level = level
        if preorder:
            self._do_recursive_call(func_names)
            
        if len(self.filter_list) > 0:
            # TO-DO This is a hack, needs fix for initialising
            # _ordered_filter_list
            for short_name in self._ordered_filter_list:
                a_filter = self._filter_dict[short_name]
                a_filter._recurse(func_names, preorder, level + 1)
            
        if not preorder:
            self._do_recursive_call(func_names)
            
    def _print_filters_preorder(self):
        print '**10440** preorder  -- %s%d %s' % (
            ' ' * self.level * 4, self.level, self.name)
        
    def _print_filters_postorder(self):
        print '**10450** postorder -- %s%d %s' % (
            ' ' * self.level * 4, self.level, self.name)
            
    def _recursive_set_values_and_connect(self):
        ##print '**10100** Doing _recursive_set_vals&conn() for class %s' % (
            ##self.__class__.__name__)
        
        # From DataFilterBase.__init__()
        # ==============================
        
        # Recursively create the pipelines/filters in a hierarchy
        self._recurse(['_make_filters'])
        # For debugging
##        print '**10435** ==================================================='
##        self._recurse(['_print_filters_preorder'])
##        print '**10435** ==================================================='
##        self._recurse(['_print_filters_postorder'], preorder=False)
##        print '**10435** ==================================================='
        # Set the key values only after defaults have been extracted from
        # optional keys, to avoid setting an attribute name to something like
        # "size:0x2000" rather than "size".
        # _update_substitutions must be before _coded_update_filters
        
        # Set values for each filter
        # Set the default values before the init_filter() in case the init
        # uses something that requires a default value to have been set.        
        self._recurse(['_extract_defaults_from_keys',
                       '_set_key_values',
                       '_set_defaults',
##                       '_update_substitutions',
                       ])
        
##        self._recurse(['_update_from_factory'])
        # Coded update_filters() should be called after all the default have 
        # been set to avoid a "Can't change parameter value error"
        self._recurse(['_coded_update_filters',
                       '_update_from_factory',
                       '_update_substitutions',
                       ])  
        

        # From Pipeline.__init__()
##        self._recurse('_update_config_params')
        
        
##        self._recurse('_set_defaults')
        # The new refinery may need to update some filters.
        # Collected together in _update_config_params():
        #        self._coded_update_filters()
        #        self._update_substitutions()
        #        self._set_defaults()
        #        self._update_from_factory()    
        
        # (1) Copy callback functions from parent to children
        # Check callbacks TO-DO
        self._recurse(['_update_callbacks']) 
        # (5) Option to change the route after connection, where it might
        #     depend on filter parameters
        
        # Note that connection has to be recursed in postorder, to ensure that
        # children are linked before their parents. If parents are linked
        # first then the connections out would be overwritten with None.
        self._recurse(['_connect_filters',
                       '_update_route'], preorder=False)
        
        # (6) Only now can the validation run, after all the filters have
        #     been updated
        # Optionally initialise the coroutine, for instance, to set up 
        # calculated parameters
        self._recurse(['init_filter'])
        # Validation can be performed now, unless this filter is part of a
        # pipeline. The pipeline may be doing a _filter_update() that is
        # needed before validation.

##        if not self.refinery and not self.pipeline:
##        self._check_ftype_on_init(**kwargs)
##        if self.refinery == self:
##            self._validate()
        self._recurse(['_validate'])

        
    def _set_defaults(self):
        """If the object has the attribute already, we assume that a
        non-default value has already been set. 
        """
        for key, value in self._defaults.iteritems():
            # Avoid using 
            #     if not hasattr(self, key):            
            # because this works by checking getattr() for exceptions. If
            # there is a property with the same name as the attribute which
            # hasn't yet been set up, it will raise an AttributeError, making
            # hasattr() think the attribute isn't there. See TankQueue and 
            # tank_size for an example of this problem.
            if key not in self.__dict__:
                self.__dict__[key] = value
                
    ##def _get_key_value(self):
        ##if key matches regex:
            ##get from module
        ##else:
            ##return local value
    ##xxx = property
        
    def _set_key_values(self):
        """If there are essential/optional key values passed in from the
        route, they can be set here, unless they change a previously set
        value. We have to allow the same value because one "batch:4096" filter
        may be parsed twice, as a from and a to filter. However, once the
        value is set, it may not be changed during initialisation. 
           
           xxxxxxxxxxxxxx These can't be evaluated here because
           _coded_update_filters() has not yet run.
           Substitute values should be evaluated first, because they override
           hard-coded. ??????? TO-DO  _set_key_values() <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<< 
        """
        if self._key_values:
            ##print '**19820** Before _set_key_values(), %s._keys = %s' % (
                ##self.name, self._keys)
            ##print '**19830** Before _set_key_values(), %s._key_values = %s' % (
                ##self.name, self._key_values)
            for key, value in zip(self._keys, self._key_values):
                try:
                    value + ''
                    uc_percent = re_caps_params_with_percent.match(value)
                except TypeError:
                    uc_percent = False
                if key in self.__dict__:  # Don't use "if hasattr(self, key):"
                    if self.__dict__[key] not in [k_unset, value] and \
                       not uc_percent:
                        msg = 'Can\'t change the %s.%s parameter value ' + \
                              'from %s to %s'
                        raise FilterAttributeError, msg % (
                            self.name, key, getattr(self, key), value)
                else:
                    self.__dict__[key] = value  # Don't try to use setattr()
                    
    def _update_callbacks(self):
        """Default action is to copy callback functions from parent pipeline
        to children. Could be overridden.
        """
        if self.pipeline:
            for callback in self.callbacks:
                self.__dict__[callback] = self.pipeline.__dict__[callback]
    
    ##def _update_config_params(self):
        ##"""Perform all parameter setting at one pipeline level before recursing
        ##to the next level.
        ##"""
        ###$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$
        ### (1) Do explicit updates
        ### (2) Get missing essentials from factory.essentials
        ### (3) Override other defaults or updates with explicitly set
        ###     essential key values (_key_values)
        
        ### Trying this first, so substitutions come after programmed settings
        ##self._coded_update_filters()
        ##self._update_substitutions()
        ##self._set_defaults()
        ##self._update_from_factory()    
        
    def _update_from_factory(self):
        # Try to read default value(s) from factory.essentials if some filter
        # essential key is missing. Don't raise an exception here if something
        # is missing. Leave that to _validate().
        # In simple tests, factory may not be defined.
##        if hasattr(self, 'factory') and self.factory:
        if 'factory' in self.__dict__ and self.factory:
            for key in self._keys:
##                if not hasattr(self, key) and key in self.factory.essentials:
                if key not in self.__dict__ and key in self.factory.essentials:
                    self.__dict__[key] = self.factory.essentials[key]
            
    def _update_substitutions(self):
        """The filter may have essential or optional keys. Check these for
           substition syntax: ${foo}, and if found, read value from the 
           parent pipeline.
        """
        if not self.pipeline:
            # No point looking for substitutions because there is no parent
            # pipeline to get the values from.
            return
        
        # No _keys...        
        for key in self._keys:
            # Optional keys won't yet have been set because the _key_values
            # need to be set before the defaults are applied.
            
            if key in self.__dict__:
                value1 = self.__dict__.get(key)
                try:
                    if value1.startswith('${') and value1.endswith('}'):
                        # Get substitute value from parent pipeline.
                        # If key is not found in the parent pipeline, this
                        # may be an error --> KeyError.
                        subst_var = value1[2:-1]
                        #if subst_var == 'words_per_sec':
                            #pass
                        try:
                            new_val = getattr(self.pipeline, subst_var)
                        except AttributeError:
                            msg = '**17080** "%s" value not found in ' + \
                                  'pipeline %s or ancestors'
                            print msg % (subst_var, self.pipeline.name)
                            raise FilterAttributeError, msg % (
                                subst_var, self.pipeline.name)
                        setattr(self, key, new_val)
                        pass
                            ##msg = '**10150** Substitution: "%s.%s.%s" --> "%s"'
                            ##print msg % (self.pipeline.name, self.name, 
                                         ##value1, self.__dict__[key])
                except AttributeError:  # It isn't a string
                    pass
    
    def _update_route(self):
        pass

    def _validate(self):
        """If an essential key is missing, raise an exception.
        Check that all attributes present are allowed.
        """
        self._check_ftype()
        # Check for duplicate keys (originally with different defaults)
        if len(self._keys) != len(set(self._keys)):
            msg1 = 'Duplicate attributes found in "%s"'
            raise FilterAttributeError, msg1 % self._keys
        for key in self._keys:
            if key.lower() != key:
                msg = 'Key "%s" is not all lower case'
                raise FilterAttributeError, msg % key
##        for key in self._all_keys():
            if key and not hasattr(self, key):
                msg2 = 'Attribute "%s" is missing from key ' + \
                       'attributes of %s (class %s)\nExpected keys = %s'
                raise FilterAttributeError, msg2 % (
##                    key, self.name, self.__class__.__name__, self._all_keys())
                    key, self.name, self.__class__.__name__, self._keys)
        # Check that all attributes present are allowed.
        possible_keys = self._keys + self.standard_keys
##        possible_keys = self._all_keys() + self.standard_keys
        for key2 in self.filter_attrs:
            if not key2 in possible_keys:
                raise FilterAttributeError, \
                      'Attribute "%s" is not allowed in class %s' % (
                          key2, self.__class__.__name__)
        # Lastly, check any custom validations
        self.validate_params()
        
    def after_send_on(self, packet, fork_dest):
        """Hook to execute just after a packet is sent on
        """
        pass
    
    def before_send_on(self, packet, fork_dest):
        """Hook to execute just before a packet is sent on
        """
        pass
    
    def close_filter(self):
        """Override this to add to the closing functionality before the filter
        is finally closed.
        """
        pass
    
    ##def dynamic_update(self):
        ##"""Go through keys, and if any of the values is a string starting with
        ##"%", read the actual value from the embedded Python module, else
        ##return the literal string.
        
        ##This is automatically called before filter_data() and after send_on()
        ##for all filters. The latter enables a subsequent Python filter to
        ##change parameters before the sending filter continues. For instance
        ##you might want to change batch size for each batch you send. You can
        ##put additional updates wherever you like.
        ##"""
        ##return # <<<<<<<<<<<<<<<<<<<<< dynamic_update TO-DO
    
        ##if self.need_dynamic_update:
            ##for key, value in zip(self._keys, self._key_values):
                ##try:
                    ##if value.startswith('%') and value.isupper():
                        ##msg = '**14490** %s: Attempting dynamic update of ' + \
                              ##'key "%s" from value "%s"'
                        ##print msg % (self.name, key, value)
                        ####setattr(self, key, 
                            ####getattr(self.module_loc.module, value[1:], value))
                        ##setattr(self, key, getattr(self.emb_module, 
                                                   ##value[1:], value))
                        ##if self.__dict__[key] == value:
                            ### Value not found in module. Reject %XXX as OK
                            ##msg = 'Module is None, or unknown module attr "%s"'
                            ##raise FilterAttributeError, msg % value
                        ##msg = '**14495** %s: Successful dynamic update of ' + \
                              ##'key "%s" to value "%s"'
                        ##print msg % (self.name, key, self.__dict__[key])
                        
                ##except AttributeError:
                    ##raise AttributeError, 'oops'

    def filter_data(self, packet):
        raise FilterError, 'Abstract class: inherit from DataFilter ' + \
                           'or DataFilterExt and override filter_data()'

    def flush_buffer(self):
        """Override this for clearing out any buffered data: always before
        final close_filter(), but may be needed at intermediate stages.
        """
        pass    
        
    def init_filter(self):
        pass
    
    def send(self, *packets):
        """For the first filter in the pipeline, send in the starting data.
        This must be a DataPacket object.
        
        If not already primed, call _prime() to send a next() call to the
        generator.
        """
        if not self._primed:
            self._prime()
        if self._corout:
            for packet in packets:
                # Ensure that the only things being sent around the pipeline
                # are data packets or message bottles. (The data contained in
                # the packet can be any type, as packet.data.)
                if not issubclass(packet.__class__,  DataPacket):
                    raise DataError, 'Bad type: %s is not a packet' % (
                        packet.__class__.__name__)
                self._corout.send(packet)

    def send_on(self, packet, fork_dest='main'):
        """Send on packets to their destination.
        """
        # If there is no next_filter (main) then nothing happens. With a next
        # filter, then packet may be sent to main or branch. It will be sent
        # to branch, if there is a branch filter, else thrown away.
        self.before_send_on(packet, fork_dest)
        if packet and self.next_filter:
            packet.sent_from = self
            packet.fork_dest = fork_dest
            if fork_dest == 'main':
                self.next_filter.send(packet)
            elif fork_dest == 'branch':
                if isinstance(self.next_filter, HiddenBranchRoute):
                    self.next_filter.send(packet)
            else:
                raise FilterRoutingError, \
                      'Unknown packet fork destination "%s"' % (fork_dest)
##        self.dynamic_update()    # Get u/c param values from module
        self.after_send_on(packet, fork_dest)
        
        ##else:
            ### Send on packet for output later when send_queued_packets() runs. 
            ### This will send the packets to the correct destination, and clear 
            ### the queues.
            ##if fork_dest == 'main':
                ##self._main_packet_queue.append(packet)
            ##elif fork_dest == 'branch':
                ##self._branch_packet_queue.append(packet)
            ##else:
                ##raise FilterRoutingError, \
                      ##'Unknown packet fork destination "%s"' % (fork_dest)
        
##    def send_on(self, packet, fork_dest='main', optional=False):
    ##def send_on_now(self, packet, fork_dest='main'):
        ##"""This actually sends the packets, rather than queueing them.
        ##If there is no next_filter (main) then nothing happens.
        ##With a next filter, then packet may be sent to main or branch. It will
        ##be sent to branch, if there is a branch filter, else thrown away.
        ##"""
        ##if packet and self.next_filter:
            ##packet.sent_from = self
            ##packet.fork_destination = fork_dest
            ##if fork_dest == 'main':
                ##self.next_filter.send(packet)
            ##elif fork_dest == 'branch':
                ##if isinstance(self.next_filter, HiddenBranchRoute):
                    ##self.next_filter.send(packet)
            ##else:
                ##raise FilterRoutingError, \
                      ##'Unknown packet fork destination "%s"' % (fork_dest)
        ##else:
            ##return None

            ####if not fork_dest in ['main', 'branch']:
            ### Send on to the branch only if followed by a 
            ### HiddenBranchRoute filter
            ##if fork_dest == 'branch' and \
               ##self.next_filter.__class__.__name__ != 'HiddenBranchRoute':
                ### ROBDOC: The following is a fundamentalish change to the way
                ### send_on works - if the fork_destination is 'branch' it will
                ### not be sent on unless there is a HiddenBranchRoute filter as
                ### the next filter. Before, it was still sending on to the next
                ### filter regardless and filters do not have logic for ignoring
                ### branch packets - therefore (due to the send_on being called
                ### on the Main and the branch) we got a packet explosion as
                ### essentially we were sending the packet twice for EACH
                ### subsequent filter.                
                ### Replaced code:
                ####if not optional:
                    ####raise FilterRoutingError, \
                              ####'A Branch in the route is required after ("%s"), not "%s"' % (
                                  ####self.name, self.next_filter.__class__.__name__)
                ##if optional:
                    ### If the next filter is not a HiddenBranchRoute and the fork
                    ### destination of the packet is 'branch' we do not want the 
                    ### packet to go any further
                    ##return
                ##else:
                    ### branch (HiddenBranchRoute filter) is required if the fork
                    ### destination is 'branch'
                    ##raise FilterRoutingError, \
                          ##'A Branch in the route is required after ("%s"), not "%s"' % (
                              ##self.name, self.next_filter.__class__.__name__)
####            packet.sent_from = self
####            packet.fork_destination = fork_dest
            ##return self.next_filter.send(packet)
        ##else:
            ##return None
        
    def shut_down(self):
        """Shut down the pipeline/filter by setting a shutting_down flag. It
        doesn't work to pass close() straight to the first filter, because the
        generator sequence is still busy and comes back with an error message:
        "ValueError: generator already executing"
           
        Try to close the pipeline, but don't worry if we can't because it's
        busy: there must be a loop somewhere that should be checking the 
        shutting_down read-only property.
        """
        msg = '**12615** %s Shutting down pipeline/filter from "%s" %s'
        print msg % ('-' * 20, self.name, '-' * 20)
        self.refinery._shutting_down = True
        try:
            self._close()
        except ValueError, err:  # generator already executing
##            msg = '**12617** Tried to close %s, but couldn\'t: "%s"'
##            print msg % (self.name, err)
            pass


    def validate_params(self):
        """Override this function to check validity of input parameters. This
        is called before init_filter(), which may use the input parameters
        to calculate derived params.
        """
        pass
    
    def zero_inputs(self):
        """During initialisation of a filter, there may be inputs and counters
        that need to be set to zero. By putting these in a separate function,
        we avoid duplicating code where clearing is required repeatedly.
           
        Some filters that use carries and remainders may require clearing
        inputs before each use, to give a consistent one-off answer, for
        something like pump_data().
           
        zero_inputs() is called by the closing() context manager, but not
        until the generator receives its first data packet.
           
        Should this be called init_filter_dynamic  <<<<<< TO-DO <<<<<<
        """
        pass


class DataFilter(DataFilterBase):
    """Basic framework for data filter coroutine, sending packets on after
    receiving them. Override filter_data() for practical functionality.
    Packet received may be a data packet or a message bottle.
    """
    
    def _coroutine(self):
        with closer(self):
            while True:
                packet = (yield)
                ##print '**10240** %s packet in for filter %s' % (
                    ##packet.__class__.__name__, self.name)
                ##if packet.__class__.__name__== 'MessageBottle':
                    ##pass
                if not packet.message:  # This must be a data packet
                    self._process_data_packet(packet)
                else:
                    self._process_message_bottle(packet)
                        
    #def _import_code(self, code, module_name):
        #if not self.module_loc.module:
            #self.module_loc.module = new.module(module_name)
        #self.python_module = self.module_loc.module
        #exec code in self.module_loc.module.__dict__
        
    def _process_data_packet(self, packet):
##        self.dynamic_update()    # Get u/c param values from module
        self.before_filter_data(packet)            # Hook 1
        self.filter_data(packet)             # The main filtering is done here
        self.after_filter_data(packet)             # Hook 2
        
    def _process_message_bottle(self, packet):
        # The message bottle never gets sent to filter_data(), just
        # straight on the next filter
        if self.name == packet.destination:
            # we're at the destination filter
            self.open_message_bottle(packet)
            # Once used, the message bottle is not sent on
        elif self.ftype == packet.destination:
            # we're at a filter of the type matching the description
            self.open_message_bottle(packet)
            # we also want to send this on for other filters of the 
            # same type to open the message unless the message only
            # has a single_use flag set.
            if not packet.single_use:
                self.send_on(packet, 'branch', optional=True)
                self.send_on(packet, 'main')                        
        elif self.ftype == 'hidden_branch_route':
            # Message bottles will now travel down every branch:
            # small hack (TO-DO discuss) to ensure that messages
            # are filtered by the hidden_branch_route and passed
            # down branches
            self.filter_data(packet)
        else: 
            # Send msg to branch and main, because we don't know ?? TO-DO
            # where the destination filter is located.
            # ROBDOC: this comment might like to mention that there
            # doesn't have to be a branch
##            self.send_on(packet, 'branch', optional=True)
            self.send_on(packet, 'branch')
            self.send_on(packet, 'main')
            
    ##def _send_on_packet_queue(self, fork_dest):
        ##"""Send on all the branch packets generated from one packet arriving.
        ##"""
        ##if fork_dest == 'main':
            ##queue_to_go = self._main_packet_queue
        ##elif fork_dest == 'branch':
            ##queue_to_go = self._branch_packet_queue
        ##else:
            ##raise FilterAttributeError, 'Unknown fork dest "%s"' % fork_dest           
        ##while True:
            ##try:
                ##self.send_on(queue_to_go.pop(0), fork_dest, now=True)
            ##except IndexError:
                ##break  # No more packets to pop from list
                    
    #def _update_filter_live(self):
        #"""For u/c params listed, update their values from the live Python
        #pipeline module. Python modules cannot update themselves in this
        #way. It would get too confusing. Skip this if it is the enclosing
        #pipeline.
        
        #This is used to set the value of a filter key to a value in the
        #pipeline's embedded Python module. The obvious way to do this is
        #to take the key (now forced to be lower case) and match it with the
        #upper case Python module global.
        #"""
        #if self.ftype != 'py' and self._module_loc() != self:
            ## Is there a Python module available?
            #module = self._module_loc().module
            #for attrib in self._live_update_params:
                #old_value = getattr(self, attrib.lower(), None)
                #new_value = getattr(module, attrib.upper(), None)
###                print '**12490** %s filter -- key %s changing from %s to %s' % (
###                    self.name, attrib.lower(), old_value, new_value)
                #setattr(self, attrib.lower(), new_value)
            
    def after_filter_data(self, packet):
        """Override this to perform some action just after the incoming packet
        is processed by filter_data().
        """
        pass
    
    def before_filter_data(self, packet):
        """Override this to perform some action just before the incoming packet
        is processed by filter_data().
        """
        pass

    def open_message_bottle(self, packet):
        """Open the message bottle, and take appropriate action.
        We know what to do with these general purpose commands, applying
        generally to any filter:
            reset
            
        Other functionality may be needed, specific to one filter. In this
        case, override the open_message_bottle() in the filter. 
        e.g. WriteFile uses this to close one file and open a new file with
        a different name.
        """
        if packet.message == 'reset':
##            new_value = eval(str(packet.expression))
##            print '**10245** Reset %s parameter "%s" to "%s"' % (
##                self.name, packet.param_name, packet.new_value)
            setattr(self, packet.param_name, packet.new_value)
            # Now input params have been changed, ensure that effect is seen
##            self.update_filters()
            # Well-spotted Chris!
            self._recurse(['_coded_update_filters'])  
        else:
            e_msg = "'%s' open_message_bottle does not recognise message '%s'"
            raise MessageError, e_msg % (self.name, packet.message)
                
        
def dynamic_params(static_class):
    """Class decorator to add the functionality to look up from the embedded
    Python environment the current values of attributes whose apparent values
    start with "%" and the name is upper case.
    
    Usage: put "@dynamic_params" on the line before the class decoration
    
    Problem is that this changes the static class for all uses of it. We may
    not want all instances dynamic.
    """
    def __getattribute__(self, attr_name):
        # Call the undecorated class to get the original attribute value
        static_value = static_class.__getattribute__(self, attr_name)
        # Check dynamic parameter only if the value is a string
        try:
            static_value + ''  
            if re_caps_params_with_percent.match(static_value): 
                # e.g. %SOME_VAR, %SPEED, but not SOME_VAR or %Speed
                msg = '**14490** %s: Attempting dynamic update of ' + \
                      'key "%s" with current static_value "%s"'
                print msg % (static_class.__getattribute__(self, 'name'), 
                             attr_name, static_value)
                return getattr(embed.pype, static_value[1:])
            else:
                return static_value
        except TypeError:  # value was not a string
            return static_value  
        
    return type('Dynamic' + static_class.__name__ , (static_class,), 
                dict(__getattribute__=__getattribute__))


#------------------------------------------

class DynamicMetaClass(type):
    """Use this metaclass, derived from "type", to create the class. This sets
    a flag for checking that it is being used, and sets __getattribute__ to 
    ensure dynamic processing. This is variable at run time, as to whether we
    use the metaclass or not, but is not reversible.
    
    Note that __getattribute__ is a class attribute, not an instance
    attribute. If we set the instance attribute, it is ignored and thus not
    dynamic.
    """
    def __init__(cls, name, bases, ns):
        cls.uses_dynamic_metaclass = True
        cls.__getattribute__ = DataFilterBase._hidden__getattribute__

  
# Mix-in functions (not used, after all)

def mix_in (base, addition):
    """Mixes in place, i.e. the base class is modified.
    Tags the class with a list of names of mixed members.
    """
    assert ('_mixed_' not in base.__dict__)
    mixed = []
    for item in addition.__dict__:
        if item not in base.__dict__:
            base.__dict__[item] = addition.__dict__[item]
            mixed.append (item)
    base._mixed_ = mixed
        
def mix_in_copy (base, addition):
    """Same as mix_in, but returns a new class instead of modifying
    the base.
    """
    class NewClass(object): 
        pass
    # This gives error:
    # AttributeError: attribute '__dict__' of 'type' objects is not writable
    NewClass.__dict__ = base.__dict__.copy()
    mix_in(NewClass, addition)
    return NewClass


class DynamicMixIn(object):
    """Additional base class for Filters, where each attribute access is
    checked for beginning with "%", i.e. requiring a dynamic value.
    Dynamic property is not easily reversible.
    """

    def __getattribute__(self, attr_name):

        value = DataFilter.__getattribute__(self, attr_name)
        try:
            value + ''  # Check if string
            if re_caps_params_with_percent.match(value):  # e.g. %SOME_VAR
                msg = '**14505** %s: Attempting dynamic update of ' + \
                      'key "%s" with current value "%s"'
                print msg % (self.name, attr_name, value)
                return getattr(embed.pype, value[1:])
            else:
                return value
        except AttributeError:
            # Not a string
            return value
        except TypeError:
            # Not a string
            return value
    
    
##class DataFilterExt(DataFilterBase):
    ##"""Extension to basic framework for data filter coroutine, sending message
    ##packets within standard structure, before and after receiving data
    ##packets. Override filter_data() for practical functionality.
    
    ##Not sure how this might be used... Leave it for now.
    ##"""
    
    ##def _coroutine(self):
        ##with closer(self):
            ##while True:
                ##packet = (yield)
                ### Send message to branch -- before_filter
                ##self.filter_data(packet)
                ### Send message to branch -- after_filter
                

class DataPacket(object):
    """The data is passed through the filters in packets.  These are Python
       dictionaries that provide the means to store parameters or partial
       results, along with the data which is a string.

       Data can be passed to the packet constructor as a string parameter,
       or as data='xxx' keyword parameter.

       TO-DO: Test cloning for efficiency <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<

       When packets are split up, the parameters need to be passed along, with
       the revised data.  This is done by cloning the packet.
       
    """

#    def __init__(self, data=None, **kwargs):
    def __init__(self, data='', seq_num=-1, **kwargs):
        self.data = data   
        self.message = None  # DataPacket may not have a message (cf. Bottle)
        self.fork_dest = None   # 'main'/'branch' for use when branching
        self.sent_from = None   # Where was the data packet sent from?
        self.seq_num = seq_num  # Packets can be numbered with SeqPacket
        self.branch_up_to = 0   # For stripping off leading junk from packets
        self.__dict__.update(kwargs)
        
    def clear_data(self):
        """Clear data from packet, because we can't do that in clone()
        """
        self.data = ''
    
    def clone(self, data='', **kwargs):
        """Create a new packet, with the same parameters and data. We expect
        data as the argument. There may be keywords. If data is given, set the
        data string to this value.
        
        TO-DO: Cloning message bottles?
        
        ROBDOC : When sending on data it would be useful if the data keyword
        would raise an exception if no data is in the packet OR just allow
        there to be no data in the packet (rather than cloning the original
        data if you provide data as ''). This depends on whether you're going
        to allow a packet without any data:
        
        e.g.
        
        .. code-block:: python

            clone(self, data=None, ..):
            ..
            if data is not None:
                if data is '':
                    raise NoDataInPacketException, 'data is required in the packet'
                cloned_packet.data = data
              
        """
        cloned_packet = DataPacket()
        # Remember to copy the dictionary with .copy() to avoid pointer passing
        cloned_packet.__dict__.update(self.__dict__.copy())
        # Reset the data to the new data just passed in, if there is any
##        if data is not None:
        if data:
            cloned_packet.data = data
        # Pass remaining parameters into cloned packet
        cloned_packet.__dict__.update(kwargs)
        return cloned_packet
    
    def _get_data_length(self):
        """Use this instead of len(data) because data may not be a string.
        If not, we'll count its length as 0. 
        (Or there might be some use in converting it to a string first, or
        adding up the lengths of a list of strings.)
        """
        try:
            # Test for string before getting length, to avoid returning the
            # wrong sort of length, e.g. of a list.
            self.data + ''
            return len(self.data)
        except TypeError:
            return 0
    data_length = property(_get_data_length, doc='Length of data, if a string')    


class HiddenBranchRoute(DataFilter):
    """Route the data packets according to their fork_destination.
    'main' goes on to the next_filter as usual.
    'branch' goes to branch_filter, raising an exception if there is none.
    'prev' may link to the filter before the branch.
    
    This is called Hidden... because you shouldn't need to use it explicitly.
    Since it is never created by ftype, we need to set ftype manually.
    """
    ftype = 'hidden_branch_route'
           
    def _close(self):
        """Override base functionality to ensure branches are closed as well.
        """
        self.branch_filter._close()
        DataFilter._close(self)
    ##def close_filter(self):
        ##self.branch_filter.close()
        
    def filter_data(self, packet):
        fork_destination = packet.fork_dest  # 'main' or 'branch'
        # Don't allow the destination of the packet to persist outside
        # this HiddenBranchRoute, to avoid incorrect direction later.
        # Choose the route with a dictionary.
        packet.fork_dest = None
        route_dict = dict(main=self.next_filter, branch=self.branch_filter)
        route_dict[fork_destination].send(packet)
        
                
class MessageBottle(DataPacket):
    """Message is a type of data packet, usually with only one-time use.
    MessageBottle    -----TO-DO-----
    e.g. target = pad_bytes, message = reset:byte_count:100
    
    @destination : can be the filter name or the filter type. If filter type, the
    message is forwarded onto the rest of the pipeline main and branch so that
    other filters of the same type can open the message.
    """
    # TO-DO Descend MessageBottle and DataPacket from abstract Packet

    def __init__(self, destination, message, single_use=True, **kwargs):
        # ROBDOC : Is single_use in use?! I've added it to DataFilter logic
        # when destination == ftype, so that messages will stop there.
        self.destination = destination
        if not message:
            raise MessageError, 'MessageBottle must have a message'
        if 'data' in kwargs:
            raise MessageError, 'MessageBottle stores values, not data'
        # Two ways to get data to go along with message
        ##try:
            ##data_for_msg = kwargs['data']
            ##del(kwargs['data'])  # Avoid double parameter passing
        ##except KeyError:
        # Split values out of message, if present, e.g. "reset:100"
        message, values = fut.get_values_from_name(message)
        # Default data to null string
        DataPacket.__init__(self, data='', message=message, values=values, 
                            single_use=single_use, **kwargs)
        
        
class PriorityQueue(object):
    """Priority queue to enable looping, using TankQueue and TankFeed. List is
    sorted by heapq, using priority as the first sort field. If priorities are
    the same, then time is used to distinguish order. See p.208 of Python
    Cookbook, 2nd ed.
    """
    
    def __init__(self):
        # Queue is held in a list maintained by heapq
        self.queue = []
        self.next_priority_counter = 1

    def _debug_print(self, action, priority, time_posted, item):
        try:
            data_out = item.data
        except AttributeError:
            data_out = item
        print '**12050** %s, priority=%s, time=%s, data=%s' % (
            action, priority, time_posted, data_out)       
    
    def clear(self):
        "Empty the queue of all items"
        self.queue = []
        
    def push(self, item, priority=None):
        if priority is None:
            # Use incrementing priority counter to avoid random order from
            # having simultaneous times for rapid additions to queue.
            priority = self.next_priority_counter
            self.next_priority_counter += 1
        decorated_item = priority, time.time(), item
        ##self._debug_print('pushing', priority, decorated_item[1], item)
        heapq.heappush(self.queue, decorated_item)
        
    def push_none(self):
        """Push None on to the queue, with maximum (negative) priority so that
        it goes to the front of the queue. This is called when the queue size
        is changed by padding the front.
        """
        self.push(None, priority=-1000)
        
    def pop(self):
        priority, time_posted, item = heapq.heappop(self.queue)
        ##self._debug_print('popping', priority, time_posted, item)
        return item
    
    def queue_size(self):
        return len(self.queue)
    
    def sorted_items(self):
        return heapq.nsmallest(len(self.queue), self.queue)
        
                

