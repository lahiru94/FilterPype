# embed.py
# See Python Cookbook, 2nd ed., p.591

import sys
import filterpype

class PretendModule(object):
    modules = {}
    
    def __getattr__(self, name):
        if name == 'pype':
            name = 'singleton_pype'
        return self.modules.get(name, 'Module "%s" not found' % name)
    
sys.modules[__name__] = PretendModule()
  

# Return same module each time -- 