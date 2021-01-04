#!/usr/bin/env python3

import sys
import getopt

from typing import List

import compiler


def usage():
    print('Usage: python main.py [-h] [-o output_name] [-t target] [-I include_dirs] [-D<macro<=value>>] filename')
    print('\t-h, --help: 语法帮助')
    print('\t-o, --output=: 输出的文件名')
    print('\t-t, --target=: LLVM IR 目标平台架构，默认为 x86_64-pc-linux-gnu')
    print('\t-I, --include=: 头文件搜寻目录，允许多个')
    print('\t-D<macro<=value>>: 定义宏 macro，值设为 value，允许定义多个宏')


if __name__ == '__main__':
    pass_args = dict()
    opts, args = getopt.getopt(sys.argv[1:], "ho:t:I:D:", ["help", "output=", "target=", 'include=', 'macro='])
    if ('-h', '') in opts or ('--help', '') in opts:
        usage()
        sys.exit(0)
    if len(args) != 1:
        print('输入文件未指定或过多。')
        sys.exit(1)
    pass_args['input_file'] = args[0]
    pass_args['output_file'] = \
        '.'.join((args[0].split('.'))[0:-1]) + '.ll' if args[0].count('.') != 0 else args[0] + '.ll'
    pass_args['target_arch'] = 'x86_64-pc-linux-gnu'
    pass_args['include_dirs'] = list()
    pass_args['macros'] = dict()
    for opt_name, opt_value in opts:
        if opt_name in ('-h', '--help'):
            pass # impossible
        elif opt_name in ('-o', '--output'):
            pass_args['output_file'] = opt_value
        elif opt_name in ('-t', '--target'):
            pass_args['target_arch'] = opt_value
        elif opt_name in ('-I', '--include'):
            pass_args['include_dirs'].append(opt_value)
        elif opt_name == '-D':
            l: List[str] = opt_value.split('=')
            macro_name = l[0]
            if macro_name == '':
                print('Macro name could not be empty.')
                sys.exit(1)
            pass_args['macros'][macro_name] = None
            if len(l) > 1:
                macro_value = '='.join(l[1:])
                pass_args['macros'][macro_name] = macro_value
    compiler.compile(**pass_args)
