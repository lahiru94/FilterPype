import os
import optparse
import sys

from rst_modules import default_mods

class BuildRST(object):
    def get_classes(self):
        """ Get classes from py files
        """
        pass
    
    def get_module_list(self, modules):
        
        mod_class_dict = {}
        for module in modules:
            class_list = []
            try:
                # Import the module so we can use it
                exec "import " + module
                mod = eval(module)
                all_classes = mod.__dict__
                for clss in all_classes:
                    if clss[0] == '_':
                        # Sphinx won't build docs for private classes or methods
                        # so ignore them
                        pass
                    elif isinstance(all_classes[clss], type):
                        class_list.append(clss)
                    #else:
                        #print all_classes[clss]
            except ImportError, err:
                raise ImportError(err.__str__() + '. Please ensure that ' + \
                                  'your PYTHONPATH is configured according ' + \
                                  'to how modules are referenced in ' + \
                                  'rst_modules.py.')
            class_list.sort()
            mod_class_dict[module] = class_list
        return mod_class_dict
    
    def make_api_rst(self, class_dict):
        hdr_str = '.. _API:\n\nAPI\n===\n\nContents:\n\n.. toctree::\n   :maxdepth: 2\n\n'
        toctree_str = ''
        for mod in class_dict:
            print "Adding module %s to API" %mod
            toctree_str += '   ' + mod.split('.')[-1] + '\n'
        
        indices_tables_str = '\nIndices and tables\n==================\n\n* :ref:`genindex`\n* :ref:`modindex`\n* :ref:`search`'
        
        api_rst_str = hdr_str + toctree_str + indices_tables_str
        return api_rst_str

    def make_module_rst(self, mod_dict):
        rst_dict = {}
        for module in mod_dict:
            print "Building module:", module
            hdr_str = 'Module ' + module
            hdr_str += '\n'+ '='*(len(module)+7) + '\n\n.. toctree::'
            hdr_str += '\n   :maxdepth: 2\n\n'
        
            toctree_str = ''
            for clss in mod_dict[module]:
                print "\t- class:", clss
                toctree_str += '   ' + clss + '\n'
            
            rst_dict[module] = hdr_str + toctree_str
        return rst_dict
    
    def make_class_rst(self, class_dict):
        class_rst_dict = {}
        for module in class_dict:
            for clss in class_dict[module]:
                hdr_str = 'Class ' + clss + '\n' + '='*(len(clss) + 6) + '\n'
                automod_str = '.. automodule:: ' + module + '\n\n'
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
    class_dict = rst_builder.get_module_list(mod_list)
    api_rst = rst_builder.make_api_rst(class_dict)
    module_rst_dict = rst_builder.make_module_rst(class_dict)
    class_rst_dict = rst_builder.make_class_rst(class_dict)
    
    # The API file path
    api_file_name = os.path.join(build_dir, 'api_autogen.rst')
    
    # Write API file
    api_fd = open(api_file_name, 'w')
    api_fd.write(api_rst)
    api_fd.close()
    
    # Write Module files
    for mod in module_rst_dict:
        mod_file_fd = open(
            os.path.join(
                build_dir, mod.split('.')[-1]+'_autogen.rst'), 'w')
        mod_file_fd.write(module_rst_dict[mod])
        mod_file_fd.close()
    
    # Write Class files
    for clss in class_rst_dict:
        clss_file_fd = open(os.path.join(build_dir, clss+'_autogen.rst'), 'w')
        clss_file_fd.write(class_rst_dict[clss])
        clss_file_fd.close()

    print "Finished"
