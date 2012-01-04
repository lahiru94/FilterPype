# -*- coding: utf-8 -*-
# lex_yacc5.py

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


"""Tokenises and parses the route part of a filter config in a pipeline.
   
Remember to delete lextab.py/.pyc and parsetab.py/.pyc if anything changes,
otherwise the previous version will be used.
"""

# TO-DO Change "hidden_branch_route" to "hidden_brancher"
# TO-DO Make ">" a white space character, so it doesn't matter if it's there
#       or not. Eventually make it illegal char.
# To-DO Change the syntax to allow the perfectly sensible "A (B)" missing a
#       trailing filter.
import sys
import os
import ply.lex as lex
import ply.yacc as yacc
from ply.lex import TOKEN

import filterpype.filter_utils as fut

parser_dir = os.path.join(fut.abs_dir_of_file(__file__), 'parser')
# Format temporary filter label as %4.4d for a maximum of 10**(n-1) filters
k_label_sep = '~'
k_filter_format = '%4.4d' + k_label_sep + '%s'
k_fork_filter_format = '%4.4d' + k_label_sep + 'hidden_brancher_%2.2d'


route1 = '''
A B C
'''
route2 = '''
A (B) C
'''

route3 = '''

A1 A2 A3 (B x y z) C D (E F G) H J (K) L M

'''

route4 = '''
(
A1 A2 A3 (B) C D (E F (P Q R S T) G) H J (K) L M
)
'''

route5 = '''
(
A1 A2 A3 (B C D (E F G) H J (K) L M
)
'''

route6 = '''
A B C (D (E F) G H) J K
'''

route66 = '''
strip_file_header 
       (write_file_header) 
split_superframes
strip_superframe_header ( write_superframe_headers )
split_frames (dtetyrert)
strip_frame_header ( write_frame_headers )
split_subframes
write_subframes
'''

class RouteParser(object):
    """Parse the pipeline route, defined by a list of filters, with embedded
    parentheses.
    """
    # If any of these are changed, remember to remove lextab.py/c and
    # parsetab.py/c from main and tests directories, otherwise the old code
    # will continue to run.
    digit = r'([0-9])'
    nondigit = r'([_A-Za-z\.\:\-\$\{\}])'  
    identifier = r'(' + nondigit + r'(' + digit + r'|' + nondigit + r')*)' 
    comment = r'(\#).*'
    
    tokens = (
        'FILTER',
        'LPAREN',
        'RPAREN',
##        'BRANCH_OFF_MAIN',
##        'BRANCH_NO_MAIN',
##        'JOINTO',
    )

    t_LPAREN  = r'\('
    t_RPAREN  = r'\)'
##    t_JOINTO = r'>>>'
##    t_COMMENT = comment
    
    # A string containing ignored characters (spaces and tabs)
    t_ignore  = ' \t'

    def __init__(self, debug=False):
        self.debug = debug
        # Build the lexer, ready for later running Python with optimisation on
        self.lexer = lex.lex(object=self, debug=1, optimize=1,
                             outputdir=parser_dir)
        # Build the parser, ready for later running Python with optimisation on
        self.parser = yacc.yacc(
            module=self, debug=1, optimize=1, outputdir=parser_dir,
            write_tables=0, # Force rewrite of parse tables while debugging
            debugfile=os.path.join(parser_dir, 'parser.out'))   
        self.fork_stack = []
        self.filter_dict = {}
##        print '**3710** RouteParser self.__init__()', self
        
    def _connect_pipes(self, pipe1, pipe2, rule='', type1='main'):
        print '**10420** %s connect %s: pipe1 = "%s", pipe2 = "%s"' % (
            rule, type1, pipe1, pipe2)
##        filters1 = [x.strip('()') for x in pipe1.split()]
        filters1 = [x for x in pipe1.split()]
        # Error here <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<QQQQQQQQQ
##        if filters1[0].startswith('hidden_brancher_'):
##            # Choose the first filter which is to connect to next main
##            filter_from = filters1[0]
##        if self.fork_stack:  # We've just had a branch
##            filter_from = self.fork_stack.pop()
##        else:
        
        # Choose the last filter; we're appending to a pipe
        filter_from = filters1[-1]
        if filter_from.endswith(')'):
            pass
        
        try:
            filters2 = [x.strip('()') for x in pipe2.split()]
            filter_to = filters2[0]
        except AttributeError:
            filter_to = None
        if type1 == 'main':
            connect_as = '>>>'  # 'next_filter'
        else:
            # Decrement label to sort branch before main
            label, name = filter_from.split(k_label_sep)
            filter_from = k_filter_format % (int(label) - 1, name)
            connect_as = '^^^'  #'branch_filter'
        conn_key = ' '.join([filter_from, connect_as])
        conn_value = filter_to
        connection_str = '%s %s %s' % (filter_from, connect_as, filter_to)
        print '**10530** connection_str = "%s"' % connection_str
##        self.connections.append(connection_str)
        self.connection_dict[conn_key] = conn_value

    def _end_branch(self, prev_filter, starting_fork, filters_in_branch):
        # Connect the starting fork to the first filter in the branch,
        # and the last filter in the branch to None.
        
        txt1 = 'Ending a branch = "%s", with prev_filter "%s"' + \
               ' and starting fork = %s'
        print '**12210** ' + txt1  % (filters_in_branch, prev_filter,
                                     starting_fork)
        if starting_fork:
            # Connect the previous filter to the starting fork 
            self._connect_pipes(prev_filter, starting_fork, 
                                'end_branch_1', 'main')
            # Connect the starting fork to the first filter in the branch
            self._connect_pipes(starting_fork, filters_in_branch.split()[0], 
                                'end_branch_2', 'branch')
            # In case there's nothing following, connect the main branch of
            # the starting fork to None.
            self._connect_pipes(starting_fork, None, 'end_branch_3', 'main')
        # Connect the last branch filter to None, since that's the end.
        ##if self.fork_stack:
####            filter_from = self.fork_stack.pop()
            ##filter_from = self.fork_stack[-1]  # Don't pop it <<<< TO-DO
        ##else:
        filter_from = filters_in_branch.split()[-1]
        self._connect_pipes(filter_from, None, 'end_branch_4', 'main')
        
    def pipeline_for_print(self, prefixed_route):
        result = []
        indent = 0
        base_indent = 4
        for x in prefixed_route.split():
            txt = x
            while '(' in txt:
                indent += base_indent
                txt = txt.replace('(', '$$OPEN$$', 1)
            new_indent = indent
            while ')' in txt:
                new_indent -= base_indent
                txt = txt.replace(')', '$$CLOSE$$', 1)
            txt = txt.replace('$$OPEN$$', '(')
            txt = txt.replace('$$CLOSE$$', ')')
            if not txt.endswith(')'):
                txt += ' >>>'
            if indent > 0 and txt.startswith('('):
                extra_in = base_indent - 1
            else:
                extra_in = base_indent
            result.append(' ' * (indent + extra_in) + \
                          fut.strip_prefix(txt, k_label_sep))
            indent = new_indent
        # Route can't end in a branch, so last line has spurious trailing '>>>'
        result[-1] = result[-1][:-4]
        return result
            
    def print_connections(self, connections, route_in=''):
        if route_in:
            route_in = '  "%s"' % route_in
        else:
            route_in = 'pipeline'
        print '\nConnections for %s' % route_in
        print 30 * '-'
        # Remove prefixes
        for connection in connections:
            if connection.startswith('hidden_brancher_'):
                connection = ' ' * 6 + connection
            print connection
        print 30 * '-'
        
    def _start_branch(self, prev_pipe):
        self.branch_counter += 1
        prev_filter = prev_pipe.split()[-1]
        # Split off the four-digit label from the filter; add 5 to value
        # e.g. 0010~some_filter  -->  15
        prefix = int(prev_filter.split(k_label_sep)[0]) + 5
        # Generate fork_filter name, e.g. 0015~hidden_brancher_01
        fork_filter = k_fork_filter_format % (prefix, self.branch_counter)
        print '**10440** _start_branch, fork_filter = "%s"' % fork_filter
        return fork_filter
        
##    def parse_route(self, route_in, debug=False, tracking=False): 
    def parse_route(self, route_in, debug=1, tracking=False): 
##        self.connections = []
        self.connection_dict = {}
        self.filter_dict = {}
        self.token_counter = 0
        self.filter_counter = 0
        self.branch_counter = 0
        route2 = route_in.strip()
        if not route2:  # No input to parse
            return None, None, None
        # Make input into a branch, to simplify start/end handling. Therefore
        # it must not already start or end with parentheses. The newline is
        # needed before the final parenthesis to allow a trailing comment,
        # which would otherwise hide it, giving an "Unexpected end of file"
        # syntax error.
##        wrapped_route = '$$$start$$$(%s\n)' % route2
        wrapped_route = route2
##        print '**10490** Parsing "%s"' % wrapped_route.replace('\n', '...')
        print '**10490** Parsing "%s"' % wrapped_route
        route3 = self.parser.parse(wrapped_route, debug=debug, 
                                   tracking=tracking)
        print '\n**10430** route2 = "%s"' % route2
        print '**10470** route3 = "%s"' % route3
##        return None, None, None # <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<REMOVE
        if route3:
            ##route4 = route3.split('None ')[1]  # Remove leading None
            ##if not route4[0] == '(' or not route4[-1] == ')':
                ##raise SyntaxError, 'Bad parentheses in "%s"' % route4
            ##route_with_prefixes = route4[1:-1]  # Remove outer parentheses
            route_with_prefixes = route3  # Remove outer parentheses
            route5 = fut.strip_prefixes(route_with_prefixes,
                                        prefix_regex=r'\d\d\d\d' + k_label_sep)
##            self.connections.sort()
            connections1_iter = sorted(self.connection_dict.iteritems())
##            connections2_gen = (link.split() for link in self.connections)
            connections2_gen = (conn_key.split() + [filter_to]
                                for conn_key, filter_to in connections1_iter)
            connections3 = [self.remake_connection(*link2) 
                            for link2 in connections2_gen]
            ##filters_gen = (fut.strip_prefix(link.split()[0], k_label_sep) 
                           ##for link in self.connections)
            # Maintain the order
            ##filters = [filt for filt in set(filters_gen)]
            filter_names = []
##            for filt in filters_gen:
            for filt in sorted(self.connection_dict.iterkeys()):
                if filt not in filter_names:
                    filter_names.append(filt)
            return route5, connections3, filter_names
        else:
            return None, None, None
    
    def p_error(self, p): 
        """Error rule for syntax errors"""
        if p:
            err_msg = '***** Syntax error in pipeline, reading %s token ' + \
                      '"%s" in line %d, counting %d chars from the start.'
            err_msg2 = err_msg % (p.type, p.value, p.lineno, p.lexpos + 1)
            sys.stdout.write(err_msg2 + '\n')
        else:
            err_msg2 = 'Unexpected end of file'
        raise SyntaxError, err_msg2
        
#==============================================================

    TEST_ROUTE = [
        'A B',
        'A (B) C',
        'A (D) B C',
        'A (B (C D) B2) E',
##        'A (B) B A',
##        '(A) B',
        'A B (C D) P (E) F G',
##        'a (%n) c',
##        'a 1 b',
##?        '#a b',
        '',
        '''\
A >>>
B >>>
# This is a comment
( DDD EEE FFF)
C ; Here is another comment
D 
''',
##       'A A',
##       'A B a',
##       'A (B) a',
    ]
    
    
    TEST_ROUTE = ['''\
    
##    A X (B (C D) E) F G H
    B A 
      (C) 
    D 
      (E F (H) Q) 
    G I J
    
    ''']
##    start = 'branch'
    
    precedence = (
        ('right', 'SPUR_NO_FILTER'),
        ('right', 'SPUR_WITH_FILTER'),
        )
    
    def p_pipe1(self, p):
        "pipe : FILTER"
        p[0] = p[1]

    def p_pipe2(self, p):
        "pipe : pipe FILTER"
        ##if self.fork_stack:
            ##filter_from = self.fork_stack.pop()
        ##else:
        filter_from = p[1]
            
        self._connect_pipes(filter_from, p[2], 'pipe2')
        p[0] = ' '.join(p[1:])

    ##def p_pipe3(self, p):
        ##"pipe : spur"
        ##p[0] = p[1]

    def p_pipe4(self, p):
        "pipe : junction"
        p[0] = p[1]

    def p_spur(self, p):
        "spur : pipe LPAREN start_branch pipe RPAREN end_branch"
        # We need something that knows we have branch + pipe following.
        # start_branch and end_branch are placeholders that allow extra
        # operations to be carried out.
        ##p[0] = '%s (%s)' % (p[2], p[3])

        p[0] = '%s (%s)' % (p[1], p[4])

    ##def p_branch(self, p):
        ##"branch : LPAREN start_branch pipe RPAREN end_branch"
        ### We need something that knows we have branch + pipe following.
        ### start_branch and end_branch are placeholders that allow extra
        ### operations to be carried out.
        ####p[0] = '%s (%s)' % (p[2], p[3])
        ##print '**10540** yacc -- branch "([%s])"' % p[3]

        ##p[0] = '(%s)' % p[3]

    def p_junction(self, p):
        '''
        junction : spur           %prec SPUR_NO_FILTER
                 | spur FILTER    %prec SPUR_WITH_FILTER
        '''
        if len(p) == 2:
            print '**10500** yacc -- spur "[%s]"' % (p[1])
        elif len(p) == 3:
            print '**10510** yacc -- junc "[%s]+[%s]"' % (p[1], p[2])
        ##'''
        ##junction : FILTER branch
                 ##| FILTER branch FILTER
        ##'''
        
        ##if len(p) == 2:
            ##last_item = 'xxNonexx'
        ##elif len(p) == 3:
            ##last_item = p[2]
        ##print '**10540** yacc -- junc "[%s] [%s]"' % (p[1], last_item)

        p[0] = ' '.join(p[1:])

    ##def p_junction(self, p):
        ##"junction : pipe LPAREN start_branch pipe RPAREN end_branch FILTER"
        ### We need something that knows we have branch + pipe following.
        ### start_branch and end_branch are placeholders that allow extra
        ### operations to be carried out.
        ####p[0] = '%s (%s)' % (p[2], p[3])
        ##print '**10540** yacc -- junc "[%s] ([%s]) [%s]"' % (p[1], p[4], p[7])

        ##p[0] = '%s (%s) %s' % (p[1], p[4], p[7])

        ## Connect the FILTER to the fork created at the start of the branch
        #fork = self.fork_stack.pop()

    ##def p_junction(self, p):
        ##"junction : spur FILTER"
        ##p[0] = ' ++junc++ '.join(p[1:])

    ##def p_pipe4(self, p):
        ##"pipe : junction"
        ##p[0] = p[1]

    ##def p_pipe3(self, p):
        ##"pipe : pipe branch"
        ##p[0] = '++pbrch++'.join(p[1:])

    ##def p_pipe4(self, p):
        ##"pipe : pipe junction"
        ##p[0] = '++pjunc++'.join(p[1:])

    ##def p_branch(self, p):
        ##"branch : LPAREN pipe RPAREN"
        ##p[0] = '(%s)' % p[2]
        

    ##def p_pipe22(self, p):
        ##"pipe : pipe FILTER"
        ##p[0] = '+22+'.join(p[1:])

    ##def p_pipe27(self, p):
        ##"pipe : junctiona"
        ##p[0] = p[1]
        
    ##def p_pipe27(self, p):
        ##"pipe : junctionb"
        ##p[0] = p[1]

    ##def p_junction(self, p):
        ##"junction : spur FILTER" # %prec BRANCH_OFF_MAIN"
        ##p[0] = '++junc++'.join(p[1:])

    ##def p_spur(self, p):
        ##"spur : FILTER branch" # %prec BRANCH_NO_MAIN"
        ##p[0] = '++spur++'.join(p[1:])

    ##def p_pipe28(self, p):
        ##"pipe : junction"
        ##p[0] = p[1:]

    ##def p_pipe23(self, p):
        ##"pipe : pipe branch FILTER"
        ##p[0] = '+23+'.join(p[1:])

    ##def p_pipe24(self, p):
        ##"pipe : pipe branch"
        ##p[0] = '+24+'.join(p[1:])

#-------------------------------------------------------------------------
    
    ##def p_filter1(self, p):
        ##"filter : FILTER"
        ##print '**13191** yacc [filter:FILTER] found = %s' % p[1]
        ##p[0] = p[1]
        
    ####def p_filter2(self, p):
        ####"filter : branch"
        ####print '**13192** yacc [filter:branch] found = %s' % p[1]
        ####p[0] = p[1]
        
    ##def p_pipe1(self, p):
        ##"pipe : filter"
        ##print '**12191** yacc [pipe:filter] found = %s' % p[1]
        ##p[0] = p[1]

    ##def p_pipe7(self, p):
        ##"pipe : filter branch"
        ##p[0] = ' '.join(p[1:])
    
    ##def p_pipe8(self, p):
        ##"pipe : branch filter"
        ##p[0] = ' '.join(p[1:])
    

    ##def p_pipe2(self, p):
####        "pipe : pipe JOINTO FILTER"
####        "pipe : pipe FILTER"
        ##"pipe : pipe filter"
        ##the_pipe = ' '.join(p[1:])
####        the_pipe = p[1] + ' ' + p[3] 
        ##print '**12192** yacc [pipe:pipe+filter] found = %s' % '+++'.join(p[1:])
####        self._connect_pipes(p[1], p[3], 'pipe2')
        ##self._connect_pipes(p[1], p[2], 'pipe2')
        ##p[0] = the_pipe
        
#-------------------------------------------------------------------------

    ##def p_branch(self, p):
        ##"branch : LPAREN start_branch pipe RPAREN end_branch"
        ### start_branch and end_branch are placeholders that allow extra
        ### operations to be carried out.
        ##print '**12196** yacc [Branch pipe] found = (%s)' % p[3]
        ##p[0] = '%s (%s)' % (p[2], p[3])

    ##def p_pipe5(self, p):
        ##"pipe : branch"
####        the_pipe = ' '.join([p[1], p[2]])
        ##print '**2196** yacc: Pipe found = %s' % p[1]
####        self._connect_pipes(p[1], p[3], 'pipe4')
####        self._connect_pipes(p[1], p[2], 'pipe4')
####        p[0] = the_pipe
        ##p[0] = p[1]


    #def p_pipe3(self, p):
        #"pipe : pipe branch FILTER"
        #the_pipe = ' '.join(p[1:])
        #print '**2193** yacc: Pipe found = %s' % the_pipe
        #self._connect_pipes(p[1], p[2], 'pipe3_1')
        ## Connect the FILTER to the fork created at the start of the branch
        #fork = self.fork_stack.pop()
        #self._connect_pipes(fork, p[3], 'pipe3_2')
        #p[0] = the_pipe

    ##def p_pipe3(self, p):
####        "pipe : pipe JOINTO branch FILTER"
        ##"pipe : pipe branch FILTER"
        ### The trailing FILTER is necessary, to give "pipe" a main output as
        ### well as a branch. If this is not actually needed, end the pipeline
        ### with a no-op pass_through filter.
####        the_pipe = ' '.join([p[1], p[3], p[4]])
        ##the_pipe = ' '.join([p[1], p[2], p[3]])
####        print '**2194** yacc: Pipe found = %s' % the_pipe
####        self._connect_pipes(p[1], p[3], 'pipe3_1')
        ##self._connect_pipes(p[1], p[2], 'pipe3_1')
        ### Connect the FILTER to the fork created at the start of the branch
        ##fork = self.fork_stack.pop()
####        self._connect_pipes(fork, p[4], 'pipe3_2')
        ##self._connect_pipes(fork, p[3], 'pipe3_2')
        ##p[0] = the_pipe
    
    ##def p_pipe4(self, p):
####        "pipe : pipe JOINTO branch"
        ##"pipe : pipe branch"
        ### <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<
        ### ???? The trailing FILTER is necessary, to give "pipe" a main output as
        ### well as a branch. If this is not actually needed, end the pipeline
        ### with a no-op pass_through filter.
####        the_pipe = ' '.join([p[1], p[3]])
        ##the_pipe = ' '.join([p[1], p[2]])
        ##print '**2196** yacc: Pipe found = %s' % the_pipe
####        self._connect_pipes(p[1], p[3], 'pipe4')
        ##self._connect_pipes(p[1], p[2], 'pipe4')
        ##p[0] = the_pipe


    def p_end_branch(self, p):
        "end_branch :"
        # p[-1] is ')'
        # p[-2] gives all filters in branch, e.g. 0020~E 0030~F
        # p[-3] is 0015~hidden_brancher_01
        # p[-4] is '('
        # p[-5] is '>>>'
        # p[-6] is '0010~D'
        filters_in_branch = p[-2]
        starting_fork = p[-3]
        try:
            prev_filter = p[-5]
        except AttributeError:
            prev_filter = None
        self._end_branch(prev_filter, starting_fork, filters_in_branch)
        p[0] = 'end_branch'

    def p_start_branch(self, p):
        "start_branch :"
        try:
            ##print '**2930** p[0] =', p[0] 
            ##print '**2930** p[-1] =', p[-1] 
            ##print '**2930** p[-2] =', p[-2] 
            ##print '**2930** p[-3] =', p[-3] 
            
##            fork = self._start_branch(p[-3])
            # Either p[-3] gives an IndexError (start of pipeline) or it 
            # returns the previous filter name. 
            # p[-1] is '('
            # p[-2] is previous filter, with sorting prefix.
            fork = self._start_branch(p[-2])
            print '**10460** Appending to fork_stack', fork
            self.fork_stack.append(fork)
            p[0] = fork
        except IndexError: 
            p[0] = None  # 88
        except AttributeError: 
            p[0] = None  # 89
        
#==============================================================

    def remake_connection(self, *args):
        # Expecting three args, e.g. 'filt_from', '>>>', 'filt_to'
        if self.debug:
            return ' '.join(args)
        else:
            link_from = args[0]
            conn_type = args[1]
            link_to = args[2]
            return '%s %s %s' % (fut.strip_prefix(link_from, k_label_sep), 
                                 conn_type, 
                                 fut.strip_prefix(link_to, k_label_sep))

    @TOKEN(identifier)
    def t_FILTER(self, t):
        self.filter_dict[t.value.lower()] = t.value
        self.token_counter += 10
        ##print '**2160** lex: Found FILTER token "%s", %s' % (t.value, t)
        t.value = k_filter_format % (self.token_counter, t.value)
        return t 
    
    @TOKEN(comment)
    def t_COMMENT(self, t):
        ##print '**2165** lex: Found COMMENT token "%s", %s' % (t.value, t)
        return None

    def t_newline(self, t):
        # Define a rule so we can track line numbers
        r'\n+'
        t.lexer.lineno += len(t.value)
        
    # Error handling rule
    def t_error(self, t):
        err_msg = 'Illegal character "%s" in line %d of "%s"' % (
            t.value[0], t.lexer.lineno, '|'.join(t.value.splitlines()))
        print '*****', err_msg
        raise SyntaxError, err_msg
        # If we need to continue with lexing, use
        #     t.lexer.skip(1)

        
