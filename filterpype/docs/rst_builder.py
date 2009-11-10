import os
import optparse
import sys
import inspect

from rst_modules import default_mods

class BuildRST(object):
    
    autogen_filename = '_autogen'
    
    def get_classes(self):
        """ Get classes from py files
        """
        pass
    
    def get_module_list(self, modules):
        
        mod_class_function_m = {}
        for module in modules:
            class_list = []
            function_list = []
            try:
                # Import the module so we can use it
                exec "import " + module + " as curr_mod"
                dir_l = dir(curr_mod)
                for cf in dir_l:
                    exec 'cf_mod = inspect.getmodule(curr_mod.' + cf + ')'
                    if dir_l == dir(cf_mod):
                        exec "is_class = isinstance(curr_mod." + cf + ", type)"
                        print 'is_class', is_class
                        exec "is_func = inspect.isfunction(curr_mod." + cf + ")"
                        if is_class:
                            print 'success'
                            class_list.append(cf)
                        elif is_func:
                            function_list.append(cf)
            except:
                pass
                #mod = eval(module)
                #all_classes = mod.__dict__
                #for clss in all_classes:
                    #if clss[0] == '_':
                        ## Sphinx won't build docs for private classes or methods
                        ## so ignore them
                        #pass
                    #elif isinstance(all_classes[clss], type):
                        #class_list.append(clss)
                    ##else:
                        ##print all_classes[clss]
            #except ImportError, err:
                #raise ImportError(err.__str__() + '. Please ensure that ' + \
                                  #'your PYTHONPATH is configured according ' + \
                                  #'to how modules are referenced in ' + \
                                  #'rst_modules.py.')
            #class_list.sort()
            #mod_class_dict[module] = class_list
            class_list.sort()
            function_list.sort()
            mod_class_function_m[module] = {'classes':class_list, \
                                            'functions':function_list}
        return mod_class_function_m
    
    def make_api_rst(self, modules):
        hdr_str = '.. _API:\n\nAPI\n===\n\nContents:\n\n.. toctree::\n   :maxdepth: 2\n\n'
        toctree_str = ''
        for mod in modules:
            print "Adding module %s to API" %mod
            toctree_str += '   ' + mod.split('.')[-1] + \
                        self.autogen_filename + '\n'
        
        indices_tables_str = '\nIndices and tables\n==================\n\n* :ref:`genindex`\n* :ref:`modindex`\n* :ref:`search`'
        
        api_rst_str = hdr_str + toctree_str + indices_tables_str
        return api_rst_str

    def make_module_rst(self, mod_dict):
        rst_dict = {}
        for k, v in mod_dict.items():
            print "Building module:", k
            hdr_str = 'Module ' + k
            hdr_str += '\n'+ '='*(len(k)+7) + '\n\n .. automodule::\n ' + k + \
                    '\n\n.. toctree::'
            hdr_str += '\n   :maxdepth: 2\n\n'
        
            toctree_str = ''
            for clss in v['classes']:
                print "\t- class:", clss
                toctree_str += '   ' + clss + self.autogen_filename + '\n'
            func_str = ''
            if v['functions']:
                for func in v['functions']:
                    print "\t- function:", func
                    func_str += self.make_function_str(k, func)
            rst_dict[k] = hdr_str + toctree_str + func_str
        return rst_dict
    
    def make_function_str(self, module, func):
        return '.. autofunction:: ' + func + '\n\n'
    
    def make_class_rst(self, class_function_m):
        class_rst_dict = {}
        for k, v in class_function_m.items():
            for clss in (v['classes']):
                hdr_str = 'Class ' + clss + '\n' + '='*(len(clss) + 6) + '\n'
                automod_str = '.. automodule:: ' + k + '\n\n'
                auto_clss_str = '.. autoclass:: ' + clss + '\n   :members:'
                auto_clss_str += '\n   :show-inheritance:\n'
                if clss not in class_rst_dict.keys():
                    class_rst_dict[clss] = hdr_str+automod_str+auto_clss_str
        return class_rst_dict
    
if __name__ == '__main__':
    # optparse things for getting the user provided arguments:
    # build_dir - is the build directory
    # module_list - are the modules to build
    build_dir = '.'
    parser = optparse.OptionParser()
    parser.add_option('-b', '--build-dir', dest='build_dir',
                      help='directory to put the rst files into')
    (options, args) = parser.parse_args(sys.argv)
    if not os.path.exists(build_dir):
        print "Oops, not a valid build directory!"
        sys.exit(0)
    
    #if args[1:] < 1:
        #if default_mods < 1:
            #print "You need to supply module names"
            #sys.exit(0)
        #else:
            #print "**** Warning! Using default module list which may not be up to date"
    #else:
    mod_list = args[1:]
    mod_list.extend(default_mods)
    if len(mod_list) < 1:
        print "No modules specified!"
        sys.exit(0)
    else:
        print "Building the docs for the following modules", mod_list

    rst_builder = BuildRST()
    #mod_list = ['filterpype.data_filter', 'filterpype.data_fltr_base',
                #'filterpypefds.data_fltr_fds', 'filterpypefds.ppln_fds9']
    
    # Get the various module and class information required
    class_function_m = rst_builder.get_module_list(mod_list)
    api_rst = rst_builder.make_api_rst(mod_list)
    module_rst_dict = rst_builder.make_module_rst(class_function_m)
    class_rst_dict = rst_builder.make_class_rst(class_function_m)
    
    # The API file path
    api_file_name = os.path.join(build_dir, 'api' + \
                                 rst_builder.autogen_filename + '.rst')
    
    # Write API file
    api_fd = open(api_file_name, 'w')
    api_fd.write(api_rst)
    api_fd.close()
    
    # Write Module files
    for mod in module_rst_dict:
        mod_file_fd = open(
            os.path.join(
                build_dir, mod.split('.')[-1]+rst_builder.autogen_filename + \
                '.rst'), 'w')
        mod_file_fd.write(module_rst_dict[mod])
        mod_file_fd.close()
    
    # Write Class files
    for clss in class_rst_dict:
        clss_file_fd = open(os.path.join(build_dir, clss + \
                                rst_builder.autogen_filename + '.rst'), 'w')
        clss_file_fd.write(class_rst_dict[clss])
        clss_file_fd.close()

    print "Finished"
