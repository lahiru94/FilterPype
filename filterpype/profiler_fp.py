# -*- coding: utf-8 -*-
# profiler_fp.py

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


"""
Notes from profiler.py:

To see where slowdowns are in your Python programs, Python provides some
low-level hooks (sys.settrace) and modules to evaluate timings (profile and
its faster cousin cProfile and hotshot).

 * cProfile was added in Python 2.5 after much discussion about the downsides of
   existing profilers.
 * hotshot does not time C calls. If your code does a lot of work with built-in
   methods, like sorting lists, hotshot won't report it.

It's pretty easy to run these on your whole program. On Ubuntu make sure you
install python-profiler.

Slightly modified from the originals so the stats are displayed from within the
decorators, rather than requiring seperate execution.

It is recommended you use the 'complete' decorator (which use cProfile) in
preference to the 'partial' decorator (which uses hotshot).

References
 - http://timhatch.com/ark/2008/07/20/a-good-profiling-decorator
 - http://blog.brianbeck.com/post/22199891/the-state-of-python-profilers-in-two-words
 - http://blog.doughellmann.com/2008/08/pymotw-profile-cprofile-pstats.html
 - http://www.biais.org/blog/index.php/2007/01/20/18-python-profiling-decorator
"""

try:
    import cProfile as profile
except ImportError:  #pragma: nocover
    import profile

import os.path
import hotshot
import hotshot.stats
import pstats
import marshal
import time
import copy

__all__ = ['profiled']


class FilterPypeStats(pstats.Stats):  #pragma: nocover
    """Main reason for doing this module:
       Shorten file name in output to remove long directory names. 
    """
    def _shorten_file_name_keys(self):
        # self.stats has long file names in it
        for key, item in self.long_stats.iteritems():
            short_name = os.path.basename(key[0])
            key012 = (short_name, key[1], key[2])
            self.stats[key012] = item
    
    def load_stats(self, arg):  #pragma: nocover
        if not arg:  
            self.stats = {}
        elif isinstance(arg, basestring):
            f = open(arg, 'rb')
            self.long_stats = marshal.load(f)
            self._shorten_file_name_keys()
            f.close()
            # Can't get nocover to work, here, so get rid of unqualified
            # exception. Supposedly this will fail on Windows
            ##try:
                ##file_stats = os.stat(arg)
                ##arg = time.ctime(file_stats.st_mtime) + "    " + arg
            ### in case this is not unix
            ##except:  #pragma: nocover 
                ##pass  #pragma: nocover  
            file_stats = os.stat(arg)
            arg = time.ctime(file_stats.st_mtime) + "    " + arg
            self.files = [ arg ]
        elif hasattr(arg, 'create_stats'):
            arg.create_stats()
            self.stats = arg.stats
            arg.stats = {}
        if not self.stats:
            raise TypeError,  "Cannot create or construct a %r object from '%r''" % (
                              self.__class__, arg)
        return

    def print_call_heading(self, name_size, column_title):
        print >> self.stream, "Function ".ljust(name_size) + column_title
        # print sub-header only if we have new-style callers
        subheader = False
        for cc, nc, tt, ct, callers in self.stats.itervalues():
            if callers:
                value = callers.itervalues().next()
                subheader = isinstance(value, tuple)
                break
        if subheader:
            print >> self.stream, " "*name_size + "    ncalls  tottime  cumtime"

    def print_call_line(self, name_size, source, call_dict, arrow="->"):
        print >> self.stream, func_std_string(source).ljust(name_size) + arrow,
        if not call_dict:
            print >> self.stream
            return
        clist = call_dict.keys()
        clist.sort()
        indent = ""
        for func in clist:
            name = func_std_string(func)
            value = call_dict[func]
            if isinstance(value, tuple):
                nc, cc, tt, ct = value
                if nc != cc:
                    substats = '%5d/%4d' % (nc, cc)
                else:
                    substats = '%10d' % (nc,)
                substats = '%s %s %s    %s' % (substats.rjust(7+2*len(indent)),
                                             f8(tt), f8(ct), name)
                left_width = name_size + 1
            else:
                substats = '%s(%r) %s' % (name, value, f8(self.stats[func][3]))
                left_width = name_size + 3
            print >> self.stream, indent*left_width + substats
            indent = " "

    def print_line(self, func):  # hack : should print percentages
        cc, nc, tt, ct, callers = self.stats[func]
        c = str(nc)
        if nc != cc:
            c = c + '/' + str(cc)
        print >> self.stream, c.rjust(12),   # Rob, was 9
        print >> self.stream, pstats.f8(tt),
        if nc == 0:
            print >> self.stream, ' '*8,
        else:
            print >> self.stream, pstats.f8(tt/nc),
        print >> self.stream, pstats.f8(ct),
        if cc == 0:
            print >> self.stream, ' '*8,
        else:
            print >> self.stream, pstats.f8(ct/cc),
        print >> self.stream, '  ' + pstats.func_std_string(func)

    def print_title(self):
        print >> self.stream, '      ncalls  tottime  percall  cumtime  percall',
        print >> self.stream, '  filename:lineno(function)\n'

    def print_stats(self, *amount):
        for filename in self.files:
            print >> self.stream, filename
        if self.files: print >> self.stream
        indent = ' ' * 8
        for func in self.top_level:
            print >> self.stream, indent, func_get_function_name(func)

        print >> self.stream, indent, self.total_calls, "function calls",
        if self.total_calls != self.prim_calls:
            print >> self.stream, "(%d primitive calls)" % self.prim_calls,
        print >> self.stream, "in %.3f CPU seconds" % self.total_tt
        print >> self.stream
        width, list = self.get_print_list(amount)
        if list:
            self.print_title()
            for func in list:
                self.print_line(func)
            print >> self.stream
            print >> self.stream
        return self

    def sort_stats(self, *field):
        if not field:
            self.fcn_list = 0
            return self
        if len(field) == 1 and type(field[0]) == type(1):
            # Be compatible with old profiler
            field = [ {-1: "stdname",
                      0:"calls",
                      1:"time",
                      2: "cumulative" }  [ field[0] ] ]

        sort_arg_defs = self.get_sort_arg_defs()
        sort_tuple = ()
        self.sort_type = ""
        connector = ""
        for word in field:
            sort_tuple = sort_tuple + sort_arg_defs[word][0]
            self.sort_type += connector + sort_arg_defs[word][1]
            connector = ", "

        stats_list = []
        for func, (cc, nc, tt, ct, callers) in self.stats.iteritems():
            stats_list.append((cc, nc, tt, ct) + func +
                              (pstats.func_std_string(func), func))

        stats_list.sort(pstats.TupleComp(sort_tuple).compare)

        self.fcn_list = fcn_list = []
        counter = 0
        for tup in stats_list:
            counter += 1
            filnam, line, fn = tup[-1]
            new_tup = (filnam, line, fn)
            fcn_list.append(new_tup)
        return self

    
def complete(lines):  #pragma: nocover
    """
    Decorator to allow individual functions to be profiled, without profiling
    the whole program.  This allows for much more targeted profiling, which is
    necessary for threaded programs or if performance becomes an issue.

    lines: Number of lines to display in the profiler stats.

    multi: if True, adds a sequential number to each profile run to prevent
                    name collisions.
           if False, the last invocation wins.
    """
    # This extra layer of indirection is so the decorator can accept arguments
    # When the user doesn't provide arguments, the first arg is the function,
    # so detect that and show an error.
 
    def decorator(func):
        def newfunc(*args, **kwargs):
            prof = profile.Profile()
            result = prof.runcall(func, *args, **kwargs)
            filename = 'temp_profile.dat'
            prof.dump_stats(filename)
            FilterPypeStats(filename).sort_stats("time").print_stats(lines)
            return result
        # Be well-behaved
        newfunc.__name__ = func.__name__
        newfunc.__doc__ = func.__doc__
        newfunc.__dict__.update(func.__dict__)
        return newfunc
    return decorator

profiler = complete

def partial(lines=30):  #pragma: nocover
    """
    Simple profiler decorator using hotshot profiler and timeit modules from
    the standard library.

    lines: Number of lines to display in the profiler stats.
    """
    def decorator(func):
        def newfunc(*args, **kwargs):
            pr = hotshot.Profile("profiling.data")
            ret = pr.runcall(func, *args, **kwargs)
            pr.close()
            stats = hotshot.stats.load("profiling.data")
            stats.strip_dirs()
            stats.sort_stats('time')
            stats.print_stats(lines)
            return ret
        return newfunc
    return decorator


import hotshot, hotshot.stats
 
def profileit(printlines=20):  #pragma: nocover
    def _my(func):
        def _func(*args, **kargs):
            prof = hotshot.Profile("profiling.data")
            res = prof.runcall(func, *args, **kargs)
            prof.close()
            stats = hotshot.stats.load("profiling.data")
            stats.strip_dirs()
            stats.sort_stats('time', 'calls')
            print ">>>99---- Begin profiling print"
            stats.print_stats(printlines)
            print ">>>---- End profiling print"
            return res
        return _func
    return _my
