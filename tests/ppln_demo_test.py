# -*- coding: utf-8 -*-

k_run_long_tests = True

import StringIO
import os
import sys
import unittest 
import time
import re
import pprint as pp

import filterpype.lex_yacc4
import filterpype.data_fltr_base as dfb
import filterpype.data_filter as df
import filterpype.pipeline as ppln
import filterpype.ppln_demo as ppln_demo
import filterpype.filter_factory as ff
import filterpype.filter_utils as fut
import filterpype.profiler_fp as prof

data_dir3 = '../test_data3'
data_dir4 = '../test_data4'

k_run_long_tests = True

def dir_fn3(fname):
    return os.path.join(data_dir3, fname)

def dir_fn4(fname):
    return os.path.join(data_dir4, fname)
data_dir5 = os.path.join(fut.abs_dir_of_file(__file__), 
                         'test_data', 'tst_data5')
data_dir_europython = os.path.join(fut.abs_dir_of_file(__file__), 
                         'test_data', 'europython')

file_in_name1 = dir_fn3('file_data1.dat')
file_out_name1 = dir_fn3('file_data1.out')
file_in_name2 = dir_fn3('file_data2.dat')
file_out_name2 = dir_fn3('file_data2.out')

def setUp():
##    print '**9440** calling setUp for ppln_demo_test.py'
    global full_input_file_name, full_output_file_name, test_data_file_name
    data_dir_demo = os.path.join(fut.abs_dir_of_file(__file__), 
                             'test_data', 'tst_data_demo')
    data_filename1 = 'whats_new_in_2.6.dat'
##    data_filename1 = 'moonfleet.txt'
    data_filename_out = 'whats_new_in_2.6.out'
##    data_filename_out = 'moonfleet.out'
    full_input_file_name = os.path.join(data_dir_demo, data_filename1)
    full_output_file_name = os.path.join(data_dir_demo, data_filename_out)
    ##f1 = open(test_data_file_name, 'wb')
    ##try:
        ##for j in xrange(4):
            ##f1.write(fut.hex_string_to_data('12 03 45 06 78 09 AB 0C'))
    ##finally:
        ##f1.close()
        
# Why isn't this being called by Nose?
module_setUp = setUp


class DummyOne(object):
    def __new__(cls, *args, **kwargs):
        if kwargs.get('factory'):
            return kwargs['factory'].make_dummy('one')
        else:
            return object.__new__(cls, *args, **kwargs)
        
    def __init__(self, *args, **kwargs):
        print 'DummyOne init'

class DummyTwo(object):
    def __new__(cls, *args, **kwargs):
        if kwargs.get('factory'):
            return kwargs['factory'].make_dummy('two')
        else:
            return object.__new__(cls, *args, **kwargs)
        
    def __init__(self, *args, **kwargs):
        print 'DummyTwo init'

        
class DummyFactory(object):
    def make_dummy(self, class_name):
        if class_name == 'one':
            return DummyOne()
        elif class_name == 'two':
            return DummyTwo()
        
def dummies():
    factry = DummyFactory()
    print '\n1', DummyOne(factory=factry)
    print '\n2', DummyTwo(factory=factry)
    print '\n3', factry.make_dummy('one')
    print '\n4', factry.make_dummy('two')
    
# This example comes from Graham Ellis:
# http://www.wellho.net/mouth/1146_-new-v-init-python-constructor-
#        alternatives-.html
class A(object):
    def __new__(cls, *args, **kwargs):
        print "one"
        print "A.__new__", args, kwargs
        return object.__new__(B, *args, **kwargs)
    def __init__(cls, *args, **kwargs):
        print "two"
        print "A.__init__", args, kwargs
        
class B(object):
    def __new__(cls, *args, **kwargs):
        print "three"
        print cls
        print B
        print "B.__new__", args, kwargs
        return object.__new__(cls, *args, **kwargs)
    def __init__(cls, *args, **kwargs):
        print "four"
        print "B.__init__", args, kwargs
        
class C(object):
    def __init__(cls, *args, **kwargs):
        print "five"
        print "C.__init__", args, kwargs
        
def abc():
    print C()
    print "====================="
    print A()
    print "====================="
    print B()

    
class TestFactorial(unittest.TestCase):
    """Experiment to see if we can loop recursively with filters.
       We can't: ValueError: generator already executing.
       Update: yes, we can!
    """
    def setUp(self):
        self.factory = ff.DemoFilterFactory()
        self.route_parser1 = filterpype.lex_yacc4.RouteParser(debug=False)
        
    def tearDown(self):
        pass

    def test_factorial(self):
        packet1 = dfb.DataPacket(x=6)
        packet2 = dfb.DataPacket(x=3)
        packet3 = dfb.DataPacket(x=4)
        
        factorial = ppln_demo.Factorial(factory=self.factory)
        factorial.send(packet1)
        factorial.send(packet2)
        factorial.send(packet3)
        factorial.shut_down()
        results_packet1 = factorial.getf('sink').results[0]
        self.assertEquals(results_packet1.x_factorial, 720)
        results_packet2 = factorial.getf('sink').results[1]
        self.assertEquals(results_packet2.x_factorial, 6)
        results_packet3 = factorial.getf('sink').results[2]
        self.assertEquals(results_packet3.x_factorial, 24)
        
    def test_factorial2(self):
        route_in = '''
        tank_queue >>>
        factorial_calc >>>
        branch_if:recurse >>>
            (tank_feed >>> tank_queue)
        sink
        '''
        route_out, connections, fltrs = self.route_parser1.parse_route(
            route_in, debug=0, tracking=True)
        print '**2601** route =', route_out
        print '**2611** connections =', connections
        if connections:
            self.route_parser1.print_connections(connections)


        
class TestHiawatha(unittest.TestCase):
    """Count the paragraphs and sentences in "Hiawatha"
    """
    def setUp(self):
        self.factory = ff.DemoFilterFactory()
        module_setUp()
        
    def tearDown(self):
        pass
    
    def make_padded_data(self):
        poem_file_name = os.path.join(data_dir_europython, 
                                      'hiawatha.txt')
        f1 = open(poem_file_name)
        try:
            for line in f1.readlines():
                print line.rstrip()
            while False:
                chars = f1.read(100)
                if not chars:
                    break
                print chars,
            
        finally:
            f1.close()
                    

#=================================================================

class TestOuterFooInnerBar(unittest.TestCase):
    
    def setUp(self):
        self.factory = ff.DemoFilterFactory()
    
    def tearDown(self):
        pass
    
    def test_01(self):
        ##inner_bar = ppln_demo.InnerBar(factory=self.factory,
                                       ##temperature=15,
                                       ##speed=95)
        small_pipe_baz = ppln_demo.SmallPipeBaz(factory=self.factory,
                                                temperature=15, speed=95)
        print '\n**14420**', 60 * '-'
        print '\n'.join(small_pipe_baz.module_loc._python_code_lines)
        print '**14420**', 60 * '-'
        
        packet1 = dfb.DataPacket('hello')
        small_pipe_baz.send(packet1)
        
        new_temp = 34
        print '\n**14460** Changing temperature from %d to %d' % (
            small_pipe_baz.temperature, new_temp)
        small_pipe_baz.temperature = new_temp
        packet2 = dfb.DataPacket('and')
        small_pipe_baz.send(packet2)
        
        new_speed = 700
        print '\n**14470** Changing speed from %d to %d' % (
            small_pipe_baz.speed, new_speed)
        small_pipe_baz.speed = new_speed
        packet3 = dfb.DataPacket('goodbye')
        small_pipe_baz.send(packet3)

        new_SPEED = 20
        print '\n**14495** Changing SPEED from %s to %s' % (
            small_pipe_baz.emb_module.SPEED, new_SPEED)
        small_pipe_baz.emb_module.SPEED = new_SPEED
        packet4 = dfb.DataPacket('world')
        small_pipe_baz.send(packet4)
        
        small_pipe_baz.shut_down()
        
#=================================================================
        

class TrivialPython(ppln.Pipeline):

    config = '''\
    [--main--]
    ftype = testing_update_live
    description = Reading live data from Python module
    keys = foo, bar, baz:20
    update_live = foo:FOO, bar:BAR_17, baz:BAZ
        
    [py_trivial]
    x = 3
    
    [--route--]
    py_trivial >>>
    sink
    '''


class TestSimpleLoop(unittest.TestCase):
    """Go round a loop five time printing the packet number
    """
    def setUp(self):
        self.factory = ff.DemoFilterFactory()
        
    def tearDown(self):
        pass
    
    def test_simple_loop(self):
        simple_loop = ppln_demo.SimpleLoop

    
##class TestCopyFile(unittest.TestCase):
    ##"""Read file and write it straight out with no processing in between.
    ##"""
    ##def setUp(self):
        ##self.factory = ff.DemoFilterFactory()
        ##self.file_name2 = os.path.join(data_dir5, 'short2.dat')
        ##self.file_name_out = os.path.join(data_dir5, 'short2.out')
        ##f2 = open(self.file_name2, 'wb')
        ##try:
            ##f2.write('one two three four five six')
        ##finally:
            ##f2.close()
        
    ##def tearDown(self):
        ##pass
    
    ##def test_copy_file1(self):
        ##pipeline8 = ppln.CopyFile(factory=self.factory, 
                                       ##file_from_name=file_in_name1,
                                       ##file_to_name=file_out_name1)

####        pipeline8.pump_data()
        ##assert 45 == 45
    
    ##def test_copy_file2(self):
        ##return # <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<
        ##file_copier = ppln.CopyFile(factory=self.factory, 
                                         ##file_from_name=self.file_name2,
                                         ##file_to_name=self.file_name_out)
        ##file_copier.pump_data()
        ##file_copier.close()
        ##assert 2 == 5
            

class TestSquareNumber(unittest.TestCase):
    
    def setUp(self):       
        self.factory = ff.DemoFilterFactory()
    
    def tearDown(self):
        pass
    
    def test_square_number(self):
        square_no1 = ppln_demo.SquareNumber(factory=self.factory)
        self.assertEquals(square_no1.pump_data(3), 9)
        self.assertEquals(square_no1.pump_data(-2.5), 6.25)
        self.assertEquals(square_no1.pump_data('5'), 25)
        self.assertEquals(square_no1.pump_data('qwerty'), 'qwerty')
        self.assertEquals(square_no1(3), 9)
    
    def test_square_number_with_call(self):    
        square_no2 = ppln_demo.SquareNumber(factory=self.factory)
        self.assertEquals(square_no2(4), 16)
        
    def test_square_number_lists(self):
        pipeline71 = ppln_demo.SquareNumber(factory=self.factory)
        self.assertEquals(pipeline71.pump_data([3]), 9)
        self.assertEquals(pipeline71.pump_data([2, 3, 4]), [4, 9, 16])
        self.assertEquals(pipeline71.pump_data(['5']), 25)
        self.assertEquals(pipeline71.pump_data(['qwerty']), 'qwerty')
##        self.assertEquals(pipeline71.last_sink, pipeline71.last_filter)

        self.assertEquals(pipeline71([3]), 9.0)
        square_no = ppln_demo.SquareNumber(factory=self.factory)
        self.assertEquals(square_no([4, -3]), [16, 9])
        
        
class TestTempMultipleAB(unittest.TestCase):
    
    def setUp(self):       
        self.factory = ff.DemoFilterFactory()
    
    def tearDown(self):
        pass
    
    def test_multiple_ab(self):
        pipeline72 = ppln_demo.TempMultipleAB(factory=self.factory,
                                              a1='one', a2='two', 
                                              b1='three', b2='four')
        self.assertEquals(pipeline72('hello'), 'owtthreehellooneruof')

        
class TestTempMultipleSpace(unittest.TestCase):
    
    def setUp(self):       
        self.factory = ff.DemoFilterFactory()
    
    def tearDown(self):
        pass
    
    def test_multiple_space(self):
        return # Redefine pump_data functionality TO-DO <<<<<<<<<<<<<<<<<<<<<<<<<<<
        pipeline73 = ppln_demo.TempMultipleSpace(factory=self.factory,
                                                 a1='one', a2='two', 
                                                 b1='three', b2='four')
        self.assertEquals(pipeline73('hello'),
                          'o w t t h r e e h e l l o o n e r u o f')

        
class TestVariableBatch(unittest.TestCase):
    
    def setUp(self):       
        self.factory = ff.DemoFilterFactory()
    
    def tearDown(self):
        pass
  
    def test_variable_batch1(self):
        # Using Python embedded environment, change batch size from 1 to 6
        config = '''\
        [--main--]  
        ftype = variable_batch
        description = Test variable batch passing
    
        [py_init_batch_size]
        BATCH_SIZE = 1
        
        [py_set_batch_size]
        BATCH_SIZE += 1
        
        [batch]
        dynamic = true
        
        [--route--]
        py_init_batch_size >>>
        batch:%BATCH_SIZE >>>
        py_set_batch_size >>>
        sink
        '''
        ppln1 = ppln.Pipeline(factory=self.factory, config=config)
        source = 'Iamnotveryquickeating'
        packet1 = dfb.DataPacket(source)
        ppln1.send(packet1)
        ppln1.shut_down()
        print '**13120** results = ', '|'.join(ppln1.getf('sink').all_data)
        self.assertEquals('|'.join(ppln1.getf('sink').all_data),
                          'I|am|not|very|quick|eating')
        print '**13150** finished test_variable_batch1'
        
    def test_variable_batch2(self):
        # Using Python embedded environment, read batch size from data
        config = '''\
        [--main--]  
        ftype = variable_batch
        description = Test variable batch passing
        ##dynamic = true
    
        [py_init_batch_size]
        BATCH_SIZE = 2
        READING_SIZE = True
        
        [py_read_batch_size]
        if READING_SIZE:
            BATCH_SIZE = int(packet.data)
            READING_SIZE = False
            packet.fork_dest = 'branch'
        else:
            init_batch_size()
            
        [batch]
        dynamic = true
        size = %BATCH_SIZE
        
        [--route--]
        py_init_batch_size >>>
        #batch:%BATCH_SIZE >>>
        batch >>>
        py_read_batch_size >>>
        sink
        '''
        ppln2 = ppln.Pipeline(factory=self.factory, config=config)
        source = 'Mary had a little lamb; its fleece was white as snow.'
        source2 = ''.join(('%2.2d' % len(x) + x) for x in source.split())
        print '**13125** source2 =', source2
        packet2 = dfb.DataPacket(source2)
        ppln2.send(packet2)
        ppln2.shut_down()
        print '**13120** results = ', '|'.join(ppln2.getf('sink').all_data)
        self.assertEquals(' '.join(ppln2.getf('sink').all_data), source)
        print '**13150** finished test_variable_batch2'
          
        
class TestJane(unittest.TestCase):
    
    def setUp(self):       
        self.factory = ff.DemoFilterFactory()
    
    def tearDown(self):
        pass
    
    def test_jane_01(self):
        def print_hi():
            print '**16010** Hi'
            
        jane = ppln_demo.Jane()
        print '**16020** speed =', jane.speed
        freda_class = ppln_demo.Jane.__bases__[0]
        print '**16030** speed from Freda = %s' % (
            freda_class.__getattribute__(jane, 'speed'))
        jane.speed = 95
        print '**16040** speed from Freda = %s' % (
            freda_class.__getattribute__(jane, 'speed'))
        jane.zero = 0
        print '**16000** zero =', jane.zero
        jane.print_hi = print_hi
##        jane.print_hi()
        freda_class.__getattribute__(jane, 'print_hi')()
        
    
    def test_alison_01(self):
        def print_hi():
            print '**16010** Hi'
            
        alison = ppln_demo.Alison()
        alison.speed = 50
        print '**16050** alison.speed =', alison.speed
        alison.name = '%NAME'
        print '**16100** alison.name =', alison.name
##        def ga(self, attr_name):
##            print '**16060** ga, self=%s, attr_name=%s' % (self, attr_name)
##            return 'bill'
        alison.__class__.__getattribute__ = alison._hidden__getattribute__
        print '**16110** alison.speed =', alison.speed
        print '**16120** alison.name =', alison.name
        
        ##freda_class = ppln_demo.Jane.__bases__[0]
        ##print '**16030** speed from Freda = %s' % (
            ##freda_class.__getattribute__(jane, 'speed'))
        ##jane.speed = 95
        ##print '**16040** speed from Freda = %s' % (
            ##freda_class.__getattribute__(jane, 'speed'))
        ##jane.zero = 0
        ##print '**16000** zero =', jane.zero
        ##jane.print_hi = print_hi
####        jane.print_hi()
        ##freda_class.__getattribute__(jane, 'print_hi')()
        
    
    
class TestWordsInCaps(unittest.TestCase):
    
    def setUp(self):       
        self.factory = ff.DemoFilterFactory()
    
    def tearDown(self):
        pass
    
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    
    def test_subst_stage_1(self):
        # Make pipeline using optional default
        words_in_caps1 = ppln_demo.WordsInCaps(factory=self.factory)
        self.assertEquals(words_in_caps1.join_words_with, '~')
        # Make pipeline setting optional field in kwargs
        words_in_caps2 = ppln_demo.WordsInCaps(factory=self.factory, 
                                               join_words_with='+')
        self.assertEquals(words_in_caps2.join_words_with, '+')
        # Look inside pipeline to see how far the defaults have been passed in
        joiner = words_in_caps1.getf('join')
        
##        assert 78 == 89
    
    def test_caps_phrase(self):
        words_in_caps1 = ppln_demo.WordsInCaps(factory=self.factory)
        sink = df.Sink()
        words_in_caps1.next_filter = sink
        words_in_caps1.send(dfb.DataPacket('hello world'))
        self.assertEquals(sink.results, [])
##        output1 = words_in_caps1.pump_data('hello world')
##        self.assertEquals(output1, [])
##        words_in_caps1.shut_down()  # Flush joining data
##        words_in_caps1.shut_down()  # Flush joining data
        words_in_caps1.first_filter.shut_down()
        self.assertEquals(sink.results[-1].data, 'Hello~World')
        
        words_in_caps2 = ppln_demo.WordsInCaps(factory=self.factory, 
                                               join_words_with='+')
        sink2 = df.Sink()
        words_in_caps2.next_filter = sink2
        words_in_caps2.send(dfb.DataPacket('one    two three   four five'))
##        words_in_caps2.shut_down()
        words_in_caps2.first_filter.shut_down()
        self.assertEquals(sink2.results[-1].data, 'One+Two+Three+Four+Five')
##        assert 34 == 56


if __name__ == '__main__':  #pragma: nocover
    setUp()

##    TestSquareNumber('test_square_number').run()
##    TestFactorial('test_factorial').run()
##    TestReadNumberFrames('test_read_number_offset').run()
##    TestCopyFile('test_copy_file1').run()
##    TestTempMultipleAB('test_multiple_ab').run()
##    TestTempMultipleSpace('test_multiple_space').run() 
##    TestWordsInCaps('test_subst_stage_1').run()
##    TestWhatsNewIn26('test_analyse_whats_new').run()
#    TestHiawatha('make_padded_data').run()
##    TestEmbedPython('test_embedded_batch_sizing').run()
##    TestEmbedPython('test_embed_python').run()
    
    if False:
        re_python_key_sub = re.compile(r'\${\b([a-z][a-z0-9_]*)\b}')
        key_dict = dict(fred=17, jane='smart')
        text_in = 'wwwww  ${fred}  ${bill}  ${jane}  yyyyy  ${failsTOmatch}  ${}'
        text_out = text_in
        keys = re_python_key_sub.findall(text_in)
        for key in keys:
            value = key_dict.get(param, '<??%s??>' % param)
            text_out = text_out.replace('${%s}' % param, '%s' % value)
        print '**13010** text_in = "%s"' % text_in
        print '**13020** text_out = "%s"' % text_out
        ##match_obj.groups()
    


##    TestEmbedPython('test_update_live').run()
    TestVariableBatch('test_variable_batch2').run()
    ## TestOuterFooInnerBar('test_01').run()
    ## TestJane('test_alison_01').run()
##    TestSquareNumber('test_square_number').run()
    print '\n**14500** Finished.'
    

