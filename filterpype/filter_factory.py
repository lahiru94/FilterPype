# -*- coding: utf-8 -*-
# filter_factory.py

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


import copy

import filterpype.data_fltr_base as dfb
import filterpype.data_filter as df
import filterpype.data_fltr_demo as dfd
import filterpype.pipeline as ppln
import filterpype.ppln_demo as ppln_demo
import filterpype.filter_utils as fut
from filterpype.pypes import pypes_basic


class FilterFactory(object):
    """Factory class for making Filters and Pipelines"""

    abstract_class = True

    def __init__(self):
        # Basic data filters here are needed by all types of pipeline. The
        # normal class mapping process is to have the same words in the name as
        # in the class, but lower case with underscores, rather than CapsCase.
        # Maintain the list in alphabetical order, by name.
        class_map = dict(
            attribute_change_detection = df.AttributeChangeDetection,
            attribute_extractor     = df.AttributeExtractor,
            batch                   = df.Batch,
            branch_dynamic          = df.BranchDynamic,
            branch_param            = df.BranchParam, 
            branch_clone            = df.BranchClone,
            branch_first_part       = df.BranchFirstPart,
            branch_until_value      = df.BranchUntilValue,
            branch_if               = df.BranchIf,
            branch_once_triggered   = df.BranchOnceTriggered,
            branch_ref              = df.BranchRef,
            break_point             = df.BreakPoint, # For dubugging in a debugger. Don't use as a pass_through
            bzip_compress           = df.BZipCompress,
            bzip_decompress         = df.BZipDecompress,
            calc_slope              = df.CalcSlope,
            calculate               = df.Calculate,
            callback_on_attribute   = df.CallbackOnAttribute,
            callback_on_multiple_attributes = df.CallbackOnMultipleAttributes,
            collect_data            = df.CollectData,
            combine                 = df.Combine,
            concat_path             = df.ConcatPath,
            convert_bytes_to_int    = df.ConvertBytesToInt,
            convert_filename_to_path= df.ConvertFilenameToPath, # TO-DO remove
            copy_file               = ppln.CopyFile,
            count_bytes             = df.CountBytes,
            count_loops             = df.CountLoops, 
            count_packets           = df.CountPackets,
            data_length             = df.DataLength,
            dedupe_data             = df.DedupeData,
            distill_header          = df.DistillHeader,
            format_param            = df.FormatParam, 
            get_bytes               = df.GetBytes,
            hash_sha256             = df.HashSHA256,
            header_as_attribute     = df.HeaderAsAttribute,
            hidden_branch_route     = dfb.HiddenBranchRoute,            
            join                    = df.Join,
            null                    = df.Waste,
            pass_non_zero           = df.PassNonZero,
            pass_through            = df.PassThrough,
            peek                    = df.Peek,
            print_param             = df.PrintParam,
            py                      = df.EmbedPython,
            read_batch              = df.ReadBatch,
            read_bytes              = df.ReadBytes,
            rename_file             = df.RenameFile,
            reset                   = df.Reset,
            r111eset_branch         = df.R111esetBranch,
            reverse_string          = df.ReverseString,
            swap_two_bytes          = df.SwapTwoBytes,
            send_message            = df.SendMessage,
            seq_packet              = df.SeqPacket,
            set_attributes_to_data  = df.SetAttributesToData,
            sink                    = df.Sink,
            sleep                   = df.Sleep,
            split_words             = df.SplitWords,
            split_lines             = df.SplitLines,
            tag_packet              = df.TagPacket,
            tank_branch             = df.TankBranch,
            tank_feed               = df.TankFeed,
            tank_queue              = df.TankQueue,
            waste                   = df.Waste,     # Also 'null'
            wrap                    = df.Wrap,
            write_configobj_file    = df.WriteConfigObjFile,
            write_file              = df.WriteFile,
            
            check_essential_keys    = ppln.CheckEssentialKeys,
            extract_many_attributes = ppln.ExtractManyAttributes,
            )
        self._apply_class_map(class_map)
        # Link to dictionary of external configs with full filter details
        self.pypes = pypes_basic
        # To avoid having to pass parameters down many levels of pipeline, we
        # store global vars in self.essentials. These are available to
        # any filters that have defined the var as essential.
        self.essentials = dict(comparison='equals',  # For branch_if filter
                               )
        if self.__class__.abstract_class:
            raise NotImplementedError, 'Can\'t instantiate an abstract class'
        self._filter_dict_validated = False
        
    def _apply_class_map(self, class_map):
        # ROBDOC: What is this method actually doing?
        for key, _class in class_map.iteritems():
            try:
                self.factory_dict[key] = dict(_class=_class)
            except AttributeError:
                self.factory_dict = {}
                self.factory_dict[key] = dict(_class=_class)                
        
    def _validate_filter_dict(self):
        """Check that none of the filter types in the dictionary is wholly
           contained in another filter type. This could lead to confusion
           in auto-typing from the name.
           e.g. We wouldn't want a dictionary with one type 'foo' and
           another type 'foo_bar'. We start testing the longer variations,
           working towards the shorter, but still best to avoid it.
           e.g. Given the name 'widget_flange_maker_01', we look for, in order:
                   widget_flange_maker_01
                   widget_flange_maker
                   widget_flange
                   widget
        """
        keys = sorted(self.factory_dict.iterkeys())
        for j in xrange(len(keys) - 1):
            if keys[j + 1].startswith(keys[j]):
                raise dfb.FilterFactoryError, \
                      'Ambiguous filter names: "%s" starts with "%s"' % (
                    keys[j + 1], keys[j])
        self._filter_dict_validated = True
            
    def create_filter(self, param_dict_or_ftype, pipeline=None):  # TO-DO Break this up <<<<<<<<<<<<
        """Extract the right filter dictionary from the factory_dict.
        Store a reference in the object to the factory that made it.
        Pass in the filter_attrs so the new object has right attributes.
        Alternative parameter is just the ftype.
        Dictionary validation is enforced before the first use.
        
        TO-DO: pipeline is (a str? an object? required??)
        """
        if not self._filter_dict_validated:
            self._validate_filter_dict() 
            
        # TO-DO: update these comments
        # If the filter isn't typed explicitly by the param dict, give
        # it an ftype that is the name, with any trailing digits
        # removed (necessary because there are more than one of that type.)
        
        # Simple use of make_filter() is by passing in the ftype
        try:
            param_dict_or_ftype + ''
            ftype = param_dict_or_ftype
            param_dict = dict(ftype=ftype)
        except TypeError:
            param_dict = param_dict_or_ftype        
            # Search for filter in pypes directory first. This overrides any
            # programmatically defined filters/pipelines.
            
##            if param_dict.get('_name') in pypes:
            ftype_or_name = param_dict.get('ftype', param_dict.get('_name', ''))
            if ftype_or_name.startswith('pype_'):
##                ftype = param_dict['_name'][5:]
                ftype = ftype_or_name[5:]
                param_dict['ftype'] = ftype
                try:
                    filter_attrs = dict(_class=ppln.PipelineForPypes, 
                                        config=self.pypes[ftype])
                except KeyError:
                    msg = 'Filter type "%s" not found in the pypes directory'
                    raise dfb.FilterNameError, msg % ftype
            else:
                # Use explicit ftype setting in config if available.
                # Otherwise, try to read the filter type from the name.
                try:
                    ftype = param_dict['ftype']
                except KeyError:  
                    # Break up the name into parts separated by '_'. Strip off
                    # parts from the right-hand side, until we find a valid
                    # ftype.
                    short_name = fut.strip_number_suffix(param_dict['_name'])
                    name_parts = short_name.split('_')
                    for j in xrange(len(name_parts), 0, -1):
                        ftype = '_'.join(name_parts[:j])
                        if ftype in self.factory_dict:
                            break
                    else:
                        ### Last chance before giving up -- is it in pypes?
                        ##if param_dict['name'] in pypes:
                            ##ftype = param_dict['name']
                        ##else:
                        # We can't get the type from the name
                        msg = 'Can\'t get filter type from "%s"'
                        raise dfb.FilterError, msg % param_dict['_name']
                    param_dict['ftype'] = ftype
                try:
                    filter_attrs = copy.copy(self.factory_dict[ftype])
                except KeyError:
                    # Make a pipeline with this config.
                    try:
                        filter_attrs = dict(_class=ppln.PipelineForPypes, 
                                            config=self.pypes[ftype])
                    except KeyError:
                        msg = 'Filter type "%s" not found in the filter ' + \
                              'factory class map dictionary'
                        raise dfb.FilterNameError, msg % ftype
        # !! If create_filter receives a string, the except clause isn't
        # executed so filter_attrs isn't defined.
        filter_attrs['factory'] = self
        filter_attrs['pipeline'] = pipeline
                        
        # Update the dictionary so far with the parameters passed in.
        filter_attrs.update(param_dict)
        # Everything is now in place for the actual creation of the filter
        class_to_create = filter_attrs['_class']
        
        # If the config for this filter has dynamic ==  True, use metaclass
##        if filter_attrs.get('dynamic', False) == 'meta':
        if filter_attrs.get('dynamic', False):
            class_to_create2 = dfb.DynamicMetaClass(
                'DynMeta' + class_to_create.__name__,
                (class_to_create,), {})
        else:
            class_to_create2 = class_to_create        
        
        new_filter = class_to_create2(**filter_attrs)
        # Filter has now been made
        
        # Reversible dynamic approach doesn't work.
        ### If config file for filter has set 'dynamic', use reversible method
        ### to make it dynamic. Note the need to test equality with True, because
        ### of the option for the value to be 'meta'.
        ##if filter_attrs.get('dynamic', False) == True:
            ##new_filter.make_dynamic(True)
        
        if new_filter.name != new_filter.name.lower():
            raise dfb.FilterError, 'Filter name "%s" is not lower case' % (
                                                              new_filter.name)
        # Check the ftype made matches the request
        try:
            type_made = new_filter.__class__.ftype  # OK for filter
        except AttributeError:
            type_made = new_filter.ftype    # For pipeline
        # TO-DO Replace ftype check, which fails when making external pype:
        # e.g. 'align_supf' != 'p0001_align_supf'
        # Bad overloading of ftype.
        #if type_made != ftype:
            #msg = 'Filter type requested was "%s", but "%s" was made'
            #raise dfb.FilterAttributeError, msg % (ftype, 
                                                   #new_filter.__class__.ftype)
        return new_filter


class DemoFilterFactory(FilterFactory):
    """Make filters for the test spike"""

    abstract_class = False

    def __init__(self):
        FilterFactory.__init__(self)
        # Create basic class links
        class_map = dict(
            capitalise         = dfd.Capitalise,
            factorial_calc     = dfd.FactorialCalc,
            inner_bar          = ppln_demo.InnerBar,
            mult_if_int        = dfd.MultiplyIfInteger,
            reverse_string     = dfd.ReverseString,
            square_if_number   = dfd.SquareIfNumber,
            temp_multiple_ab   = ppln_demo.TempMultipleAB,
            temp_space         = dfd.TempSpace,
            temp_text_after    = dfd.TempTextAfter,
            temp_text_before   = dfd.TempTextBefore,
            copyfile_compress  = ppln.CopyFileCompression,
            key_substitutions       = dfd.KeySubstitutions,
            
        )
        self._apply_class_map(class_map)
        
###class DemoFilterFactory1(DemoFilterFactory):
    ###"""Concrete class with more detail for the factory method.

       ###Here the DemoFilterFactory has its dictionary updated with
       ###new keys whose values vary more often than those defined there."""

    ###abstract_class = False

    ###def __init__(self):
        ###DemoFilterFactory.__init__(self)
        #### Set default values for each class that needs them
        ###self.factory_dict['mult_if_int'].update(dict(
            ###multiply_by = 2,
        ###))
        ###self.factory_dict['batch'].update(dict(
            ###size = 3,
        ###))
