# -*- coding: utf-8 -*-
# lex_yacc4_test.py

# Licence
#
# FilterPype is a process-flow pipes-and-filters Python framework.
# Copyright (c) 2009-2011 Flight Data Services Ltd
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

import filterpype.lex_yacc4
import filterpype.filter_utils as fut

def setUp():
    pass
    
def tearDown():
    pass

class TestLexYacc(unittest.TestCase):
    
    def setUp(self):
        # If debug is True, then prefixes are left on filters, so some 
        # tests will fail
        self.route_parser = filterpype.lex_yacc4.RouteParser(debug=False)
    
    def tearDown(self):
        pass
    
    def test_route01(self):
        route_in = '''\
A >>> 
    (B:34) 
# This is a comment
# It shouldn't matter how many comment lines there are.
C >>> 
# This can't be a trailing comment, which gives EOF error.
D
'''
        route_out, connections, fltrs = self.route_parser.parse_route(route_in)
        print '**2600** route =', route_out
        print '**2610** connections =', connections
        self.assertEquals(route_out, 'A hidden_branch_route_01 (B:34) C D')
        if connections:
            self.route_parser.print_connections(connections)
        self.assertEquals(connections, ['A >>> hidden_branch_route_01', 
                                        'hidden_branch_route_01 ^^^ B:34', 
                                        'hidden_branch_route_01 >>> C', 
                                        'B:34 >>> None', 
                                        'C >>> D',
                                        'D >>> None'])
        
    def test_route02(self):
        route_in = 'A:2 >>> (B >>> (C >>> D) E) F >>> (G >>> H) J'
        route_out, connections, fltrs = self.route_parser.parse_route(
            route_in, debug=0, tracking=True)
        print '**2601** route =', route_out
        print '**2611** connections =', connections
        self.assertEquals(route_out, 'A:2 hidden_branch_route_01 ' + \
                                     '(B hidden_branch_route_02 (C D) ' + \
                                     'E) F hidden_branch_route_03 (G H) J')
        if connections:
            self.route_parser.print_connections(connections)
        self.assertEquals(connections, ['A:2 >>> hidden_branch_route_01', 
                                        'hidden_branch_route_01 ^^^ B', 
                                        'hidden_branch_route_01 >>> F', 
                                        'B >>> hidden_branch_route_02', 
                                        'hidden_branch_route_02 ^^^ C', 
                                        'hidden_branch_route_02 >>> E', 
                                        'C >>> D', 
                                        'D >>> None', 
                                        'E >>> None', 
                                        'F >>> hidden_branch_route_03', 
                                        'hidden_branch_route_03 ^^^ G', 
                                        'hidden_branch_route_03 >>> J', 
                                        'G >>> H', 
                                        'H >>> None', 
                                        'J >>> None'])
        
    def test_route03(self):
        route_in = 'A >>> (B >>> C'
        self.assertRaises(SyntaxError, self.route_parser.parse_route,
                          route_in, debug=0, tracking=True)
        
    def test_route04(self):
        route_in = '(A >>> (B) C)'
        self.assertRaises(SyntaxError, self.route_parser.parse_route, route_in)
        
    def test_route05(self):
        route_in = 'A >>> () C'
        self.assertRaises(SyntaxError, self.route_parser.parse_route, route_in)
        
    def test_route06(self):
        route_in = 'A >>> (B) (C) D'
        self.assertRaises(SyntaxError, self.route_parser.parse_route, route_in)
        
    def test_route07(self):
        route_in = 'A >>> (B) E >>> C >>> D'
        route_out, connections, fltrs = self.route_parser.parse_route(route_in)
        self.assertEquals(route_out, 'A hidden_branch_route_01 (B) E C D')
        self.assertEquals(connections, ['A >>> hidden_branch_route_01', 
                                        'hidden_branch_route_01 ^^^ B', 
                                        'hidden_branch_route_01 >>> E', 
                                        'B >>> None', 
                                        'E >>> C', 
                                        'C >>> D', 
                                        'D >>> None'])
        print '**2230** result = %s\n' % route_out
        print_list = self.route_parser.pipeline_for_print(route_out)
        self.assertEquals(print_list, 
                          ['    A >>>', '    hidden_branch_route_01 >>>', 
                           '       (B)', '    E >>>', '    C >>>', '    D'])
        for line in print_list:
            print line

    def test_route08(self):
        route_in = '''\
A >>>
# This is a comment
B
'''
        route_out, connections, fltrs = self.route_parser.parse_route(route_in)
        self.assertEquals(route_out, 'A B')
        self.assertEquals(connections, ['A >>> B', 'B >>> None']) 
        
        print '**2220** result = %s\n' % route_out
        print_list = self.route_parser.pipeline_for_print(route_out)
        self.assertEquals(print_list, ['    A >>>', '    B'])
        for line in print_list:
            print line
        
    def test_route09(self):
        route_in = 'A $'  # Syntax error
        self.assertRaises(SyntaxError, self.route_parser.parse_route, route_in)
        
    def test_route10(self):
        route_in = 'A >>> (B)'  # End in branch
        self.assertRaises(SyntaxError, self.route_parser.parse_route, route_in)
##        self.route_parser.parse_route(route_in)
        
    def test_route11(self):
        route_in = '''\
abc >>> 
def:hello.world >>>
xyz
'''
        route_out, connections, fltrs = self.route_parser.parse_route(route_in)
        print '**2600** route =', route_out
        print '**2610** connections =', connections
        self.assertEquals(route_out, 'abc def:hello.world xyz')
        if connections:
            self.route_parser.print_connections(connections)
        self.assertEquals(connections, ['abc >>> def:hello.world', 
                                        'def:hello.world >>> xyz', 
                                        'xyz >>> None'])

    def test_route12(self):
        route_in = 'A///'  # Illegal chars
        self.assertRaises(SyntaxError, self.route_parser.parse_route, route_in)

    def test_route13(self):
        route_in = '''\
A >>>
# Embedded comment
B
# This is a trailing comment
'''
        route_out, connections, fltrs = self.route_parser.parse_route(route_in)
        self.assertEquals(route_out, 'A B')

    def test_route14(self):
        route_in = 'A >>> (B >>> (C >>> D))'  # End in branch
        self.assertRaises(SyntaxError, self.route_parser.parse_route, route_in)
    
    def test_route15(self):
        route_in = 'A >>> B' 
        route_out, connections, fltrs = self.route_parser.parse_route(route_in)
        self.assertEquals(connections, ['A >>> B', 
                                        'B >>> None'])
    
    def test_route16(self):
        route_in = 'A >>> (B) C' 
        route_out, connections, fltrs = self.route_parser.parse_route(route_in)
        self.assertEquals(connections, ['A >>> hidden_branch_route_01', 
                                        'hidden_branch_route_01 ^^^ B', 
                                        'hidden_branch_route_01 >>> C', 
                                        'B >>> None', 'C >>> None'])
    
if __name__ == '__main__':  #pragma: nocover
    TestLexYacc('test_route16').run()
    print '\n**3010** Finished.'
    
