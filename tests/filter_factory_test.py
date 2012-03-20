# -*- coding: utf-8 -*-

import StringIO
import unittest 
##from configobj import ConfigObj

import filterpype.filter_factory as ff

import filterpype.data_filter as df


class TestMakeFactory(unittest.TestCase):
    
    def test_make_factory_which_is_abstract(self):
        self.assertRaises(NotImplementedError, ff.FilterFactory)
