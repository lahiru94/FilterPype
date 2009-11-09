'''\
__init__.py for filterpype.pypes package
'''

import filterpype.filter_utils as fut

__all__ = ['pypes_basic']

pypes_basic = dict(fut.pypes_for_dict_gen(fut.abs_dir_of_file(__file__)))
##print '**10542** Basic pypes', [key for key in pypes.iterkeys()]

if __name__ == '__main__':  #pragma: nocover
    print fut.all_files('*.pype', fut.abs_dir_of_file(__file__)).next()
